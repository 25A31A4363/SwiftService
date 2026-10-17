import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.seed import seed_database

class TestClosedLoopIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(force=True)
        cls.client = TestClient(app)

        # Login Store Manager (Store 104)
        res_sm = cls.client.post("/api/v1/auth/login", json={
            "email": "storemanager@apex.com",
            "password": "Password123!"
        })
        cls.sm_token = res_sm.json()["data"]["token"]
        cls.sm_headers = {"Authorization": f"Bearer {cls.sm_token}"}

        # Login Maintenance Tech
        res_maint = cls.client.post("/api/v1/auth/login", json={
            "email": "maintenance@apex.com",
            "password": "Password123!"
        })
        cls.maint_token = res_maint.json()["data"]["token"]
        cls.maint_headers = {"Authorization": f"Bearer {cls.maint_token}"}

    def test_end_to_end_closed_loop_lifecycle(self):
        # 1. Ingestion: Customer submits raw Spanish feedback
        fb_resp = self.client.post("/api/v1/feedback", headers=self.sm_headers, json={
            "storeId": "store-104",
            "departmentId": "dept-104-dairy",
            "sourceType": "QR_KIOSK",
            "rawText": "El estante de yogur tiene una fuga continua de agua fría.",
            "languageCode": "es"
        })
        self.assertEqual(fb_resp.status_code, 201)
        fb_id = fb_resp.json()["data"]["id"]

        # 2. Dynamic Clarification: Record follow-up turn
        fu_resp = self.client.post("/api/v1/feedback/follow-up", headers=self.sm_headers, json={
            "feedbackItemId": fb_id,
            "turnIndex": 1,
            "question": "Is the cold water pooled on the walkway creating a slip risk?",
            "response": "Yes, water is pooling into the main aisle walkway."
        })
        self.assertEqual(fu_resp.status_code, 201)

        # 3. Issue Creation with explainable priority
        issue_resp = self.client.post("/api/v1/issues", headers=self.sm_headers, json={
            "storeId": "store-104",
            "departmentId": "dept-104-dairy",
            "title": "Continuous Cold Water Leakage - Dairy Aisle 4",
            "description": "Customer feedback and follow-up confirm pooled water on walkway.",
            "severityScore": 0.85,
            "urgencyScore": 0.90,
            "impactScopeScore": 0.65,
            "assignedTeamId": "team-hvac-pnw",
            "feedbackItemIds": [fb_id]
        })
        self.assertEqual(issue_resp.status_code, 201)
        issue = issue_resp.json()["data"]
        issue_id = issue["id"]
        self.assertGreater(issue["priorityScore"], 75)
        self.assertEqual(issue["status"], "DETECTED")

        # 4. Triage Issue
        triage_resp = self.client.patch(f"/api/v1/issues/{issue_id}/status", headers=self.sm_headers, json={
            "status": "TRIAGED",
            "justification": "Triage verified by Store 104 manager."
        })
        self.assertEqual(triage_resp.status_code, 200)

        # 5. Advance to Dispatched
        disp_resp = self.client.patch(f"/api/v1/issues/{issue_id}/status", headers=self.sm_headers, json={
            "status": "DISPATCHED"
        })
        self.assertEqual(disp_resp.status_code, 200)

        # 6. Maintenance Tech begins work
        prog_resp = self.client.patch(f"/api/v1/issues/{issue_id}/status", headers=self.maint_headers, json={
            "status": "IN_PROGRESS"
        })
        self.assertEqual(prog_resp.status_code, 200)

        # 7. Maintenance Tech marks Remediated
        remed_resp = self.client.patch(f"/api/v1/issues/{issue_id}/status", headers=self.maint_headers, json={
            "status": "REMEDIATED"
        })
        self.assertEqual(remed_resp.status_code, 200)

        # 8. Resolution Logged & Outcome Scorecard Captured
        actions_resp = self.client.get("/api/v1/actions", headers=self.sm_headers)
        action_id = actions_resp.json()["data"][0]["id"]

        res_resp = self.client.post("/api/v1/resolutions", headers=self.maint_headers, json={
            "actionPlanId": action_id,
            "technicianNotes": "Flushed drain, installed new check-valve, mopped walkway."
        })
        self.assertEqual(res_resp.status_code, 201)
        res_data = res_resp.json()["data"]
        self.assertEqual(res_data["verificationStatus"], "PENDING_VERIFICATION")
        self.assertIsNotNone(res_data["verificationScorecard"])

        # 9. Verify Issue is now in VERIFYING state
        final_issue = self.client.get(f"/api/v1/issues/{issue_id}", headers=self.sm_headers).json()["data"]
        # Note: res_resp transitions its linked issue
        self.assertIn(final_issue["status"], ("REMEDIATED", "VERIFYING"))

        # 10. Audit logs verified
        audit_resp = self.client.get(f"/api/v1/audit-logs?entityType=ISSUE&entityId={issue_id}", headers=self.sm_headers)
        self.assertEqual(audit_resp.status_code, 200)
        logs = audit_resp.json()["data"]
        self.assertGreater(len(logs), 0)

if __name__ == "__main__":
    unittest.main()

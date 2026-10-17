import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.seed import seed_database

class TestDomainApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(force=True)
        cls.client = TestClient(app)

        # Login Org Admin
        res_admin = cls.client.post("/api/v1/auth/login", json={
            "email": "orgadmin@apex.com",
            "password": "Password123!"
        })
        cls.admin_token = res_admin.json()["data"]["token"]
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}

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

    def test_get_organizations(self):
        resp = self.client.get("/api/v1/organizations", headers=self.admin_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertGreater(len(data), 0)
        self.assertEqual(data[0]["code"], "APEX")

    def test_get_stores_scoping(self):
        # Admin gets all 4 stores
        resp_admin = self.client.get("/api/v1/stores", headers=self.admin_headers)
        self.assertEqual(len(resp_admin.json()["data"]), 4)

        # Store Manager Store 104 only gets their 1 store
        resp_sm = self.client.get("/api/v1/stores", headers=self.sm_headers)
        self.assertEqual(len(resp_sm.json()["data"]), 1)
        self.assertEqual(resp_sm.json()["data"][0]["id"], "store-104")

    def test_submit_multilingual_feedback(self):
        # Spanish submission
        resp_es = self.client.post("/api/v1/feedback", headers=self.sm_headers, json={
            "storeId": "store-104",
            "departmentId": "dept-104-dairy",
            "sourceType": "QR_KIOSK",
            "rawText": "El piso en lácteos está mojado y resbaladizo cerca de la nevera 4.",
            "languageCode": "es"
        })
        self.assertEqual(resp_es.status_code, 201)
        data = resp_es.json()["data"]
        self.assertEqual(data["languageCode"], "es")
        self.assertFalse(data["hasPii"])

        # Submission with PII (phone number)
        resp_pii = self.client.post("/api/v1/feedback", headers=self.sm_headers, json={
            "storeId": "store-104",
            "sourceType": "CUSTOMER_VOICE",
            "rawText": "Call customer John back at 206-555-0199 regarding spoiled yogurt",
            "languageCode": "en"
        })
        self.assertEqual(resp_pii.status_code, 201)
        self.assertTrue(resp_pii.json()["data"]["hasPii"])

    def test_issue_lifecycle_and_priority_calculation(self):
        # Create an issue
        resp = self.client.post("/api/v1/issues", headers=self.sm_headers, json={
            "storeId": "store-104",
            "departmentId": "dept-104-dairy",
            "title": "Severe Condensation Puddle in Dairy Aisle",
            "description": "Standing water from cooler 4B creating active hazard.",
            "severityScore": 0.90,
            "urgencyScore": 0.85,
            "impactScopeScore": 0.70
        })
        self.assertEqual(resp.status_code, 201)
        issue = resp.json()["data"]
        # Priority = round(100 * (0.40*0.90 + 0.35*0.85 + 0.25*0.70)) = round(100 * (0.36 + 0.2975 + 0.175)) = round(83.25) = 83
        self.assertEqual(issue["priorityScore"], 83)
        self.assertEqual(issue["priorityTier"], "P2_HIGH")
        self.assertEqual(issue["status"], "DETECTED")

        issue_id = issue["id"]

        # Valid transition: DETECTED -> TRIAGED
        resp_triage = self.client.patch(f"/api/v1/issues/{issue_id}/status", headers=self.sm_headers, json={
            "status": "TRIAGED",
            "justification": "Verified by store floor lead."
        })
        self.assertEqual(resp_triage.status_code, 200)
        self.assertEqual(resp_triage.json()["data"]["status"], "TRIAGED")

        # Invalid transition: TRIAGED -> IN_PROGRESS (Must go to DISPATCHED first)
        resp_invalid = self.client.patch(f"/api/v1/issues/{issue_id}/status", headers=self.sm_headers, json={
            "status": "IN_PROGRESS"
        })
        self.assertEqual(resp_invalid.status_code, 422)

    def test_action_routing_override_and_audit_log(self):
        # Fetch actions
        resp_actions = self.client.get("/api/v1/actions", headers=self.sm_headers)
        self.assertEqual(resp_actions.status_code, 200)
        actions = resp_actions.json()["data"]
        self.assertGreater(len(actions), 0)
        action_id = actions[0]["id"]

        # Manager overrides routing to Janitorial
        resp_override = self.client.post(f"/api/v1/actions/{action_id}/override", headers=self.sm_headers, json={
            "newTargetTeamId": "team-janitorial-104",
            "overrideReason": "Immediate floor cleanup takes precedence before vendor arrives."
        })
        self.assertEqual(resp_override.status_code, 200)
        updated = resp_override.json()["data"]
        self.assertEqual(updated["targetTeamId"], "team-janitorial-104")
        self.assertEqual(updated["approvalStatus"], "OVERRIDDEN")

        # Verify audit log recorded the override
        resp_audit = self.client.get(f"/api/v1/audit-logs?entityType=ACTION_PLAN&entityId={action_id}", headers=self.sm_headers)
        self.assertEqual(resp_audit.status_code, 200)
        logs = resp_audit.json()["data"]
        self.assertTrue(any(l["action"] == "ROUTING_OVERRIDE" for l in logs))

    def test_maintenance_resolution_flow(self):
        # Fetch seeded action
        resp_actions = self.client.get("/api/v1/actions", headers=self.admin_headers)
        action_id = resp_actions.json()["data"][0]["id"]
        issue_id = resp_actions.json()["data"][0]["issueId"]

        # Tech submits resolution
        resp_res = self.client.post("/api/v1/resolutions", headers=self.maint_headers, json={
            "actionPlanId": action_id,
            "technicianNotes": "Cleaned overflow pan, sanitized area, and tested drainage line."
        })
        self.assertEqual(resp_res.status_code, 201)
        res_data = resp_res.json()["data"]
        self.assertEqual(res_data["verificationStatus"], "PENDING_VERIFICATION")

        # Verify issue status transitioned to VERIFYING
        resp_issue = self.client.get(f"/api/v1/issues/{issue_id}", headers=self.admin_headers)
        self.assertEqual(resp_issue.json()["data"]["status"], "VERIFYING")

if __name__ == "__main__":
    unittest.main()

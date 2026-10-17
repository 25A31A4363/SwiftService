"""
R5 Operational Intelligence Platform - Phase 12 Post-Intervention Outcome Measurement Tests
Tests cover:
1. Baseline snapshot calculation
2. Intervention timestamp and details
3. Post-intervention observation window
4. Deterministic comparison (BEFORE vs AFTER)
5. Outcome states: Improved, No significant change, Worsened, Inconclusive
6. Insufficiency guard: "outcome cannot yet be determined." (no fabricated improvements)
7. Evidence lineage and citations
8. Confidence scoring
9. Outcome dashboard API and statistics
10. RBAC permissions
"""

import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import get_connection
from backend.app.db.seed import seed_database
from backend.app.core.security import create_access_token


class TestPhase12OutcomeMeasurement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(force=True)
        cls.client = TestClient(app)

        # Tokens
        cls.admin_token = create_access_token({
            "userId": "usr-admin",
            "email": "orgadmin@apex.com",
            "role": "ORGANIZATION_ADMIN",
            "organizationId": "org-apex-01"
        })
        cls.store_token = create_access_token({
            "userId": "usr-store",
            "email": "storemanager@apex.com",
            "role": "STORE_MANAGER",
            "organizationId": "org-apex-01",
            "storeId": "store-104",
            "regionId": "reg-pnw-01"
        })
        cls.viewer_token = create_access_token({
            "userId": "usr-viewer",
            "email": "viewer@apex.com",
            "role": "VIEWER",
            "organizationId": "org-apex-01",
            "storeId": "store-104"
        })

    def _headers(self, token: str):
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    # -------------------------------------------------------------------------
    # 1. Baseline Snapshot Calculation
    # -------------------------------------------------------------------------
    def test_baseline_snapshot_deterministic_calculation(self):
        """
        Verify that capturing a baseline snapshot correctly measures pre-intervention
        complaint volume, arrival frequency per day, avg severity, and locations.
        """
        res = self.client.post("/api/v1/outcomes/issues/issue-104-892/baseline", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        self.assertIn("windowStart", data)
        self.assertIn("windowEnd", data)
        self.assertGreater(data["windowHours"], 0.0)
        self.assertGreaterEqual(data["complaintVolume"], 1)
        self.assertGreater(data["issueFrequencyPerDay"], 0.0)
        self.assertGreaterEqual(data["avgSeverity"], 0.0)
        self.assertLessEqual(data["avgSeverity"], 1.0)
        self.assertGreaterEqual(data["affectedLocationsCount"], 1)
        self.assertIsInstance(data["affectedLocations"], list)
        self.assertIsInstance(data["sampleCitations"], list)

    # -------------------------------------------------------------------------
    # 2. Outcome State: IMPROVED (When complaints stop after intervention)
    # -------------------------------------------------------------------------
    def test_outcome_improved_when_complaints_curtailed(self):
        """
        Issue 104-892 (Dairy Cooler Condensate Repair):
        Had baseline complaints. Resolved and mopped walkway.
        Over 48h post-intervention observation window, 0 recurrence occurred.
        Status MUST be 'Improved', frequency change -100%, confidence >= 0.85.
        """
        res = self.client.get("/api/v1/outcomes/issues/issue-104-892", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        self.assertEqual(data["outcomeStatus"], "Improved")
        self.assertEqual(data["comparison"]["recurrenceCount"], 0)
        self.assertEqual(data["comparison"]["volumeChangePct"], -100.0)
        self.assertEqual(data["comparison"]["frequencyChangePct"], -100.0)
        self.assertGreaterEqual(data["confidence"], 0.85)
        self.assertIn("Operational problem resolved", data["statusMessage"])
        self.assertTrue(data["observationWindow"]["isWindowSufficient"])

    # -------------------------------------------------------------------------
    # 3. Outcome State: NO SIGNIFICANT CHANGE (When complaint rate persists)
    # -------------------------------------------------------------------------
    def test_outcome_no_significant_change_when_rate_persists(self):
        """
        Issue 104-893 (POS Checkout Scanner):
        Intervention performed, but customer reports continued at roughly
        the same arrival frequency (-33% / within variation band) with recurring events.
        Status MUST be 'No significant change'.
        """
        res = self.client.get("/api/v1/outcomes/issues/issue-104-893", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        self.assertEqual(data["outcomeStatus"], "No significant change")
        self.assertGreater(data["comparison"]["recurrenceCount"], 0)
        self.assertIn("persists without significant change", data["statusMessage"])
        self.assertGreaterEqual(data["confidence"], 0.65)
        self.assertTrue(data["observationWindow"]["isWindowSufficient"])

    # -------------------------------------------------------------------------
    # 4. Outcome State: WORSENED (When complaints or severity surge)
    # -------------------------------------------------------------------------
    def test_outcome_worsened_when_complaints_surge(self):
        """
        Issue 104-894 (Restroom Valve Pressure Surge):
        Intervention failed, water pipe burst, complaints tripled (+200% arrival rate),
        severe puddles and screaming customers reported.
        Status MUST be 'Worsened', with high confidence in the failure.
        """
        res = self.client.get("/api/v1/outcomes/issues/issue-104-894", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        self.assertEqual(data["outcomeStatus"], "Worsened")
        self.assertGreaterEqual(data["comparison"]["frequencyChangePct"], 25.0)
        self.assertGreaterEqual(data["comparison"]["recurrenceCount"], 3)
        self.assertIn("worsened", data["statusMessage"].lower())
        self.assertGreaterEqual(data["confidence"], 0.80)

    # -------------------------------------------------------------------------
    # 5. Outcome State: INCONCLUSIVE (Insufficient Observation Window Guard)
    # -------------------------------------------------------------------------
    def test_outcome_inconclusive_when_observation_window_immature(self):
        """
        Issue 104-895 (Produce Misting Line Clog):
        Resolved only 30 minutes ago (0.5 hours).
        The system MUST NOT fabricate improvements.
        Because observation window is < 12.0 hours, status MUST be 'Inconclusive'
        and status message MUST BE EXACTLY: 'outcome cannot yet be determined.'
        """
        res = self.client.get("/api/v1/outcomes/issues/issue-104-895", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        self.assertEqual(data["outcomeStatus"], "Inconclusive")
        self.assertEqual(data["statusMessage"], "outcome cannot yet be determined.")
        self.assertFalse(data["observationWindow"]["isWindowSufficient"])
        self.assertLess(data["observationWindow"]["windowHours"], 12.0)
        # Confidence must reflect uncertainty
        self.assertLessEqual(data["confidence"], 0.45)

    # -------------------------------------------------------------------------
    # 6. Insufficiency Guard: Missing Intervention
    # -------------------------------------------------------------------------
    def test_outcome_inconclusive_when_issue_has_no_intervention(self):
        """
        Creating a new open issue with no resolution/intervention.
        Outcome measurement must not invent an outcome:
        Must return 'Inconclusive' with 'outcome cannot yet be determined.'
        """
        # Create un-intervened issue
        create_res = self.client.post("/api/v1/issues", json={
            "storeId": "store-104",
            "title": "Un-remediated Bakery Display Rack Wobble",
            "description": "Loose screw on bottom shelf.",
            "severityScore": 0.4,
            "urgencyScore": 0.4,
            "impactScopeScore": 0.3
        }, headers=self._headers(self.store_token))
        self.assertEqual(create_res.status_code, 201)
        new_issue_id = create_res.json()["data"]["id"]

        eval_res = self.client.post(f"/api/v1/outcomes/issues/{new_issue_id}/evaluate", headers=self._headers(self.store_token))
        self.assertEqual(eval_res.status_code, 200)
        data = eval_res.json()["data"]

        self.assertEqual(data["outcomeStatus"], "Inconclusive")
        self.assertEqual(data["statusMessage"], "outcome cannot yet be determined.")
        self.assertFalse(data["observationWindow"]["isWindowSufficient"])

    # -------------------------------------------------------------------------
    # 7. Evidence Citations and Traceability
    # -------------------------------------------------------------------------
    def test_evidence_citations_audit_lineage(self):
        """
        Outcome measurements must generate structured evidence across:
        - BASELINE: quotes and arrival stats
        - INTERVENTION: technician notes and timestamps
        - POST_OBSERVATION: post-telemetry quotes
        - DETERMINATION: mathematical proof
        """
        res = self.client.get("/api/v1/outcomes/issues/issue-104-892", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        evidence = data["evidence"]
        self.assertGreaterEqual(len(evidence), 3)

        stages = [e["stage"] for e in evidence]
        self.assertIn("BASELINE", stages)
        self.assertIn("INTERVENTION", stages)
        self.assertIn("POST_OBSERVATION", stages)
        self.assertIn("DETERMINATION", stages)

        for item in evidence:
            self.assertIn("title", item)
            self.assertIn("claim", item)
            self.assertIn("timestamp", item)
            self.assertIn("sourceMetadata", item)

    # -------------------------------------------------------------------------
    # 8. Deterministic SLA Compliance & Latency Measurements
    # -------------------------------------------------------------------------
    def test_deterministic_sla_compliance_and_latencies(self):
        """
        Check that response time, resolution time, and SLA compliance
        are calculated accurately without fabrication.
        """
        res = self.client.get("/api/v1/outcomes/issues/issue-104-892", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        c = data["comparison"]

        self.assertIsNotNone(c["resolutionTimeMinutes"])
        self.assertGreater(c["resolutionTimeMinutes"], 0)
        self.assertIsInstance(c["slaCompliance"], bool)

    # -------------------------------------------------------------------------
    # 9. Outcome Dashboard Endpoint Summary
    # -------------------------------------------------------------------------
    def test_outcomes_dashboard_summary_endpoint(self):
        """
        GET /api/v1/outcomes/dashboard returns aggregate metrics, counts for all
        4 outcome states, improvement rate, SLA compliance, and category breakdown.
        """
        res = self.client.get("/api/v1/outcomes/dashboard", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        self.assertGreaterEqual(data["totalResolvedIssues"], 4)
        self.assertGreaterEqual(data["improvedCount"], 1)
        self.assertGreaterEqual(data["noChangeCount"], 1)
        self.assertGreaterEqual(data["worsenedCount"], 1)
        self.assertGreaterEqual(data["inconclusiveCount"], 1)

        self.assertGreater(data["improvedRatePct"], 0.0)
        self.assertGreater(data["slaComplianceRatePct"], 0.0)
        self.assertIn("categoryBreakdown", data)
        self.assertIsInstance(data["outcomes"], list)

    # -------------------------------------------------------------------------
    # 10. Filter Outcomes by Status
    # -------------------------------------------------------------------------
    def test_filter_outcomes_by_status(self):
        """
        GET /api/v1/outcomes?outcomeStatus=Improved returns only Improved outcomes.
        GET /api/v1/outcomes?outcomeStatus=Inconclusive returns only Inconclusive outcomes.
        """
        res_imp = self.client.get("/api/v1/outcomes?outcomeStatus=Improved", headers=self._headers(self.store_token))
        self.assertEqual(res_imp.status_code, 200)
        for o in res_imp.json()["data"]:
            self.assertEqual(o["outcomeStatus"], "Improved")

        res_inc = self.client.get("/api/v1/outcomes?outcomeStatus=Inconclusive", headers=self._headers(self.store_token))
        self.assertEqual(res_inc.status_code, 200)
        for o in res_inc.json()["data"]:
            self.assertEqual(o["outcomeStatus"], "Inconclusive")
            self.assertEqual(o["statusMessage"], "outcome cannot yet be determined.")

    # -------------------------------------------------------------------------
    # 11. On-Demand Outcome Evaluation with Custom Observation Window
    # -------------------------------------------------------------------------
    def test_on_demand_simulation_with_custom_observation_window(self):
        """
        POST /api/v1/outcomes/issues/{id}/evaluate allows simulating observation window.
        When observation window is simulated to 48 hours for a newly resolved issue,
        it transitions from Inconclusive to a decisive outcome.
        """
        # Create fresh synthetic issue
        c_res = self.client.post("/api/v1/issues", json={
            "storeId": "store-104",
            "title": "Bakery Conveyor Oven Belt Sensor Glitch",
            "description": "Belt sensor intermittently pausing rack.",
            "severityScore": 0.5,
            "urgencyScore": 0.5,
            "impactScopeScore": 0.4
        }, headers=self._headers(self.store_token))
        self.assertEqual(c_res.status_code, 201)
        sim_issue_id = c_res.json()["data"]["id"]

        # Add resolution
        conn = get_connection()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            INSERT INTO resolutions (
                id, organization_id, issue_id, action_plan_id, technician_notes,
                resolved_by, resolved_at, verification_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING_VERIFICATION', ?, ?);
        """, (f"res-sim-{sim_issue_id[:8]}", "org-apex-01", sim_issue_id, "action-104-01", "Calibrated optical encoder", "usr-maint", now_iso, now_iso, now_iso))
        conn.commit()

        # Initial check without simulation: observation window is 0h -> Inconclusive
        init_res = self.client.get(f"/api/v1/outcomes/issues/{sim_issue_id}", headers=self._headers(self.store_token))
        self.assertEqual(init_res.status_code, 200)
        self.assertEqual(init_res.json()["data"]["outcomeStatus"], "Inconclusive")

        # Now simulate 48 hours observation
        sim_res = self.client.post(f"/api/v1/outcomes/issues/{sim_issue_id}/evaluate", json={
            "observationHours": 48.0,
            "minObservationHours": 12.0,
            "forceReevaluate": True
        }, headers=self._headers(self.store_token))
        self.assertEqual(sim_res.status_code, 200)
        data = sim_res.json()["data"]

        self.assertEqual(data["outcomeStatus"], "Improved")
        self.assertTrue(data["observationWindow"]["isWindowSufficient"])
        self.assertEqual(data["observationWindow"]["windowHours"], 48.0)
        self.assertIn("Operational problem resolved", data["statusMessage"])

    # -------------------------------------------------------------------------
    # 12. RBAC Permissions Enforcement
    # -------------------------------------------------------------------------
    def test_rbac_permissions_on_outcomes(self):
        """
        - Viewer role has read-only access to dashboard and outcomes.
        - Viewer role is forbidden from triggering evaluation (requires RESOLUTION_VERIFY).
        """
        # Viewer can read dashboard
        view_res = self.client.get("/api/v1/outcomes/dashboard", headers=self._headers(self.viewer_token))
        self.assertEqual(view_res.status_code, 200)

        # Viewer cannot evaluate
        eval_res = self.client.post("/api/v1/outcomes/issues/issue-104-892/evaluate", json={
            "observationHours": 24.0
        }, headers=self._headers(self.viewer_token))
        self.assertEqual(eval_res.status_code, 403)


if __name__ == "__main__":
    unittest.main()

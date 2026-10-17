"""
Phase 21: Complete End-to-End Retail Operational Demonstration Test Suite
Verifies the complete 15-stage R5 lifecycle:
RAW FEEDBACK -> AI UNDERSTANDING -> INVESTIGATION -> CLUSTER -> EMERGING ISSUE ->
PRIORITY -> EVIDENCE -> ROUTING -> ACTION -> RESOLUTION -> OUTCOME -> EXECUTIVE BRIEF
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import get_connection
from backend.app.services.demo_scenario_service import (
    DemoScenarioService,
    DEMO_ISSUE_ID,
    DEMO_CLUSTER_ID,
    DEMO_ALERT_ID,
    DEMO_ACTION_ID,
    DEMO_RESOLUTION_ID,
    DEMO_STORE_ID
)


@pytest.fixture
def db_conn():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        try:
            DemoScenarioService.reset_demonstration(conn)
        except Exception:
            pass
        conn.close()


@pytest.fixture
def auth_headers():
    client = TestClient(app)
    res = client.post("/api/v1/auth/login", json={
        "email": "storemanager@apex.com",
        "password": "Password123!"
    })
    assert res.status_code == 200
    token = res.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


class TestPhase21EndToEndDemonstration:
    """Test suite validating Phase 21 End-to-End Demonstration and closed-loop lifecycle."""

    def test_demo_scenario_definition(self):
        """Verify scenario definition metadata, store parameters, and 15 lifecycle stages."""
        scenario = DemoScenarioService.get_scenario_definition()
        assert scenario["scenarioId"] == "scenario-retail-coldchain-01"
        assert scenario["store"]["id"] == DEMO_STORE_ID
        assert len(scenario["lifecycleStages"]) == 15

        stage_codes = [s["code"] for s in scenario["lifecycleStages"]]
        expected_codes = [
            "BASELINE_SEEDING", "RAW_FEEDBACK_INGESTION", "AI_UNDERSTANDING",
            "INVESTIGATION_FOLLOWUP", "SEMANTIC_CLUSTERING", "EMERGING_ISSUE_DETECTION",
            "EXPLAINABLE_PRIORITIZATION", "TRACEABLE_EVIDENCE_LINEAGE", "DETERMINISTIC_ROUTING",
            "ACTION_PLAN_DISPATCH", "SLA_TRACKING", "TECHNICIAN_RESOLUTION",
            "SYSTEM_VERIFICATION", "OUTCOME_MEASUREMENT", "EXECUTIVE_BRIEF"
        ]
        assert stage_codes == expected_codes

    def test_full_lifecycle_demonstration_service(self, db_conn: sqlite3.Connection):
        """Execute the entire 15-stage demonstration and verify state progression and mathematical grounding."""
        result = DemoScenarioService.run_demonstration(conn=db_conn, auto_advance=True)

        assert result["status"] == "SUCCESS"
        assert result["totalStages"] == 15
        stages = result["stages"]
        assert len(stages) == 15

        # Verify all stages completed successfully
        for stage in stages:
            assert stage["status"] == "COMPLETED"
            assert stage["durationMs"] >= 0

        # Stage 1: Baseline Seeding
        st1 = stages[0]
        assert st1["stageCode"] == "BASELINE_SEEDING"
        assert st1["metrics"]["historicalRecordCount"] == 5

        # Stage 2: Ingestion
        st2 = stages[1]
        assert st2["stageCode"] == "RAW_FEEDBACK_INGESTION"
        assert st2["metrics"]["recordCount"] == 6
        assert st2["metrics"]["distinctLanguages"] >= 5

        # Stage 3: AI Understanding
        st3 = stages[2]
        assert st3["stageCode"] == "AI_UNDERSTANDING"
        assert st3["metrics"]["safetyHazardsDetected"] >= 4

        # Stage 4: Investigation Follow-up
        st4 = stages[3]
        assert st4["stageCode"] == "INVESTIGATION_FOLLOWUP"
        assert st4["metrics"]["questionTriggered"] == "clarify_location"
        assert "location" in st4["metrics"]["enrichedFields"]

        # Stage 5: Semantic Clustering
        st5 = stages[4]
        assert st5["stageCode"] == "SEMANTIC_CLUSTERING"
        assert st5["metrics"]["feedbackCount"] == 6
        assert st5["metrics"]["sourceChannelDiversity"] >= 5

        # Stage 6: Emerging Issue
        st6 = stages[5]
        assert st6["stageCode"] == "EMERGING_ISSUE_DETECTION"
        assert st6["metrics"]["velocityZScore"] > 1.80

        # Stage 7: Priority
        st7 = stages[6]
        assert st7["stageCode"] == "EXPLAINABLE_PRIORITIZATION"
        assert st7["metrics"]["priorityTier"] == "P1_CRITICAL"
        assert st7["metrics"]["isSafetyHazard"] is True

        # Stage 8: Evidence Lineage
        st8 = stages[7]
        assert st8["stageCode"] == "TRACEABLE_EVIDENCE_LINEAGE"
        assert st8["metrics"]["nodeCount"] > 10
        assert st8["metrics"]["verbatimCitationCount"] == 6

        # Stage 9: Routing
        st9 = stages[8]
        assert st9["stageCode"] == "DETERMINISTIC_ROUTING"
        assert st9["metrics"]["slaMinutes"] == 30
        assert "HVAC" in st9["metrics"]["primaryTeam"]

        # Stage 10: Action Plan Dispatch
        st10 = stages[9]
        assert st10["stageCode"] == "ACTION_PLAN_DISPATCH"
        assert st10["metrics"]["approvalStatus"] == "APPROVED"
        assert st10["metrics"]["newIssueStatus"] == "IN_PROGRESS"

        # Stage 11: SLA Tracking
        st11 = stages[10]
        assert st11["stageCode"] == "SLA_TRACKING"
        assert st11["metrics"]["slaCompliance"] == "SLA_MET"
        assert st11["metrics"]["actualResponseMinutes"] < 30

        # Stage 12: Resolution
        st12 = stages[11]
        assert st12["stageCode"] == "TECHNICIAN_RESOLUTION"
        assert st12["metrics"]["issueStatus"] == "VERIFYING"
        assert st12["metrics"]["restoredCabinetTempF"] == 36.0

        # Stage 13: System Verification
        st13 = stages[12]
        assert st13["stageCode"] == "SYSTEM_VERIFICATION"
        assert st13["metrics"]["verificationStatus"] == "VERIFIED"

        # Stage 14: Outcome Measurement
        st14 = stages[13]
        assert st14["stageCode"] == "OUTCOME_MEASUREMENT"
        assert st14["metrics"]["outcomeStatus"] == "Improved"
        assert st14["metrics"]["frequencyDeltaPct"] == -100.0
        assert st14["metrics"]["finalIssueStatus"] == "CLOSED"

        # Stage 15: Executive Brief
        st15 = stages[14]
        assert st15["stageCode"] == "EXECUTIVE_BRIEF"
        assert st15["metrics"]["groundedClaimCount"] > 0
        assert len(st15["data"]["executiveSummary"]) > 50

        # Verify Issue final state in database is CLOSED
        cur = db_conn.cursor()
        cur.execute("SELECT status, priority_tier FROM issues WHERE id = ?;", (DEMO_ISSUE_ID,))
        row = cur.fetchone()
        assert row is not None
        assert row["status"] == "CLOSED"
        assert row["priority_tier"] == "P1_CRITICAL"
        db_conn.commit()

    def test_demonstration_reset(self, db_conn: sqlite3.Connection):
        """Verify that reset cleans all demo entities and leaves no orphaned records."""
        # Run demo first to create entities
        DemoScenarioService.run_demonstration(conn=db_conn, auto_advance=True)
        db_conn.commit()

        # Reset
        reset_res = DemoScenarioService.reset_demonstration(db_conn)
        assert reset_res["status"] == "SUCCESS"
        db_conn.commit()

        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM issues WHERE id = ?;", (DEMO_ISSUE_ID,))
        assert cur.fetchone()[0] == 0

        cur.execute("SELECT COUNT(*) FROM issue_clusters WHERE id = ?;", (DEMO_CLUSTER_ID,))
        assert cur.fetchone()[0] == 0
        db_conn.commit()

        cur.execute("SELECT COUNT(*) FROM feedback_items WHERE id LIKE 'fb-demo-%';")
        assert cur.fetchone()[0] == 0

        cur.execute("SELECT COUNT(*) FROM alerts WHERE id = ?;", (DEMO_ALERT_ID,))
        assert cur.fetchone()[0] == 0

        cur.execute("SELECT COUNT(*) FROM action_plans WHERE id = ?;", (DEMO_ACTION_ID,))
        assert cur.fetchone()[0] == 0

        cur.execute("SELECT COUNT(*) FROM resolutions WHERE id = ?;", (DEMO_RESOLUTION_ID,))
        assert cur.fetchone()[0] == 0

    def test_demo_api_endpoints(self, auth_headers):
        """Test REST API endpoints for /api/v1/demo/*."""
        client = TestClient(app)

        # 1. GET Scenario
        res_scenario = client.get("/api/v1/demo/scenario", headers=auth_headers)
        assert res_scenario.status_code == 200
        json_sc = res_scenario.json()
        assert json_sc["success"] is True
        assert json_sc["data"]["scenarioId"] == "scenario-retail-coldchain-01"

        # 2. POST Run
        res_run = client.post("/api/v1/demo/run", json={"autoAdvance": True}, headers=auth_headers)
        assert res_run.status_code == 200
        json_run = res_run.json()
        assert json_run["success"] is True
        assert json_run["data"]["status"] == "SUCCESS"
        assert len(json_run["data"]["stages"]) == 15

        # 3. GET Status
        res_status = client.get("/api/v1/demo/status", headers=auth_headers)
        assert res_status.status_code == 200
        json_status = res_status.json()
        assert json_status["success"] is True
        assert json_status["data"]["isDemoActive"] is True
        assert json_status["data"]["issue"]["status"] == "CLOSED"

        # 4. POST Reset
        res_reset = client.post("/api/v1/demo/reset", headers=auth_headers)
        assert res_reset.status_code == 200
        assert res_reset.json()["success"] is True

        # 5. GET Status after reset
        res_status_after = client.get("/api/v1/demo/status", headers=auth_headers)
        assert res_status_after.status_code == 200
        assert res_status_after.json()["data"]["isDemoActive"] is False

import json
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import get_connection
from backend.app.db.seed import seed_database
from backend.app.services.brief_service import BriefService
from backend.app.core.security import create_access_token

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    seed_database(force=True)
    yield


@pytest.fixture
def auth_headers():
    token = create_access_token({
        "userId": "usr-ops",
        "email": "opsmanager@apex.com",
        "role": "OPERATIONS_MANAGER",
        "organizationId": "org-apex-01"
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers():
    token = create_access_token({
        "userId": "usr-viewer",
        "email": "viewer@apex.com",
        "role": "VIEWER",
        "organizationId": "org-apex-01",
        "storeId": "store-104"
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def maint_headers():
    token = create_access_token({
        "userId": "usr-maint",
        "email": "maintenance@apex.com",
        "role": "MAINTENANCE_TEAM",
        "organizationId": "org-apex-01",
        "storeId": "store-104"
    })
    return {"Authorization": f"Bearer {token}"}


class TestPhase14IntelligenceBriefs:
    def test_brief_contains_all_ten_sections(self, auth_headers):
        """Verify brief contains all 10 mandatory sections with rich deterministic payload."""
        response = client.post(
            "/api/v1/briefs/generate",
            json={"timeframeType": "DAILY"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()["data"]

        # 1. What changed
        assert "whatChanged" in data
        wc = data["whatChanged"]
        assert "feedbackVolumeDelta" in wc
        assert "feedbackVolumeChangePct" in wc
        assert "newIssuesCount" in wc
        assert "resolvedIssuesCount" in wc
        assert "slaComplianceRatePct" in wc
        assert "summaryText" in wc

        # 2. Emerging issues
        assert "emergingIssues" in data
        assert isinstance(data["emergingIssues"], list)

        # 3. Highest-priority issues
        assert "highestPriorityIssues" in data
        assert isinstance(data["highestPriorityIssues"], list)
        assert len(data["highestPriorityIssues"]) > 0
        p1_item = data["highestPriorityIssues"][0]
        assert "priorityScore" in p1_item
        assert "priorityTier" in p1_item
        assert "explainableSummary" in p1_item

        # 4. Affected locations
        assert "affectedLocations" in data
        assert isinstance(data["affectedLocations"], list)
        assert len(data["affectedLocations"]) > 0
        loc = data["affectedLocations"][0]
        assert "storeId" in loc
        assert "incidentCount" in loc
        assert "riskLevel" in loc

        # 5. Evidence
        assert "evidence" in data
        assert isinstance(data["evidence"], list)
        assert len(data["evidence"]) > 0
        ev = data["evidence"][0]
        assert "feedbackItemId" in ev
        assert "verbatimQuote" in ev

        # 6. Possible explanations/hypotheses
        assert "hypotheses" in data
        assert isinstance(data["hypotheses"], list)
        assert len(data["hypotheses"]) > 0
        hyp = data["hypotheses"][0]
        assert "hypothesis" in hyp
        assert "supportingObservations" in hyp

        # 7. Recommended actions
        assert "recommendedActions" in data
        assert isinstance(data["recommendedActions"], list)
        assert len(data["recommendedActions"]) > 0
        rec = data["recommendedActions"][0]
        assert "recommendation" in rec
        assert "targetTeamName" in rec
        assert "groundedRationale" in rec

        # 8. Uncertainty
        assert "uncertainties" in data
        assert isinstance(data["uncertainties"], list)
        assert len(data["uncertainties"]) > 0
        unc = data["uncertainties"][0]
        assert "area" in unc
        assert "description" in unc
        assert "missingInformation" in unc

        # 9. Unresolved issues
        assert "unresolvedIssues" in data
        assert isinstance(data["unresolvedIssues"], list)
        assert len(data["unresolvedIssues"]) > 0
        unres = data["unresolvedIssues"][0]
        assert "issueId" in unres
        assert "ageHours" in unres
        assert "slaStatus" in unres

        # 10. Outcome of previous interventions
        assert "interventionOutcomes" in data
        assert isinstance(data["interventionOutcomes"], list)
        assert len(data["interventionOutcomes"]) > 0
        outc = data["interventionOutcomes"][0]
        assert "outcomeStatus" in outc
        assert "statusMessage" in outc
        assert "confidence" in outc

    def test_grounding_numerical_claims_match_sql_analytics(self, auth_headers):
        """
        Critical constraint: The AI must NOT invent statistics.
        All numerical claims must originate from deterministic analytics.
        Cross-reference brief metrics directly against SQLite ground-truth.
        """
        conn = get_connection()
        cur = conn.cursor()

        response = client.post(
            "/api/v1/briefs/generate",
            json={"timeframeType": "DAILY"},
            headers=auth_headers
        )
        assert response.status_code == 200
        brief = response.json()["data"]

        start_iso = brief["startDate"]
        end_iso = brief["endDate"]

        # 1. Ground truth for feedback items in window
        cur.execute("""
            SELECT COUNT(*) FROM feedback_items
            WHERE organization_id = 'org-apex-01'
              AND submitted_at >= ? AND submitted_at <= ?;
        """, (start_iso, end_iso))
        sql_fb_count = cur.fetchone()[0]
        assert brief["deterministicMetrics"]["total_feedback"] == sql_fb_count

        # 2. Ground truth for new issues in window
        cur.execute("""
            SELECT COUNT(*) FROM issues
            WHERE organization_id = 'org-apex-01'
              AND created_at >= ? AND created_at <= ?;
        """, (start_iso, end_iso))
        sql_new_issues = cur.fetchone()[0]
        assert brief["whatChanged"]["newIssuesCount"] == sql_new_issues
        assert brief["deterministicMetrics"]["new_issues_count"] == sql_new_issues

        # 3. Ground truth for active backlog
        cur.execute("""
            SELECT COUNT(*) FROM issues
            WHERE organization_id = 'org-apex-01'
              AND status NOT IN ('RESOLVED', 'CLOSED');
        """, ())
        sql_active_backlog = cur.fetchone()[0]
        assert len(brief["unresolvedIssues"]) == sql_active_backlog
        assert brief["deterministicMetrics"]["active_backlog_count"] == sql_active_backlog

        # 4. Ground truth for outcome measurements
        cur.execute("""
            SELECT COUNT(*) FROM outcome_measurements
            WHERE organization_id = 'org-apex-01';
        """, ())
        sql_outcomes_count = cur.fetchone()[0]
        assert len(brief["interventionOutcomes"]) == min(10, sql_outcomes_count)
        assert brief["deterministicMetrics"]["evaluated_outcomes_count"] == min(10, sql_outcomes_count)

        conn.close()

    def test_epistemic_claims_labeling(self, auth_headers):
        """
        Constraint: Clearly label: observation, hypothesis, recommendation, unknown.
        Verify that labeledClaims contains explicit epistemic categories with traceable grounding sources.
        """
        response = client.post(
            "/api/v1/briefs/generate",
            json={"timeframeType": "DAILY"},
            headers=auth_headers
        )
        assert response.status_code == 200
        brief = response.json()["data"]

        claims = brief["labeledClaims"]
        assert len(claims) >= 4

        claimed_types = {c["type"] for c in claims}
        assert "OBSERVATION" in claimed_types
        assert "HYPOTHESIS" in claimed_types
        assert "RECOMMENDATION" in claimed_types
        assert "UNKNOWN" in claimed_types

        for claim in claims:
            assert claim["type"] in ["OBSERVATION", "HYPOTHESIS", "RECOMMENDATION", "UNKNOWN"]
            assert len(claim["statement"]) > 5
            assert "groundingSource" in claim
            assert 0.0 <= claim["confidence"] <= 1.0

            # Observations must be grounded in sqlite data
            if claim["type"] == "OBSERVATION":
                assert claim["confidence"] >= 0.90
                assert claim["groundingSource"].startswith("sqlite:")

    def test_recommendations_grounded_in_observed_evidence(self, auth_headers):
        """Constraint: Recommendations must be grounded in observed evidence."""
        conn = get_connection()
        cur = conn.cursor()

        response = client.post(
            "/api/v1/briefs/generate",
            json={"timeframeType": "DAILY"},
            headers=auth_headers
        )
        brief = response.json()["data"]

        recommendations = brief["recommendedActions"]
        assert len(recommendations) > 0

        for rec in recommendations:
            assert "issueId" in rec
            assert "recommendation" in rec
            assert "targetTeamName" in rec
            assert "groundedRationale" in rec
            assert len(rec["groundedRationale"]) > 10

            # Verify issue actually exists in database
            cur.execute("SELECT id, title FROM issues WHERE id = ?;", (rec["issueId"],))
            db_issue = cur.fetchone()
            assert db_issue is not None

        conn.close()

    def test_daily_weekly_custom_timeframes(self, auth_headers):
        """Verify support for daily, weekly, and custom reporting windows."""
        # 1. DAILY
        r_daily = client.post("/api/v1/briefs/generate", json={"timeframeType": "DAILY"}, headers=auth_headers)
        assert r_daily.status_code == 200
        b_daily = r_daily.json()["data"]
        assert b_daily["timeframeType"] == "DAILY"

        # 2. WEEKLY
        r_weekly = client.post("/api/v1/briefs/generate", json={"timeframeType": "WEEKLY"}, headers=auth_headers)
        assert r_weekly.status_code == 200
        b_weekly = r_weekly.json()["data"]
        assert b_weekly["timeframeType"] == "WEEKLY"

        # 3. CUSTOM
        now = datetime.now(timezone.utc)
        start_custom = (now - timedelta(days=3)).isoformat()
        end_custom = now.isoformat()

        r_custom = client.post(
            "/api/v1/briefs/generate",
            json={
                "timeframeType": "CUSTOM",
                "startDate": start_custom,
                "endDate": end_custom
            },
            headers=auth_headers
        )
        assert r_custom.status_code == 200
        b_custom = r_custom.json()["data"]
        assert b_custom["timeframeType"] == "CUSTOM"
        assert b_custom["startDate"] == start_custom
        assert b_custom["endDate"] == end_custom

    def test_brief_retrieval_and_history(self, auth_headers):
        """Verify latest brief retrieval and list endpoints."""
        # Latest brief
        r_latest = client.get("/api/v1/briefs/latest", headers=auth_headers)
        assert r_latest.status_code == 200
        b_latest = r_latest.json()["data"]
        assert b_latest is not None
        assert "id" in b_latest

        # Get by ID
        brief_id = b_latest["id"]
        r_by_id = client.get(f"/api/v1/briefs/{brief_id}", headers=auth_headers)
        assert r_by_id.status_code == 200
        assert r_by_id.json()["data"]["id"] == brief_id

        # List briefs
        r_list = client.get("/api/v1/briefs", headers=auth_headers)
        assert r_list.status_code == 200
        briefs_list = r_list.json()["data"]
        assert isinstance(briefs_list, list)
        assert len(briefs_list) >= 1
        assert any(b["id"] == brief_id for b in briefs_list)

    def test_rbac_unauthorized_access(self, viewer_headers, maint_headers):
        """Verify that unauthorized users cannot execute restricted brief actions."""
        # Viewer lacks analytics:export -> POST /generate is 403 Forbidden
        r_gen = client.post("/api/v1/briefs/generate", json={}, headers=viewer_headers)
        assert r_gen.status_code == 403

        # Maintenance team lacks analytics:read -> GET /latest is 403 Forbidden
        r_get = client.get("/api/v1/briefs/latest", headers=maint_headers)
        assert r_get.status_code == 403

        # Unauthenticated request -> 401 Unauthorized
        r_unauth = client.get("/api/v1/briefs")
        assert r_unauth.status_code == 401

    def test_deterministic_analytics_injection_zero_hallucination(self, auth_headers):
        """
        Verify strict numerical fidelity with newly injected synthetic feedback items.
        Inject exactly 3 feedback items in a specific historical window and assert exact match.
        """
        conn = get_connection()
        cur = conn.cursor()

        now = datetime.now(timezone.utc)
        target_start = (now - timedelta(days=50)).isoformat()
        target_end = (now - timedelta(days=49)).isoformat()
        mid_time = (now - timedelta(days=49, hours=12)).isoformat()

        # Insert 3 unique synthetic feedback items in that window
        syn_ids = [f"syn-fb-{uuid.uuid4().hex[:8]}" for _ in range(3)]
        for fid in syn_ids:
            cur.execute("""
                INSERT INTO feedback_items (
                    id, organization_id, store_id, department_id, source_type, channel_type,
                    raw_text, language_code, sentiment_score, processing_status, status,
                    submitted_at, created_at, updated_at
                ) VALUES (?, 'org-apex-01', 'store-104', 'dept-104-dairy', 'MOBILE_APP', 'APP',
                          'Synthetic temperature report verification', 'en', -0.5, 'analyzed',
                          'PROCESSED', ?, ?, ?);
            """, (fid, mid_time, mid_time, mid_time))
        conn.commit()

        # Generate custom brief for that exact historical window
        r_brief = client.post(
            "/api/v1/briefs/generate",
            json={
                "timeframeType": "CUSTOM",
                "storeId": "store-104",
                "startDate": target_start,
                "endDate": target_end
            },
            headers=auth_headers
        )
        assert r_brief.status_code == 200
        b_data = r_brief.json()["data"]

        # Exact match constraint: exactly 3 items must be counted, not 2, not 4, not invented.
        assert b_data["deterministicMetrics"]["total_feedback"] == 3
        assert b_data["whatChanged"]["feedbackVolumeDelta"] >= 0

        # Cleanup synthetic items to preserve clean test state
        for fid in syn_ids:
            cur.execute("DELETE FROM feedback_items WHERE id = ?;", (fid,))
        conn.commit()
        conn.close()

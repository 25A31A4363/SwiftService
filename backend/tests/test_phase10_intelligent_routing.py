"""
R5 Operational Intelligence Platform - Phase 10: Intelligent Operational Routing Automated Tests

Coverage:
- Deterministic Operational Routing Rules (Category, Store, Region, Ownership Mapping, Specialization)
- Safety Hazard Emergency Override & Expedited SLA (15-30m)
- Ambiguous Routing & Low-Confidence Protection (Human Triage Queue)
- Manual Reassignment with Provenance (Human Override)
- Operational Escalation with Accelerated SLA
- Chronological Routing History Lineage
- Human Triage Queue Retrieval
- Routing Simulation API
"""

import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.seed import seed_database
from backend.app.db.database import get_connection
from backend.app.core.security import create_access_token
from backend.app.services.routing_service import RoutingService
from backend.app.services.issue_service import IssueService


class TestPhase10IntelligentRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(force=True)
        cls.client = TestClient(app)

        # Auth Tokens
        cls.admin_token = create_access_token({
            "userId": "usr-admin",
            "email": "orgadmin@apex.com",
            "role": "ORGANIZATION_ADMIN",
            "organizationId": "org-apex-01"
        })
        cls.ops_token = create_access_token({
            "userId": "usr-ops",
            "email": "opsmanager@apex.com",
            "role": "OPERATIONS_MANAGER",
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
            "organizationId": "org-apex-01"
        })

    def _headers(self, token: str):
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _create_test_issue(self, title: str, category: str, severity: float = 0.6, is_safety: bool = False, store_id: str = "store-104") -> str:
        # Create an issue via Issue API
        res = self.client.post("/api/v1/issues", json={
            "storeId": store_id,
            "title": title,
            "description": f"Incident test description for {title}",
            "severityScore": severity,
            "urgencyScore": 0.7,
            "impactScopeScore": 0.6
        }, headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 201)
        issue_id = res.json()["data"]["id"]

        # If safety or specific category, update issue record or link
        if is_safety or category:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE issues
                SET factor_breakdown = json_object('isSafetyHazard', ?, 'safety', ?),
                    title = ?
                WHERE id = ?;
            """, (1 if is_safety else 0, 20.0 if is_safety else 0.0, f"[{category}] {title}", issue_id))
            conn.commit()

        return issue_id

    # -------------------------------------------------------------------------
    # 1. Deterministic Operational Ownership Mapping Routing
    # -------------------------------------------------------------------------
    def test_deterministic_ownership_mapping_routing(self):
        """
        Store 104 HVAC/refrigeration issue must deterministically route to 'team-hvac-pnw'
        based on active operational ownership mapping 'map-104-hvac', with confidence >= 0.90
        and mapped SLA window.
        """
        issue_id = self._create_test_issue(
            title="Commercial Dairy Reach-in Cooler 4B Temperature Elevation",
            category="FACILITIES_MAINTENANCE"
        )

        res = self.client.post(f"/api/v1/routing/issues/{issue_id}/route", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        self.assertEqual(data["issueId"], issue_id)
        self.assertEqual(data["selectedTeamId"], "team-hvac-pnw")
        self.assertIn("HVAC", data["selectedTeamName"])
        self.assertEqual(data["routingStrategy"], "DETERMINISTIC_OWNERSHIP_RULE")
        self.assertEqual(data["routingTier"], "STORE_SPECIALIST")
        self.assertGreaterEqual(data["confidence"], 0.90)
        self.assertFalse(data["isAmbiguous"])
        self.assertIsNotNone(data["fallbackTeamId"])
        self.assertGreater(data["slaMinutes"], 0)
        self.assertIsNotNone(data["slaDeadline"])

        # Check issue was updated
        issue_res = self.client.get(f"/api/v1/issues/{issue_id}", headers=self._headers(self.store_token))
        issue = issue_res.json()["data"]
        self.assertEqual(issue["assignedTeamId"], "team-hvac-pnw")
        self.assertEqual(issue["routingStatus"], "ROUTED")
        self.assertEqual(issue["status"], "DISPATCHED")

    def test_pos_hardware_ownership_routing(self):
        """
        Front checkout POS scanner failure must route to 'team-it-pnw'
        via 'map-104-pos' ownership rule with SLA 30m.
        """
        issue_id = self._create_test_issue(
            title="Self-Checkout POS Register 3 Barcode Scanner Frozen",
            category="CHECKOUT_POS"
        )

        res = self.client.post(f"/api/v1/routing/issues/{issue_id}/route", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        self.assertEqual(data["selectedTeamId"], "team-it-pnw")
        self.assertIn("IT", data["selectedTeamName"])
        self.assertEqual(data["routingStrategy"], "DETERMINISTIC_OWNERSHIP_RULE")
        self.assertGreaterEqual(data["confidence"], 0.90)

    # -------------------------------------------------------------------------
    # 2. Safety Hazard Emergency Override & Expedited SLA
    # -------------------------------------------------------------------------
    def test_safety_hazard_emergency_override_and_sla(self):
        """
        A confirmed slip/fall hazard with high severity must trigger the Emergency Safety Override,
        routing directly to Store 104 Janitorial squad with an expedited 15-minute emergency SLA.
        """
        issue_id = self._create_test_issue(
            title="Active liquid spill and severe slip puddle on floor in Aisle 4",
            category="SAFETY_HAZARD",
            severity=0.90,
            is_safety=True
        )

        res = self.client.post(f"/api/v1/routing/issues/{issue_id}/route", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        self.assertEqual(data["selectedTeamId"], "team-janitorial-104")
        self.assertIn("Janitorial", data["selectedTeamName"])
        self.assertEqual(data["routingStrategy"], "SAFETY_HAZARD_EMERGENCY_OVERRIDE")
        self.assertGreaterEqual(data["confidence"], 0.95)
        # Emergency safety SLA must be 15 minutes
        self.assertEqual(data["slaMinutes"], 15)
        self.assertIn("Emergency safety hazard detected", data["reason"])

    # -------------------------------------------------------------------------
    # 3. Ambiguous Routing & Human Triage Queue Protection
    # -------------------------------------------------------------------------
    def test_ambiguous_routing_protection_routes_to_human_triage(self):
        """
        When category/intent is completely ambiguous or has no specialized team,
        the system must NOT guess. It must route to the Central Human Triage Queue
        with isAmbiguous = True and confidence <= 0.50.
        """
        issue_id = self._create_test_issue(
            title="Mysterious unclassified noise and unspecified disturbance in facility",
            category="NONEXISTENT_EXOTIC_UNKNOWN_CATEGORY"
        )

        res = self.client.post(f"/api/v1/routing/issues/{issue_id}/route", headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        # Must NOT guess a team
        self.assertIsNone(data["selectedTeamId"])
        self.assertTrue(data["isAmbiguous"])
        self.assertEqual(data["routingTier"], "HUMAN_TRIAGE_QUEUE")
        self.assertEqual(data["routingStrategy"], "AMBIGUOUS_TRIAGE_QUEUE")
        self.assertLessEqual(data["confidence"], 0.50)
        self.assertIn("Human Triage Queue", data["reason"])

        # Check issue state reflects triage queue
        issue_res = self.client.get(f"/api/v1/issues/{issue_id}", headers=self._headers(self.store_token))
        issue = issue_res.json()["data"]
        self.assertEqual(issue["routingStatus"], "TRIAGE_QUEUE")
        self.assertEqual(issue["status"], "TRIAGE_QUEUE")

    def test_get_triage_queue_endpoint(self):
        """
        Triage operators can query the Human Triage Queue to view all ambiguous incidents.
        """
        # Create an ambiguous issue to ensure queue has at least 1 item
        self._create_test_issue(
            title="Unidentified anomaly in store perimeter",
            category="AMBIGUOUS_UNKNOWN"
        )
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM issues WHERE title LIKE '%Unidentified anomaly%' ORDER BY created_at DESC LIMIT 1;")
        ambig_id = cur.fetchone()["id"]
        self.client.post(f"/api/v1/routing/issues/{ambig_id}/route", headers=self._headers(self.store_token))

        # Query triage queue
        queue_res = self.client.get("/api/v1/routing/triage-queue", headers=self._headers(self.ops_token))
        self.assertEqual(queue_res.status_code, 200)
        items = queue_res.json()["data"]
        self.assertGreater(len(items), 0)

        first_item = items[0]
        self.assertIn("issue", first_item)
        self.assertIn("ambiguityReason", first_item)
        self.assertIn("suggestedTeams", first_item)

    # -------------------------------------------------------------------------
    # 4. Manual Reassignment (Human Override Provenance)
    # -------------------------------------------------------------------------
    def test_manual_reassignment_human_override(self):
        """
        Authorized operator manually reassigns an issue to a different team.
        The system records human override flag, operator ID, and justification.
        """
        issue_id = self._create_test_issue(
            title="Cooler vibration needs specialized acoustic dampening check",
            category="FACILITIES_MAINTENANCE"
        )
        # Route first
        self.client.post(f"/api/v1/routing/issues/{issue_id}/route", headers=self._headers(self.store_token))

        # Reassign to IT team with reason
        reassign_res = self.client.post(f"/api/v1/routing/issues/{issue_id}/reassign", json={
            "targetTeamId": "team-it-pnw",
            "targetUserId": "usr-maint",
            "reassignmentReason": "Temperature telemetry sensor firmware needs IT network gateway reboot."
        }, headers=self._headers(self.store_token))
        self.assertEqual(reassign_res.status_code, 200)
        data = reassign_res.json()["data"]

        self.assertEqual(data["selectedTeamId"], "team-it-pnw")
        self.assertTrue(data["isHumanOverride"])
        self.assertEqual(data["overrideBy"], "usr-store")
        self.assertIn("firmware needs IT network gateway", data["overrideReason"])
        self.assertEqual(data["routingStrategy"], "HUMAN_OVERRIDE")

        # Verify Issue record
        issue = self.client.get(f"/api/v1/issues/{issue_id}", headers=self._headers(self.store_token)).json()["data"]
        self.assertEqual(issue["assignedTeamId"], "team-it-pnw")
        self.assertEqual(issue["routingStatus"], "REASSIGNED")

    # -------------------------------------------------------------------------
    # 5. Operational Escalation & Accelerated SLA
    # -------------------------------------------------------------------------
    def test_operational_escalation_and_accelerated_sla(self):
        """
        Escalating an incident accelerates the SLA deadline (cuts remaining window in half)
        and re-routes to secondary escalation tier.
        """
        issue_id = self._create_test_issue(
            title="HVAC Rooftop Compressor tripped twice today",
            category="FACILITIES_MAINTENANCE"
        )
        route_data = self.client.post(f"/api/v1/routing/issues/{issue_id}/route", headers=self._headers(self.store_token)).json()["data"]
        initial_sla = route_data["slaMinutes"]

        # Escalate issue
        esc_res = self.client.post(f"/api/v1/routing/issues/{issue_id}/escalate", json={
            "escalationReason": "Compressor thermal cutout triggered second time; regional contractor needed.",
            "targetTeamId": "team-food-safety"
        }, headers=self._headers(self.store_token))
        self.assertEqual(esc_res.status_code, 200)
        esc_data = esc_res.json()["data"]

        self.assertEqual(esc_data["routingTier"], "ESCALATION_TIER")
        self.assertEqual(esc_data["routingStrategy"], "OPERATIONAL_ESCALATION")
        # Accelerated SLA should be half of initial (or min 15)
        self.assertLessEqual(esc_data["slaMinutes"], initial_sla)
        self.assertEqual(esc_data["selectedTeamId"], "team-food-safety")

        # Verify Issue state
        issue = self.client.get(f"/api/v1/issues/{issue_id}", headers=self._headers(self.store_token)).json()["data"]
        self.assertEqual(issue["routingStatus"], "ESCALATED")
        self.assertEqual(issue["status"], "IN_PROGRESS")

    # -------------------------------------------------------------------------
    # 6. Chronological Routing History Lineage
    # -------------------------------------------------------------------------
    def test_chronological_routing_history_lineage(self):
        """
        Routing history endpoint returns all chronological decision milestones:
        Auto-route -> Reassign -> Escalate.
        """
        issue_id = self._create_test_issue(title="Multi-stage routing lifecycle issue", category="CHECKOUT_POS")

        # 1. Auto-route
        self.client.post(f"/api/v1/routing/issues/{issue_id}/route", headers=self._headers(self.store_token))
        # 2. Reassign
        self.client.post(f"/api/v1/routing/issues/{issue_id}/reassign", json={
            "targetTeamId": "team-janitorial-104",
            "reassignmentReason": "Physical register table damaged"
        }, headers=self._headers(self.store_token))
        # 3. Escalate
        self.client.post(f"/api/v1/routing/issues/{issue_id}/escalate", json={
            "escalationReason": "Register glass shattered"
        }, headers=self._headers(self.store_token))

        # Query history
        hist_res = self.client.get(f"/api/v1/routing/issues/{issue_id}/history", headers=self._headers(self.store_token))
        self.assertEqual(hist_res.status_code, 200)
        history = hist_res.json()["data"]

        self.assertEqual(len(history), 3)
        # Most recent first
        self.assertEqual(history[0]["routingStrategy"], "OPERATIONAL_ESCALATION")
        self.assertEqual(history[1]["routingStrategy"], "HUMAN_OVERRIDE")
        self.assertEqual(history[2]["routingStrategy"], "DETERMINISTIC_OWNERSHIP_RULE")

    # -------------------------------------------------------------------------
    # 7. Routing Simulation Endpoint
    # -------------------------------------------------------------------------
    def test_routing_simulation(self):
        """
        Simulation endpoint previews routing decisions without persisting to database.
        """
        sim_res = self.client.post("/api/v1/routing/simulate", json={
            "storeId": "store-104",
            "category": "FACILITIES_MAINTENANCE",
            "severity": 0.8,
            "isSafetyHazard": False
        }, headers=self._headers(self.admin_token))
        self.assertEqual(sim_res.status_code, 200)
        sim = sim_res.json()["data"]

        self.assertEqual(sim["selectedTeamId"], "team-hvac-pnw")
        self.assertEqual(sim["routingStrategy"], "DETERMINISTIC_OWNERSHIP_RULE")
        self.assertGreaterEqual(sim["confidence"], 0.90)


if __name__ == "__main__":
    unittest.main()

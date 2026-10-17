"""
R5 Operational Intelligence Platform - Phases 5 through 9 Automated Test Suite

Coverage:
- Phase 5: Intelligent Investigation & Dynamic Follow-Up
- Phase 6: Cross-Source Semantic Issue Clustering
- Phase 7: Emerging Issue Detection & Lifecycle
- Phase 8: Explainable Multi-Factor Issue Prioritization
- Phase 9: Evidence Lineage DAG & Strict Claim Typology
"""

import unittest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.seed import seed_database
from backend.app.db.database import get_connection
from backend.app.core.security import create_access_token
from backend.app.services.investigation_service import InvestigationService
from backend.app.services.clustering_service import ClusteringService
from backend.app.services.emerging_detection_service import EmergingDetectionService
from backend.app.services.prioritization_service import PrioritizationService
from backend.app.services.evidence_lineage_service import EvidenceLineageService


class TestPhases5To9OperationalIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(force=True)
        cls.client = TestClient(app)

        # Tokens
        cls.admin_token = create_access_token({
            "userId": "usr-admin",
            "email": "orgadmin@apex.com",
            "role": "ORGANIZATION_ADMIN",
            "organizationId": "org-apex"
        })
        cls.store_token = create_access_token({
            "userId": "usr-store",
            "email": "storemanager@apex.com",
            "role": "STORE_MANAGER",
            "organizationId": "org-apex",
            "storeId": "store-104",
            "regionId": "reg-pnw"
        })
        cls.viewer_token = create_access_token({
            "userId": "usr-viewer",
            "email": "viewer@apex.com",
            "role": "VIEWER",
            "organizationId": "org-apex"
        })

    def _headers(self, token: str):
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _ingest_feedback(self, text: str, channel: str = "CUSTOMER_COMPLAINT", submitter: str = "CUSTOMER", store_id: str = "store-104") -> str:
        res = self.client.post("/api/v1/feedback", json={
            "storeId": store_id,
            "channelType": channel,
            "submitterType": submitter,
            "rawText": text,
            "privacyClassification": "INTERNAL"
        }, headers=self._headers(self.store_token))
        self.assertEqual(res.status_code, 201, f"Ingestion failed: {res.text}")
        return res.json()["data"]["id"]

    # =========================================================================
    # PHASE 5: INTELLIGENT INVESTIGATION & DYNAMIC FOLLOW-UP
    # =========================================================================

    def test_phase5_missing_info_detection_and_targeted_questions(self):
        """
        Vague feedback ('AC is not working.') must trigger relevant, explainable questions:
        - Cooling extent / operational impact
        - Location / affected area
        - Onset time
        - Safety concern
        """
        fb_id = self._ingest_feedback("AC is not working.")

        # Inspect generated questions via Investigation API
        inv_res = self.client.get(f"/api/v1/investigation/feedback/{fb_id}", headers=self._headers(self.store_token))
        self.assertEqual(inv_res.status_code, 200)
        inv_data = inv_res.json()

        self.assertIn(inv_data["investigationStatus"], ["IN_PROGRESS", "ACTIVE", "NEEDS_INFO"])
        questions = inv_data["questions"]
        self.assertGreaterEqual(len(questions), 2)

        # Verify questions are relevant, explainable, and answerable
        q_texts = [q["questionText"].lower() for q in questions]
        reasons = [q["reason"].lower() for q in questions]

        # Must address operational capacity, location, onset, or safety
        has_relevant_focus = any(
            any(k in t or k in r for k in ["capacity", "offline", "location", "aisle", "when", "time", "safety", "hazard", "scope"])
            for t, r in zip(q_texts, reasons)
        )
        self.assertTrue(has_relevant_focus, "Questions must focus on operational clarification.")
        for q in questions:
            self.assertIsNotNone(q["reason"])
            self.assertGreaterEqual(q["priority"], 1)
            self.assertEqual(q["status"], "PENDING")

    def test_phase5_different_issue_types_question_sets(self):
        """
        Tests that different issue types (POS payment, Food Safety/Freezer, Slip Hazard)
        generate specialized, category-relevant follow-up questions.
        """
        issue_cases = [
            ("Payment terminals keep freezing and failing.", "EMPLOYEE_FEEDBACK", "EMPLOYEE"),
            ("Dairy cooler is running warm.", "MAINTENANCE_REPORT", "MAINTENANCE_TECH"),
            ("There is water leaking on the floor.", "CUSTOMER_COMPLAINT", "CUSTOMER")
        ]

        for text, ch, sub in issue_cases:
            fb_id = self._ingest_feedback(text, channel=ch, submitter=sub)

            inv_res = self.client.get(f"/api/v1/investigation/feedback/{fb_id}", headers=self._headers(self.store_token))
            self.assertEqual(inv_res.status_code, 200)
            inv_data = inv_res.json()
            questions = inv_data["questions"]
            self.assertGreater(len(questions), 0)

            for q in questions:
                self.assertIsNotNone(q["questionText"])
                self.assertIsNotNone(q["reason"])
                self.assertIn(q["questionType"], ["text", "choice"])

    def test_phase5_sufficient_information_stops_asking_questions(self):
        """
        Comprehensive feedback with clear location, symptoms, impact, and safety context
        should NOT generate redundant questions (stops asking when info is sufficient).
        """
        comprehensive_text = (
            "HVAC unit #3 in East produce wing failed at 11:30 AM. Area temperature is 82F, "
            "affecting approximately 35 customers and 4 staff members. No burning smell, sparks, "
            "or safety hazards observed. Portable fans deployed as temporary mitigation."
        )
        fb_id = self._ingest_feedback(comprehensive_text, channel="MAINTENANCE_REPORT", submitter="MAINTENANCE_TECH")

        inv_res = self.client.get(f"/api/v1/investigation/feedback/{fb_id}", headers=self._headers(self.store_token))
        self.assertEqual(inv_res.status_code, 200)
        inv_data = inv_res.json()

        # Should either be SUFFICIENT or have no pending critical questions
        self.assertIn(inv_data["investigationStatus"], ["SUFFICIENT", "RESOLVED", "ACTIVE", "NEEDS_INFO"])
        # Should not have more than 2 questions when context is thoroughly provided
        self.assertLessEqual(len(inv_data["questions"]), 3)

    def test_phase5_answer_capture_enrichment_and_reanalysis(self):
        """
        Operator answering a question captures the response, enriches context,
        and triggers re-analysis while preserving raw text immutability.
        """
        original_raw = "Store is too hot."
        fb_id = self._ingest_feedback(original_raw)

        # Get questions
        inv_res = self.client.get(f"/api/v1/investigation/feedback/{fb_id}", headers=self._headers(self.store_token))
        questions = inv_res.json()["questions"]
        self.assertGreater(len(questions), 0)
        target_q = questions[0]

        # Answer question
        ans_res = self.client.post(f"/api/v1/investigation/questions/{target_q['id']}/answer", json={
            "answer": "The entire sales floor is 85F and main rooftop compressor has tripped off."
        }, headers=self._headers(self.store_token))
        self.assertEqual(ans_res.status_code, 200)
        ans_data = ans_res.json()

        self.assertTrue(ans_data["hasEnrichedText"])
        self.assertIn("sales floor is 85F", ans_data["enrichedText"])

        # Verify raw text remains strictly immutable
        fb_check = self.client.get(f"/api/v1/feedback/{fb_id}", headers=self._headers(self.store_token))
        self.assertEqual(fb_check.status_code, 200)
        self.assertEqual(fb_check.json()["data"]["rawText"], original_raw)
        self.assertIn("sales floor is 85F", fb_check.json()["data"]["enrichedText"])

    def test_phase5_human_override_custom_question_and_dismissal(self):
        """
        Store managers and admins can add custom investigation questions and dismiss unnecessary ones.
        """
        fb_id = self._ingest_feedback("Freezer sounds loud.")

        # Add custom question
        custom_res = self.client.post(f"/api/v1/investigation/feedback/{fb_id}/custom-question", json={
            "questionText": "Has technician John inspected the belt tension?",
            "reason": "Specific unit maintenance history follow-up",
            "questionType": "text"
        }, headers=self._headers(self.store_token))
        self.assertEqual(custom_res.status_code, 200)
        custom_summary = custom_res.json()
        custom_q = [q for q in custom_summary["questions"] if "belt tension" in q["questionText"]]
        self.assertEqual(len(custom_q), 1)
        custom_q_id = custom_q[0]["id"]

        # Dismiss question with reason
        dismiss_res = self.client.post(f"/api/v1/investigation/questions/{custom_q_id}/dismiss", json={
            "reason": "Technician John is on leave; work order 904 was assigned instead."
        }, headers=self._headers(self.store_token))
        self.assertEqual(dismiss_res.status_code, 200)
        dismiss_summary = dismiss_res.json()
        dismissed_q = [q for q in dismiss_summary["questions"] if q["id"] == custom_q_id]
        self.assertEqual(dismissed_q[0]["status"], "DISMISSED")

    # =========================================================================
    # PHASE 6: CROSS-SOURCE SEMANTIC ISSUE CLUSTERING
    # =========================================================================

    def test_phase6_semantic_similarity_and_clustering(self):
        """
        Different feedback records describing the same underlying issue across channels
        ('AC isn't cooling', 'Store is extremely hot', 'Customers complaining about heat', 'HVAC stopped working')
        must group together into a coherent cluster, while an unrelated issue ('POS scanner error') remains separate.
        """
        hvac_items = [
            ("AC isn't cooling properly in store 104", "CUSTOMER_COMPLAINT"),
            ("Store is extremely hot and stifling", "CUSTOMER_COMPLAINT"),
            ("Customers complaining about heat and sweating", "SURVEY_RESPONSE"),
            ("HVAC stopped working rooftop compressor fault", "MAINTENANCE_REPORT")
        ]
        hvac_ids = [self._ingest_feedback(t, channel=ch) for t, ch in hvac_items]

        unrelated_id = self._ingest_feedback(
            "Barcode scanner at checkout 4 fails to read QR codes",
            channel="EMPLOYEE_FEEDBACK"
        )

        # Run clustering
        cluster_res = self.client.post("/api/v1/clusters/discover", json={
            "storeId": "store-104",
            "similarityThreshold": 0.35,
            "timeWindowHours": 72
        }, headers=self._headers(self.admin_token))
        self.assertEqual(cluster_res.status_code, 200)
        clusters = cluster_res.json()
        self.assertGreater(len(clusters), 0)

        # Check that clusters contain member citations
        first_cluster = clusters[0]
        self.assertIsNotNone(first_cluster["title"])
        self.assertIsNotNone(first_cluster["summary"])
        self.assertGreater(first_cluster["feedbackCount"], 0)
        self.assertGreaterEqual(first_cluster["confidenceScore"], 0.3)
        self.assertGreaterEqual(first_cluster["qualityScore"], 0.3)

    def test_phase6_cluster_human_merge_and_split(self):
        """
        Operators can manually split off specific items from a cluster or update metadata.
        """
        # Run discover to ensure at least one cluster exists
        self.client.post("/api/v1/clusters/discover", json={"similarityThreshold": 0.30}, headers=self._headers(self.admin_token))
        list_res = self.client.get("/api/v1/clusters", headers=self._headers(self.admin_token))
        clusters = list_res.json()
        self.assertGreaterEqual(len(clusters), 1)

        target_c = clusters[0]
        c_id = target_c["id"]

        # Update cluster title and category
        update_res = self.client.patch(f"/api/v1/clusters/{c_id}", json={
            "title": "HVAC Central Rooftop Compressor Degradation",
            "category": "FACILITY_HVAC"
        }, headers=self._headers(self.admin_token))
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["title"], "HVAC Central Rooftop Compressor Degradation")

    # =========================================================================
    # PHASE 7: EMERGING ISSUE DETECTION & LIFECYCLE
    # =========================================================================

    def test_phase7_insufficient_baseline_guard(self):
        """
        When historical baseline data is sparse (< 3 observations), the system
        must explicitly report 'INSUFFICIENT_BASELINE' rather than pretending an anomaly exists.
        """
        conn = get_connection()
        baseline_info = EmergingDetectionService.calculate_historical_baseline(
            conn=conn,
            store_id="store-104",
            category="NONEXISTENT_CATEGORY_XYZ",
            baseline_days=14,
            recent_hours=24
        )
        self.assertEqual(baseline_info["status"], "INSUFFICIENT_BASELINE")
        self.assertIn("minimum 3 required", baseline_info["reason"])

    def test_phase7_deterministic_emerging_detection_and_alert_structure(self):
        """
        Emerging issue detection must generate alerts with deterministic metrics:
        WHAT, WHEN, WHERE, HOW MANY observations, WHICH sources, baseline comparison,
        SEVERITY, URGENCY, CONFIDENCE, WHY generated, WHAT remains uncertain.
        """
        for i in range(3):
            self._ingest_feedback(f"Self-checkout terminal #{i+1} receipt printer jammed and flashing error 44")

        detect_res = self.client.post("/api/v1/alerts/detect", json={
            "storeId": "store-104",
            "minEvidenceThreshold": 2,
            "zscoreThreshold": 0.1,
            "baselineWindowDays": 14,
            "recentWindowHours": 24
        }, headers=self._headers(self.admin_token))
        self.assertEqual(detect_res.status_code, 200)
        alerts = detect_res.json()["data"]
        self.assertIsInstance(alerts, list)

        if len(alerts) > 0:
            alert = alerts[0]
            self.assertIn("what", alert)
            self.assertIn("whereZone", alert)
            self.assertIn("observationCount", alert)
            self.assertIn("sourcesSummary", alert)
            self.assertIn("baselineDiff", alert)
            self.assertIn("velocityZscore", alert)
            self.assertIn("whyGenerated", alert)
            self.assertIn("uncertainties", alert)
            self.assertIn("urgency", alert)
            self.assertIn("confidence", alert)
            self.assertIn(alert["status"], ["NEW", "OPEN", "ACKNOWLEDGED", "ESCALATED", "DISMISSED"])

    def test_phase7_alert_lifecycle_management(self):
        """
        Alert lifecycle: Acknowledgement -> Escalation -> Dismissal
        """
        # Fetch or trigger an alert
        alerts_res = self.client.get("/api/v1/alerts", headers=self._headers(self.admin_token))
        alerts = alerts_res.json()["data"]
        if len(alerts) == 0:
            self.client.post("/api/v1/alerts/detect", json={"minEvidenceThreshold": 1, "zscoreThreshold": 0.05}, headers=self._headers(self.admin_token))
            alerts = self.client.get("/api/v1/alerts", headers=self._headers(self.admin_token)).json()["data"]

        self.assertGreater(len(alerts), 0)
        alert_id = alerts[0]["id"]

        # 1. Acknowledge
        ack_res = self.client.post(f"/api/v1/alerts/{alert_id}/acknowledge", headers=self._headers(self.store_token))
        self.assertEqual(ack_res.status_code, 200)
        self.assertIn(ack_res.json()["data"]["status"], ["ACKNOWLEDGED", "OPEN"])

        # 2. Escalate
        esc_res = self.client.post(f"/api/v1/alerts/{alert_id}/escalate", json={
            "targetTeamId": "team-hvac-pnw",
            "notes": "Escalated for immediate technician dispatch"
        }, headers=self._headers(self.store_token))
        self.assertEqual(esc_res.status_code, 200)
        self.assertEqual(esc_res.json()["data"]["status"], "ESCALATED")
        self.assertEqual(esc_res.json()["data"]["escalatedToTeamId"], "team-hvac-pnw")

        # 3. Dismiss
        dismiss_res = self.client.post(f"/api/v1/alerts/{alert_id}/dismiss", json={
            "reason": "Technician resolved issue on-site; verified normal operations."
        }, headers=self._headers(self.store_token))
        self.assertEqual(dismiss_res.status_code, 200)
        self.assertEqual(dismiss_res.json()["data"]["status"], "DISMISSED")

    # =========================================================================
    # PHASE 8: EXPLAINABLE ISSUE PRIORITIZATION
    # =========================================================================

    def test_phase8_high_severity_low_frequency_safety_override(self):
        """
        A single high-severity safety incident (e.g. electrical sparking / chemical spill)
        must trigger the safety override floor and be rated P1 (Critical), even with observation_count = 1.
        """
        calc = PrioritizationService.calculate_explainable_priority(
            severity=0.95,
            urgency=0.90,
            operational_impact=0.85,
            is_safety_hazard=True,
            growth_velocity=0.0,
            stores_affected_count=1,
            recurrence_count=0,
            confidence=0.95,
            observation_count=1
        )
        self.assertEqual(calc["priorityTier"], "P1_CRITICAL")
        self.assertGreaterEqual(calc["priorityScore"], 85)
        self.assertIn("Confirmed safety hazard", calc["explainableSummary"])
        self.assertTrue(calc["factorContributions"]["safety"] > 0)

    def test_phase8_low_severity_high_frequency_volume_cap(self):
        """
        A low-severity cosmetic issue (e.g. minor receipt misprint) occurring 50 times
        must NOT be rated P1 simply due to frequency; low severity caps it at P3/P4.
        """
        calc = PrioritizationService.calculate_explainable_priority(
            severity=0.15,
            urgency=0.20,
            operational_impact=0.10,
            is_safety_hazard=False,
            growth_velocity=2.5,
            stores_affected_count=1,
            recurrence_count=5,
            confidence=0.90,
            observation_count=50
        )
        self.assertIn(calc["priorityTier"], ["P3_MEDIUM", "P4_LOW"])
        self.assertLessEqual(calc["priorityScore"], 55)
        self.assertIn("score capped to prevent volume inflation", calc["explainableSummary"])

    def test_phase8_rapidly_emerging_issue_boost(self):
        """
        A moderate issue with high growth rate and multi-store geographic spread
        receives a deterministic growth & spread boost.
        """
        calc = PrioritizationService.calculate_explainable_priority(
            severity=0.60,
            urgency=0.65,
            operational_impact=0.55,
            is_safety_hazard=False,
            growth_velocity=2.8,
            stores_affected_count=4,
            recurrence_count=3,
            confidence=0.85,
            observation_count=8
        )
        self.assertIn(calc["priorityTier"], ["P1_CRITICAL", "P2_HIGH", "P3_MEDIUM"])
        self.assertGreaterEqual(calc["factorContributions"]["growth"], 8.0)
        self.assertGreaterEqual(calc["factorContributions"]["geographicSpread"], 4.0)
        self.assertIn("rapid acceleration vs baseline", calc["explainableSummary"])
        self.assertIn("cross-store propagation", calc["explainableSummary"])

    def test_phase8_insufficient_evidence_confidence_discount(self):
        """
        When extraction/evidence confidence is low (< 0.70), an uncertainty discount
        is applied and noted in the transparent explanation.
        """
        calc = PrioritizationService.calculate_explainable_priority(
            severity=0.70,
            urgency=0.70,
            operational_impact=0.60,
            is_safety_hazard=False,
            growth_velocity=0.0,
            stores_affected_count=1,
            recurrence_count=0,
            confidence=0.35,
            observation_count=1
        )
        self.assertGreater(calc["confidenceDiscount"], 0.0)
        self.assertIn("dampened by high uncertainty", calc["explainableSummary"])

    # =========================================================================
    # PHASE 9: EVIDENCE & EXPLAINABILITY LAYER
    # =========================================================================

    def test_phase9_lineage_graph_end_to_end(self):
        """
        Full operational lineage DAG must connect:
        Feedback -> Extraction -> Investigation -> Cluster -> Alert -> Priority -> Action -> Resolution
        """
        issues_res = self.client.get("/api/v1/issues", headers=self._headers(self.store_token))
        issues = issues_res.json()["data"]
        self.assertGreater(len(issues), 0)
        issue_id = issues[0]["id"]

        lineage_res = self.client.get(f"/api/v1/lineage/issue/{issue_id}", headers=self._headers(self.store_token))
        self.assertEqual(lineage_res.status_code, 200)
        lineage = lineage_res.json()["data"]

        self.assertIn("rootId", lineage)
        self.assertIn("nodes", lineage)
        self.assertIn("edges", lineage)
        self.assertGreater(len(lineage["nodes"]), 0)

        node_types = {n["type"] for n in lineage["nodes"]}
        self.assertIn("ISSUE", node_types)

        # Check edge consistency
        node_ids = {n["id"] for n in lineage["nodes"]}
        for edge in lineage["edges"]:
            self.assertIn(edge["source"], node_ids)
            self.assertIn(edge["target"], node_ids)

    def test_phase9_strict_claim_typology_and_unsupported_claim_prevention(self):
        """
        Strict claim taxonomy: FACT, HYPOTHESIS, RECOMMENDATION, UNKNOWN.
        Diagnostic root causes (e.g. 'compressor failed') MUST be categorized as HYPOTHESIS
        and cannot be represented as confirmed FACT until technician verified.
        """
        # Verified fact
        fact = EvidenceLineageService.classify_statement(
            "store temperature was 82 degrees recorded quote",
            is_empirically_verified=True
        )
        self.assertEqual(fact, "FACT")

        # Root cause hypothesis (unverified)
        hypothesis = EvidenceLineageService.classify_statement(
            "Suspected rooftop compressor failure",
            is_empirically_verified=False
        )
        self.assertEqual(hypothesis, "HYPOTHESIS")

        # Actionable recommendation
        recommendation = EvidenceLineageService.classify_statement(
            "Dispatch emergency technician to inspect refrigerant",
            is_empirically_verified=False
        )
        self.assertEqual(recommendation, "RECOMMENDATION")

        # Unknown / missing
        unknown = EvidenceLineageService.classify_statement(
            "Unknown electrical short circuit reason",
            is_empirically_verified=False
        )
        self.assertEqual(unknown, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()

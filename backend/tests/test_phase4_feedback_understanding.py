"""
R5 Operational Intelligence Platform - Phase 4 Automated Tests
AI-Powered Feedback Understanding:
- Multilingual language detection & confidence
- Grounded structured extraction (14 operational attributes)
- Strict prevention of hallucinated/invented facts ('unknown' with confidence 0.0)
- Exact evidence spans verification
- Separation of deterministic system facts from AI-derived facts
- Human review and override capabilities with provenance
- Re-analysis endpoints and audit logging
"""

import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.seed import seed_database
from backend.app.core.security import create_access_token
from backend.app.services.ai_understanding_service import AIUnderstandingService


class TestPhase4FeedbackUnderstanding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(force=True)
        cls.client = TestClient(app)

        # Auth Tokens
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

    # -------------------------------------------------------------------------
    # 1. Multilingual Language Detection & Confidence
    # -------------------------------------------------------------------------
    def test_language_detection_and_confidence(self):
        cases = [
            ("El refrigerador en el pasillo 3 tiene una fuga de agua.", "es", 0.70),
            ("Le congelateur du rayon bio fait un bruit inhabituel et fuit sur le sol.", "fr", 0.70),
            ("Das Kuehlregal im Gang 2 tropft und der Boden ist sehr nass.", "de", 0.70),
            ("डेयरी सेक्शन में पानी गिर रहा है और बहुत खराब स्थिति है।", "hi", 0.60),
            ("Customer noticed wet floor near checkout lane 2.", "en", 0.50)
        ]

        for text, expected_lang, min_conf in cases:
            res = AIUnderstandingService.detect_language(text)
            self.assertEqual(res["code"], expected_lang, f"Failed language detection for '{text}'")
            self.assertGreaterEqual(res["confidence"], min_conf)
            self.assertIsInstance(res["evidence"], list)

        # Test empty/gibberish fallback
        res_empty = AIUnderstandingService.detect_language("12345 67890 !@#$%", hint_language="en")
        self.assertTrue(res_empty["uncertainty"])
        self.assertIn("recognizable words", res_empty["uncertaintyReason"].lower())

    # -------------------------------------------------------------------------
    # 2. Grounded Structured Extraction with Evidence Spans
    # -------------------------------------------------------------------------
    def test_grounded_structured_extraction_and_spans(self):
        raw_text = "Urgent: The freezer in Aisle 4 is leaking water, creating a dangerous puddle on the floor."

        resp = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "channelType": "CUSTOMER_COMPLAINT",
                "rawText": raw_text
            }
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()["data"]
        ai = data["aiInterpretation"]

        # Check category & issue type
        self.assertIn(ai["issueCategory"]["value"], ["FACILITIES_MAINTENANCE", "SAFETY_HAZARD"])
        self.assertGreater(ai["issueCategory"]["confidence"], 0.8)
        self.assertIsNotNone(ai["issueCategory"]["evidence"])

        # Check location
        self.assertEqual(ai["location"]["value"], "Aisle 4")
        self.assertFalse(ai["location"]["uncertainty"])
        self.assertGreater(ai["location"]["confidence"], 0.8)
        loc_ev = ai["location"]["evidence"]
        self.assertEqual(loc_ev["text"], "Aisle 4")
        # Verify exact span offset in source text
        self.assertEqual(raw_text[loc_ev["start"]:loc_ev["end"]], loc_ev["text"])

        # Check affected entity
        self.assertIn("Freezer", ai["affectedEntity"]["value"])
        self.assertFalse(ai["affectedEntity"]["uncertainty"])
        ent_ev = ai["affectedEntity"]["evidence"]
        self.assertEqual(raw_text[ent_ev["start"]:ent_ev["end"]].lower(), "freezer")

        # Check severity & urgency
        self.assertIn(ai["severity"]["value"], ["CRITICAL", "HIGH"])
        self.assertIn(ai["urgency"]["value"], ["IMMEDIATE", "WITHIN_HOUR"])

        # Check symptoms
        symptoms = ai["symptoms"]
        self.assertGreater(len(symptoms), 0)
        for sym in symptoms:
            self.assertEqual(raw_text[sym["start"]:sym["end"]], sym["text"])

    # -------------------------------------------------------------------------
    # 3. Prevention of Invented/Hallucinated Facts ('unknown' handling)
    # -------------------------------------------------------------------------
    def test_no_invented_facts_when_data_is_absent(self):
        # Text has sentiment and category cues, but NO location, NO affected entity, NO temporal info
        vague_text = "The associate at customer service was exceptionally helpful and resolved my question."

        resp = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "channelType": "SURVEY_RESPONSE",
                "rawText": vague_text
            }
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()["data"]
        ai = data["aiInterpretation"]

        # AI MUST NOT invent location
        self.assertEqual(ai["location"]["value"], "unknown")
        self.assertEqual(ai["location"]["confidence"], 0.0)
        self.assertIsNone(ai["location"]["evidence"])
        self.assertTrue(ai["location"]["uncertainty"])
        self.assertIn("No physical location", ai["location"]["uncertaintyReason"])

        # AI MUST NOT invent affected equipment/entity
        self.assertEqual(ai["affectedEntity"]["value"], "unknown")
        self.assertEqual(ai["affectedEntity"]["confidence"], 0.0)
        self.assertIsNone(ai["affectedEntity"]["evidence"])
        self.assertTrue(ai["affectedEntity"]["uncertainty"])

        # AI MUST NOT invent temporal information
        self.assertEqual(ai["temporalInformation"]["value"], "unknown")
        self.assertEqual(ai["temporalInformation"]["confidence"], 0.0)
        self.assertIsNone(ai["temporalInformation"]["evidence"])
        self.assertTrue(ai["temporalInformation"]["uncertainty"])

        # Sentiment should correctly identify POSITIVE without hallucinating hazards
        self.assertEqual(ai["sentiment"]["label"], "POSITIVE")
        self.assertEqual(ai["safetyRelevance"]["value"], "NON_HAZARD")

    # -------------------------------------------------------------------------
    # 4. Evidence Spans Absolute Accuracy
    # -------------------------------------------------------------------------
    def test_evidence_spans_absolute_accuracy(self):
        text = "Around 2 hours ago, scanner 3 at self-checkout was frozen and refused to read barcodes."
        ai = AIUnderstandingService.extract_understanding(text)

        # Verify temporal evidence span
        temp = ai["temporalInformation"]
        self.assertFalse(temp["uncertainty"])
        self.assertEqual(text[temp["evidence"]["start"]:temp["evidence"]["end"]], temp["evidence"]["text"])

        # Verify entity evidence span
        entity = ai["affectedEntity"]
        self.assertFalse(entity["uncertainty"])
        self.assertEqual(text[entity["evidence"]["start"]:entity["evidence"]["end"]], entity["evidence"]["text"])

        # Verify sentiment evidence
        sent = ai["sentiment"]
        if sent["evidence"]:
            self.assertEqual(text[sent["evidence"]["start"]:sent["evidence"]["end"]], sent["evidence"]["text"])

    # -------------------------------------------------------------------------
    # 5. Strict Separation of System Facts and AI Facts
    # -------------------------------------------------------------------------
    def test_separation_of_system_and_ai_facts(self):
        raw_text = "Leaking water detected under dairy cooler in Aisle 2"
        resp = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "channelType": "MAINTENANCE_REPORT",
                "submitterType": "MAINTENANCE_TECH",
                "privacyClassification": "INTERNAL",
                "rawText": raw_text
            }
        )
        self.assertEqual(resp.status_code, 201)
        fb_id = resp.json()["data"]["id"]

        # Call Phase 4 understanding decomposition endpoint
        decomp_resp = self.client.get(
            f"/api/v1/feedback/{fb_id}/understanding",
            headers=self._headers(self.store_token)
        )
        self.assertEqual(decomp_resp.status_code, 200)
        payload = decomp_resp.json()["data"]

        # 1. Deterministic System Facts
        sys_facts = payload["systemFacts"]
        self.assertEqual(sys_facts["feedbackId"], fb_id)
        self.assertEqual(sys_facts["storeId"], "store-104")
        self.assertEqual(sys_facts["channelType"], "MAINTENANCE_REPORT")
        self.assertEqual(sys_facts["submitterType"], "MAINTENANCE_TECH")
        self.assertEqual(sys_facts["privacyClassification"], "INTERNAL")
        self.assertIsNotNone(sys_facts["contentHash"])

        # 2. AI-Derived Facts
        ai_facts = payload["aiDerivedFacts"]
        self.assertIn("issueCategory", ai_facts)
        self.assertIn("location", ai_facts)
        self.assertIn("severity", ai_facts)
        self.assertIn("overallConfidence", ai_facts)
        self.assertIn("overallUncertainty", ai_facts)

        # Verify AI facts do NOT overwrite system facts
        self.assertNotIn("contentHash", ai_facts)
        self.assertNotIn("storeId", ai_facts)

    # -------------------------------------------------------------------------
    # 6. Human Review and Override Capability
    # -------------------------------------------------------------------------
    def test_human_review_and_field_override(self):
        raw_text = "Puddle of water in Aisle 4 near the dairy fridge."
        resp = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "channelType": "CUSTOMER_COMPLAINT",
                "rawText": raw_text
            }
        )
        self.assertEqual(resp.status_code, 201)
        fb_id = resp.json()["data"]["id"]
        initial_fb = resp.json()["data"]

        initial_severity = initial_fb["aiInterpretation"]["severity"]["value"]

        # Operator inspects and submits override
        review_resp = self.client.post(
            f"/api/v1/feedback/{fb_id}/review",
            headers=self._headers(self.store_token),
            json={
                "processingStatus": "reviewed",
                "status": "IN_REVIEW",
                "reviewNotes": "Puddle confirmed by floor associate. Upgraded severity to CRITICAL due to heavy foot traffic.",
                "overrides": {
                    "severity": {
                        "value": "CRITICAL",
                        "reason": "Slip hazard located in main thoroughfare during peak hours"
                    },
                    "location": "Aisle 4 - Dairy Case 2B"
                }
            }
        )
        self.assertEqual(review_resp.status_code, 200)
        updated_data = review_resp.json()["data"]

        # 1. Processing status updated to 'reviewed'
        self.assertEqual(updated_data["processingStatus"], "reviewed")
        self.assertEqual(updated_data["status"], "IN_REVIEW")
        self.assertEqual(updated_data["reviewedBy"], "storemanager@apex.com")
        self.assertIsNotNone(updated_data["reviewedAt"])

        # 2. Raw text remains strictly immutable
        self.assertEqual(updated_data["rawText"], raw_text)

        # 3. AI-derived facts remain unchanged
        self.assertEqual(updated_data["aiInterpretation"]["severity"]["value"], initial_severity)

        # 4. Human overrides are recorded with provenance
        overrides = updated_data["humanOverrides"]["overrides"]
        self.assertIn("severity", overrides)
        self.assertEqual(overrides["severity"]["value"], "CRITICAL")
        self.assertEqual(overrides["location"]["value"], "Aisle 4 - Dairy Case 2B")

        # 5. Effective interpretation prioritizes human corrections
        eff = updated_data["effectiveInterpretation"]["effectiveFields"]
        self.assertEqual(eff["severity"]["value"], "CRITICAL")
        self.assertTrue(eff["severity"]["isOverridden"])
        self.assertEqual(eff["severity"]["originalAiValue"], initial_severity)
        self.assertEqual(eff["location"]["value"], "Aisle 4 - Dairy Case 2B")
        self.assertTrue(eff["location"]["isOverridden"])

    # -------------------------------------------------------------------------
    # 7. Re-analyze Feedback Endpoint
    # -------------------------------------------------------------------------
    def test_reanalyze_feedback_endpoint(self):
        raw_text = "Scanner 2 at self-checkout lane is frozen and not scanning barcodes"
        resp = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "channelType": "CUSTOMER_COMPLAINT",
                "rawText": raw_text
            }
        )
        fb_id = resp.json()["data"]["id"]

        reanalyze_resp = self.client.post(
            f"/api/v1/feedback/{fb_id}/analyze",
            headers=self._headers(self.store_token)
        )
        self.assertEqual(reanalyze_resp.status_code, 200)
        data = reanalyze_resp.json()["data"]
        self.assertEqual(data["processingStatus"], "analyzed")
        self.assertEqual(data["aiInterpretation"]["issueCategory"]["value"], "CHECKOUT_POS")

    # -------------------------------------------------------------------------
    # 8. RBAC Permissions on Review and Override
    # -------------------------------------------------------------------------
    def test_rbac_protection_on_human_review(self):
        raw_text = "Notice: Clean floor in aisle 1"
        resp = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "channelType": "MANUAL_ENTRY",
                "rawText": raw_text
            }
        )
        fb_id = resp.json()["data"]["id"]

        # Viewer role does NOT have permission to submit review overrides
        forbidden_resp = self.client.post(
            f"/api/v1/feedback/{fb_id}/review",
            headers=self._headers(self.viewer_token),
            json={
                "reviewNotes": "Unauthorized attempt",
                "overrides": {"severity": "LOW"}
            }
        )
        self.assertEqual(forbidden_resp.status_code, 403)

    # -------------------------------------------------------------------------
    # 9. PII Scrubbing and Span Mapping
    # -------------------------------------------------------------------------
    def test_pii_normalization_and_span_tracking(self):
        raw_with_pii = "Customer John Doe (phone 555-234-5678, email john.doe@example.com) reported broken shelf in aisle 3."
        norm_res = AIUnderstandingService.normalize_text(raw_with_pii)

        self.assertTrue(norm_res["hasPii"])
        self.assertIn("[PHONE_REDACTED]", norm_res["normalizedText"])
        self.assertIn("[EMAIL_REDACTED]", norm_res["normalizedText"])
        self.assertEqual(len(norm_res["piiSpans"]), 2)

    # -------------------------------------------------------------------------
    # 10. Audit Logging on Human Review and Override
    # -------------------------------------------------------------------------
    def test_audit_logging_on_human_override(self):
        resp = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "channelType": "CUSTOMER_COMPLAINT",
                "rawText": "Wet floor near entrance"
            }
        )
        fb_id = resp.json()["data"]["id"]

        self.client.post(
            f"/api/v1/feedback/{fb_id}/review",
            headers=self._headers(self.store_token),
            json={
                "reviewNotes": "Audited in person",
                "overrides": {"severity": "CRITICAL"}
            }
        )

        # Check audit trail
        audit_resp = self.client.get(
            "/api/v1/audit-logs",
            headers=self._headers(self.admin_token),
            params={"entityType": "FEEDBACK_ITEM", "entityId": fb_id}
        )
        self.assertEqual(audit_resp.status_code, 200)
        logs = audit_resp.json()["data"]
        override_logs = [log for log in logs if log["action"] == "FEEDBACK_REVIEWED_AND_OVERRIDDEN" and log["entityId"] == fb_id]
        self.assertGreater(len(override_logs), 0)


if __name__ == "__main__":
    unittest.main()

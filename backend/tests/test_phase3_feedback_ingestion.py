"""
R5 Operational Intelligence Platform - Phase 3 Automated Tests
Multichannel Feedback Ingestion, Pluggable Connectors, Duplicate Protection,
Multilingual Processing, Bulk Import (JSON & CSV), and 3-Stage Lifecycle.
"""

import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.seed import seed_database
from backend.app.core.security import create_access_token

class TestPhase3FeedbackIngestion(unittest.TestCase):
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
    # 1. Valid Input Across Ingestion Channels
    # -------------------------------------------------------------------------
    def test_valid_multichannel_feedback_ingestion(self):
        channels = [
            ("MANUAL_ENTRY", "STORE_ASSOCIATE", "Customer asked for gluten-free oats in Aisle 2"),
            ("CUSTOMER_COMPLAINT", "CUSTOMER", "The frozen yogurt dispenser is spraying sticky residue on the floor"),
            ("EMPLOYEE_FEEDBACK", "EMPLOYEE", "Restroom soap dispensers on 2nd floor have been empty all afternoon"),
            ("MAINTENANCE_REPORT", "MAINTENANCE_TECH", "Cooler 3A vibration noise exceeds 75dB, compressor belt needs tightening"),
            ("SURVEY_RESPONSE", "CUSTOMER", "Loved the fresh produce section, but checkout lane 4 was backed up 10 minutes"),
            ("OPERATIONAL_NOTE", "STORE_MANAGER", "Audit note: verified night-shift sanitation logged and wet floor cones stored in closet")
        ]

        for channel, submitter, text in channels:
            resp = self.client.post(
                "/api/v1/feedback",
                headers=self._headers(self.store_token),
                json={
                    "storeId": "store-104",
                    "channelType": channel,
                    "submitterType": submitter,
                    "rawText": text,
                    "privacyClassification": "INTERNAL"
                }
            )
            self.assertEqual(resp.status_code, 201, f"Failed for channel {channel}: {resp.text}")
            data = resp.json()["data"]
            self.assertEqual(data["channelType"], channel)
            self.assertEqual(data["submitterType"], submitter)
            self.assertEqual(data["rawText"], text) # Never overwritten
            self.assertIsNotNone(data["normalizedText"])
            self.assertIsNotNone(data["contentHash"])
            self.assertEqual(data["processingStatus"], "analyzed")
            self.assertEqual(data["status"], "NEW")
            self.assertFalse(data["isDuplicate"])
            self.assertIsNotNone(data["aiInterpretation"])
            self.assertIn("detectedIntent", data["aiInterpretation"])
            self.assertIn("summary", data["aiInterpretation"])

    # -------------------------------------------------------------------------
    # 2. Invalid Input Validation
    # -------------------------------------------------------------------------
    def test_invalid_input_validation(self):
        # Empty text
        resp1 = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={"storeId": "store-104", "rawText": "   "}
        )
        self.assertEqual(resp1.status_code, 422)
        self.assertIn("at least 3", resp1.json()["error"]["message"])

        # Text too short (< 3 characters)
        resp2 = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={"storeId": "store-104", "rawText": "hi"}
        )
        self.assertEqual(resp2.status_code, 422)
        self.assertIn("at least 3", resp2.json()["error"]["message"])

    # -------------------------------------------------------------------------
    # 3. Missing Context Validation
    # -------------------------------------------------------------------------
    def test_missing_context_validation(self):
        # Missing storeId entirely (using admin token without default storeId)
        resp1 = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.admin_token),
            json={"rawText": "Liquid spill observed on floor"}
        )
        self.assertEqual(resp1.status_code, 422)
        self.assertIn("storeId must be provided", resp1.json()["error"]["message"])

        # Non-existent storeId
        resp2 = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.admin_token),
            json={"storeId": "store-phantom-9999", "rawText": "Liquid spill on floor"}
        )
        self.assertEqual(resp2.status_code, 422)
        self.assertIn("does not exist", resp2.json()["error"]["message"])

    # -------------------------------------------------------------------------
    # 4. Duplicate Detection & Protection
    # -------------------------------------------------------------------------
    def test_duplicate_detection_and_rejection(self):
        unique_text = "Water pooling around ice cream display near Aisle 6"

        # First ingestion -> success, isDuplicate = False
        resp1 = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "rawText": unique_text,
                "channelType": "CUSTOMER_COMPLAINT"
            }
        )
        self.assertEqual(resp1.status_code, 201)
        data1 = resp1.json()["data"]
        id1 = data1["id"]
        self.assertFalse(data1["isDuplicate"])
        self.assertIsNone(data1["duplicateOfId"])

        # Second ingestion with same text -> flagged as duplicate, linked to id1
        resp2 = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "rawText": f"  {unique_text}   ", # Extra whitespace collapses to identical content hash
                "channelType": "CUSTOMER_COMPLAINT",
                "allowDuplicates": True
            }
        )
        self.assertEqual(resp2.status_code, 201)
        data2 = resp2.json()["data"]
        self.assertTrue(data2["isDuplicate"])
        self.assertEqual(data2["duplicateOfId"], id1)
        self.assertEqual(data2["contentHash"], data1["contentHash"])

        # Third ingestion with allowDuplicates = False -> raises 409 Conflict / DuplicateFeedbackError
        resp3 = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "rawText": unique_text,
                "allowDuplicates": False
            }
        )
        self.assertEqual(resp3.status_code, 409)
        self.assertIn("Duplicate feedback rejected", resp3.json()["error"]["message"])

    # -------------------------------------------------------------------------
    # 5. Multilingual Ingestion & Language Detection
    # -------------------------------------------------------------------------
    def test_multilingual_feedback_ingestion(self):
        samples = [
            ("es", "El congelador del pasillo 4 tiene una fuga de agua fria y hace ruido."),
            ("fr", "Le congelateur du rayon bio fait un bruit inhabituel et fuit sur le sol."),
            ("de", "Das Kuehlregal im Gang 2 tropft und der Boden ist sehr rutschig."),
            ("hi", "डेयरी सेक्शन में फर्श पर पानी बह रहा है और फिसलने का खतरा है।")
        ]

        for expected_lang, text in samples:
            resp = self.client.post(
                "/api/v1/feedback",
                headers=self._headers(self.store_token),
                json={
                    "storeId": "store-104",
                    "rawText": text,
                    "channelType": "CUSTOMER_COMPLAINT",
                    "languageCode": "auto"
                }
            )
            self.assertEqual(resp.status_code, 201)
            data = resp.json()["data"]
            self.assertEqual(data["languageCode"], expected_lang)
            self.assertEqual(data["rawText"], text)
            self.assertIsNotNone(data["aiInterpretation"])
            self.assertEqual(data["aiInterpretation"]["detectedLanguage"], expected_lang)

    # -------------------------------------------------------------------------
    # 6. PII Scrubbing & Privacy Classification
    # -------------------------------------------------------------------------
    def test_pii_detection_and_privacy_elevation(self):
        # Feedback containing customer phone number and email
        text_with_pii = "Please call customer Jane at 555-234-5678 or jane.doe@example.com regarding damaged strawberries."
        resp = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "rawText": text_with_pii,
                "privacyClassification": "INTERNAL"
            }
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()["data"]
        self.assertTrue(data["hasPii"])
        # Privacy should be elevated automatically to RESTRICTED_PII
        self.assertEqual(data["privacyClassification"], "RESTRICTED_PII")
        self.assertEqual(data["rawText"], text_with_pii) # Raw text remains verbatim

    # -------------------------------------------------------------------------
    # 7. Bulk JSON Ingestion
    # -------------------------------------------------------------------------
    def test_bulk_json_ingestion(self):
        bulk_items = [
            {"storeId": "store-104", "rawText": "Bulk item 1: Organic milk cartons leaking in dairy cooler", "channelType": "BULK_IMPORT"},
            {"storeId": "store-104", "rawText": "Bulk item 2: Missing pricing labels on cereal boxes", "channelType": "BULK_IMPORT"},
            {"storeId": "store-104", "rawText": "no", "channelType": "BULK_IMPORT"}, # Invalid < 3 chars
            {"storeId": "store-phantom", "rawText": "Bulk item 4: Invalid store context", "channelType": "BULK_IMPORT"} # Invalid store
        ]

        resp = self.client.post(
            "/api/v1/feedback/bulk",
            headers=self._headers(self.store_token),
            json={"items": bulk_items}
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()["data"]
        self.assertEqual(data["totalProcessed"], 4)
        self.assertEqual(data["succeeded"], 2)
        self.assertEqual(data["failed"], 2)
        self.assertEqual(len(data["errors"]), 2)

    # -------------------------------------------------------------------------
    # 8. Bulk CSV Ingestion
    # -------------------------------------------------------------------------
    def test_bulk_csv_ingestion(self):
        csv_payload = (
            "rawText,channelType,submitterType,languageCode\n"
            "Produce misting nozzles spraying customer walking path,MAINTENANCE_REPORT,MAINTENANCE_TECH,en\n"
            "Self checkout lane 2 receipt printer jammed,CUSTOMER_COMPLAINT,CUSTOMER,en\n"
            "Un pallet de cajas bloquea la salida de emergencia pasillo 9,EMPLOYEE_FEEDBACK,EMPLOYEE,es\n"
        )

        resp = self.client.post(
            "/api/v1/feedback/bulk/csv?storeId=store-104",
            headers={
                "Authorization": f"Bearer {self.store_token}",
                "Content-Type": "text/plain"
            },
            content=csv_payload
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()["data"]
        self.assertEqual(data["totalProcessed"], 3)
        self.assertEqual(data["succeeded"], 3)
        self.assertEqual(data["failed"], 0)

    # -------------------------------------------------------------------------
    # 9. Processing Status Lifecycle & Review
    # -------------------------------------------------------------------------
    def test_processing_status_lifecycle_and_review(self):
        resp = self.client.post(
            "/api/v1/feedback",
            headers=self._headers(self.store_token),
            json={
                "storeId": "store-104",
                "rawText": "Freezer aisle tile cracked and causing cart wheel to catch",
                "channelType": "CUSTOMER_COMPLAINT"
            }
        )
        self.assertEqual(resp.status_code, 201)
        fb_id = resp.json()["data"]["id"]
        self.assertEqual(resp.json()["data"]["processingStatus"], "analyzed")

        # Advance to 'reviewed' with review notes
        patch_resp = self.client.patch(
            f"/api/v1/feedback/{fb_id}/status",
            headers=self._headers(self.store_token),
            json={
                "processingStatus": "reviewed",
                "status": "TRIAGED",
                "reviewNotes": "Verified by David Miller (Store Lead); work order planned for evening shift."
            }
        )
        self.assertEqual(patch_resp.status_code, 200)
        updated = patch_resp.json()["data"]
        self.assertEqual(updated["processingStatus"], "reviewed")
        self.assertEqual(updated["status"], "TRIAGED")
        self.assertIn("reviewNotes", updated["metadata"])
        self.assertEqual(updated["metadata"]["reviewNotes"], "Verified by David Miller (Store Lead); work order planned for evening shift.")

    # -------------------------------------------------------------------------
    # 10. Filtered Query & Pagination
    # -------------------------------------------------------------------------
    def test_feedback_query_filtering_and_pagination(self):
        resp = self.client.get(
            "/api/v1/feedback?storeId=store-104&page=1&limit=5",
            headers=self._headers(self.store_token)
        )
        self.assertEqual(resp.status_code, 200)
        res = resp.json()
        self.assertIn("data", res)
        self.assertIn("meta", res)
        self.assertGreaterEqual(len(res["data"]), 1)
        self.assertEqual(res["meta"]["page"], 1)
        self.assertEqual(res["meta"]["limit"], 5)
        self.assertGreaterEqual(res["meta"]["total"], 1)

if __name__ == "__main__":
    unittest.main()

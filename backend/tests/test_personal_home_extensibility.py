import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.seed import seed_database

class TestPersonalHomeExtensibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(force=True)
        cls.client = TestClient(app)

        # Login User
        res = cls.client.post("/api/v1/auth/login", json={
            "email": "storemanager@apex.com",
            "password": "Password123!"
        })
        cls.token = res.json()["data"]["token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_register_home_appliance_isolated(self):
        # Register a TV
        resp = self.client.post("/api/v1/personal-home/appliances", headers=self.headers, json={
            "applianceType": "TV",
            "brand": "Sony",
            "modelNumber": "XR-65A80K",
            "serialNumber": "SN-SONY-77192",
            "purchaseDate": "2024-01-10",
            "warrantyUntil": "2027-01-10"
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.json()["data"]
        self.assertEqual(data["applianceType"], "TV")
        self.assertEqual(data["brand"], "Sony")
        appliance_id = data["id"]

        # File a warranty service ticket
        ticket_resp = self.client.post("/api/v1/personal-home/tickets", headers=self.headers, json={
            "applianceId": appliance_id,
            "complaintDescription": "OLED panel flickers green line on HDMI 2 port.",
            "classifiedCategory": "DISPLAY_PANEL",
            "routedServiceChannel": "Sony Authorized Repair Center"
        })
        self.assertEqual(ticket_resp.status_code, 201)
        ticket = ticket_resp.json()["data"]
        self.assertEqual(ticket["status"], "SUBMITTED")
        self.assertTrue(ticket["externalReferenceId"].startswith("EXT-SON-"))

        # Verify that personal appliances and tickets do NOT leak into retail store issues
        retail_issues = self.client.get("/api/v1/issues", headers=self.headers).json()["data"]
        self.assertFalse(any("XR-65A80K" in i["title"] or "XR-65A80K" in i["description"] for i in retail_issues))

if __name__ == "__main__":
    unittest.main()

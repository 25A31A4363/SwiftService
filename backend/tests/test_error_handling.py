import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestErrorHandling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_401_unauthorized_error_format(self):
        resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")
        self.assertIn("timestamp", data["error"])
        self.assertIn("path", data["error"])

    def test_404_not_found_error_format(self):
        # Login first to bypass 401
        res = self.client.post("/api/v1/auth/login", json={
            "email": "orgadmin@apex.com",
            "password": "Password123!"
        })
        token = res.json()["data"]["token"]

        resp = self.client.get("/api/v1/issues/non-existent-issue-id", headers={
            "Authorization": f"Bearer {token}"
        })
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "NOT_FOUND")
        self.assertIn("timestamp", data["error"])

    def test_422_validation_error_format(self):
        res = self.client.post("/api/v1/auth/login", json={
            "email": "orgadmin@apex.com",
            "password": "Password123!"
        })
        token = res.json()["data"]["token"]

        # Missing required rawText and sourceType
        resp = self.client.post("/api/v1/feedback", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "storeId": "store-104"
        })
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertIsInstance(data["error"]["details"], list)
        self.assertGreater(len(data["error"]["details"]), 0)

if __name__ == "__main__":
    unittest.main()

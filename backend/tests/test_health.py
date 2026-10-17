import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["status"], "healthy")
        self.assertIn("uptimeSeconds", data["data"])

    def test_db_health_endpoint(self):
        resp = self.client.get("/api/v1/health/db")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["connected"])
        self.assertGreater(data["data"]["counts"]["organizations"], 0)
        self.assertGreater(data["data"]["counts"]["stores"], 0)

if __name__ == "__main__":
    unittest.main()

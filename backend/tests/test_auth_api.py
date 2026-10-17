import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.seed import seed_database

class TestAuthApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(force=True)
        cls.client = TestClient(app)

    def test_login_success_org_admin(self):
        resp = self.client.post("/api/v1/auth/login", json={
            "email": "orgadmin@apex.com",
            "password": "Password123!"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("token", data["data"])
        self.assertEqual(data["data"]["user"]["role"], "ORGANIZATION_ADMIN")

    def test_login_invalid_password(self):
        resp = self.client.post("/api/v1/auth/login", json={
            "email": "orgadmin@apex.com",
            "password": "WrongPassword999"
        })
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")

    def test_login_non_existent_email(self):
        resp = self.client.post("/api/v1/auth/login", json={
            "email": "nobody@apex.com",
            "password": "Password123!"
        })
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")

    def test_protected_route_without_token(self):
        resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")

    def test_protected_route_with_valid_token(self):
        login_resp = self.client.post("/api/v1/auth/login", json={
            "email": "storemanager@apex.com",
            "password": "Password123!"
        })
        token = login_resp.json()["data"]["token"]

        me_resp = self.client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        self.assertEqual(me_resp.status_code, 200)
        user_data = me_resp.json()["data"]
        self.assertEqual(user_data["email"], "storemanager@apex.com")
        self.assertEqual(user_data["role"], "STORE_MANAGER")
        self.assertEqual(user_data["storeId"], "store-104")

if __name__ == "__main__":
    unittest.main()

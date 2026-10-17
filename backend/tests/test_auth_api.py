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

    def test_update_profile_success_and_login_with_new_email(self):
        # 1. Login as store manager
        login_resp = self.client.post("/api/v1/auth/login", json={
            "email": "storemanager@apex.com",
            "password": "Password123!"
        })
        token = login_resp.json()["data"]["token"]

        # 2. Update email and full name
        update_resp = self.client.put("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "email": "david.miller.updated@apex.com",
            "fullName": "David Miller (Updated Lead)"
        })
        self.assertEqual(update_resp.status_code, 200)
        updated_data = update_resp.json()["data"]
        self.assertEqual(updated_data["email"], "david.miller.updated@apex.com")
        self.assertEqual(updated_data["fullName"], "David Miller (Updated Lead)")

        # 3. Verify get_me reflects the change
        me_resp = self.client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        self.assertEqual(me_resp.json()["data"]["email"], "david.miller.updated@apex.com")

        # 4. Old email should no longer log in
        old_login = self.client.post("/api/v1/auth/login", json={
            "email": "storemanager@apex.com",
            "password": "Password123!"
        })
        self.assertEqual(old_login.status_code, 401)

        # 5. New email must authenticate successfully with original password
        new_login = self.client.post("/api/v1/auth/login", json={
            "email": "david.miller.updated@apex.com",
            "password": "Password123!"
        })
        self.assertEqual(new_login.status_code, 200)

        # Revert email back for other tests
        new_token = new_login.json()["data"]["token"]
        self.client.put("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {new_token}"
        }, json={
            "email": "storemanager@apex.com",
            "fullName": "David Miller (Store 104 Lead)"
        })

    def test_update_profile_duplicate_email_conflict(self):
        login_resp = self.client.post("/api/v1/auth/login", json={
            "email": "storemanager@apex.com",
            "password": "Password123!"
        })
        token = login_resp.json()["data"]["token"]

        # Attempt to change email to existing admin email
        resp = self.client.put("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "email": "orgadmin@apex.com"
        })
        self.assertEqual(resp.status_code, 409)
        self.assertIn("already assigned", resp.json()["error"]["message"])

    def test_change_password_flow(self):
        # 1. Login with initial password
        login_resp = self.client.post("/api/v1/auth/login", json={
            "email": "maintenance@apex.com",
            "password": "Password123!"
        })
        token = login_resp.json()["data"]["token"]

        # 2. Reject wrong current password
        bad_change = self.client.post("/api/v1/auth/change-password", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "currentPassword": "IncorrectPassword1!",
            "newPassword": "NewSecurePassword456!"
        })
        self.assertEqual(bad_change.status_code, 401)
        self.assertIn("Current password is incorrect", bad_change.json()["error"]["message"])

        # 3. Successful password change
        good_change = self.client.post("/api/v1/auth/change-password", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "currentPassword": "Password123!",
            "newPassword": "NewSecurePassword456!"
        })
        self.assertEqual(good_change.status_code, 200)

        # 4. Old password should fail
        old_auth = self.client.post("/api/v1/auth/login", json={
            "email": "maintenance@apex.com",
            "password": "Password123!"
        })
        self.assertEqual(old_auth.status_code, 401)

        # 5. New password must authenticate successfully
        new_auth = self.client.post("/api/v1/auth/login", json={
            "email": "maintenance@apex.com",
            "password": "NewSecurePassword456!"
        })
        self.assertEqual(new_auth.status_code, 200)

        # Revert password back
        new_token = new_auth.json()["data"]["token"]
        self.client.post("/api/v1/auth/change-password", headers={
            "Authorization": f"Bearer {new_token}"
        }, json={
            "currentPassword": "NewSecurePassword456!",
            "newPassword": "Password123!"
        })

    def test_unauthorized_profile_update_rejected(self):
        resp = self.client.put("/api/v1/auth/me", json={
            "email": "hacker@apex.com"
        })
        self.assertEqual(resp.status_code, 401)

if __name__ == "__main__":
    unittest.main()

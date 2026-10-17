import unittest
from backend.app.core.rbac import (
    Role, Permission, has_permission, can_access_store, ROLE_PERMISSIONS
)

class TestRbacUnit(unittest.TestCase):
    def test_all_seven_roles_defined(self):
        expected_roles = {
            "ORGANIZATION_ADMIN",
            "OPERATIONS_MANAGER",
            "REGIONAL_MANAGER",
            "STORE_MANAGER",
            "MAINTENANCE_TEAM",
            "ANALYST",
            "VIEWER",
            "CUSTOMER"
        }
        actual_roles = {r.value for r in Role}
        self.assertEqual(expected_roles, actual_roles)

    def test_org_admin_has_all_permissions(self):
        for perm in Permission:
            self.assertTrue(
                has_permission(Role.ORGANIZATION_ADMIN.value, perm),
                f"Org Admin must have permission {perm.value}"
            )

    def test_viewer_has_read_only_permissions(self):
        self.assertTrue(has_permission(Role.VIEWER.value, Permission.ISSUE_READ))
        self.assertTrue(has_permission(Role.VIEWER.value, Permission.FEEDBACK_READ))
        self.assertFalse(has_permission(Role.VIEWER.value, Permission.ISSUE_TRIAGE))
        self.assertFalse(has_permission(Role.VIEWER.value, Permission.ACTION_APPROVE))
        self.assertFalse(has_permission(Role.VIEWER.value, Permission.ORG_MANAGE))

    def test_store_manager_permissions(self):
        self.assertTrue(has_permission(Role.STORE_MANAGER.value, Permission.ACTION_APPROVE))
        self.assertTrue(has_permission(Role.STORE_MANAGER.value, Permission.ACTION_OVERRIDE))
        self.assertTrue(has_permission(Role.STORE_MANAGER.value, Permission.ISSUE_OVERRIDE))
        self.assertFalse(has_permission(Role.STORE_MANAGER.value, Permission.ORG_MANAGE))

    def test_maintenance_team_permissions(self):
        self.assertTrue(has_permission(Role.MAINTENANCE_TEAM.value, Permission.ACTION_EXECUTE))
        self.assertTrue(has_permission(Role.MAINTENANCE_TEAM.value, Permission.RESOLUTION_CREATE))
        self.assertFalse(has_permission(Role.MAINTENANCE_TEAM.value, Permission.ACTION_APPROVE))
        self.assertFalse(has_permission(Role.MAINTENANCE_TEAM.value, Permission.ISSUE_OVERRIDE))

    def test_store_boundary_access_control(self):
        # Org Admin can access any store
        admin_user = {"role": Role.ORGANIZATION_ADMIN.value}
        self.assertTrue(can_access_store(admin_user, "store-104", "reg-pnw"))
        self.assertTrue(can_access_store(admin_user, "store-201", "reg-na"))

        # Regional Manager can only access stores in their assigned region
        reg_user = {"role": Role.REGIONAL_MANAGER.value, "region_id": "reg-pnw"}
        self.assertTrue(can_access_store(reg_user, "store-104", "reg-pnw"))
        self.assertFalse(can_access_store(reg_user, "store-201", "reg-na"))

        # Store Manager can only access their specific store
        store_user = {"role": Role.STORE_MANAGER.value, "store_id": "store-104"}
        self.assertTrue(can_access_store(store_user, "store-104", "reg-pnw"))
        self.assertFalse(can_access_store(store_user, "store-108", "reg-pnw"))

if __name__ == "__main__":
    unittest.main()

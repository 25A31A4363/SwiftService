import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.seed import seed_database

class TestPhase2OrganizationLayer(unittest.TestCase):
    def setUp(self):
        seed_database(force=True)
        self.client = TestClient(app)

        # 1. Login Org Admin (Full permissions)
        res_admin = self.client.post("/api/v1/auth/login", json={
            "email": "orgadmin@apex.com",
            "password": "Password123!"
        })
        self.admin_token = res_admin.json()["data"]["token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

        # 2. Login Operations Manager
        res_ops = self.client.post("/api/v1/auth/login", json={
            "email": "opsmanager@apex.com",
            "password": "Password123!"
        })
        self.ops_token = res_ops.json()["data"]["token"]
        self.ops_headers = {"Authorization": f"Bearer {self.ops_token}"}

        # 3. Login Store Manager (Store 104)
        res_sm = self.client.post("/api/v1/auth/login", json={
            "email": "storemanager@apex.com",
            "password": "Password123!"
        })
        self.sm_token = res_sm.json()["data"]["token"]
        self.sm_headers = {"Authorization": f"Bearer {self.sm_token}"}

        # 4. Login Viewer (Read-only)
        res_vw = self.client.post("/api/v1/auth/login", json={
            "email": "viewer@apex.com",
            "password": "Password123!"
        })
        self.vw_token = res_vw.json()["data"]["token"]
        self.vw_headers = {"Authorization": f"Bearer {self.vw_token}"}

    # =========================================================================
    # 1. Organization Management
    # =========================================================================
    def test_organization_crud_and_validation(self):
        # Create
        create_resp = self.client.post("/api/v1/organizations", headers=self.admin_headers, json={
            "name": "Global Retail Partners",
            "code": "GRP",
            "description": "European and transatlantic retail partner network",
            "status": "ACTIVE"
        })
        self.assertEqual(create_resp.status_code, 201)
        org = create_resp.json()["data"]
        org_id = org["id"]
        self.assertEqual(org["code"], "GRP")

        # Conflict on duplicate code
        dup_resp = self.client.post("/api/v1/organizations", headers=self.admin_headers, json={
            "name": "Another Org",
            "code": "GRP"
        })
        self.assertEqual(dup_resp.status_code, 409)

        # Get single
        get_resp = self.client.get(f"/api/v1/organizations/{org_id}", headers=self.admin_headers)
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["data"]["name"], "Global Retail Partners")

        # Update
        up_resp = self.client.put(f"/api/v1/organizations/{org_id}", headers=self.admin_headers, json={
            "name": "Global Retail Partners Holdings",
            "description": "Updated corporate holding entity"
        })
        self.assertEqual(up_resp.status_code, 200)
        self.assertEqual(up_resp.json()["data"]["name"], "Global Retail Partners Holdings")

        # Search / List with pagination
        list_resp = self.client.get("/api/v1/organizations?q=Holdings", headers=self.admin_headers)
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.json()["data"]), 1)
        self.assertEqual(list_resp.json()["meta"]["total"], 1)

        # Delete
        del_resp = self.client.delete(f"/api/v1/organizations/{org_id}", headers=self.admin_headers)
        self.assertEqual(del_resp.status_code, 200)

        # Verify not found after deletion
        not_found = self.client.get(f"/api/v1/organizations/{org_id}", headers=self.admin_headers)
        self.assertEqual(not_found.status_code, 404)

    # =========================================================================
    # 2. Region Management & Assignment
    # =========================================================================
    def test_region_crud_and_assignment(self):
        # Create
        create_resp = self.client.post("/api/v1/regions", headers=self.admin_headers, json={
            "organizationId": "org-apex-01",
            "name": "Mid-Atlantic Corridor",
            "code": "REG-MIDATL",
            "description": "Washington DC, Philadelphia and Baltimore operational stores"
        })
        self.assertEqual(create_resp.status_code, 201)
        reg = create_resp.json()["data"]
        reg_id = reg["id"]
        self.assertEqual(reg["code"], "REG-MIDATL")

        # Duplicate code in same org rejected
        dup_resp = self.client.post("/api/v1/regions", headers=self.admin_headers, json={
            "organizationId": "org-apex-01",
            "name": "Duplicate Region",
            "code": "REG-MIDATL"
        })
        self.assertEqual(dup_resp.status_code, 409)

        # Update lead user
        up_resp = self.client.put(f"/api/v1/regions/{reg_id}", headers=self.admin_headers, json={
            "leadUserId": "usr-reg",
            "description": "Assigned VP of Regional Operations"
        })
        self.assertEqual(up_resp.status_code, 200)
        self.assertEqual(up_resp.json()["data"]["leadUserId"], "usr-reg")

        # List regions
        list_resp = self.client.get("/api/v1/regions?organizationId=org-apex-01", headers=self.admin_headers)
        self.assertEqual(list_resp.status_code, 200)
        reg_codes = [r["code"] for r in list_resp.json()["data"]]
        self.assertIn("REG-MIDATL", reg_codes)

        # Delete
        del_resp = self.client.delete(f"/api/v1/regions/{reg_id}", headers=self.admin_headers)
        self.assertEqual(del_resp.status_code, 200)

    # =========================================================================
    # 3. Store Management: Status, Metadata & Scoping
    # =========================================================================
    def test_store_crud_metadata_and_operating_status(self):
        # Create store with operating status and rich metadata
        create_resp = self.client.post("/api/v1/stores", headers=self.admin_headers, json={
            "organizationId": "org-apex-01",
            "regionId": "reg-pnw-01",
            "name": "Apex Innovation Store - Redmond Tech City",
            "storeNumber": 310,
            "address": {
                "street": "16000 NE 36th Way",
                "city": "Redmond",
                "state": "WA",
                "postalCode": "98052",
                "country": "USA"
            },
            "timezone": "America/Los_Angeles",
            "operatingStatus": "OPERATIONAL",
            "metadata": {
                "formatTier": "FLAGSHIP_AUTOMATED",
                "squareFootage": 95000,
                "contactPhone": "+1-425-555-0310",
                "openingHours": "24_HOURS",
                "coldChainZoneCount": 8
            }
        })
        self.assertEqual(create_resp.status_code, 201)
        store = create_resp.json()["data"]
        store_id = store["id"]
        self.assertEqual(store["operatingStatus"], "OPERATIONAL")
        self.assertEqual(store["metadata"]["formatTier"], "FLAGSHIP_AUTOMATED")

        # Quick Operating Status Transition via PATCH
        status_resp = self.client.patch(f"/api/v1/stores/{store_id}/status", headers=self.admin_headers, json={
            "operatingStatus": "MAINTENANCE_HOLD",
            "justification": "Emergency automated chiller system firmware patch"
        })
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.json()["data"]["operatingStatus"], "MAINTENANCE_HOLD")

        # Filter stores by operatingStatus
        maint_list = self.client.get("/api/v1/stores?operatingStatus=MAINTENANCE_HOLD", headers=self.admin_headers)
        self.assertEqual(maint_list.status_code, 200)
        maint_ids = [s["id"] for s in maint_list.json()["data"]]
        self.assertIn(store_id, maint_ids)
        self.assertIn("store-205", maint_ids)  # Seeded Cambridge store

        # Clean up
        self.client.delete(f"/api/v1/stores/{store_id}", headers=self.admin_headers)

    # =========================================================================
    # 4. Team Management: Specialization, Responsibility & Membership
    # =========================================================================
    def test_team_crud_specialization_and_members(self):
        # Create specialized team
        team_resp = self.client.post("/api/v1/teams", headers=self.admin_headers, json={
            "organizationId": "org-apex-01",
            "regionId": "reg-pnw-01",
            "name": "Pacific Northwest Fire & Life Safety Unit",
            "teamType": "FIRE_SAFETY",
            "slaTier": "MISSION_CRITICAL",
            "contactEmail": "safety-pnw@apex.com",
            "responsibility": "Emergency fire suppression, smoke damper diagnostics, and egress hazard clearance",
            "specialization": "CRITICAL_INFRASTRUCTURE",
            "escalationContact": "+1-206-555-FIRE",
            "escalationTier": "TIER_1",
            "leadUserId": "usr-maint"
        })
        self.assertEqual(team_resp.status_code, 201)
        team = team_resp.json()["data"]
        team_id = team["id"]
        self.assertEqual(team["specialization"], "CRITICAL_INFRASTRUCTURE")
        self.assertEqual(team["escalationTier"], "TIER_1")

        # Assign team member
        add_member_resp = self.client.post(f"/api/v1/teams/{team_id}/members", headers=self.admin_headers, json={
            "userId": "usr-maint",
            "roleInTeam": "CHIEF_FIRE_ENGINEER",
            "isPrimary": True
        })
        self.assertEqual(add_member_resp.status_code, 201)
        self.assertEqual(add_member_resp.json()["data"]["roleInTeam"], "CHIEF_FIRE_ENGINEER")

        # Get team members
        members_resp = self.client.get(f"/api/v1/teams/{team_id}/members", headers=self.admin_headers)
        self.assertEqual(members_resp.status_code, 200)
        self.assertEqual(len(members_resp.json()["data"]), 1)
        self.assertEqual(members_resp.json()["data"][0]["userId"], "usr-maint")

        # Remove team member
        rm_resp = self.client.delete(f"/api/v1/teams/{team_id}/members/usr-maint", headers=self.admin_headers)
        self.assertEqual(rm_resp.status_code, 200)

        # Delete team
        self.client.delete(f"/api/v1/teams/{team_id}", headers=self.admin_headers)

    # =========================================================================
    # 5. User Management & Role Assignment
    # =========================================================================
    def test_user_management_and_role_assignment(self):
        # Create user
        usr_resp = self.client.post("/api/v1/users", headers=self.admin_headers, json={
            "organizationId": "org-apex-01",
            "email": "testtech@apex.com",
            "password": "Password123!",
            "fullName": "Jordan Sparks (Automation Tech)",
            "role": "MAINTENANCE_TEAM",
            "storeId": "store-104",
            "teamId": "team-hvac-pnw",
            "isActive": True
        })
        self.assertEqual(usr_resp.status_code, 201)
        u = usr_resp.json()["data"]
        user_id = u["id"]
        self.assertEqual(u["email"], "testtech@apex.com")
        self.assertEqual(u["role"], "MAINTENANCE_TEAM")
        self.assertEqual(u["storeId"], "store-104")

        # Duplicate email rejected
        dup_usr = self.client.post("/api/v1/users", headers=self.admin_headers, json={
            "organizationId": "org-apex-01",
            "email": "testtech@apex.com",
            "password": "Password123!",
            "fullName": "Clone User",
            "role": "STORE_MANAGER"
        })
        self.assertEqual(dup_usr.status_code, 409)

        # Search users
        search_resp = self.client.get("/api/v1/users?q=Jordan", headers=self.admin_headers)
        self.assertEqual(search_resp.status_code, 200)
        self.assertEqual(len(search_resp.json()["data"]), 1)

        # Update user role to Operations Manager
        up_usr = self.client.put(f"/api/v1/users/{user_id}", headers=self.admin_headers, json={
            "role": "OPERATIONS_MANAGER",
            "fullName": "Jordan Sparks (Promoted Ops)"
        })
        self.assertEqual(up_usr.status_code, 200)
        self.assertEqual(up_usr.json()["data"]["role"], "OPERATIONS_MANAGER")

        # Self-deletion prevented (ValidationError -> 422)
        del_self = self.client.delete("/api/v1/users/usr-admin", headers=self.admin_headers)
        self.assertEqual(del_self.status_code, 422)

        # Delete created user
        del_usr = self.client.delete(f"/api/v1/users/{user_id}", headers=self.admin_headers)
        self.assertEqual(del_usr.status_code, 200)

    # =========================================================================
    # 6. Roles & Role Permissions Matrix
    # =========================================================================
    def test_roles_and_permissions_matrix(self):
        # Get roles list
        roles_resp = self.client.get("/api/v1/roles", headers=self.admin_headers)
        self.assertEqual(roles_resp.status_code, 200)
        roles = roles_resp.json()["data"]
        role_names = [r["name"] for r in roles]
        self.assertIn("ORGANIZATION_ADMIN", role_names)
        self.assertIn("STORE_MANAGER", role_names)

        # Get full permissions matrix
        matrix_resp = self.client.get("/api/v1/roles/permissions-matrix", headers=self.admin_headers)
        self.assertEqual(matrix_resp.status_code, 200)
        matrix = matrix_resp.json()["data"]
        self.assertIn("roles", matrix)
        self.assertIn("allPermissions", matrix)
        self.assertGreaterEqual(len(matrix["allPermissions"]), 25)

        # Create custom role
        custom_role = self.client.post("/api/v1/roles", headers=self.admin_headers, json={
            "name": "FACILITIES_DISPATCHER",
            "description": "Triage coordinator for physical assets and work orders",
            "permissions": ["store:read", "team:read", "action:read", "action:approve", "issue:read", "issue:triage"]
        })
        self.assertEqual(custom_role.status_code, 201)
        c_role = custom_role.json()["data"]
        c_id = c_role["id"]
        self.assertIn("action:approve", c_role["permissions"])

        # Update custom role permissions
        up_role = self.client.put(f"/api/v1/roles/{c_id}/permissions", headers=self.admin_headers, json={
            "permissions": ["store:read", "action:read"]
        })
        self.assertEqual(up_role.status_code, 200)
        self.assertEqual(len(up_role.json()["data"]["permissions"]), 2)

        # Attempt to delete built-in system role (rejected with ValidationError -> 422)
        sys_del = self.client.delete("/api/v1/roles/role-admin", headers=self.admin_headers)
        self.assertEqual(sys_del.status_code, 422)

        # Delete custom role
        del_custom = self.client.delete(f"/api/v1/roles/{c_id}", headers=self.admin_headers)
        self.assertEqual(del_custom.status_code, 200)

    # =========================================================================
    # 7. Operational Ownership Mapping
    # =========================================================================
    def test_operational_ownership_mapping_crud(self):
        # Create mapping
        map_resp = self.client.post("/api/v1/ownership-mappings", headers=self.admin_headers, json={
            "organizationId": "org-apex-01",
            "regionId": "reg-pnw-01",
            "storeId": "store-108",
            "operationalDomain": "HVAC_CHILLERS",
            "primaryTeamId": "team-hvac-pnw",
            "secondaryTeamId": "team-janitorial-104",
            "escalationUserId": "usr-reg",
            "slaMinutes": 40,
            "autoEscalateHours": 2.5,
            "description": "Bellevue Crossroads store chiller outage ownership"
        })
        self.assertEqual(map_resp.status_code, 201)
        m = map_resp.json()["data"]
        map_id = m["id"]
        self.assertEqual(m["operationalDomain"], "HVAC_CHILLERS")
        self.assertEqual(m["slaMinutes"], 40)

        # List mappings
        list_maps = self.client.get("/api/v1/ownership-mappings?domain=HVAC_CHILLERS", headers=self.admin_headers)
        self.assertEqual(list_maps.status_code, 200)
        self.assertEqual(len(list_maps.json()["data"]), 1)

        # Update mapping
        up_map = self.client.put(f"/api/v1/ownership-mappings/{map_id}", headers=self.admin_headers, json={
            "slaMinutes": 30,
            "autoEscalateHours": 1.5
        })
        self.assertEqual(up_map.status_code, 200)
        self.assertEqual(up_map.json()["data"]["slaMinutes"], 30)

        # Delete mapping
        del_map = self.client.delete(f"/api/v1/ownership-mappings/{map_id}", headers=self.admin_headers)
        self.assertEqual(del_map.status_code, 200)

    # =========================================================================
    # 8. Operational Lineage & Tracing (Org -> Region -> Store -> Team -> User)
    # =========================================================================
    def test_operational_trace_lineage(self):
        # Trace by Store 104 and REFRIGERATION_HVAC domain
        trace_resp = self.client.get(
            "/api/v1/hierarchy/trace?storeId=store-104&domain=REFRIGERATION_HVAC",
            headers=self.admin_headers
        )
        self.assertEqual(trace_resp.status_code, 200)
        trace = trace_resp.json()["data"]

        # Verify lineage contains complete operational hierarchy
        chain = trace["lineageChain"]
        types_in_chain = [n["type"] for n in chain]

        self.assertIn("ORGANIZATION", types_in_chain)
        self.assertIn("REGION", types_in_chain)
        self.assertIn("STORE", types_in_chain)
        self.assertIn("TEAM", types_in_chain)
        self.assertIn("USER", types_in_chain)

        # Verify exact node details
        self.assertEqual(trace["organization"]["details"]["code"], "APEX")
        self.assertEqual(trace["store"]["name"], "Apex Supercenter - Seattle Downtown")
        self.assertEqual(trace["primaryTeam"]["name"], "Regional Commercial HVAC & Refrigeration")
        self.assertIn("Apex Retail International", trace["traceSummary"])
        self.assertIn("Seattle Downtown", trace["traceSummary"])

        # Trace by Asset (asset-cooler-104b)
        trace_asset = self.client.get(
            "/api/v1/hierarchy/trace?entityType=ASSET&entityId=asset-cooler-104b",
            headers=self.admin_headers
        )
        self.assertEqual(trace_asset.status_code, 200)
        t_asset = trace_asset.json()["data"]
        self.assertEqual(t_asset["store"]["id"], "store-104")

    # =========================================================================
    # 9. RBAC Permission Boundaries
    # =========================================================================
    def test_rbac_security_boundaries(self):
        # Store Manager cannot create organization (Forbidden)
        resp_sm_org = self.client.post("/api/v1/organizations", headers=self.sm_headers, json={
            "name": "Illegal Org",
            "code": "ILL"
        })
        self.assertEqual(resp_sm_org.status_code, 403)

        # Store Manager cannot create user (Forbidden)
        resp_sm_usr = self.client.post("/api/v1/users", headers=self.sm_headers, json={
            "organizationId": "org-apex-01",
            "email": "hacked@apex.com",
            "password": "Password123!",
            "fullName": "Fake User",
            "role": "ORGANIZATION_ADMIN"
        })
        self.assertEqual(resp_sm_usr.status_code, 403)

        # Viewer cannot modify store status (Forbidden)
        resp_vw_store = self.client.patch("/api/v1/stores/store-104/status", headers=self.vw_headers, json={
            "operatingStatus": "DECOMMISSIONED"
        })
        self.assertEqual(resp_vw_store.status_code, 403)

        # Unauthenticated request rejected (Unauthorized)
        unauth_resp = self.client.get("/api/v1/users")
        self.assertEqual(unauth_resp.status_code, 401)

    # =========================================================================
    # 10. Audit Logging Verification
    # =========================================================================
    def test_audit_logs_for_operational_changes(self):
        # Trigger an operational change to generate audit log
        patch_res = self.client.patch("/api/v1/stores/store-104/status", headers=self.admin_headers, json={
            "operatingStatus": "OPERATIONAL",
            "justification": "Routine audit trail verification"
        })
        self.assertEqual(patch_res.status_code, 200)

        # Fetch audit logs for STORE entity type
        audit_resp = self.client.get("/api/v1/audit-logs?entityType=STORE", headers=self.admin_headers)
        self.assertEqual(audit_resp.status_code, 200)
        logs = audit_resp.json()["data"]
        self.assertGreater(len(logs), 0)
        actions = [log["action"] for log in logs]
        self.assertTrue(any("STORE" in a for a in actions))

if __name__ == "__main__":
    unittest.main()

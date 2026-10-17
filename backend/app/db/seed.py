import json
import hashlib
from datetime import datetime, timezone, timedelta
from backend.app.core.security import hash_password
from backend.app.core.logger import logger
from backend.app.core.rbac import Role, ROLE_PERMISSIONS
from backend.app.db.database import get_connection, init_db
from backend.app.services.brief_service import BriefService

def seed_database(force: bool = False) -> None:
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Check if already seeded
        cur.execute("SELECT COUNT(*) FROM organizations;")
        if cur.fetchone()[0] > 0 and not force:
            logger.info("Database already seeded with organizational entities.")
            return

        if force:
            logger.info("Force flag enabled: purging existing tables for clean seed...")
            tables = [
                "operational_briefs", "outcome_measurements", "personal_service_tickets", "personal_home_appliances", "audit_logs",
                "evidence", "resolutions", "action_plans", "alerts", "issue_feedback_links",
                "issues", "follow_up_exchanges", "feedback_items", "operational_ownership_mappings",
                "team_members", "users", "operational_teams", "assets", "departments",
                "stores", "regions", "organizations", "role_permissions", "roles"
            ]
            for t in tables:
                cur.execute(f"DELETE FROM {t};")

        logger.info("Seeding realistic retail organization and operational baseline data...")
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        four_days_ago = (now_dt - timedelta(days=4)).isoformat()
        three_days_ago = (now_dt - timedelta(days=3)).isoformat()
        two_days_ago = (now_dt - timedelta(days=2)).isoformat()
        yesterday = (now_dt - timedelta(days=1)).isoformat()
        two_hours_ago = (now_dt - timedelta(hours=2)).isoformat()
        one_hour_ago = (now_dt - timedelta(hours=1)).isoformat()
        thirty_mins_ago = (now_dt - timedelta(minutes=30)).isoformat()
        sla_deadline = (now_dt + timedelta(minutes=45)).isoformat()

        # 0. Roles & Role Permissions Matrix
        roles_definitions = [
            ("role-admin", Role.ORGANIZATION_ADMIN.value, "Enterprise Administrator with unrestricted operational authority across all organizations, regions, stores, and governance policies.", 1),
            ("role-ops", Role.OPERATIONS_MANAGER.value, "Central Operations Executive coordinating cross-store triage, emergency escalations, SLAs, and operational dispatch.", 1),
            ("role-reg", Role.REGIONAL_MANAGER.value, "Regional Vice President overseeing store clusters, regional SLAs, cross-store asset transfers, and regional teams.", 1),
            ("role-store", Role.STORE_MANAGER.value, "Store General Manager managing physical store facility, department dispatch, technician work orders, and local safety.", 1),
            ("role-maint", Role.MAINTENANCE_TEAM.value, "Field Technician / Specialized Engineer executing physical work orders, preventative maintenance, and incident repairs.", 1),
            ("role-analyst", Role.ANALYST.value, "Operational Intelligence Analyst conducting root-cause investigations, anomaly detection audits, and SLA reporting.", 1),
            ("role-viewer", Role.VIEWER.value, "Store Auditor / Stakeholder with read-only visibility into operational dashboards, reports, and incident states.", 1),
        ]
        cur.executemany("""
            INSERT OR REPLACE INTO roles (id, name, description, is_system, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(r[0], r[1], r[2], r[3], now, now) for r in roles_definitions])

        # Seed role permissions
        role_perm_rows = []
        for role_id, role_enum_val, _, _ in roles_definitions:
            r_enum = Role(role_enum_val)
            for perm in ROLE_PERMISSIONS.get(r_enum, set()):
                role_perm_rows.append((role_id, perm.value))
        cur.executemany("""
            INSERT OR REPLACE INTO role_permissions (role_id, permission)
            VALUES (?, ?)
        """, role_perm_rows)

        # 1. Organization
        org_id = "org-apex-01"
        cur.execute("""
            INSERT OR REPLACE INTO organizations (id, name, code, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (org_id, "Apex Retail International", "APEX", "Global omnichannel retail enterprise operating multi-tier physical supercenters and urban metro locations.", "ACTIVE", now, now))

        # 2. Regions
        reg_na = "reg-na-01"
        reg_pnw = "reg-pnw-01"
        cur.execute("""
            INSERT OR REPLACE INTO regions (id, organization_id, name, code, description, lead_user_id, created_at, updated_at)
            VALUES 
            (?, ?, 'North Atlantic Region', 'REG-NA', 'Northeastern metropolitan territory encompassing high-density urban express stores.', NULL, ?, ?),
            (?, ?, 'Pacific Northwest Region', 'REG-PNW', 'Northwestern regional network consisting of large-format supercenters and fulfillment hubs.', NULL, ?, ?)
        """, (reg_na, org_id, now, now, reg_pnw, org_id, now, now))

        # 3. Stores with operational status and rich metadata
        store_104 = "store-104"
        store_108 = "store-108"
        store_201 = "store-201"
        store_205 = "store-205"

        stores_data = [
            (store_104, org_id, reg_pnw, "Apex Supercenter - Seattle Downtown", 104, 
             "1400 4th Ave", "Seattle", "WA", "98101", "USA", "America/Los_Angeles", "OPERATIONAL",
             json.dumps({
                 "formatTier": "SUPERCENTER",
                 "squareFootage": 142000,
                 "openingHours": "06:00-23:00",
                 "contactPhone": "+1-206-555-0104",
                 "generalManager": "David Miller",
                 "coldChainZoneCount": 14,
                 "posLanesCount": 24,
                 "emergencyShutoff": "Dock B Utility Room"
             }), now, now),
            (store_108, org_id, reg_pnw, "Apex Supercenter - Bellevue Crossroads", 108, 
             "15600 NE 8th St", "Bellevue", "WA", "98008", "USA", "America/Los_Angeles", "OPERATIONAL",
             json.dumps({
                 "formatTier": "SUPERCENTER",
                 "squareFootage": 115000,
                 "openingHours": "07:00-22:00",
                 "contactPhone": "+1-425-555-0108",
                 "generalManager": "Lisa Vance",
                 "coldChainZoneCount": 10,
                 "posLanesCount": 18,
                 "emergencyShutoff": "Main Utility Bay"
             }), now, now),
            (store_201, org_id, reg_na, "Apex Metro - Boston Back Bay", 201, 
             "500 Boylston St", "Boston", "MA", "02116", "USA", "America/New_York", "OPERATIONAL",
             json.dumps({
                 "formatTier": "METRO_EXPRESS",
                 "squareFootage": 48000,
                 "openingHours": "06:30-22:00",
                 "contactPhone": "+1-617-555-0201",
                 "generalManager": "Robert Thorne",
                 "coldChainZoneCount": 6,
                 "posLanesCount": 8,
                 "emergencyShutoff": "Basement Mechanical"
             }), now, now),
            (store_205, org_id, reg_na, "Apex Metro - Cambridge Galleria", 205, 
             "100 Cambridgeside Pl", "Cambridge", "MA", "02141", "USA", "America/New_York", "MAINTENANCE_HOLD",
             json.dumps({
                 "formatTier": "METRO_EXPRESS",
                 "squareFootage": 52000,
                 "openingHours": "07:00-21:00",
                 "contactPhone": "+1-617-555-0205",
                 "generalManager": "Elena Rostov",
                 "coldChainZoneCount": 6,
                 "posLanesCount": 10,
                 "maintenanceNotice": "Central chiller replacement in progress; non-refrigerated sections operational."
             }), now, now),
        ]
        cur.executemany("""
            INSERT OR REPLACE INTO stores (
                id, organization_id, region_id, name, store_number, street, city, state, postal_code,
                country, timezone, operating_status, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, stores_data)

        # 4. Departments
        dept_dairy_104 = "dept-104-dairy"
        dept_pos_104 = "dept-104-pos"
        dept_produce_104 = "dept-104-produce"
        departments_data = [
            (dept_dairy_104, org_id, store_104, "Dairy & Refrigerated", "Aisle 4-5", now, now),
            (dept_pos_104, org_id, store_104, "Front Checkout & Self-Pay", "Front Zone", now, now),
            (dept_produce_104, org_id, store_104, "Fresh Produce", "Perimeter West", now, now),
        ]
        cur.executemany("""
            INSERT OR REPLACE INTO departments (id, organization_id, store_id, name, floor_zone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, departments_data)

        # 5. Assets
        asset_cooler_104 = "asset-cooler-104b"
        asset_pos_104 = "asset-pos-104-03"
        assets_data = [
            (asset_cooler_104, org_id, store_104, dept_dairy_104, "Commercial Reach-in Dairy Cooler 4B", 
             "ASSET-COOLER-104B", "REFRIGERATION", "DEGRADED", json.dumps({"refrigerant": "R-448A", "installYear": 2022}), now, now),
            (asset_pos_104, org_id, store_104, dept_pos_104, "Self-Checkout Scanner Lane #3", 
             "ASSET-POS-104-03", "POS_TERMINAL", "OPERATIONAL", json.dumps({"firmware": "v4.1.9"}), now, now),
        ]
        cur.executemany("""
            INSERT OR REPLACE INTO assets (id, organization_id, store_id, department_id, name, asset_tag, category, status, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, assets_data)

        # 6. Operational Teams with responsibilities, specializations, escalation tiers
        team_hvac = "team-hvac-pnw"
        team_janitorial = "team-janitorial-104"
        team_it = "team-it-pnw"
        team_food_safety = "team-food-safety"

        teams_data = [
            (team_hvac, org_id, reg_pnw, None, "Regional Commercial HVAC & Refrigeration", "HVAC_REFRIGERATION",
             "MISSION_CRITICAL", "hvac-dispatch@apex.com",
             "Emergency repair and preventative maintenance for walk-in chillers, cold chain displays, compressors, and roof HVAC units.",
             "REFRIGERATION_HVAC", "urgent-hvac@apex.com", "TIER_1", None, "ACTIVE", now, now),
            (team_janitorial, org_id, reg_pnw, store_104, "Store 104 Janitorial & Sanitation", "JANITORIAL",
             "EXPEDITED", "janitorial104@apex.com",
             "Immediate spill containment, wet floor hazard remediation, physical barrier deployment, and daily customer sanitation.",
             "JANITORIAL_SANITATION", "janitorial104-pager@apex.com", "TIER_1", None, "ACTIVE", now, now),
            (team_it, org_id, reg_pnw, None, "Regional Store IT & POS Systems", "IT_POS",
             "EXPEDITED", "pos-support@apex.com",
             "Self-checkout lanes, barcode scan engines, payment terminals, network switches, and electronic shelf label gateways.",
             "POS_HARDWARE", "pos-hotline@apex.com", "TIER_2", None, "ACTIVE", now, now),
            (team_food_safety, org_id, reg_pnw, None, "Regional Food Safety & Perishables Compliance", "FOOD_SAFETY",
             "MISSION_CRITICAL", "foodsafety@apex.com",
             "HACCP compliance monitoring, spoiled stock condemnation, temperature integrity sign-off, and health inspection liaison.",
             "FOOD_SAFETY", "foodsafety-urgent@apex.com", "TIER_2", None, "ACTIVE", now, now),
        ]
        cur.executemany("""
            INSERT OR REPLACE INTO operational_teams (
                id, organization_id, region_id, store_id, name, team_type, sla_tier, contact_email,
                responsibility, specialization, escalation_contact, escalation_tier, lead_user_id, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, teams_data)

        # 7. Users across all 7 RBAC roles (Default password: "Password123!")
        default_pwd_hash = hash_password("Password123!")
        users_data = [
            ("usr-admin", org_id, None, None, None, "orgadmin@apex.com", default_pwd_hash, "Eleanor Vance (Org Admin)", "ORGANIZATION_ADMIN", 1, now, now),
            ("usr-ops", org_id, None, None, None, "opsmanager@apex.com", default_pwd_hash, "Marcus Sterling (Ops Manager)", "OPERATIONS_MANAGER", 1, now, now),
            ("usr-reg", org_id, None, reg_pnw, None, "regmanager@apex.com", default_pwd_hash, "Sarah Chen (Regional VP PNW)", "REGIONAL_MANAGER", 1, now, now),
            ("usr-store", org_id, store_104, reg_pnw, None, "storemanager@apex.com", default_pwd_hash, "David Miller (Store 104 Lead)", "STORE_MANAGER", 1, now, now),
            ("usr-maint", org_id, store_104, reg_pnw, team_hvac, "maintenance@apex.com", default_pwd_hash, "Carlos Gomez (Senior HVAC Tech)", "MAINTENANCE_TEAM", 1, now, now),
            ("usr-analyst", org_id, None, None, None, "analyst@apex.com", default_pwd_hash, "Priya Sharma (Operations Analyst)", "ANALYST", 1, now, now),
            ("usr-viewer", org_id, store_104, reg_pnw, None, "viewer@apex.com", default_pwd_hash, "Alex Reed (Store Auditor)", "VIEWER", 1, now, now),
        ]
        cur.executemany("""
            INSERT OR REPLACE INTO users (id, organization_id, store_id, region_id, team_id, email, password_hash, full_name, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, users_data)

        # Update region and team leads now that users exist
        cur.execute("UPDATE regions SET lead_user_id = 'usr-reg' WHERE id = ?;", (reg_pnw,))
        cur.execute("UPDATE operational_teams SET lead_user_id = 'usr-maint' WHERE id = ?;", (team_hvac,))

        # 7b. Team Memberships (Assigning users into operational teams)
        team_members_data = [
            ("tm-01", team_hvac, "usr-maint", "LEAD_TECHNICIAN", 1, now),
            ("tm-02", team_janitorial, "usr-store", "SUPERVISOR", 0, now),
        ]
        cur.executemany("""
            INSERT OR REPLACE INTO team_members (id, team_id, user_id, role_in_team, is_primary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, team_members_data)

        # 7c. Operational Ownership & Escalation Mappings
        ownership_mappings_data = [
            ("map-104-hvac", org_id, reg_pnw, store_104, dept_dairy_104, "REFRIGERATION_HVAC",
             team_hvac, team_janitorial, "usr-store", 45, 2.0,
             "Store 104 Dairy & Perishables cold chain failure routing: direct dispatch to Regional HVAC, escalation to Store Manager.", now, now),
            ("map-104-jan", org_id, reg_pnw, store_104, None, "JANITORIAL_SANITATION",
             team_janitorial, team_hvac, "usr-store", 15, 1.0,
             "Store 104 Slip and liquid hazard containment: immediate dispatch to Janitorial, secondary fallback to Facilities.", now, now),
            ("map-104-pos", org_id, reg_pnw, store_104, dept_pos_104, "POS_HARDWARE",
             team_it, None, "usr-store", 30, 2.0,
             "Front checkout lane hardware interruptions routed to Regional IT POS team.", now, now),
            ("map-pnw-food", org_id, reg_pnw, None, None, "FOOD_SAFETY",
             team_food_safety, team_hvac, "usr-reg", 30, 1.5,
             "Regional perishables and food safety contamination alerts routed to Food Safety Compliance team, escalation to Regional VP.", now, now),
        ]
        cur.executemany("""
            INSERT OR REPLACE INTO operational_ownership_mappings (
                id, organization_id, region_id, store_id, department_id, operational_domain,
                primary_team_id, secondary_team_id, escalation_user_id, sla_minutes, auto_escalate_hours,
                description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ownership_mappings_data)

        # 8. Feedback Items (Phase 3 Multichannel raw human inputs with 3-stage lifecycle)
        fb_1 = "fb-104-01"
        fb_2 = "fb-104-02"
        fb_3 = "fb-104-03"
        fb_4 = "fb-104-04"
        fb_5 = "fb-104-05"
        fb_6 = "fb-104-06"

        def make_hash(store, text):
            return hashlib.sha256(f"{store}:{text.lower().strip()}".encode('utf-8')).hexdigest()

        txt_1 = "El estante de leche en el pasillo 4 se siente tibio y hay agua estancada goteando en el piso."
        txt_2 = "Dairy cooler 4B is buzzing loud, internal temp reading is 48F instead of 36F, severe puddle."
        txt_3 = "Self checkout scanner on lane 3 kept freezing during barcode scan."
        txt_4 = "Routine 14-day refrigeration walk: found slight ice buildup on condenser fans in dairy section, temp gauge fluctuated between 38F and 44F."
        txt_5 = "Store checkout was fast today but the organic dairy section had a big puddle on the floor."
        txt_6 = "Shift turnover note: Associate reported customer slip hazard in Aisle 4. Pager dispatched to Janitorial squad at 14:15."

        feedback_data = [
            (fb_1, org_id, reg_pnw, store_104, dept_dairy_104, "CUSTOMER_COMPLAINT", "CUSTOMER_COMPLAINT", "CUSTOMER",
             "INTERNAL", "analyzed", "NEW", txt_1, "es", txt_1, make_hash(store_104, txt_1), 0, None,
             json.dumps({"detectedLanguage": "es", "detectedIntent": "COLD_CHAIN_REFRIGERATION", "sentimentScore": -0.85, "urgencyScore": 0.88, "extractedEntities": ["Aisle 4", "Cooler"], "summary": "Warm milk shelf and dripping water in Aisle 4"}),
             None, -0.85, 0, 0, json.dumps({"source": "QR_KIOSK_AISLE4"}), two_hours_ago, two_hours_ago, two_hours_ago),
            (fb_2, org_id, reg_pnw, store_104, dept_dairy_104, "EMPLOYEE_FEEDBACK", "EMPLOYEE_FEEDBACK", "EMPLOYEE",
             "CONFIDENTIAL", "analyzed", "NEW", txt_2, "en", txt_2, make_hash(store_104, txt_2), 0, None,
             json.dumps({"detectedLanguage": "en", "detectedIntent": "COLD_CHAIN_REFRIGERATION", "sentimentScore": -0.90, "urgencyScore": 0.92, "extractedEntities": ["Cooler 4B", "Temp 48°"], "summary": "Cooler 4B temperature elevation to 48F with severe floor puddle"}),
             None, -0.90, 0, 0, json.dumps({"associateId": "EMP-492"}), one_hour_ago, one_hour_ago, one_hour_ago),
            (fb_3, org_id, reg_pnw, store_104, dept_pos_104, "CUSTOMER_COMPLAINT", "CUSTOMER_COMPLAINT", "CUSTOMER",
             "INTERNAL", "analyzed", "NEW", txt_3, "en", txt_3, make_hash(store_104, txt_3), 0, None,
             json.dumps({"detectedLanguage": "en", "detectedIntent": "POS_CHECKOUT_SYSTEMS", "sentimentScore": -0.45, "urgencyScore": 0.55, "extractedEntities": ["Lane #3"], "summary": "Lane 3 self-checkout scanner freeze issue"}),
             None, -0.45, 0, 0, json.dumps({"lane": 3}), two_hours_ago, two_hours_ago, two_hours_ago),
            (fb_4, org_id, reg_pnw, store_104, dept_dairy_104, "MAINTENANCE_REPORT", "MAINTENANCE_REPORT", "MAINTENANCE_TECH",
             "INTERNAL", "analyzed", "NEW", txt_4, "en", txt_4, make_hash(store_104, txt_4), 0, None,
             json.dumps({"detectedLanguage": "en", "detectedIntent": "COLD_CHAIN_REFRIGERATION", "sentimentScore": -0.50, "urgencyScore": 0.65, "extractedEntities": ["Condenser", "Temp 44°"], "summary": "Ice buildup on condenser fans and temperature fluctuation"}),
             None, -0.50, 0, 0, json.dumps({"technicianBadge": "TECH-88"}), one_hour_ago, one_hour_ago, one_hour_ago),
            (fb_5, org_id, reg_pnw, store_104, dept_dairy_104, "SURVEY_RESPONSE", "SURVEY_RESPONSE", "CUSTOMER",
             "INTERNAL", "analyzed", "NEW", txt_5, "en", txt_5, make_hash(store_104, txt_5), 0, None,
             json.dumps({"detectedLanguage": "en", "detectedIntent": "SLIP_FALL_SAFETY", "sentimentScore": -0.30, "urgencyScore": 0.70, "extractedEntities": ["Aisle 4"], "summary": "CSAT comment noting organic dairy floor puddle"}),
             None, -0.30, 0, 0, json.dumps({"csatScore": 3}), two_hours_ago, two_hours_ago, two_hours_ago),
            (fb_6, org_id, reg_pnw, store_104, dept_dairy_104, "OPERATIONAL_NOTE", "OPERATIONAL_NOTE", "STORE_MANAGER",
             "INTERNAL", "reviewed", "TRIAGED", txt_6, "en", txt_6, make_hash(store_104, txt_6), 0, None,
             json.dumps({"detectedLanguage": "en", "detectedIntent": "SLIP_FALL_SAFETY", "sentimentScore": -0.40, "urgencyScore": 0.75, "extractedEntities": ["Aisle 4"], "summary": "Manager shift turnover dispatch record for Aisle 4 puddle"}),
             None, -0.40, 0, 0, json.dumps({"author": "David Miller", "shift": "Day"}), one_hour_ago, one_hour_ago, one_hour_ago),
        ]
        cur.executemany("""
            INSERT OR REPLACE INTO feedback_items (
                id, organization_id, region_id, store_id, department_id,
                source_type, channel_type, submitter_type, privacy_classification,
                processing_status, status, raw_text, language_code, normalized_text,
                content_hash, is_duplicate, duplicate_of_id, ai_interpretation,
                processing_error, sentiment_score, is_ambiguous, has_pii,
                metadata, submitted_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, feedback_data)

        # 9. Follow-Up Clarification Example
        cur.execute("""
            INSERT OR REPLACE INTO follow_up_exchanges (id, feedback_item_id, turn_index, question, response, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("fu-104-01", fb_1, 1, 
              "Could you specify the aisle number and if the liquid creates a slip hazard?", 
              "Aisle 4 dairy cooler. Yes, customers are stepping in the puddle.", two_hours_ago))

        # 10. Operational Issue (Formed from clustering)
        issue_104 = "issue-104-892"
        cur.execute("""
            INSERT OR REPLACE INTO issues (
                id, organization_id, store_id, department_id, asset_id, title, description,
                status, priority_score, priority_tier, severity_score, urgency_score, impact_scope_score,
                confidence_score, is_emerging_anomaly, anomaly_velocity_zscore, assigned_team_id,
                root_cause_hypothesis, feedback_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            issue_104, org_id, store_104, dept_dairy_104, asset_cooler_104,
            "Cold Chain Breakdown & Slip Hazard - Dairy Unit 4B",
            "Multiple feedback reports indicate temperature rise (48F) and drainage condensation leakage across Aisle 4 floor.",
            "DISPATCHED", 88, "P1_CRITICAL", 0.85, 0.92, 0.60, 0.88, 1, 3.82, team_hvac,
            "Suspected condenser coil failure and blocked drain pipe causing overflow and refrigeration failure.",
            2, one_hour_ago, now
        ))

        # Link issue to feedback
        cur.execute("""
            INSERT OR REPLACE INTO issue_feedback_links (issue_id, feedback_item_id)
            VALUES (?, ?), (?, ?)
        """, (issue_104, fb_1, issue_104, fb_2))

        # 11. Alert
        alert_104 = "alert-104-01"
        cur.execute("""
            INSERT OR REPLACE INTO alerts (id, organization_id, store_id, issue_id, alert_type, severity, message, is_acknowledged, acknowledged_by, acknowledged_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert_104, org_id, store_104, issue_104,
            "EMERGING_ANOMALY", "CRITICAL",
            "Emerging Anomaly Detected: Dairy Aisle 4 complaint velocity +3.82z above 14-day baseline.",
            1, "usr-store", one_hour_ago, one_hour_ago
        ))

        # 12. Action Plan & Work Order
        action_104 = "action-104-01"
        cur.execute("""
            INSERT OR REPLACE INTO action_plans (
                id, organization_id, issue_id, recommended_action, target_team_id,
                requires_human_approval, approval_status, approved_by, approved_at,
                override_reason, sla_deadline, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            action_104, org_id, issue_104,
            "Deploy safety cones to aisle 4 immediately; dispatch certified technician to repair condensate pump and inspect compressor.",
            team_hvac, 1, "APPROVED", "usr-store", one_hour_ago, None, sla_deadline, one_hour_ago, now
        ))

        # 13. Resolution Record
        res_104 = "res-104-01"
        cur.execute("""
            INSERT OR REPLACE INTO resolutions (
                id, organization_id, issue_id, action_plan_id, technician_notes,
                resolved_by, resolved_at, verification_status, verification_scorecard, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res_104, org_id, issue_104, action_104,
            "Replaced faulty condensate drainage valve, flushed overflow line, verified temp restored to 34F.",
            "usr-maint", now, "PENDING_VERIFICATION",
            json.dumps({
                "preFeedbackRate": 2.5,
                "postFeedbackRate": 0.0,
                "feedbackRateDeltaPct": -100.0,
                "sentimentShift": 0.75,
                "recurrenceCount": 0,
                "evaluatedAt": now
            }), now, now
        ))

        # 14. Evidence Citations
        cur.execute("""
            INSERT OR REPLACE INTO evidence (id, organization_id, issue_id, feedback_item_id, verbatim_quote, source_metadata, confidence_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "ev-104-01", org_id, issue_104, fb_1,
            "El estante de leche en el pasillo 4 se siente tibio y hay agua estancada",
            json.dumps({"source": "QR_KIOSK", "language": "es", "submittedAt": two_hours_ago}),
            0.92, one_hour_ago
        ))

        # 15. Audit Log
        cur.execute("""
            INSERT OR REPLACE INTO audit_logs (id, organization_id, user_id, entity_type, entity_id, action, previous_state, new_state, justification, ip_address, user_agent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "aud-104-01", org_id, "usr-store", "ACTION_PLAN", action_104, "ACTION_APPROVED",
            json.dumps({"approvalStatus": "PENDING"}), json.dumps({"approvalStatus": "APPROVED"}),
            "Approved emergency technician dispatch for high slip hazard.", "192.168.1.104", "R5-Cockpit-Web/v1.0", one_hour_ago
        ))

        # 16. Future Extensibility: Segregated Personal / Home Mode Seed
        cur.execute("""
            INSERT OR REPLACE INTO personal_home_appliances (
                id, user_id, appliance_type, brand, model_number, serial_number, purchase_date, warranty_until, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "appl-home-01", "usr-store", "REFRIGERATOR", "Samsung", "RF28R7351SR", "SN-88291039",
            "2023-05-15", "2026-05-15", now, now
        ))

        cur.execute("""
            INSERT OR REPLACE INTO personal_service_tickets (
                id, appliance_id, user_id, complaint_description, classified_category, routed_service_channel, status, external_reference_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "ticket-home-01", "appl-home-01", "usr-store",
            "Ice maker is jamming and leaking small drops into freezer tray.",
            "DEFROST_AND_ICE_MAKER", "Samsung Authorized Service Network", "SUBMITTED", "EXT-SAM-9901", now, now
        ))

        # 17. Phase 12: Post-Intervention Outcome Measurements Seed
        from backend.app.services.outcome_service import OutcomeService

        # Seed Issue 893: POS Checkout (No significant change)
        cur.execute("""
            INSERT OR REPLACE INTO issues (
                id, organization_id, store_id, department_id, title, description,
                status, priority_score, priority_tier, severity_score, urgency_score, impact_scope_score,
                confidence_score, assigned_team_id, feedback_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "issue-104-893", org_id, store_104, dept_pos_104,
            "Lane 3 & 4 Optical Scanner Intermittent Misreads",
            "Registers 3 and 4 fail to read barcodes on curved produce and milk jugs.",
            "VERIFYING", 68, "P3_MEDIUM", 0.60, 0.65, 0.50, 0.85, team_it, 3, four_days_ago, two_days_ago
        ))
        cur.execute("""
            INSERT OR REPLACE INTO action_plans (
                id, organization_id, issue_id, recommended_action, target_team_id,
                requires_human_approval, approval_status, approved_by, approved_at, sla_deadline, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "action-104-893", org_id, "issue-104-893",
            "Clean scanner glass with alcohol swabs and update scanner firmware build 4.2",
            team_it, 0, "APPROVED", "usr-store", three_days_ago, two_days_ago, three_days_ago, two_days_ago
        ))
        cur.execute("""
            INSERT OR REPLACE INTO resolutions (
                id, organization_id, issue_id, action_plan_id, technician_notes,
                resolved_by, resolved_at, verification_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "res-104-893", org_id, "issue-104-893", "action-104-893",
            "Cleaned glass, tested scan on test milk jug successfully, rebooted terminal.",
            "usr-maint", two_days_ago, "PENDING_VERIFICATION", two_days_ago, two_days_ago
        ))

        fb_pos_1 = "fb-pos-893-1"
        fb_pos_2 = "fb-pos-893-2"
        cur.execute("""
            INSERT OR REPLACE INTO feedback_items (
                id, organization_id, store_id, department_id, source_type, channel_type,
                raw_text, language_code, sentiment_score, processing_status, status, submitted_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'en', ?, 'analyzed', 'PROCESSED', ?, ?, ?);
        """, (fb_pos_1, org_id, store_104, dept_pos_104, "QR_KIOSK", "KIOSK", "Lane 3 scanner takes 5 tries to scan anything.", -0.6, three_days_ago, three_days_ago, three_days_ago))
        cur.execute("""
            INSERT OR REPLACE INTO feedback_items (
                id, organization_id, store_id, department_id, source_type, channel_type,
                raw_text, language_code, sentiment_score, processing_status, status, submitted_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'en', ?, 'analyzed', 'PROCESSED', ?, ?, ?);
        """, (fb_pos_2, org_id, store_104, dept_pos_104, "QR_KIOSK", "KIOSK", "Lane 4 scanner skipping items and double scanning.", -0.6, two_days_ago, two_days_ago, two_days_ago))
        cur.execute("INSERT OR REPLACE INTO issue_feedback_links (issue_id, feedback_item_id) VALUES (?, ?), (?, ?);", ("issue-104-893", fb_pos_1, "issue-104-893", fb_pos_2))

        fb_pos_post = "fb-pos-893-post"
        cur.execute("""
            INSERT OR REPLACE INTO feedback_items (
                id, organization_id, store_id, department_id, source_type, channel_type,
                raw_text, language_code, sentiment_score, processing_status, status, submitted_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'en', ?, 'analyzed', 'PROCESSED', ?, ?, ?);
        """, (fb_pos_post, org_id, store_104, dept_pos_104, "CUSTOMER_SURVEY", "MOBILE_APP", "Cashier at register 3 had to key in every item manually scanner not working.", -0.65, yesterday, yesterday, yesterday))
        cur.execute("INSERT OR REPLACE INTO issue_feedback_links (issue_id, feedback_item_id) VALUES (?, ?);", ("issue-104-893", fb_pos_post))

        # Seed Issue 894: Restroom Flush Valve Pressure Surge (Worsened)
        cur.execute("""
            INSERT OR REPLACE INTO issues (
                id, organization_id, store_id, department_id, title, description,
                status, priority_score, priority_tier, severity_score, urgency_score, impact_scope_score,
                confidence_score, assigned_team_id, feedback_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "issue-104-894", org_id, store_104, None,
            "Customer Restroom Flush Valve Pressure Surge",
            "Flush valves vibrating and spraying mist above stall walls.",
            "VERIFYING", 76, "P2_HIGH", 0.50, 0.70, 0.60, 0.88, team_janitorial, 2, three_days_ago, two_days_ago
        ))
        cur.execute("""
            INSERT OR REPLACE INTO action_plans (
                id, organization_id, issue_id, recommended_action, target_team_id,
                requires_human_approval, approval_status, approved_by, approved_at, sla_deadline, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "action-104-894", org_id, "issue-104-894",
            "Adjust main pressure regulator valve on secondary water line",
            team_janitorial, 0, "APPROVED", "usr-store", two_days_ago, two_days_ago, two_days_ago, two_days_ago
        ))
        cur.execute("""
            INSERT OR REPLACE INTO resolutions (
                id, organization_id, issue_id, action_plan_id, technician_notes,
                resolved_by, resolved_at, verification_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "res-104-894", org_id, "issue-104-894", "action-104-894",
            "Tightened regulator screw clockwise 2 turns.",
            "usr-maint", two_days_ago, "PENDING_VERIFICATION", two_days_ago, two_days_ago
        ))

        fb_rest_1 = "fb-rest-894-1"
        cur.execute("""
            INSERT OR REPLACE INTO feedback_items (
                id, organization_id, store_id, department_id, source_type, channel_type,
                raw_text, language_code, sentiment_score, processing_status, status, submitted_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'en', ?, 'analyzed', 'PROCESSED', ?, ?, ?);
        """, (fb_rest_1, org_id, store_104, None, "STORE_ASSOCIATE", "INTERNAL_PORTAL", "Restroom toilet valve whistling loudly after flush.", -0.4, three_days_ago, three_days_ago, three_days_ago))
        cur.execute("INSERT OR REPLACE INTO issue_feedback_links (issue_id, feedback_item_id) VALUES (?, ?);", ("issue-104-894", fb_rest_1))

        fb_rest_post1 = "fb-rest-894-post1"
        fb_rest_post2 = "fb-rest-894-post2"
        fb_rest_post3 = "fb-rest-894-post3"
        for fid, txt in [
            (fb_rest_post1, "Restroom flooded with 2 inches of water pouring into hallway!"),
            (fb_rest_post2, "Major leak in restrooms slipping hazard customers screaming!"),
            (fb_rest_post3, "Water leaking out into customer walkway from restroom burst valve.")
        ]:
            cur.execute("""
                INSERT OR REPLACE INTO feedback_items (
                    id, organization_id, store_id, department_id, source_type, channel_type,
                    raw_text, language_code, sentiment_score, processing_status, status, submitted_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'en', ?, 'analyzed', 'PROCESSED', ?, ?, ?);
            """, (fid, org_id, store_104, None, "QR_KIOSK", "KIOSK", txt, -0.9, yesterday, yesterday, yesterday))
            cur.execute("INSERT OR REPLACE INTO issue_feedback_links (issue_id, feedback_item_id) VALUES (?, ?);", ("issue-104-894", fid))

        # Seed Issue 895: Produce Misting Line (Inconclusive - resolved 30 mins ago)
        cur.execute("""
            INSERT OR REPLACE INTO issues (
                id, organization_id, store_id, department_id, title, description,
                status, priority_score, priority_tier, severity_score, urgency_score, impact_scope_score,
                confidence_score, assigned_team_id, feedback_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "issue-104-895", org_id, store_104, dept_produce_104,
            "Produce Organic Greens Misting Line Clog",
            "Misting heads on broccoli stand are dripping instead of spraying.",
            "VERIFYING", 52, "P3_MEDIUM", 0.45, 0.50, 0.40, 0.85, team_hvac, 2, two_hours_ago, thirty_mins_ago
        ))
        cur.execute("""
            INSERT OR REPLACE INTO action_plans (
                id, organization_id, issue_id, recommended_action, target_team_id,
                requires_human_approval, approval_status, approved_by, approved_at, sla_deadline, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "action-104-895", org_id, "issue-104-895",
            "Clear mineral build-up from nozzle apertures",
            team_hvac, 0, "APPROVED", "usr-store", one_hour_ago, now, one_hour_ago, thirty_mins_ago
        ))
        cur.execute("""
            INSERT OR REPLACE INTO resolutions (
                id, organization_id, issue_id, action_plan_id, technician_notes,
                resolved_by, resolved_at, verification_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "res-104-895", org_id, "issue-104-895", "action-104-895",
            "De-scaled nozzle orifices with acetic acid rinse. Flow verified.",
            "usr-maint", thirty_mins_ago, "PENDING_VERIFICATION", thirty_mins_ago, thirty_mins_ago
        ))

        # Evaluate outcomes for rich dashboard display
        OutcomeService.evaluate_issue_outcome(conn, issue_104, observation_hours=48.0, min_observation_hours=12.0)
        OutcomeService.evaluate_issue_outcome(conn, "issue-104-893", observation_hours=36.0, min_observation_hours=12.0)
        OutcomeService.evaluate_issue_outcome(conn, "issue-104-894", observation_hours=24.0, min_observation_hours=12.0)
        OutcomeService.evaluate_issue_outcome(conn, "issue-104-895", observation_hours=0.5, min_observation_hours=12.0)

        # Generate Phase 14 baseline AI Operational Intelligence Brief
        BriefService.generate_brief(conn, org_id, timeframe_type="DAILY", user_id="usr-ops")

        # 18. Phase 16: Security & Data Retention Policies
        from backend.app.services.retention_service import RetentionService
        from backend.app.services.security_audit_service import SecurityAuditService

        RetentionService.set_policy(conn, org_id, "FEEDBACK_ITEMS", retention_days=365, action_on_expire="ANONYMIZE")
        RetentionService.set_policy(conn, org_id, "INVESTIGATION_QUESTIONS", retention_days=180, action_on_expire="PURGE")
        RetentionService.set_policy(conn, org_id, "ALERTS", retention_days=90, action_on_expire="PURGE")
        RetentionService.set_policy(conn, org_id, "AUDIT_LOGS", retention_days=730, action_on_expire="PURGE")

        SecurityAuditService.record_event(
            conn=conn,
            event_type="SECURITY_SYSTEM_INITIALIZED",
            severity="LOW",
            organization_id=org_id,
            user_id="usr-admin",
            path="/system/init",
            details={"status": "ACTIVE", "policiesLoaded": 4}
        )

        conn.commit()
        logger.info("Database seeding completed successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error seeding database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    seed_database(force=True)

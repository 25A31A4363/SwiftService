"""
Phase 10: Intelligent Operational Routing Service

R5 CORE CAPABILITY:
Detected issues must reach the responsible operational team or owner without guesswork.

Deterministic routing hierarchy:
1. Safety Relevance & Emergency Priority Override (15-30m emergency SLA)
2. Store-level Operational Ownership Mapping (confidence 0.95)
3. Region-level Operational Ownership Mapping (confidence 0.90)
4. Team Specialization / Responsibility Rules (confidence 0.80)
5. Ambiguous Context / Low Confidence -> Human Triage Queue (confidence <= 0.50, prevents operational misrouting)

Every routing decision records:
- selected team
- reason
- supporting data
- confidence
- fallback team
- human override details
- deterministic SLA deadline
"""

import json
import uuid
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.services.audit_service import AuditService

# Deterministic category-to-operational-domain mapping
DOMAIN_CATEGORY_MAP = {
    "SAFETY_HAZARD": "JANITORIAL_SANITATION",
    "FACILITIES_MAINTENANCE": "REFRIGERATION_HVAC",
    "CHECKOUT_POS": "POS_HARDWARE",
    "INVENTORY_STOCK": "FOOD_SAFETY",
    "OPERATIONAL_HYGIENE": "JANITORIAL_SANITATION",
    "RESTROOM_HYGIENE": "JANITORIAL_SANITATION",
    "CUSTOMER_SERVICE": "STORE_OPERATIONS",
    "EQUIPMENT_FAILURE": "REFRIGERATION_HVAC",
    "COLD_CHAIN_REFRIGERATION": "REFRIGERATION_HVAC",
    "POS_CHECKOUT_SYSTEMS": "POS_HARDWARE",
    "SLIP_FALL_SAFETY": "JANITORIAL_SANITATION",
}

# SLA deadlines based on priority tier and safety relevance (in minutes)
DEFAULT_SLA_BY_TIER = {
    "P1_CRITICAL": 30,
    "P2_HIGH": 60,
    "P3_MEDIUM": 240,   # 4 hours
    "P4_LOW": 1440      # 24 hours
}

class RoutingService:
    @staticmethod
    def map_category_to_domain(category: str, issue_title: str = "", description: str = "") -> str:
        """Deterministically map issue categorization to an operational domain."""
        cat_upper = (category or "").upper()
        if cat_upper in DOMAIN_CATEGORY_MAP:
            return DOMAIN_CATEGORY_MAP[cat_upper]

        import re
        # Check bracketed prefix in title if category not directly mapped
        bracket_match = re.search(r"\[([A-Za-z0-9_]+)\]", issue_title)
        if bracket_match:
            b_cat = bracket_match.group(1).upper()
            if b_cat in DOMAIN_CATEGORY_MAP:
                return DOMAIN_CATEGORY_MAP[b_cat]
        combined = f"{issue_title} {description}".lower()
        if re.search(r"\b(slip|spill|wet floor|puddle|leaking|leak\w*|restroom|toilet|clean(?:ing|up)?|custodial|janitor\w*)\b", combined):
            return "JANITORIAL_SANITATION"
        if re.search(r"\b(cooler|freezer|ac|hvac|refrigerat\w*|chiller|compressor)\b", combined):
            return "REFRIGERATION_HVAC"
        if re.search(r"\b(pos|scanner|register|terminal|card reader|printer|kiosk)\b", combined):
            return "POS_HARDWARE"
        if re.search(r"\b(spoil\w*|expired|food|perish\w*|dairy|temperature)\b", combined):
            return "FOOD_SAFETY"

        return "UNKNOWN_DOMAIN"

    @staticmethod
    def calculate_deterministic_sla(
        priority_tier: str,
        is_safety_hazard: bool = False,
        mapping_sla_minutes: Optional[int] = None
    ) -> int:
        """Calculate deterministic SLA minutes with safety acceleration."""
        if mapping_sla_minutes and mapping_sla_minutes > 0:
            base_sla = mapping_sla_minutes
        else:
            base_sla = DEFAULT_SLA_BY_TIER.get(priority_tier, 120)

        # Safety hazard override: SLA cut in half, capped at max 30 minutes
        if is_safety_hazard:
            return min(30, max(15, base_sla // 2))

        return base_sla

    @staticmethod
    def determine_routing(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: str,
        category: str,
        priority_tier: str = "P3_MEDIUM",
        severity_score: float = 0.5,
        is_safety_hazard: bool = False,
        department_id: Optional[str] = None,
        issue_title: str = "",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluate deterministic operational routing rules.
        If routing confidence is low, routes to Human Triage Queue instead of guessing.
        """
        cur = conn.cursor()
        domain = RoutingService.map_category_to_domain(category, issue_title, description)

        # 0. Retrieve store operational context (e.g. region_id)
        cur.execute("SELECT region_id, name, operating_status FROM stores WHERE id = ?;", (store_id,))
        store_row = cur.fetchone()
        region_id = store_row["region_id"] if store_row else None
        store_name = store_row["name"] if store_row else store_id

        supporting_data = {
            "evaluatedDomain": domain,
            "category": category,
            "storeId": store_id,
            "storeName": store_name,
            "regionId": region_id,
            "departmentId": department_id,
            "severityScore": severity_score,
            "priorityTier": priority_tier,
            "isSafetyHazard": is_safety_hazard
        }

        # 1. EMERGENCY SAFETY OVERRIDE
        # High severity safety hazards (e.g. wet floor spill or chemical leak)
        # route directly to on-site custodial/janitorial hazard squad with emergency SLA
        if is_safety_hazard and domain == "JANITORIAL_SANITATION":
            cur.execute("""
                SELECT id, name FROM operational_teams
                WHERE store_id = ? AND (team_type = 'JANITORIAL' OR specialization = 'JANITORIAL_SANITATION')
                  AND status = 'ACTIVE' LIMIT 1;
            """, (store_id,))
            team = cur.fetchone()
            if team:
                sla_mins = RoutingService.calculate_deterministic_sla(priority_tier, is_safety_hazard=True, mapping_sla_minutes=15)
                supporting_data["ruleTrigger"] = "EMERGENCY_SAFETY_OVERRIDE"
                return {
                    "selectedTeamId": team["id"],
                    "selectedTeamName": team["name"],
                    "assignedUserId": None,
                    "routingTier": "STORE_SPECIALIST",
                    "routingStrategy": "SAFETY_HAZARD_EMERGENCY_OVERRIDE",
                    "reason": f"Emergency safety hazard detected; routed directly to Store Janitorial/Safety team with {sla_mins}m emergency SLA.",
                    "supportingData": supporting_data,
                    "confidence": 0.98,
                    "isAmbiguous": False,
                    "fallbackTeamId": None,
                    "slaMinutes": sla_mins
                }

        # 2. STORE-LEVEL OPERATIONAL OWNERSHIP MAPPING
        # Check explicit store ownership mapping for domain
        cur.execute("""
            SELECT m.*, t.name as primary_team_name, s.name as secondary_team_name
            FROM operational_ownership_mappings m
            JOIN operational_teams t ON m.primary_team_id = t.id
            LEFT JOIN operational_teams s ON m.secondary_team_id = s.id
            WHERE m.organization_id = ?
              AND m.store_id = ?
              AND m.operational_domain = ?
            ORDER BY m.department_id IS NOT NULL DESC
            LIMIT 1;
        """, (organization_id, store_id, domain))
        store_map = cur.fetchone()

        if store_map:
            sla_mins = RoutingService.calculate_deterministic_sla(
                priority_tier,
                is_safety_hazard=is_safety_hazard,
                mapping_sla_minutes=store_map["sla_minutes"]
            )
            supporting_data["ownershipMappingId"] = store_map["id"]
            supporting_data["mappingDescription"] = store_map["description"]

            return {
                "selectedTeamId": store_map["primary_team_id"],
                "selectedTeamName": store_map["primary_team_name"],
                "assignedUserId": store_map["escalation_user_id"],
                "routingTier": "STORE_SPECIALIST",
                "routingStrategy": "DETERMINISTIC_OWNERSHIP_RULE",
                "reason": f"Matched active store operational ownership rule '{store_map['id']}' for domain '{domain}' at {store_name}.",
                "supportingData": supporting_data,
                "confidence": 0.95,
                "isAmbiguous": False,
                "fallbackTeamId": store_map["secondary_team_id"],
                "fallbackTeamName": store_map["secondary_team_name"],
                "slaMinutes": sla_mins
            }

        # 3. REGION-LEVEL OPERATIONAL OWNERSHIP MAPPING
        if region_id:
            cur.execute("""
                SELECT m.*, t.name as primary_team_name, s.name as secondary_team_name
                FROM operational_ownership_mappings m
                JOIN operational_teams t ON m.primary_team_id = t.id
                LEFT JOIN operational_teams s ON m.secondary_team_id = s.id
                WHERE m.organization_id = ?
                  AND m.region_id = ?
                  AND m.store_id IS NULL
                  AND m.operational_domain = ?
                LIMIT 1;
            """, (organization_id, region_id, domain))
            reg_map = cur.fetchone()

            if reg_map:
                sla_mins = RoutingService.calculate_deterministic_sla(
                    priority_tier,
                    is_safety_hazard=is_safety_hazard,
                    mapping_sla_minutes=reg_map["sla_minutes"]
                )
                supporting_data["ownershipMappingId"] = reg_map["id"]
                return {
                    "selectedTeamId": reg_map["primary_team_id"],
                    "selectedTeamName": reg_map["primary_team_name"],
                    "assignedUserId": reg_map["escalation_user_id"],
                    "routingTier": "REGIONAL_SPECIALIST",
                    "routingStrategy": "REGIONAL_OWNERSHIP_RULE",
                    "reason": f"Matched regional operational ownership rule for domain '{domain}' across Region '{region_id}'.",
                    "supportingData": supporting_data,
                    "confidence": 0.90,
                    "isAmbiguous": False,
                    "fallbackTeamId": reg_map["secondary_team_id"],
                    "fallbackTeamName": reg_map["secondary_team_name"],
                    "slaMinutes": sla_mins
                }

        # 4. TEAM SPECIALIZATION & RESPONSIBILITY RULES
        # Search active teams in store or region matching specialization
        spec_query = """
            SELECT id, name, team_type, specialization, sla_tier
            FROM operational_teams
            WHERE organization_id = ?
              AND (store_id = ? OR region_id = ? OR (store_id IS NULL AND region_id IS NULL))
              AND (specialization = ? OR team_type = ? OR responsibility LIKE ?)
              AND status = 'ACTIVE';
        """
        like_domain = f"%{domain}%"
        cur.execute(spec_query, (organization_id, store_id, region_id, domain, domain, like_domain))
        specialized_teams = cur.fetchall()

        if len(specialized_teams) == 1:
            team = specialized_teams[0]
            sla_mins = RoutingService.calculate_deterministic_sla(priority_tier, is_safety_hazard=is_safety_hazard)
            supporting_data["matchedSpecialization"] = team["specialization"]
            return {
                "selectedTeamId": team["id"],
                "selectedTeamName": team["name"],
                "assignedUserId": None,
                "routingTier": "SPECIALIZED_TEAM",
                "routingStrategy": "TEAM_SPECIALIZATION_MATCH",
                "reason": f"Matched operational team '{team['name']}' based on verified specialization '{team['specialization']}'.",
                "supportingData": supporting_data,
                "confidence": 0.80,
                "isAmbiguous": False,
                "fallbackTeamId": None,
                "slaMinutes": sla_mins
            }

        # 5. AMBIGUOUS CONTEXT / LOW CONFIDENCE -> HUMAN TRIAGE QUEUE
        # If multiple conflicting teams match or domain is unknown:
        # Never guess to avoid operational ping-pong. Route directly to Central Human Triage.
        ambiguity_reason = (
            f"Multiple conflicting specialized teams ({len(specialized_teams)}) matched domain '{domain}'."
            if len(specialized_teams) > 1
            else f"No specialized operational ownership rule or team specialization matched domain '{domain}'."
        )
        supporting_data["candidateTeamsCount"] = len(specialized_teams)
        supporting_data["candidateTeams"] = [{"id": t["id"], "name": t["name"]} for t in specialized_teams]
        supporting_data["ambiguityReason"] = ambiguity_reason

        return {
            "selectedTeamId": None,
            "selectedTeamName": None,
            "assignedUserId": None,
            "routingTier": "HUMAN_TRIAGE_QUEUE",
            "routingStrategy": "AMBIGUOUS_TRIAGE_QUEUE",
            "reason": f"Routing confidence is low (0.45). {ambiguity_reason} Routed to Central Human Triage Queue.",
            "supportingData": supporting_data,
            "confidence": 0.45,
            "isAmbiguous": True,
            "fallbackTeamId": None,
            "slaMinutes": 45  # Triage queue SLA to review within 45 minutes
        }

    @staticmethod
    def route_issue(
        conn: sqlite3.Connection,
        issue_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute deterministic routing for an issue, record the decision, and assign SLA."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM issues WHERE id = ?;", (issue_id,))
        issue = cur.fetchone()
        if not issue:
            raise NotFoundError("Issue", issue_id)

        # Infer category and title cues
        category = "unknown"
        if issue["cluster_id"]:
            cur.execute("SELECT category FROM issue_clusters WHERE id = ?;", (issue["cluster_id"],))
            cl = cur.fetchone()
            if cl:
                category = cl["category"]

        # If not from cluster, check linked feedback items
        if category == "unknown":
            cur.execute("""
                SELECT fi.ai_interpretation, fi.raw_text FROM issue_feedback_links ifl
                JOIN feedback_items fi ON ifl.feedback_item_id = fi.id
                WHERE ifl.issue_id = ? LIMIT 1;
            """, (issue_id,))
            fb = cur.fetchone()
            if fb and fb["ai_interpretation"]:
                try:
                    interp = json.loads(fb["ai_interpretation"])
                    category = interp.get("issueCategory", {}).get("value", "unknown")
                except Exception:
                    category = "unknown"

        # Check safety hazard from factor breakdown or title
        is_safety = False
        if issue["factor_breakdown"]:
            try:
                breakdown = json.loads(issue["factor_breakdown"])
                is_safety = breakdown.get("isSafetyHazard", False) or (breakdown.get("safety", 0.0) > 0)
            except Exception:
                is_safety = False

        decision = RoutingService.determine_routing(
            conn=conn,
            organization_id=issue["organization_id"],
            store_id=issue["store_id"],
            category=category,
            priority_tier=issue["priority_tier"],
            severity_score=issue["severity_score"],
            is_safety_hazard=is_safety,
            department_id=issue["department_id"],
            issue_title=issue["title"],
            description=issue["description"]
        )

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        sla_mins = decision["slaMinutes"]
        sla_deadline = (now + timedelta(minutes=sla_mins)).isoformat()
        escalation_deadline = (now + timedelta(minutes=int(sla_mins * 1.5))).isoformat()

        decision_id = f"rd-{uuid.uuid4().hex[:10]}"
        supporting_json = json.dumps(decision["supportingData"])

        # Insert routing decision history record
        cur.execute("""
            INSERT INTO routing_decisions (
                id, organization_id, issue_id, selected_team_id, assigned_user_id,
                routing_tier, routing_strategy, reason, supporting_data, confidence,
                is_ambiguous, fallback_team_id, is_human_override, sla_minutes,
                sla_deadline, escalation_deadline, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?);
        """, (
            decision_id,
            issue["organization_id"],
            issue_id,
            decision["selectedTeamId"],
            decision["assignedUserId"],
            decision["routingTier"],
            decision["routingStrategy"],
            decision["reason"],
            supporting_json,
            decision["confidence"],
            1 if decision["isAmbiguous"] else 0,
            decision["fallbackTeamId"],
            sla_mins,
            sla_deadline,
            escalation_deadline,
            now_iso
        ))

        # Update Issue with assignment, status, and SLA
        new_status = "TRIAGE_QUEUE" if decision["isAmbiguous"] else "DISPATCHED"
        routing_status = "TRIAGE_QUEUE" if decision["isAmbiguous"] else "ROUTED"

        cur.execute("""
            UPDATE issues
            SET assigned_team_id = ?,
                assigned_user_id = ?,
                sla_minutes = ?,
                sla_deadline = ?,
                routing_status = ?,
                routing_decision_id = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?;
        """, (
            decision["selectedTeamId"],
            decision["assignedUserId"],
            sla_mins,
            sla_deadline,
            routing_status,
            decision_id,
            new_status,
            now_iso,
            issue_id
        ))

        AuditService.record_audit(
            conn=conn,
            organization_id=issue["organization_id"],
            user_id=user_id,
            entity_type="ISSUE",
            entity_id=issue_id,
            action="ISSUE_ROUTED",
            new_state={
                "routingDecisionId": decision_id,
                "selectedTeamId": decision["selectedTeamId"],
                "routingTier": decision["routingTier"],
                "isAmbiguous": decision["isAmbiguous"],
                "slaMinutes": sla_mins,
                "slaDeadline": sla_deadline
            }
        )

        return RoutingService.get_routing_decision(conn, decision_id)

    @staticmethod
    def reassign_issue(
        conn: sqlite3.Connection,
        issue_id: str,
        target_team_id: Optional[str],
        target_user_id: Optional[str],
        override_reason: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Human operator overrides automatic routing and reassigns issue to a new team/user."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM issues WHERE id = ?;", (issue_id,))
        issue = cur.fetchone()
        if not issue:
            raise NotFoundError("Issue", issue_id)

        _target_team_name = None
        if target_team_id:
            cur.execute("SELECT name FROM operational_teams WHERE id = ?;", (target_team_id,))
            team = cur.fetchone()
            if not team:
                raise ValidationError(f"Target team '{target_team_id}' does not exist.")
            _target_team_name = team["name"]

        _target_user_name = None
        if target_user_id:
            cur.execute("SELECT full_name FROM users WHERE id = ?;", (target_user_id,))
            u = cur.fetchone()
            if u:
                _target_user_name = u["full_name"]

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        sla_mins = issue["sla_minutes"] or 60
        sla_deadline = (now + timedelta(minutes=sla_mins)).isoformat()
        decision_id = f"rd-{uuid.uuid4().hex[:10]}"

        supporting_data = {
            "previousTeamId": issue["assigned_team_id"],
            "previousUserId": issue["assigned_user_id"],
            "reassignedBy": user_id,
            "reassignmentReason": override_reason
        }

        cur.execute("""
            INSERT INTO routing_decisions (
                id, organization_id, issue_id, selected_team_id, assigned_user_id,
                routing_tier, routing_strategy, reason, supporting_data, confidence,
                is_ambiguous, fallback_team_id, is_human_override, override_by,
                override_reason, sla_minutes, sla_deadline, escalation_deadline, created_at
            ) VALUES (?, ?, ?, ?, ?, 'MANUAL_REASSIGNMENT', 'HUMAN_OVERRIDE', ?, ?, 1.0, 0, NULL, 1, ?, ?, ?, ?, NULL, ?);
        """, (
            decision_id,
            issue["organization_id"],
            issue_id,
            target_team_id,
            target_user_id,
            f"Human override reassignment: {override_reason}",
            json.dumps(supporting_data),
            user_id,
            override_reason,
            sla_mins,
            sla_deadline,
            now_iso
        ))

        cur.execute("""
            UPDATE issues
            SET assigned_team_id = ?,
                assigned_user_id = ?,
                routing_status = 'REASSIGNED',
                routing_decision_id = ?,
                status = 'DISPATCHED',
                updated_at = ?
            WHERE id = ?;
        """, (target_team_id, target_user_id, decision_id, now_iso, issue_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=issue["organization_id"],
            user_id=user_id,
            entity_type="ISSUE",
            entity_id=issue_id,
            action="ISSUE_ROUTING_REASSIGNED",
            new_state={
                "targetTeamId": target_team_id,
                "targetUserId": target_user_id,
                "reason": override_reason
            }
        )

        return RoutingService.get_routing_decision(conn, decision_id)

    @staticmethod
    def escalate_issue(
        conn: sqlite3.Connection,
        issue_id: str,
        escalation_reason: str,
        target_team_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Escalate an issue to secondary tier or management, shortening the SLA deadline."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM issues WHERE id = ?;", (issue_id,))
        issue = cur.fetchone()
        if not issue:
            raise NotFoundError("Issue", issue_id)

        # Determine escalation team: if target_team_id not provided, check fallback on latest routing decision
        esc_team_id = target_team_id
        if not esc_team_id:
            cur.execute("""
                SELECT fallback_team_id FROM routing_decisions
                WHERE issue_id = ? AND fallback_team_id IS NOT NULL
                ORDER BY created_at DESC LIMIT 1;
            """, (issue_id,))
            fb_row = cur.fetchone()
            if fb_row:
                esc_team_id = fb_row["fallback_team_id"]

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        current_sla = issue["sla_minutes"] or 60
        # Escalation accelerates SLA deadline (cut in half, min 15 minutes)
        accelerated_sla = max(15, current_sla // 2)
        accelerated_deadline = (now + timedelta(minutes=accelerated_sla)).isoformat()
        decision_id = f"rd-{uuid.uuid4().hex[:10]}"

        supporting_data = {
            "previousTeamId": issue["assigned_team_id"],
            "escalatedBy": user_id,
            "escalationReason": escalation_reason,
            "acceleratedSlaMinutes": accelerated_sla
        }

        cur.execute("""
            INSERT INTO routing_decisions (
                id, organization_id, issue_id, selected_team_id, assigned_user_id,
                routing_tier, routing_strategy, reason, supporting_data, confidence,
                is_ambiguous, fallback_team_id, is_human_override, override_by,
                override_reason, sla_minutes, sla_deadline, escalation_deadline, created_at
            ) VALUES (?, ?, ?, ?, NULL, 'ESCALATION_TIER', 'OPERATIONAL_ESCALATION', ?, ?, 1.0, 0, NULL, 1, ?, ?, ?, ?, NULL, ?);
        """, (
            decision_id,
            issue["organization_id"],
            issue_id,
            esc_team_id or issue["assigned_team_id"],
            f"Operational escalation: {escalation_reason}",
            json.dumps(supporting_data),
            user_id,
            escalation_reason,
            accelerated_sla,
            accelerated_deadline,
            now_iso
        ))

        cur.execute("""
            UPDATE issues
            SET assigned_team_id = COALESCE(?, assigned_team_id),
                sla_minutes = ?,
                sla_deadline = ?,
                routing_status = 'ESCALATED',
                routing_decision_id = ?,
                status = 'IN_PROGRESS',
                updated_at = ?
            WHERE id = ?;
        """, (esc_team_id, accelerated_sla, accelerated_deadline, decision_id, now_iso, issue_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=issue["organization_id"],
            user_id=user_id,
            entity_type="ISSUE",
            entity_id=issue_id,
            action="ISSUE_ROUTING_ESCALATED",
            new_state={
                "escalatedTeamId": esc_team_id,
                "acceleratedSlaMinutes": accelerated_sla,
                "reason": escalation_reason
            }
        )

        return RoutingService.get_routing_decision(conn, decision_id)

    @staticmethod
    def get_routing_decision(conn: sqlite3.Connection, decision_id: str) -> Dict[str, Any]:
        """Fetch a routing decision by ID with resolved team and user labels."""
        cur = conn.cursor()
        cur.execute("""
            SELECT rd.*,
                   t.name as selected_team_name,
                   f.name as fallback_team_name,
                   u.full_name as assigned_user_name,
                   ob.full_name as override_user_name
            FROM routing_decisions rd
            LEFT JOIN operational_teams t ON rd.selected_team_id = t.id
            LEFT JOIN operational_teams f ON rd.fallback_team_id = f.id
            LEFT JOIN users u ON rd.assigned_user_id = u.id
            LEFT JOIN users ob ON rd.override_by = ob.id
            WHERE rd.id = ?;
        """, (decision_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("RoutingDecision", decision_id)

        supp_data = {}
        if row["supporting_data"]:
            try:
                supp_data = json.loads(row["supporting_data"])
            except Exception:
                pass

        return {
            "id": row["id"],
            "issueId": row["issue_id"],
            "organizationId": row["organization_id"],
            "selectedTeamId": row["selected_team_id"],
            "selectedTeamName": row["selected_team_name"],
            "assignedUserId": row["assigned_user_id"],
            "assignedUserName": row["assigned_user_name"],
            "routingTier": row["routing_tier"],
            "routingStrategy": row["routing_strategy"],
            "reason": row["reason"],
            "supportingData": supp_data,
            "confidence": row["confidence"],
            "isAmbiguous": bool(row["is_ambiguous"]),
            "fallbackTeamId": row["fallback_team_id"],
            "fallbackTeamName": row["fallback_team_name"],
            "isHumanOverride": bool(row["is_human_override"]),
            "overrideBy": row["override_by"],
            "overrideReason": row["override_reason"],
            "slaMinutes": row["sla_minutes"],
            "slaDeadline": row["sla_deadline"],
            "escalationDeadline": row["escalation_deadline"],
            "createdAt": row["created_at"]
        }

    @staticmethod
    def get_issue_routing_history(conn: sqlite3.Connection, issue_id: str) -> List[Dict[str, Any]]:
        """Retrieve complete chronological routing lineage for an issue."""
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM routing_decisions
            WHERE issue_id = ?
            ORDER BY created_at DESC;
        """, (issue_id,))
        rows = cur.fetchall()
        return [RoutingService.get_routing_decision(conn, r["id"]) for r in rows]

    @staticmethod
    def get_triage_queue(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all issues routed to Human Triage Queue due to ambiguous classification,
        low confidence, or missing operational ownership rules.
        """
        cur = conn.cursor()
        query = """
            SELECT i.id as issue_id, rd.id as decision_id, rd.reason, rd.supporting_data, rd.created_at as routed_at
            FROM issues i
            JOIN routing_decisions rd ON i.routing_decision_id = rd.id
            WHERE i.organization_id = ?
              AND (i.routing_status = 'TRIAGE_QUEUE' OR rd.is_ambiguous = 1)
        """
        params: List[Any] = [organization_id]
        if store_id:
            query += " AND i.store_id = ?"
            params.append(store_id)

        query += " ORDER BY i.priority_score DESC, rd.created_at ASC;"
        cur.execute(query, params)
        rows = cur.fetchall()

        results = []
        from backend.app.services.issue_service import IssueService

        for r in rows:
            issue_data = IssueService.get_issue_by_id(conn, r["issue_id"])
            supp = {}
            if r["supporting_data"]:
                try:
                    supp = json.loads(r["supporting_data"])
                except Exception:
                    pass

            candidate_teams = supp.get("candidateTeams", [])
            results.append({
                "issue": issue_data,
                "ambiguityReason": r["reason"],
                "suggestedTeams": candidate_teams,
                "routedAt": r["routed_at"]
            })

        return results

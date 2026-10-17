import uuid
import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.app.schemas.domain import IssueCreate, IssueStatusUpdate, IssuePriorityOverride
from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.services.audit_service import AuditService

VALID_TRANSITIONS: Dict[str, List[str]] = {
    "DETECTED": ["TRIAGED", "CLOSED"],
    "TRIAGED": ["DISPATCHED", "CLOSED"],
    "DISPATCHED": ["IN_PROGRESS", "TRIAGED"],
    "IN_PROGRESS": ["REMEDIATED"],
    "REMEDIATED": ["VERIFYING", "CLOSED"],
    "VERIFYING": ["CLOSED", "REOPENED"],
    "CLOSED": ["REOPENED"],
    "REOPENED": ["TRIAGED", "DISPATCHED"]
}

def calculate_priority(severity: float, urgency: float, impact: float) -> tuple[int, str]:
    raw_score = 100.0 * ((0.40 * severity) + (0.35 * urgency) + (0.25 * impact))
    score = max(1, min(100, round(raw_score)))
    if score >= 85:
        tier = "P1_CRITICAL"
    elif score >= 70:
        tier = "P2_HIGH"
    elif score >= 45:
        tier = "P3_MEDIUM"
    else:
        tier = "P4_LOW"
    return score, tier

class IssueService:
    @staticmethod
    def create_issue(
        conn: sqlite3.Connection,
        organization_id: str,
        payload: IssueCreate,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        fb_count = len(payload.feedbackItemIds) if payload.feedbackItemIds else 1
        priority_score, priority_tier = calculate_priority(
            payload.severityScore,
            payload.urgencyScore,
            payload.impactScopeScore
        )
        factor_breakdown_json = json.dumps({
            "severity": round(100.0 * 0.40 * payload.severityScore, 2),
            "urgency": round(100.0 * 0.35 * payload.urgencyScore, 2),
            "operationalImpact": round(100.0 * 0.25 * payload.impactScopeScore, 2)
        })
        explanation = (
            f"Priority {priority_tier} ({priority_score}/100) calculated from: "
            f"severity={payload.severityScore:.2f} (40%), urgency={payload.urgencyScore:.2f} (35%), scope={payload.impactScopeScore:.2f} (25%)."
        )

        issue_id = f"issue-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO issues (
                id, organization_id, store_id, department_id, asset_id,
                title, description, status, priority_score, priority_tier,
                severity_score, urgency_score, impact_scope_score, confidence_score,
                is_emerging_anomaly, anomaly_velocity_zscore, assigned_team_id,
                root_cause_hypothesis, feedback_count, factor_breakdown,
                prioritization_explanation, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            issue_id,
            organization_id,
            payload.storeId,
            payload.departmentId,
            payload.assetId,
            payload.title,
            payload.description,
            "DETECTED",
            priority_score,
            priority_tier,
            payload.severityScore,
            payload.urgencyScore,
            payload.impactScopeScore,
            0.85, # Confidence baseline
            0,
            0.0,
            payload.assignedTeamId,
            "Preliminary triage hypothesis pending investigation.",
            fb_count,
            factor_breakdown_json,
            explanation,
            now,
            now
        ))

        # Link feedback items if provided
        if payload.feedbackItemIds:
            for fb_id in payload.feedbackItemIds:
                cur.execute("""
                    INSERT OR IGNORE INTO issue_feedback_links (issue_id, feedback_item_id)
                    VALUES (?, ?);
                """, (issue_id, fb_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=organization_id,
            user_id=user_id,
            entity_type="ISSUE",
            entity_id=issue_id,
            action="ISSUE_CREATED",
            new_state={"title": payload.title, "priorityScore": priority_score, "status": "DETECTED"}
        )

        return IssueService.get_issue_by_id(conn, issue_id)

    @staticmethod
    def update_issue_status(
        conn: sqlite3.Connection,
        issue_id: str,
        payload: IssueStatusUpdate,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM issues WHERE id = ?;", (issue_id,))
        current = cur.fetchone()
        if not current:
            raise NotFoundError("Issue", issue_id)

        current_status = current["status"]
        new_status = payload.status

        # Validate transition
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed and new_status != current_status:
            raise ValidationError(
                f"Invalid state transition from '{current_status}' to '{new_status}'. Allowed transitions: {allowed}"
            )

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE issues SET status = ?, updated_at = ? WHERE id = ?;", (new_status, now, issue_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=current["organization_id"],
            user_id=user_id,
            entity_type="ISSUE",
            entity_id=issue_id,
            action="STATUS_CHANGE",
            previous_state={"status": current_status},
            new_state={"status": new_status},
            justification=payload.justification
        )

        return IssueService.get_issue_by_id(conn, issue_id)

    @staticmethod
    def override_priority(
        conn: sqlite3.Connection,
        issue_id: str,
        payload: IssuePriorityOverride,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM issues WHERE id = ?;", (issue_id,))
        current = cur.fetchone()
        if not current:
            raise NotFoundError("Issue", issue_id)

        old_score = current["priority_score"]
        new_score = payload.newPriorityScore
        if new_score >= 85:
            new_tier = "P1_CRITICAL"
        elif new_score >= 70:
            new_tier = "P2_HIGH"
        elif new_score >= 45:
            new_tier = "P3_MEDIUM"
        else:
            new_tier = "P4_LOW"

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE issues SET priority_score = ?, priority_tier = ?, updated_at = ? WHERE id = ?;
        """, (new_score, new_tier, now, issue_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=current["organization_id"],
            user_id=user_id,
            entity_type="ISSUE",
            entity_id=issue_id,
            action="PRIORITY_OVERRIDE",
            previous_state={"priorityScore": old_score, "priorityTier": current["priority_tier"]},
            new_state={"priorityScore": new_score, "priorityTier": new_tier},
            justification=payload.justification
        )

        return IssueService.get_issue_by_id(conn, issue_id)

    @staticmethod
    def get_issue_by_id(conn: sqlite3.Connection, issue_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT i.*, t.name as assigned_team_name, u.full_name as assigned_user_name
            FROM issues i
            LEFT JOIN operational_teams t ON i.assigned_team_id = t.id
            LEFT JOIN users u ON i.assigned_user_id = u.id
            WHERE i.id = ?;
        """, (issue_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("Issue", issue_id)

        factors = None
        if r["factor_breakdown"]:
            try:
                factors = json.loads(r["factor_breakdown"])
            except Exception:
                factors = None

        r_keys = r.keys()
        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "storeId": r["store_id"],
            "departmentId": r["department_id"],
            "assetId": r["asset_id"],
            "clusterId": r["cluster_id"],
            "title": r["title"],
            "description": r["description"],
            "status": r["status"],
            "priorityScore": r["priority_score"],
            "priorityTier": r["priority_tier"],
            "severityScore": r["severity_score"],
            "urgencyScore": r["urgency_score"],
            "impactScopeScore": r["impact_scope_score"],
            "confidenceScore": r["confidence_score"],
            "isEmergingAnomaly": bool(r["is_emerging_anomaly"]),
            "anomalyVelocityZScore": r["anomaly_velocity_zscore"],
            "assignedTeamId": r["assigned_team_id"],
            "assignedTeamName": r["assigned_team_name"],
            "assignedUserId": r["assigned_user_id"] if "assigned_user_id" in r_keys else None,
            "assignedUserName": r["assigned_user_name"] if "assigned_user_name" in r_keys else None,
            "slaMinutes": r["sla_minutes"] if "sla_minutes" in r_keys else 60,
            "slaDeadline": r["sla_deadline"] if "sla_deadline" in r_keys else None,
            "routingStatus": r["routing_status"] if "routing_status" in r_keys else "ROUTED",
            "routingDecisionId": r["routing_decision_id"] if "routing_decision_id" in r_keys else None,
            "rootCauseHypothesis": r["root_cause_hypothesis"],
            "feedbackCount": r["feedback_count"],
            "recurrenceCount": r["recurrence_count"] if "recurrence_count" in r_keys else 0,
            "geographicSpreadCount": r["geographic_spread_count"] if "geographic_spread_count" in r_keys else 1,
            "factorBreakdown": factors,
            "prioritizationExplanation": r["prioritization_explanation"] if "prioritization_explanation" in r_keys else None,
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

    @staticmethod
    def get_issues(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        status: Optional[str] = None,
        priority_tier: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT i.*, t.name as assigned_team_name, u.full_name as assigned_user_name
            FROM issues i
            LEFT JOIN operational_teams t ON i.assigned_team_id = t.id
            LEFT JOIN users u ON i.assigned_user_id = u.id
            WHERE i.organization_id = ?
        """
        params: List[Any] = [organization_id]
        if store_id:
            query += " AND i.store_id = ?"
            params.append(store_id)
        if status:
            query += " AND i.status = ?"
            params.append(status)
        if priority_tier:
            query += " AND i.priority_tier = ?"
            params.append(priority_tier)

        query += " ORDER BY i.priority_score DESC, i.created_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        result = []
        for r in rows:
            factors = None
            if r["factor_breakdown"]:
                try:
                    factors = json.loads(r["factor_breakdown"])
                except Exception:
                    factors = None
            result.append({
                "id": r["id"],
                "organizationId": r["organization_id"],
                "storeId": r["store_id"],
                "departmentId": r["department_id"],
                "assetId": r["asset_id"],
                "clusterId": r["cluster_id"],
                "title": r["title"],
                "description": r["description"],
                "status": r["status"],
                "priorityScore": r["priority_score"],
                "priorityTier": r["priority_tier"],
                "severityScore": r["severity_score"],
                "urgencyScore": r["urgency_score"],
                "impactScopeScore": r["impact_scope_score"],
                "confidenceScore": r["confidence_score"],
                "isEmergingAnomaly": bool(r["is_emerging_anomaly"]),
                "anomalyVelocityZScore": r["anomaly_velocity_zscore"],
                "assignedTeamId": r["assigned_team_id"],
                "assignedTeamName": r["assigned_team_name"],
                "assignedUserId": r["assigned_user_id"] if "assigned_user_id" in r.keys() else None,
                "assignedUserName": r["assigned_user_name"] if "assigned_user_name" in r.keys() else None,
                "slaMinutes": r["sla_minutes"] if "sla_minutes" in r.keys() else 60,
                "slaDeadline": r["sla_deadline"] if "sla_deadline" in r.keys() else None,
                "routingStatus": r["routing_status"] if "routing_status" in r.keys() else "ROUTED",
                "routingDecisionId": r["routing_decision_id"] if "routing_decision_id" in r.keys() else None,
                "rootCauseHypothesis": r["root_cause_hypothesis"],
                "feedbackCount": r["feedback_count"],
                "recurrenceCount": r["recurrence_count"] if "recurrence_count" in r.keys() else 0,
                "geographicSpreadCount": r["geographic_spread_count"] if "geographic_spread_count" in r.keys() else 1,
                "factorBreakdown": factors,
                "prioritizationExplanation": r["prioritization_explanation"] if "prioritization_explanation" in r.keys() else None,
                "createdAt": r["created_at"],
                "updatedAt": r["updated_at"]
            })
        return result

    @staticmethod
    def get_issues_paginated(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        status: Optional[str] = None,
        priority_tier: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> tuple[List[Dict[str, Any]], Any]:
        from backend.app.schemas.common import PaginationMeta
        cur = conn.cursor()
        base_where = "WHERE i.organization_id = ?"
        params: List[Any] = [organization_id]
        if store_id:
            base_where += " AND i.store_id = ?"
            params.append(store_id)
        if status:
            base_where += " AND i.status = ?"
            params.append(status)
        if priority_tier:
            base_where += " AND i.priority_tier = ?"
            params.append(priority_tier)

        # Count total
        count_sql = f"SELECT COUNT(*) FROM issues i {base_where};"
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        # Fetch page
        query = f"""
            SELECT i.*, t.name as assigned_team_name, u.full_name as assigned_user_name
            FROM issues i
            LEFT JOIN operational_teams t ON i.assigned_team_id = t.id
            LEFT JOIN users u ON i.assigned_user_id = u.id
            {base_where}
            ORDER BY i.priority_score DESC, i.created_at DESC
            LIMIT ? OFFSET ?;
        """
        page_params = list(params) + [limit, (page - 1) * limit]
        cur.execute(query, page_params)
        rows = cur.fetchall()

        result = []
        for r in rows:
            factors = None
            if r["factor_breakdown"]:
                try:
                    factors = json.loads(r["factor_breakdown"])
                except Exception:
                    factors = None
            result.append({
                "id": r["id"],
                "organizationId": r["organization_id"],
                "storeId": r["store_id"],
                "departmentId": r["department_id"],
                "assetId": r["asset_id"],
                "clusterId": r["cluster_id"],
                "title": r["title"],
                "description": r["description"],
                "status": r["status"],
                "priorityScore": r["priority_score"],
                "priorityTier": r["priority_tier"],
                "severityScore": r["severity_score"],
                "urgencyScore": r["urgency_score"],
                "impactScopeScore": r["impact_scope_score"],
                "confidenceScore": r["confidence_score"],
                "isEmergingAnomaly": bool(r["is_emerging_anomaly"]),
                "anomalyVelocityZScore": r["anomaly_velocity_zscore"],
                "assignedTeamId": r["assigned_team_id"],
                "assignedTeamName": r["assigned_team_name"],
                "assignedUserId": r["assigned_user_id"] if "assigned_user_id" in r.keys() else None,
                "assignedUserName": r["assigned_user_name"] if "assigned_user_name" in r.keys() else None,
                "slaMinutes": r["sla_minutes"] if "sla_minutes" in r.keys() else 60,
                "slaDeadline": r["sla_deadline"] if "sla_deadline" in r.keys() else None,
                "routingStatus": r["routing_status"] if "routing_status" in r.keys() else "ROUTED",
                "routingDecisionId": r["routing_decision_id"] if "routing_decision_id" in r.keys() else None,
                "rootCauseHypothesis": r["root_cause_hypothesis"],
                "feedbackCount": r["feedback_count"],
                "recurrenceCount": r["recurrence_count"] if "recurrence_count" in r.keys() else 0,
                "geographicSpreadCount": r["geographic_spread_count"] if "geographic_spread_count" in r.keys() else 1,
                "factorBreakdown": factors,
                "prioritizationExplanation": r["prioritization_explanation"] if "prioritization_explanation" in r.keys() else None,
                "createdAt": r["created_at"],
                "updatedAt": r["updated_at"]
            })

        total_pages = max(1, (total + limit - 1) // limit)
        meta = PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages)
        return result, meta

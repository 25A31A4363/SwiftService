import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.app.schemas.domain import ActionApprovalUpdate, ActionOverrideUpdate
from backend.app.core.errors import NotFoundError
from backend.app.services.audit_service import AuditService

class ActionService:
    @staticmethod
    def get_actions(
        conn: sqlite3.Connection,
        organization_id: str,
        issue_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT a.*, t.name as target_team_name
            FROM action_plans a
            LEFT JOIN operational_teams t ON a.target_team_id = t.id
            WHERE a.organization_id = ?
        """
        params: List[Any] = [organization_id]
        if issue_id:
            query += " AND a.issue_id = ?"
            params.append(issue_id)

        query += " ORDER BY a.created_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return [{
            "id": r["id"],
            "organizationId": r["organization_id"],
            "issueId": r["issue_id"],
            "recommendedAction": r["recommended_action"],
            "targetTeamId": r["target_team_id"],
            "targetTeamName": r["target_team_name"],
            "requiresHumanApproval": bool(r["requires_human_approval"]),
            "approvalStatus": r["approval_status"],
            "approvedBy": r["approved_by"],
            "approvedAt": r["approved_at"],
            "overrideReason": r["override_reason"],
            "slaDeadline": r["sla_deadline"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in rows]

    @staticmethod
    def approve_action(
        conn: sqlite3.Connection,
        action_id: str,
        payload: ActionApprovalUpdate,
        user_id: str
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM action_plans WHERE id = ?;", (action_id,))
        action = cur.fetchone()
        if not action:
            raise NotFoundError("ActionPlan", action_id)

        now = datetime.now(timezone.utc).isoformat()
        new_status = payload.decision # 'APPROVED' or 'REJECTED'

        cur.execute("""
            UPDATE action_plans
            SET approval_status = ?, approved_by = ?, approved_at = ?, updated_at = ?
            WHERE id = ?;
        """, (new_status, user_id, now, now, action_id))

        # If approved, also advance the linked issue to DISPATCHED
        if new_status == "APPROVED":
            cur.execute("""
                UPDATE issues SET status = 'DISPATCHED', updated_at = ?
                WHERE id = ? AND status = 'TRIAGED';
            """, (now, action["issue_id"]))

        AuditService.record_audit(
            conn=conn,
            organization_id=action["organization_id"],
            user_id=user_id,
            entity_type="ACTION_PLAN",
            entity_id=action_id,
            action=f"ACTION_{new_status}",
            previous_state={"approvalStatus": action["approval_status"]},
            new_state={"approvalStatus": new_status, "approvedAt": now},
            justification=payload.justification
        )

        return ActionService.get_action_by_id(conn, action_id)

    @staticmethod
    def override_routing(
        conn: sqlite3.Connection,
        action_id: str,
        payload: ActionOverrideUpdate,
        user_id: str
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM action_plans WHERE id = ?;", (action_id,))
        action = cur.fetchone()
        if not action:
            raise NotFoundError("ActionPlan", action_id)

        # Check new team exists
        cur.execute("SELECT id, name FROM operational_teams WHERE id = ?;", (payload.newTargetTeamId,))
        team = cur.fetchone()
        if not team:
            raise NotFoundError("OperationalTeam", payload.newTargetTeamId)

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE action_plans
            SET target_team_id = ?, approval_status = 'OVERRIDDEN', override_reason = ?, approved_by = ?, approved_at = ?, updated_at = ?
            WHERE id = ?;
        """, (payload.newTargetTeamId, payload.overrideReason, user_id, now, now, action_id))

        # Update issue assigned team as well
        cur.execute("""
            UPDATE issues SET assigned_team_id = ?, updated_at = ? WHERE id = ?;
        """, (payload.newTargetTeamId, now, action["issue_id"]))

        AuditService.record_audit(
            conn=conn,
            organization_id=action["organization_id"],
            user_id=user_id,
            entity_type="ACTION_PLAN",
            entity_id=action_id,
            action="ROUTING_OVERRIDE",
            previous_state={"targetTeamId": action["target_team_id"]},
            new_state={"targetTeamId": payload.newTargetTeamId, "approvalStatus": "OVERRIDDEN"},
            justification=payload.overrideReason
        )

        return ActionService.get_action_by_id(conn, action_id)

    @staticmethod
    def get_action_by_id(conn: sqlite3.Connection, action_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.*, t.name as target_team_name
            FROM action_plans a
            LEFT JOIN operational_teams t ON a.target_team_id = t.id
            WHERE a.id = ?;
        """, (action_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("ActionPlan", action_id)

        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "issueId": r["issue_id"],
            "recommendedAction": r["recommended_action"],
            "targetTeamId": r["target_team_id"],
            "targetTeamName": r["target_team_name"],
            "requiresHumanApproval": bool(r["requires_human_approval"]),
            "approvalStatus": r["approval_status"],
            "approvedBy": r["approved_by"],
            "approvedAt": r["approved_at"],
            "overrideReason": r["override_reason"],
            "slaDeadline": r["sla_deadline"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

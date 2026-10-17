import uuid
import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any
from backend.app.schemas.domain import ResolutionCreate
from backend.app.core.errors import NotFoundError
from backend.app.services.audit_service import AuditService

class ResolutionService:
    @staticmethod
    def create_resolution(
        conn: sqlite3.Connection,
        payload: ResolutionCreate,
        user_id: str
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM action_plans WHERE id = ?;", (payload.actionPlanId,))
        action = cur.fetchone()
        if not action:
            raise NotFoundError("ActionPlan", payload.actionPlanId)

        issue_id = action["issue_id"]
        cur.execute("SELECT * FROM issues WHERE id = ?;", (issue_id,))
        issue = cur.fetchone()
        if not issue:
            raise NotFoundError("Issue", issue_id)

        resolution_id = f"res-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()

        # Scorecard baseline
        scorecard = {
            "preFeedbackRate": 2.0,
            "postFeedbackRate": 0.0,
            "feedbackRateDeltaPct": -100.0,
            "sentimentShift": 0.65,
            "recurrenceCount": 0,
            "evaluatedAt": now
        }

        cur.execute("""
            INSERT INTO resolutions (
                id, organization_id, issue_id, action_plan_id, technician_notes,
                resolved_by, resolved_at, verification_status, verification_scorecard, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            resolution_id,
            issue["organization_id"],
            issue_id,
            payload.actionPlanId,
            payload.technicianNotes,
            user_id,
            now,
            "PENDING_VERIFICATION",
            json.dumps(scorecard),
            now,
            now
        ))

        # Advance issue state to VERIFYING
        cur.execute("""
            UPDATE issues SET status = 'VERIFYING', updated_at = ? WHERE id = ?;
        """, (now, issue_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=issue["organization_id"],
            user_id=user_id,
            entity_type="RESOLUTION",
            entity_id=resolution_id,
            action="RESOLUTION_LOGGED",
            new_state={"verificationStatus": "PENDING_VERIFICATION", "technicianNotes": payload.technicianNotes}
        )

        return ResolutionService.get_resolution_by_id(conn, resolution_id)

    @staticmethod
    def get_resolution_by_id(conn: sqlite3.Connection, resolution_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*, u.full_name as resolved_by_name
            FROM resolutions r
            LEFT JOIN users u ON r.resolved_by = u.id
            WHERE r.id = ?;
        """, (resolution_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("Resolution", resolution_id)

        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "issueId": r["issue_id"],
            "actionPlanId": r["action_plan_id"],
            "technicianNotes": r["technician_notes"],
            "resolvedBy": r["resolved_by"],
            "resolvedByName": r["resolved_by_name"],
            "resolvedAt": r["resolved_at"],
            "verificationStatus": r["verification_status"],
            "verificationScorecard": json.loads(r["verification_scorecard"]) if r["verification_scorecard"] else None,
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

    @staticmethod
    def get_resolutions_for_issue(conn: sqlite3.Connection, issue_id: str) -> List[Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*, u.full_name as resolved_by_name
            FROM resolutions r
            LEFT JOIN users u ON r.resolved_by = u.id
            WHERE r.issue_id = ?
            ORDER BY r.created_at DESC;
        """, (issue_id,))
        return [{
            "id": r["id"],
            "organizationId": r["organization_id"],
            "issueId": r["issue_id"],
            "actionPlanId": r["action_plan_id"],
            "technicianNotes": r["technician_notes"],
            "resolvedBy": r["resolved_by"],
            "resolvedByName": r["resolved_by_name"],
            "resolvedAt": r["resolved_at"],
            "verificationStatus": r["verification_status"],
            "verificationScorecard": json.loads(r["verification_scorecard"]) if r["verification_scorecard"] else None,
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in cur.fetchall()]

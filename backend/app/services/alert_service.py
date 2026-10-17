import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.app.core.errors import NotFoundError
from backend.app.services.audit_service import AuditService

class AlertService:
    @staticmethod
    def get_alerts(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        is_acknowledged: Optional[bool] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM alerts WHERE organization_id = ?"
        params: List[Any] = [organization_id]
        if store_id:
            query += " AND store_id = ?"
            params.append(store_id)
        if is_acknowledged is not None:
            query += " AND is_acknowledged = ?"
            params.append(1 if is_acknowledged else 0)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return [{
            "id": r["id"],
            "organizationId": r["organization_id"],
            "storeId": r["store_id"],
            "issueId": r["issue_id"],
            "alertType": r["alert_type"],
            "severity": r["severity"],
            "message": r["message"],
            "isAcknowledged": bool(r["is_acknowledged"]),
            "acknowledgedBy": r["acknowledged_by"],
            "acknowledgedAt": r["acknowledged_at"],
            "createdAt": r["created_at"]
        } for r in rows]

    @staticmethod
    def acknowledge_alert(
        conn: sqlite3.Connection,
        alert_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM alerts WHERE id = ?;", (alert_id,))
        alert = cur.fetchone()
        if not alert:
            raise NotFoundError("Alert", alert_id)

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE alerts SET is_acknowledged = 1, acknowledged_by = ?, acknowledged_at = ? WHERE id = ?;
        """, (user_id, now, alert_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=alert["organization_id"],
            user_id=user_id,
            entity_type="ALERT",
            entity_id=alert_id,
            action="ALERT_ACKNOWLEDGED",
            previous_state={"isAcknowledged": False},
            new_state={"isAcknowledged": True, "acknowledgedAt": now}
        )

        return {
            "id": alert["id"],
            "organizationId": alert["organization_id"],
            "storeId": alert["store_id"],
            "issueId": alert["issue_id"],
            "alertType": alert["alert_type"],
            "severity": alert["severity"],
            "message": alert["message"],
            "isAcknowledged": True,
            "acknowledgedBy": user_id,
            "acknowledgedAt": now,
            "createdAt": alert["created_at"]
        }

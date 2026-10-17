import uuid
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from backend.app.core.errors import ValidationError
from backend.app.services.security_audit_service import SecurityAuditService

VALID_ENTITY_TYPES = {
    "FEEDBACK_ITEMS",
    "INVESTIGATION_QUESTIONS",
    "ALERTS",
    "ACTION_PLANS",
    "AUDIT_LOGS"
}

VALID_ACTIONS = {"PURGE", "ANONYMIZE"}

class RetentionService:
    """
    Manages data retention policies and executes compliance-driven
    purges and PII anonymizations for expired records.
    """

    @classmethod
    def set_policy(
        cls,
        conn: sqlite3.Connection,
        organization_id: str,
        entity_type: str,
        retention_days: int,
        action_on_expire: str = "PURGE",
        is_active: bool = True
    ) -> Dict[str, Any]:
        if entity_type not in VALID_ENTITY_TYPES:
            raise ValidationError(
                f"Invalid entityType '{entity_type}'. Allowed: {sorted(list(VALID_ENTITY_TYPES))}"
            )

        if action_on_expire not in VALID_ACTIONS:
            raise ValidationError(
                f"Invalid actionOnExpire '{action_on_expire}'. Allowed: {sorted(list(VALID_ACTIONS))}"
            )

        if retention_days < 1 or retention_days > 3650:
            raise ValidationError("retentionDays must be between 1 and 3650 days.")

        cur = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        # Check existing policy
        cur.execute("""
            SELECT id FROM data_retention_policies
            WHERE organization_id = ? AND entity_type = ?;
        """, (organization_id, entity_type))
        existing = cur.fetchone()

        if existing:
            policy_id = existing["id"]
            cur.execute("""
                UPDATE data_retention_policies
                SET retention_days = ?,
                    action_on_expire = ?,
                    is_active = ?,
                    updated_at = ?
                WHERE id = ?;
            """, (retention_days, action_on_expire, 1 if is_active else 0, now, policy_id))
        else:
            policy_id = f"ret-{uuid.uuid4().hex[:10]}"
            cur.execute("""
                INSERT INTO data_retention_policies (
                    id, organization_id, entity_type, retention_days,
                    action_on_expire, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                policy_id, organization_id, entity_type, retention_days,
                action_on_expire, 1 if is_active else 0, now, now
            ))

        conn.commit()
        return {
            "id": policy_id,
            "organizationId": organization_id,
            "entityType": entity_type,
            "retentionDays": retention_days,
            "actionOnExpire": action_on_expire,
            "isActive": is_active,
            "updatedAt": now
        }

    @classmethod
    def list_policies(cls, conn: sqlite3.Connection, organization_id: str) -> List[Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, organization_id, entity_type, retention_days,
                   action_on_expire, is_active, created_at, updated_at
            FROM data_retention_policies
            WHERE organization_id = ?
            ORDER BY entity_type ASC;
        """, (organization_id,))
        rows = cur.fetchall()

        return [
            {
                "id": r["id"],
                "organizationId": r["organization_id"],
                "entityType": r["entity_type"],
                "retentionDays": r["retention_days"],
                "actionOnExpire": r["action_on_expire"],
                "isActive": bool(r["is_active"]),
                "createdAt": r["created_at"],
                "updatedAt": r["updated_at"]
            }
            for r in rows
        ]

    @classmethod
    def execute_purge(
        cls,
        conn: sqlite3.Connection,
        organization_id: str,
        user_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Executes retention policy sweeps. Purges or anonymizes expired records.
        """
        policies = cls.list_policies(conn, organization_id)
        now_dt = datetime.now(timezone.utc)
        results = []
        total_affected = 0

        cur = conn.cursor()

        for pol in policies:
            if not pol["isActive"]:
                continue

            entity_type = pol["entityType"]
            retention_days = pol["retentionDays"]
            action = pol["actionOnExpire"]
            cutoff_dt = now_dt - timedelta(days=retention_days)
            cutoff_iso = cutoff_dt.isoformat()

            affected_count = 0

            if entity_type == "FEEDBACK_ITEMS":
                if dry_run:
                    cur.execute("""
                        SELECT COUNT(*) as cnt FROM feedback_items
                        WHERE organization_id = ? AND created_at < ?;
                    """, (organization_id, cutoff_iso))
                    affected_count = cur.fetchone()["cnt"]
                else:
                    if action == "PURGE":
                        cur.execute("""
                            DELETE FROM feedback_items
                            WHERE organization_id = ? AND created_at < ?;
                        """, (organization_id, cutoff_iso))
                        affected_count = cur.rowcount
                    elif action == "ANONYMIZE":
                        cur.execute("""
                            UPDATE feedback_items
                            SET raw_text = '[ANONYMIZED_EXPIRED_DATA]',
                                normalized_text = '[ANONYMIZED_EXPIRED_DATA]'
                            WHERE organization_id = ? AND created_at < ?
                              AND raw_text != '[ANONYMIZED_EXPIRED_DATA]';
                        """, (organization_id, cutoff_iso))
                        affected_count = cur.rowcount

            elif entity_type == "INVESTIGATION_QUESTIONS":
                if dry_run:
                    cur.execute("""
                        SELECT COUNT(*) as cnt FROM investigation_questions
                        WHERE feedback_item_id IN (
                            SELECT id FROM feedback_items WHERE organization_id = ?
                        ) AND created_at < ?;
                    """, (organization_id, cutoff_iso))
                    affected_count = cur.fetchone()["cnt"]
                else:
                    cur.execute("""
                        DELETE FROM investigation_questions
                        WHERE feedback_item_id IN (
                            SELECT id FROM feedback_items WHERE organization_id = ?
                        ) AND created_at < ?;
                    """, (organization_id, cutoff_iso))
                    affected_count = cur.rowcount

            elif entity_type == "ALERTS":
                if dry_run:
                    cur.execute("""
                        SELECT COUNT(*) as cnt FROM alerts
                        WHERE issue_id IN (
                            SELECT id FROM issues WHERE store_id IN (
                                SELECT id FROM stores WHERE organization_id = ?
                            )
                        ) AND created_at < ?;
                    """, (organization_id, cutoff_iso))
                    affected_count = cur.fetchone()["cnt"]
                else:
                    cur.execute("""
                        DELETE FROM alerts
                        WHERE issue_id IN (
                            SELECT id FROM issues WHERE store_id IN (
                                SELECT id FROM stores WHERE organization_id = ?
                            )
                        ) AND created_at < ?;
                    """, (organization_id, cutoff_iso))
                    affected_count = cur.rowcount

            elif entity_type == "AUDIT_LOGS":
                if dry_run:
                    cur.execute("""
                        SELECT COUNT(*) as cnt FROM audit_logs
                        WHERE organization_id = ? AND created_at < ?;
                    """, (organization_id, cutoff_iso))
                    affected_count = cur.fetchone()["cnt"]
                else:
                    cur.execute("""
                        DELETE FROM audit_logs
                        WHERE organization_id = ? AND created_at < ?;
                    """, (organization_id, cutoff_iso))
                    affected_count = cur.rowcount

            results.append({
                "entityType": entity_type,
                "retentionDays": retention_days,
                "cutoffTimestamp": cutoff_iso,
                "action": action,
                "affectedRecords": affected_count
            })
            total_affected += affected_count

        if not dry_run:
            conn.commit()

            # Record security audit event
            SecurityAuditService.record_event(
                conn=conn,
                event_type="RETENTION_PURGE",
                severity="MEDIUM",
                organization_id=organization_id,
                user_id=user_id,
                path="/security/retention/purge",
                details={
                    "totalAffected": total_affected,
                    "policiesExecuted": len(results),
                    "summary": results
                }
            )

        return {
            "organizationId": organization_id,
            "dryRun": dry_run,
            "totalAffected": total_affected,
            "executedAt": now_dt.isoformat(),
            "details": results
        }

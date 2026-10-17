import uuid
import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from backend.app.core.logger import logger

class AuditService:
    @staticmethod
    def record_audit(
        conn: sqlite3.Connection,
        organization_id: str,
        user_id: Optional[str],
        entity_type: str,
        entity_id: str,
        action: str,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        justification: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        audit_id = f"aud-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()

        # Validate that user_id exists in users table; if not (e.g. system actor or missing), set to None for FK integrity
        valid_user_id = None
        if user_id:
            cur.execute("SELECT id FROM users WHERE id = ?;", (user_id,))
            if cur.fetchone():
                valid_user_id = user_id

        cur.execute("""
            INSERT INTO audit_logs (
                id, organization_id, user_id, entity_type, entity_id, action,
                previous_state, new_state, justification, ip_address, user_agent, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            organization_id,
            valid_user_id,
            entity_type,
            entity_id,
            action,
            json.dumps(previous_state) if previous_state else None,
            json.dumps(new_state) if new_state else None,
            justification,
            ip_address,
            user_agent,
            now
        ))
        logger.info(f"Audit log recorded: {action} on {entity_type} {entity_id} by user {user_id}")
        return audit_id

    @staticmethod
    def get_audit_logs(
        conn: sqlite3.Connection,
        organization_id: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT a.*, u.email as user_email, u.full_name as user_full_name
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.organization_id = ?
        """
        params: List[Any] = [organization_id]
        if entity_type:
            query += " AND a.entity_type = ?"
            params.append(entity_type)
        if entity_id:
            query += " AND a.entity_id = ?"
            params.append(entity_id)

        query += " ORDER BY a.created_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "organizationId": r["organization_id"],
                "userId": r["user_id"],
                "userEmail": r["user_email"],
                "entityType": r["entity_type"],
                "entityId": r["entity_id"],
                "action": r["action"],
                "previousState": json.loads(r["previous_state"]) if r["previous_state"] else None,
                "newState": json.loads(r["new_state"]) if r["new_state"] else None,
                "justification": r["justification"],
                "createdAt": r["created_at"]
            })
        return result

    @staticmethod
    def get_audit_logs_paginated(
        conn: sqlite3.Connection,
        organization_id: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> tuple[List[Dict[str, Any]], Any]:
        from backend.app.schemas.common import PaginationMeta
        cur = conn.cursor()
        base_where = "WHERE a.organization_id = ?"
        params: List[Any] = [organization_id]
        if entity_type:
            base_where += " AND a.entity_type = ?"
            params.append(entity_type)
        if entity_id:
            base_where += " AND a.entity_id = ?"
            params.append(entity_id)

        count_sql = f"SELECT COUNT(*) FROM audit_logs a {base_where};"
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        query = f"""
            SELECT a.*, u.email as user_email, u.full_name as user_full_name
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            {base_where}
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?;
        """
        page_params = list(params) + [limit, (page - 1) * limit]
        cur.execute(query, page_params)
        rows = cur.fetchall()

        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "organizationId": r["organization_id"],
                "userId": r["user_id"],
                "userEmail": r["user_email"],
                "entityType": r["entity_type"],
                "entityId": r["entity_id"],
                "action": r["action"],
                "previousState": json.loads(r["previous_state"]) if r["previous_state"] else None,
                "newState": json.loads(r["new_state"]) if r["new_state"] else None,
                "justification": r["justification"],
                "ipAddress": r["ip_address"],
                "createdAt": r["created_at"]
            })

        total_pages = max(1, (total + limit - 1) // limit)
        meta = PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages)
        return result, meta

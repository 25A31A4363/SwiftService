import uuid
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.app.core.logger import logger

class SecurityAuditService:
    """
    Manages recording and querying security audit events:
    - Prompt injection attempts
    - Rate limit violations
    - Unauthorized access breaches
    - Unsafe/malicious upload attempts
    - Retention purges & anonymizations
    - AI governance overrides
    """

    @classmethod
    def record_event(
        cls,
        conn: sqlite3.Connection,
        event_type: str,
        severity: str = "MEDIUM",
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        event_id = f"sec-evt-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details or {})

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO security_audit_events (
                id, organization_id, user_id, event_type, severity,
                source_ip, path, details, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            event_id, organization_id, user_id, event_type, severity,
            source_ip, path, details_json, now
        ))
        conn.commit()

        logger.warning(
            f"SECURITY AUDIT EVENT: [{severity}] {event_type} | User: {user_id or 'anonymous'} | Path: {path} | Details: {details_json}"
        )

        return {
            "id": event_id,
            "organizationId": organization_id,
            "userId": user_id,
            "eventType": event_type,
            "severity": severity,
            "sourceIp": source_ip,
            "path": path,
            "details": details or {},
            "createdAt": now
        }

    @classmethod
    def list_events(
        cls,
        conn: sqlite3.Connection,
        organization_id: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        conditions = []
        params: List[Any] = []

        if organization_id:
            conditions.append("(organization_id = ? OR organization_id IS NULL)")
            params.append(organization_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Total count
        cur.execute(f"SELECT COUNT(*) as cnt FROM security_audit_events{where_clause};", tuple(params))
        total = cur.fetchone()["cnt"]

        # Fetch records
        query = f"""
            SELECT id, organization_id, user_id, event_type, severity,
                   source_ip, path, details, created_at
            FROM security_audit_events
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        events = []
        for r in rows:
            parsed_details = {}
            if r["details"]:
                try:
                    parsed_details = json.loads(r["details"])
                except Exception:
                    parsed_details = {"raw": r["details"]}

            events.append({
                "id": r["id"],
                "organizationId": r["organization_id"],
                "userId": r["user_id"],
                "eventType": r["event_type"],
                "severity": r["severity"],
                "sourceIp": r["source_ip"],
                "path": r["path"],
                "details": parsed_details,
                "createdAt": r["created_at"]
            })

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "events": events
        }

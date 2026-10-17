import uuid
import json
import sqlite3
import random
import string
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from backend.app.core.logger import logger
from backend.app.schemas.complaints import ComplaintCreate, ComplaintStatusUpdate
from backend.app.services.audit_service import AuditService

ALLOWED_TRANSITIONS = {
    "SUBMITTED": ["UNDER_REVIEW", "IN_PROGRESS", "RESOLVED", "CLOSED"],
    "UNDER_REVIEW": ["IN_PROGRESS", "RESOLVED", "CLOSED"],
    "IN_PROGRESS": ["RESOLVED", "CLOSED"],
    "RESOLVED": ["CLOSED", "IN_PROGRESS"],
    "CLOSED": ["IN_PROGRESS"]
}

SEVERITY_KEYWORDS = {
    "CRITICAL": ["fire", "hazard", "injury", "hospital", "poison", "violence", "threat", "collapse", "electrocution"],
    "HIGH": ["safety", "urgent", "emergency", "stolen", "theft", "harassment", "assault", "spoiled", "expired"],
    "MEDIUM": ["broken", "refund", "overcharged", "damaged", "defective", "missing", "dirty", "unhelpful"],
    "LOW": ["suggestion", "minor", "inquiry", "queue", "delay", "parking", "aesthetic"]
}

class ComplaintsService:
    @staticmethod
    def generate_reference(conn: sqlite3.Connection) -> str:
        """Generate a unique human-friendly reference number: REF-2026-XXXXX"""
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        cur = conn.cursor()
        for _ in range(50):
            suffix = "".join(random.choices(chars, k=5))
            ref = f"REF-2026-{suffix}"
            cur.execute("SELECT 1 FROM customer_complaints WHERE reference_number = ?;", (ref,))
            if not cur.fetchone():
                return ref
        return f"REF-2026-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def _assess_priority(subject: str, description: str) -> str:
        """Deterministic rule-based severity baseline (transparent, non-hallucinating)."""
        combined = (subject + " " + description).lower()
        for level, words in SEVERITY_KEYWORDS.items():
            for word in words:
                if word in combined:
                    return level
        return "MEDIUM"

    @classmethod
    def create_complaint(
        cls,
        conn: sqlite3.Connection,
        customer_id: str,
        data: ComplaintCreate,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a new customer complaint, link to feedback_items, and generate reference."""
        cur = conn.cursor()
        
        # 1. Fetch Customer Account
        cur.execute("SELECT id, full_name, email, phone, organization_id, store_id FROM users WHERE id = ?;", (customer_id,))
        user_row = cur.fetchone()
        if not user_row:
            raise ValueError("Customer account not found.")

        org_id = user_row["organization_id"]
        if not org_id:
            cur.execute("SELECT id FROM organizations LIMIT 1;")
            org_row = cur.fetchone()
            org_id = org_row["id"] if org_row else "org-apex-01"

        cust_name = user_row["full_name"] or "Retail Customer"
        cust_email = user_row["email"]
        cust_phone = user_row["phone"]

        # 2. Resolve Store
        target_store_id = data.storeId or user_row["store_id"]
        store_name = None
        region_id = None
        if target_store_id:
            cur.execute("SELECT id, name, region_id FROM stores WHERE id = ?;", (target_store_id,))
            s_row = cur.fetchone()
            if s_row:
                store_name = s_row["name"]
                region_id = s_row["region_id"]
        
        if not store_name:
            cur.execute("SELECT id, name, region_id FROM stores WHERE operating_status = 'OPERATIONAL' LIMIT 1;")
            s_row = cur.fetchone()
            if s_row:
                target_store_id = s_row["id"]
                store_name = s_row["name"]
                region_id = s_row["region_id"]
            else:
                target_store_id = "store-001"
                store_name = "Flagship Store"

        # 3. Assess Priority & Generate Identifiers
        now = datetime.now(timezone.utc).isoformat()
        priority = cls._assess_priority(data.subject, data.description)
        ref_number = cls.generate_reference(conn)
        complaint_id = f"cmp-{uuid.uuid4().hex[:12]}"
        feedback_item_id = f"fb-{uuid.uuid4().hex[:12]}"

        # 4. Ingest into feedback_items for unified R5 Operations Pipeline
        raw_text = f"[{data.category}] {data.subject}\n\n{data.description}"
        cur.execute("""
            INSERT INTO feedback_items (
                id, organization_id, region_id, store_id, source_type, channel_type,
                submitter_type, privacy_classification, processing_status, status,
                raw_text, language_code, sentiment_score, submitted_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'en', ?, ?, ?, ?)
        """, (
            feedback_item_id, org_id, region_id, target_store_id,
            "CUSTOMER_PORTAL", "WEB_FORM", "CUSTOMER", "INTERNAL",
            "processed", "NEW", raw_text, -0.6, now, now, now
        ))

        # 5. Build Initial Timeline
        timeline = [
            {
                "status": "SUBMITTED",
                "timestamp": now,
                "actor": "Customer",
                "note": "Complaint submitted via RetailWave Customer Portal."
            }
        ]

        # 6. Insert into customer_complaints
        cur.execute("""
            INSERT INTO customer_complaints (
                id, reference_number, customer_id, customer_name, customer_email,
                customer_phone, category, order_number, store_id, store_name,
                subject, description, attachment_url, attachment_name, status,
                priority, investigation_notes, resolution_summary,
                feedback_item_id, timeline, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            complaint_id, ref_number, customer_id, cust_name, cust_email,
            cust_phone, data.category, data.orderNumber, target_store_id, store_name,
            data.subject, data.description, data.attachmentUrl, data.attachmentName,
            "SUBMITTED", priority, None, None,
            feedback_item_id, json.dumps(timeline), now, now
        ))

        # 7. Audit Log
        AuditService.record_audit(
            conn=conn,
            organization_id=org_id,
            user_id=customer_id,
            entity_type="CUSTOMER_COMPLAINT",
            entity_id=complaint_id,
            action="CREATE",
            new_state={"reference": ref_number, "category": data.category, "status": "SUBMITTED"},
            justification="New customer complaint submitted",
            ip_address=ip_address
        )

        return cls._format_complaint(cur, complaint_id)

    @classmethod
    def get_customer_complaints(cls, conn: sqlite3.Connection, customer_id: str) -> List[Dict[str, Any]]:
        """Fetch all complaints submitted by a specific customer."""
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, t.name as assigned_team_name, u.full_name as assigned_to_name
            FROM customer_complaints c
            LEFT JOIN operational_teams t ON c.assigned_team_id = t.id
            LEFT JOIN users u ON c.assigned_to_user_id = u.id
            WHERE c.customer_id = ?
            ORDER BY c.created_at DESC;
        """, (customer_id,))
        rows = cur.fetchall()
        return [cls._row_to_dict(r) for r in rows]

    @classmethod
    def get_complaint_by_id(
        cls,
        conn: sqlite3.Connection,
        complaint_id: str,
        requesting_user_id: str,
        requesting_role: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch single complaint ensuring customer isolation."""
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, t.name as assigned_team_name, u.full_name as assigned_to_name
            FROM customer_complaints c
            LEFT JOIN operational_teams t ON c.assigned_team_id = t.id
            LEFT JOIN users u ON c.assigned_to_user_id = u.id
            WHERE c.id = ?;
        """, (complaint_id,))
        row = cur.fetchone()
        if not row:
            return None

        # RBAC Customer Isolation Check
        if requesting_role == "CUSTOMER" and row["customer_id"] != requesting_user_id:
            raise PermissionError("Access denied: You do not have permission to view this complaint.")

        return cls._row_to_dict(row)

    @classmethod
    def track_by_reference(cls, conn: sqlite3.Connection, reference_number: str) -> Optional[Dict[str, Any]]:
        """
        Public or customer lookup by reference number.
        Strict privacy: Redacts internal investigation notes and customer private info.
        """
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.reference_number, c.customer_name, c.category, c.order_number,
                   c.store_name, c.subject, c.description, c.attachment_name, c.status,
                   c.priority, c.resolution_summary, c.timeline, c.created_at, c.updated_at,
                   t.name as assigned_team_name
            FROM customer_complaints c
            LEFT JOIN operational_teams t ON c.assigned_team_id = t.id
            WHERE UPPER(c.reference_number) = UPPER(?);
        """, (reference_number.strip(),))
        row = cur.fetchone()
        if not row:
            return None

        timeline = []
        try:
            timeline = json.loads(row["timeline"]) if row["timeline"] else []
        except Exception:
            timeline = []

        return {
            "id": row["id"],
            "referenceNumber": row["reference_number"],
            "customerName": row["customer_name"],
            "category": row["category"],
            "orderNumber": row["order_number"],
            "storeName": row["store_name"],
            "subject": row["subject"],
            "description": row["description"],
            "attachmentName": row["attachment_name"],
            "status": row["status"],
            "priority": row["priority"],
            "assignedTeamName": row["assigned_team_name"],
            "resolutionSummary": row["resolution_summary"],
            "timeline": timeline,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"]
        }

    @classmethod
    def get_all_complaints_for_staff(
        cls,
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        store_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Fetch incoming complaints for authorized R5 operational staff with filters."""
        cur = conn.cursor()
        query = """
            SELECT c.*, t.name as assigned_team_name, u.full_name as assigned_to_name
            FROM customer_complaints c
            LEFT JOIN operational_teams t ON c.assigned_team_id = t.id
            LEFT JOIN users u ON c.assigned_to_user_id = u.id
            WHERE 1=1
        """
        params: List[Any] = []

        if status:
            query += " AND c.status = ?"
            params.append(status.upper())
        if category:
            query += " AND c.category = ?"
            params.append(category)
        if store_id:
            query += " AND c.store_id = ?"
            params.append(store_id)
        if search:
            query += " AND (c.reference_number LIKE ? OR c.subject LIKE ? OR c.customer_name LIKE ? OR c.description LIKE ?)"
            s_param = f"%{search.strip()}%"
            params.extend([s_param, s_param, s_param, s_param])

        count_query = f"SELECT COUNT(*) FROM ({query})"
        cur.execute(count_query, params)
        total = cur.fetchone()[0]

        query += " ORDER BY c.created_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()
        items = [cls._row_to_dict(r) for r in rows]

        return {"items": items, "total": total}

    @classmethod
    def update_complaint_status(
        cls,
        conn: sqlite3.Connection,
        complaint_id: str,
        update: ComplaintStatusUpdate,
        staff_user_id: str,
        staff_name: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authorized staff action: updates status, team assignment, investigation notes, and customer resolution."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM customer_complaints WHERE id = ?;", (complaint_id,))
        existing = cur.fetchone()
        if not existing:
            raise ValueError(f"Complaint {complaint_id} not found.")

        old_status = existing["status"]
        new_status = update.status or old_status

        # Validate transition if status is changed
        if new_status != old_status:
            allowed = ALLOWED_TRANSITIONS.get(old_status, [])
            if new_status not in allowed:
                raise ValueError(f"Invalid status transition from {old_status} to {new_status}. Allowed: {allowed}")

        # Resolve Team Assignment
        assigned_team_id = update.assignedTeamId if update.assignedTeamId is not None else existing["assigned_team_id"]
        assigned_team_name = existing["assigned_team_name"]
        if update.assignedTeamId:
            cur.execute("SELECT name FROM operational_teams WHERE id = ?;", (update.assignedTeamId,))
            t_row = cur.fetchone()
            if t_row:
                assigned_team_name = t_row["name"]

        # Parse existing timeline
        timeline = []
        try:
            timeline = json.loads(existing["timeline"]) if existing["timeline"] else []
        except Exception:
            timeline = []

        now = datetime.now(timezone.utc).isoformat()

        # Append timeline entry if status changed or resolution added
        if new_status != old_status or update.resolutionSummary:
            note_text = update.resolutionSummary if (new_status in ("RESOLVED", "CLOSED") and update.resolutionSummary) else f"Status transitioned from {old_status} to {new_status}."
            timeline.append({
                "status": new_status,
                "timestamp": now,
                "actor": staff_name,
                "note": note_text
            })

        # Notes
        investigation_notes = update.investigationNotes if update.investigationNotes is not None else existing["investigation_notes"]
        resolution_summary = update.resolutionSummary if update.resolutionSummary is not None else existing["resolution_summary"]

        cur.execute("""
            UPDATE customer_complaints
            SET status = ?,
                assigned_team_id = ?,
                assigned_team_name = ?,
                investigation_notes = ?,
                resolution_summary = ?,
                timeline = ?,
                updated_at = ?
            WHERE id = ?;
        """, (
            new_status, assigned_team_id, assigned_team_name,
            investigation_notes, resolution_summary,
            json.dumps(timeline), now, complaint_id
        ))

        # Audit Log
        cur.execute("SELECT organization_id FROM users WHERE id = ?;", (staff_user_id,))
        staff_row = cur.fetchone()
        org_id = staff_row["organization_id"] if staff_row and staff_row["organization_id"] else None
        if not org_id:
            cur.execute("SELECT id FROM organizations LIMIT 1;")
            org_row = cur.fetchone()
            org_id = org_row["id"] if org_row else "org-apex-01"

        AuditService.record_audit(
            conn=conn,
            organization_id=org_id,
            user_id=staff_user_id,
            entity_type="CUSTOMER_COMPLAINT",
            entity_id=complaint_id,
            action="UPDATE_STATUS",
            previous_state={"status": old_status},
            new_state={"status": new_status, "team": assigned_team_name},
            justification=f"Staff updated status to {new_status}",
            ip_address=ip_address
        )

        return cls._format_complaint(cur, complaint_id)

    @classmethod
    def _format_complaint(cls, cur: sqlite3.Cursor, complaint_id: str) -> Dict[str, Any]:
        cur.execute("""
            SELECT c.*, t.name as assigned_team_name, u.full_name as assigned_to_name
            FROM customer_complaints c
            LEFT JOIN operational_teams t ON c.assigned_team_id = t.id
            LEFT JOIN users u ON c.assigned_to_user_id = u.id
            WHERE c.id = ?;
        """, (complaint_id,))
        row = cur.fetchone()
        return cls._row_to_dict(row)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        timeline = []
        try:
            timeline = json.loads(row["timeline"]) if row["timeline"] else []
        except Exception:
            timeline = []

        return {
            "id": row["id"],
            "referenceNumber": row["reference_number"],
            "customerId": row["customer_id"],
            "customerName": row["customer_name"],
            "customerEmail": row["customer_email"],
            "customerPhone": row["customer_phone"],
            "category": row["category"],
            "orderNumber": row["order_number"],
            "storeId": row["store_id"],
            "storeName": row["store_name"],
            "subject": row["subject"],
            "description": row["description"],
            "attachmentUrl": row["attachment_url"],
            "attachmentName": row["attachment_name"],
            "status": row["status"],
            "priority": row["priority"],
            "assignedTeamId": row["assigned_team_id"],
            "assignedTeamName": row["assigned_team_name"] if "assigned_team_name" in row.keys() else None,
            "assignedToUserId": row["assigned_to_user_id"],
            "assignedToName": row["assigned_to_name"] if "assigned_to_name" in row.keys() else None,
            "investigationNotes": row["investigation_notes"],
            "resolutionSummary": row["resolution_summary"],
            "feedbackItemId": row["feedback_item_id"],
            "issueId": row["issue_id"],
            "timeline": timeline,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"]
        }

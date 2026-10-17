import uuid
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any
from backend.app.schemas.personal_home import PersonalApplianceCreate, PersonalTicketCreate
from backend.app.core.errors import NotFoundError

class PersonalHomeService:
    @staticmethod
    def register_appliance(
        conn: sqlite3.Connection,
        user_id: str,
        payload: PersonalApplianceCreate
    ) -> Dict[str, Any]:
        appliance_id = f"appl-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO personal_home_appliances (
                id, user_id, appliance_type, brand, model_number, serial_number,
                purchase_date, warranty_until, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            appliance_id,
            user_id,
            payload.applianceType,
            payload.brand,
            payload.modelNumber,
            payload.serialNumber,
            payload.purchaseDate,
            payload.warrantyUntil,
            now,
            now
        ))

        return {
            "id": appliance_id,
            "userId": user_id,
            "applianceType": payload.applianceType,
            "brand": payload.brand,
            "modelNumber": payload.modelNumber,
            "serialNumber": payload.serialNumber,
            "purchaseDate": payload.purchaseDate,
            "warrantyUntil": payload.warrantyUntil,
            "createdAt": now,
            "updatedAt": now
        }

    @staticmethod
    def get_user_appliances(conn: sqlite3.Connection, user_id: str) -> List[Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM personal_home_appliances WHERE user_id = ? ORDER BY created_at DESC;", (user_id,))
        return [{
            "id": r["id"],
            "userId": r["user_id"],
            "applianceType": r["appliance_type"],
            "brand": r["brand"],
            "modelNumber": r["model_number"],
            "serialNumber": r["serial_number"],
            "purchaseDate": r["purchase_date"],
            "warrantyUntil": r["warranty_until"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in cur.fetchall()]

    @staticmethod
    def create_service_ticket(
        conn: sqlite3.Connection,
        user_id: str,
        payload: PersonalTicketCreate
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM personal_home_appliances WHERE id = ? AND user_id = ?;", (payload.applianceId, user_id))
        appliance = cur.fetchone()
        if not appliance:
            raise NotFoundError("PersonalAppliance", payload.applianceId)

        ticket_id = f"ticket-{uuid.uuid4().hex[:10]}"
        ext_ref = f"EXT-{appliance['brand'][:3].upper()}-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        cur.execute("""
            INSERT INTO personal_service_tickets (
                id, appliance_id, user_id, complaint_description, classified_category,
                routed_service_channel, status, external_reference_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_id,
            payload.applianceId,
            user_id,
            payload.complaintDescription,
            payload.classifiedCategory,
            payload.routedServiceChannel,
            "SUBMITTED",
            ext_ref,
            now,
            now
        ))

        return {
            "id": ticket_id,
            "applianceId": payload.applianceId,
            "userId": user_id,
            "complaintDescription": payload.complaintDescription,
            "classifiedCategory": payload.classifiedCategory,
            "routedServiceChannel": payload.routedServiceChannel,
            "status": "SUBMITTED",
            "externalReferenceId": ext_ref,
            "createdAt": now,
            "updatedAt": now
        }

    @staticmethod
    def get_user_tickets(conn: sqlite3.Connection, user_id: str) -> List[Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM personal_service_tickets WHERE user_id = ? ORDER BY created_at DESC;", (user_id,))
        return [{
            "id": r["id"],
            "applianceId": r["appliance_id"],
            "userId": r["user_id"],
            "complaintDescription": r["complaint_description"],
            "classifiedCategory": r["classified_category"],
            "routedServiceChannel": r["routed_service_channel"],
            "status": r["status"],
            "externalReferenceId": r["external_reference_id"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in cur.fetchall()]

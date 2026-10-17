import json
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.app.core.errors import NotFoundError, ConflictError
from backend.app.services.audit_service import AuditService

class HierarchyService:
    # =========================================================================
    # Organizations
    # =========================================================================
    @staticmethod
    def get_organizations(
        conn: sqlite3.Connection,
        q: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        where_clauses = []
        params: List[Any] = []

        if q:
            where_clauses.append("(o.name LIKE ? OR o.code LIKE ? OR o.description LIKE ?)")
            term = f"%{q.strip()}%"
            params.extend([term, term, term])

        if status:
            where_clauses.append("o.status = ?")
            params.append(status)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM organizations o {where_sql};", params)
        total = cur.fetchone()[0]

        offset = max(0, (page - 1) * limit)
        query = f"""
            SELECT o.*,
                   (SELECT COUNT(*) FROM regions WHERE organization_id = o.id) as region_count,
                   (SELECT COUNT(*) FROM stores WHERE organization_id = o.id) as store_count
            FROM organizations o
            {where_sql}
            ORDER BY o.name ASC
            LIMIT ? OFFSET ?;
        """
        cur.execute(query, params + [limit, offset])
        rows = cur.fetchall()

        items = [{
            "id": r["id"],
            "name": r["name"],
            "code": r["code"],
            "description": r["description"] if "description" in r.keys() else None,
            "status": r["status"] if "status" in r.keys() else "ACTIVE",
            "regionCount": r["region_count"],
            "storeCount": r["store_count"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in rows]

        return items, total

    @staticmethod
    def get_organization(conn: sqlite3.Connection, org_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT o.*,
                   (SELECT COUNT(*) FROM regions WHERE organization_id = o.id) as region_count,
                   (SELECT COUNT(*) FROM stores WHERE organization_id = o.id) as store_count
            FROM organizations o
            WHERE o.id = ?;
        """, (org_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("Organization", org_id)

        return {
            "id": r["id"],
            "name": r["name"],
            "code": r["code"],
            "description": r["description"] if "description" in r.keys() else None,
            "status": r["status"] if "status" in r.keys() else "ACTIVE",
            "regionCount": r["region_count"],
            "storeCount": r["store_count"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

    @staticmethod
    def create_organization(
        conn: sqlite3.Connection,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        code_upper = data.code.strip().upper()

        cur.execute("SELECT id FROM organizations WHERE code = ?;", (code_upper,))
        if cur.fetchone():
            raise ConflictError(f"Organization code '{code_upper}' already exists")

        org_id = f"org-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        cur.execute("""
            INSERT INTO organizations (id, name, code, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (org_id, data.name.strip(), code_upper, data.description, data.status or "ACTIVE", now, now))

        new_org = HierarchyService.get_organization(conn, org_id)
        AuditService.record_audit(
            conn=conn,
            organization_id=org_id,
            user_id=user_id,
            entity_type="ORGANIZATION",
            entity_id=org_id,
            action="ORG_CREATED",
            new_state=new_org,
            justification="Created organization record",
            ip_address=ip,
            user_agent=ua
        )
        return new_org

    @staticmethod
    def update_organization(
        conn: sqlite3.Connection,
        org_id: str,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        prev_org = HierarchyService.get_organization(conn, org_id)
        cur = conn.cursor()

        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name.strip())
        if data.code is not None:
            code_upper = data.code.strip().upper()
            cur.execute("SELECT id FROM organizations WHERE code = ? AND id != ?;", (code_upper, org_id))
            if cur.fetchone():
                raise ConflictError(f"Organization code '{code_upper}' is already in use by another organization")
            updates.append("code = ?")
            params.append(code_upper)
        if data.description is not None:
            updates.append("description = ?")
            params.append(data.description)
        if data.status is not None:
            updates.append("status = ?")
            params.append(data.status)

        if not updates:
            return prev_org

        updates.append("updated_at = ?")
        params.append(now)
        params.append(org_id)

        cur.execute(f"UPDATE organizations SET {', '.join(updates)} WHERE id = ?;", params)
        updated_org = HierarchyService.get_organization(conn, org_id)

        AuditService.record_audit(
            conn=conn,
            organization_id=org_id,
            user_id=user_id,
            entity_type="ORGANIZATION",
            entity_id=org_id,
            action="ORG_UPDATED",
            previous_state=prev_org,
            new_state=updated_org,
            justification="Updated organization details",
            ip_address=ip,
            user_agent=ua
        )
        return updated_org

    @staticmethod
    def delete_organization(
        conn: sqlite3.Connection,
        org_id: str,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> None:
        prev_org = HierarchyService.get_organization(conn, org_id)
        cur = conn.cursor()

        operator_org = None
        if user_id:
            cur.execute("SELECT organization_id FROM users WHERE id = ?;", (user_id,))
            u_row = cur.fetchone()
            if u_row and u_row[0] != org_id:
                operator_org = u_row[0]

        if operator_org:
            AuditService.record_audit(
                conn=conn,
                organization_id=operator_org,
                user_id=user_id,
                entity_type="ORGANIZATION",
                entity_id=org_id,
                action="ORG_DELETED",
                previous_state=prev_org,
                justification=f"Deleted organization {prev_org['name']}",
                ip_address=ip,
                user_agent=ua
            )

        cur.execute("DELETE FROM organizations WHERE id = ?;", (org_id,))

    # =========================================================================
    # Regions
    # =========================================================================
    @staticmethod
    def get_regions(
        conn: sqlite3.Connection,
        organization_id: str,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        where_clauses = ["r.organization_id = ?"]
        params: List[Any] = [organization_id]

        if q:
            where_clauses.append("(r.name LIKE ? OR r.code LIKE ? OR r.description LIKE ?)")
            term = f"%{q.strip()}%"
            params.extend([term, term, term])

        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM regions r {where_sql};", params)
        total = cur.fetchone()[0]

        offset = max(0, (page - 1) * limit)
        query = f"""
            SELECT r.*,
                   u.full_name as lead_user_name,
                   (SELECT COUNT(*) FROM stores WHERE region_id = r.id) as store_count
            FROM regions r
            LEFT JOIN users u ON r.lead_user_id = u.id
            {where_sql}
            ORDER BY r.name ASC
            LIMIT ? OFFSET ?;
        """
        cur.execute(query, params + [limit, offset])
        rows = cur.fetchall()

        items = [{
            "id": r["id"],
            "organizationId": r["organization_id"],
            "name": r["name"],
            "code": r["code"],
            "description": r["description"] if "description" in r.keys() else None,
            "leadUserId": r["lead_user_id"] if "lead_user_id" in r.keys() else None,
            "leadUserName": r["lead_user_name"],
            "storeCount": r["store_count"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in rows]

        return items, total

    @staticmethod
    def get_region(conn: sqlite3.Connection, reg_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*,
                   u.full_name as lead_user_name,
                   (SELECT COUNT(*) FROM stores WHERE region_id = r.id) as store_count
            FROM regions r
            LEFT JOIN users u ON r.lead_user_id = u.id
            WHERE r.id = ?;
        """, (reg_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("Region", reg_id)

        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "name": r["name"],
            "code": r["code"],
            "description": r["description"] if "description" in r.keys() else None,
            "leadUserId": r["lead_user_id"] if "lead_user_id" in r.keys() else None,
            "leadUserName": r["lead_user_name"],
            "storeCount": r["store_count"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

    @staticmethod
    def create_region(
        conn: sqlite3.Connection,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        # Validate org exists
        HierarchyService.get_organization(conn, data.organizationId)
        cur = conn.cursor()

        code_upper = data.code.strip().upper()
        cur.execute("SELECT id FROM regions WHERE organization_id = ? AND code = ?;", (data.organizationId, code_upper))
        if cur.fetchone():
            raise ConflictError(f"Region code '{code_upper}' already exists in this organization")

        reg_id = f"reg-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        cur.execute("""
            INSERT INTO regions (id, organization_id, name, code, description, lead_user_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (reg_id, data.organizationId, data.name.strip(), code_upper, data.description, data.leadUserId, now, now))

        new_reg = HierarchyService.get_region(conn, reg_id)
        AuditService.record_audit(
            conn=conn,
            organization_id=data.organizationId,
            user_id=user_id,
            entity_type="REGION",
            entity_id=reg_id,
            action="REGION_CREATED",
            new_state=new_reg,
            justification="Created region entity",
            ip_address=ip,
            user_agent=ua
        )
        return new_reg

    @staticmethod
    def update_region(
        conn: sqlite3.Connection,
        reg_id: str,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        prev_reg = HierarchyService.get_region(conn, reg_id)
        cur = conn.cursor()

        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name.strip())
        if data.code is not None:
            code_upper = data.code.strip().upper()
            cur.execute("SELECT id FROM regions WHERE organization_id = ? AND code = ? AND id != ?;",
                        (prev_reg["organizationId"], code_upper, reg_id))
            if cur.fetchone():
                raise ConflictError(f"Region code '{code_upper}' is already in use")
            updates.append("code = ?")
            params.append(code_upper)
        if data.description is not None:
            updates.append("description = ?")
            params.append(data.description)
        if data.leadUserId is not None:
            updates.append("lead_user_id = ?")
            params.append(data.leadUserId)

        if not updates:
            return prev_reg

        updates.append("updated_at = ?")
        params.append(now)
        params.append(reg_id)

        cur.execute(f"UPDATE regions SET {', '.join(updates)} WHERE id = ?;", params)
        updated_reg = HierarchyService.get_region(conn, reg_id)

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_reg["organizationId"],
            user_id=user_id,
            entity_type="REGION",
            entity_id=reg_id,
            action="REGION_UPDATED",
            previous_state=prev_reg,
            new_state=updated_reg,
            justification="Updated region properties",
            ip_address=ip,
            user_agent=ua
        )
        return updated_reg

    @staticmethod
    def delete_region(
        conn: sqlite3.Connection,
        reg_id: str,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> None:
        prev_reg = HierarchyService.get_region(conn, reg_id)
        cur = conn.cursor()
        cur.execute("DELETE FROM regions WHERE id = ?;", (reg_id,))

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_reg["organizationId"],
            user_id=user_id,
            entity_type="REGION",
            entity_id=reg_id,
            action="REGION_DELETED",
            previous_state=prev_reg,
            justification="Deleted region entity",
            ip_address=ip,
            user_agent=ua
        )

    # =========================================================================
    # Stores
    # =========================================================================
    @staticmethod
    def get_stores(
        conn: sqlite3.Connection,
        organization_id: str,
        region_id: Optional[str] = None,
        operating_status: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        where_clauses = ["s.organization_id = ?"]
        params: List[Any] = [organization_id]

        if region_id:
            where_clauses.append("s.region_id = ?")
            params.append(region_id)

        if operating_status:
            where_clauses.append("s.operating_status = ?")
            params.append(operating_status)

        if q:
            term = f"%{q.strip()}%"
            where_clauses.append("(s.name LIKE ? OR s.city LIKE ? OR CAST(s.store_number AS TEXT) LIKE ?)")
            params.extend([term, term, term])

        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM stores s {where_sql};", params)
        total = cur.fetchone()[0]

        offset = max(0, (page - 1) * limit)
        query = f"""
            SELECT s.*, r.name as region_name
            FROM stores s
            JOIN regions r ON s.region_id = r.id
            {where_sql}
            ORDER BY s.store_number ASC
            LIMIT ? OFFSET ?;
        """
        cur.execute(query, params + [limit, offset])
        rows = cur.fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r["id"],
                "organizationId": r["organization_id"],
                "regionId": r["region_id"],
                "regionName": r["region_name"],
                "name": r["name"],
                "storeNumber": r["store_number"],
                "address": {
                    "street": r["street"],
                    "city": r["city"],
                    "state": r["state"],
                    "postalCode": r["postal_code"],
                    "country": r["country"]
                },
                "timezone": r["timezone"],
                "operatingStatus": r["operating_status"] if "operating_status" in r.keys() else "OPERATIONAL",
                "metadata": json.loads(r["metadata"]) if ("metadata" in r.keys() and r["metadata"]) else None,
                "createdAt": r["created_at"],
                "updatedAt": r["updated_at"]
            })

        return items, total

    @staticmethod
    def get_store(conn: sqlite3.Connection, store_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.*, r.name as region_name
            FROM stores s
            JOIN regions r ON s.region_id = r.id
            WHERE s.id = ?;
        """, (store_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("Store", store_id)

        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "regionId": r["region_id"],
            "regionName": r["region_name"],
            "name": r["name"],
            "storeNumber": r["store_number"],
            "address": {
                "street": r["street"],
                "city": r["city"],
                "state": r["state"],
                "postalCode": r["postal_code"],
                "country": r["country"]
            },
            "timezone": r["timezone"],
            "operatingStatus": r["operating_status"] if "operating_status" in r.keys() else "OPERATIONAL",
            "metadata": json.loads(r["metadata"]) if ("metadata" in r.keys() and r["metadata"]) else None,
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

    @staticmethod
    def create_store(
        conn: sqlite3.Connection,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        # Verify region belongs to org
        HierarchyService.get_region(conn, data.regionId)
        cur = conn.cursor()

        cur.execute("SELECT id FROM stores WHERE store_number = ?;", (data.storeNumber,))
        if cur.fetchone():
            raise ConflictError(f"Store number {data.storeNumber} is already registered")

        store_id = f"store-{data.storeNumber}"
        now = datetime.now(timezone.utc).isoformat()
        addr = data.address

        meta_json = json.dumps(data.metadata) if data.metadata else None

        cur.execute("""
            INSERT INTO stores (
                id, organization_id, region_id, name, store_number, street, city, state, postal_code,
                country, timezone, operating_status, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            store_id,
            data.organizationId,
            data.regionId,
            data.name.strip(),
            data.storeNumber,
            addr.street if addr else None,
            addr.city if addr else None,
            addr.state if addr else None,
            addr.postalCode if addr else None,
            addr.country if addr else None,
            data.timezone or "UTC",
            data.operatingStatus or "OPERATIONAL",
            meta_json,
            now,
            now
        ))

        new_store = HierarchyService.get_store(conn, store_id)
        AuditService.record_audit(
            conn=conn,
            organization_id=data.organizationId,
            user_id=user_id,
            entity_type="STORE",
            entity_id=store_id,
            action="STORE_CREATED",
            new_state=new_store,
            justification=f"Created store #{data.storeNumber} ({data.name})",
            ip_address=ip,
            user_agent=ua
        )
        return new_store

    @staticmethod
    def update_store(
        conn: sqlite3.Connection,
        store_id: str,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        prev_store = HierarchyService.get_store(conn, store_id)
        cur = conn.cursor()

        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        if data.regionId is not None:
            HierarchyService.get_region(conn, data.regionId)
            updates.append("region_id = ?")
            params.append(data.regionId)

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name.strip())

        if data.storeNumber is not None:
            cur.execute("SELECT id FROM stores WHERE store_number = ? AND id != ?;", (data.storeNumber, store_id))
            if cur.fetchone():
                raise ConflictError(f"Store number {data.storeNumber} is in use by another store")
            updates.append("store_number = ?")
            params.append(data.storeNumber)

        if data.address is not None:
            updates.extend(["street = ?", "city = ?", "state = ?", "postal_code = ?", "country = ?"])
            params.extend([
                data.address.street,
                data.address.city,
                data.address.state,
                data.address.postalCode,
                data.address.country
            ])

        if data.timezone is not None:
            updates.append("timezone = ?")
            params.append(data.timezone)

        if data.operatingStatus is not None:
            updates.append("operating_status = ?")
            params.append(data.operatingStatus)

        if data.metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(data.metadata))

        if not updates:
            return prev_store

        updates.append("updated_at = ?")
        params.append(now)
        params.append(store_id)

        cur.execute(f"UPDATE stores SET {', '.join(updates)} WHERE id = ?;", params)
        updated_store = HierarchyService.get_store(conn, store_id)

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_store["organizationId"],
            user_id=user_id,
            entity_type="STORE",
            entity_id=store_id,
            action="STORE_UPDATED",
            previous_state=prev_store,
            new_state=updated_store,
            justification="Updated store attributes",
            ip_address=ip,
            user_agent=ua
        )
        return updated_store

    @staticmethod
    def update_store_status(
        conn: sqlite3.Connection,
        store_id: str,
        operating_status: str,
        justification: Optional[str] = None,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        prev_store = HierarchyService.get_store(conn, store_id)
        now = datetime.now(timezone.utc).isoformat()

        cur = conn.cursor()
        cur.execute("""
            UPDATE stores
            SET operating_status = ?, updated_at = ?
            WHERE id = ?;
        """, (operating_status, now, store_id))

        updated_store = HierarchyService.get_store(conn, store_id)
        AuditService.record_audit(
            conn=conn,
            organization_id=prev_store["organizationId"],
            user_id=user_id,
            entity_type="STORE",
            entity_id=store_id,
            action="STORE_STATUS_UPDATED",
            previous_state={"operatingStatus": prev_store["operatingStatus"]},
            new_state={"operatingStatus": operating_status},
            justification=justification or f"Changed operating status to {operating_status}",
            ip_address=ip,
            user_agent=ua
        )
        return updated_store

    @staticmethod
    def delete_store(
        conn: sqlite3.Connection,
        store_id: str,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> None:
        prev_store = HierarchyService.get_store(conn, store_id)
        cur = conn.cursor()
        cur.execute("DELETE FROM stores WHERE id = ?;", (store_id,))

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_store["organizationId"],
            user_id=user_id,
            entity_type="STORE",
            entity_id=store_id,
            action="STORE_DELETED",
            previous_state=prev_store,
            justification=f"Decommissioned store #{prev_store['storeNumber']}",
            ip_address=ip,
            user_agent=ua
        )

    # =========================================================================
    # Teams & Memberships
    # =========================================================================
    @staticmethod
    def get_teams(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        region_id: Optional[str] = None,
        specialization: Optional[str] = None,
        team_type: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        where_clauses = ["t.organization_id = ?"]
        params: List[Any] = [organization_id]

        if store_id:
            where_clauses.append("(t.store_id = ? OR t.store_id IS NULL)")
            params.append(store_id)

        if region_id:
            where_clauses.append("(t.region_id = ? OR t.region_id IS NULL)")
            params.append(region_id)

        if specialization:
            where_clauses.append("t.specialization = ?")
            params.append(specialization)

        if team_type:
            where_clauses.append("t.team_type = ?")
            params.append(team_type)

        if q:
            term = f"%{q.strip()}%"
            where_clauses.append("(t.name LIKE ? OR t.responsibility LIKE ? OR t.specialization LIKE ?)")
            params.extend([term, term, term])

        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM operational_teams t {where_sql};", params)
        total = cur.fetchone()[0]

        offset = max(0, (page - 1) * limit)
        query = f"""
            SELECT t.*,
                   r.name as region_name,
                   s.name as store_name,
                   u.full_name as lead_user_name,
                   (SELECT COUNT(*) FROM team_members WHERE team_id = t.id) as member_count
            FROM operational_teams t
            LEFT JOIN regions r ON t.region_id = r.id
            LEFT JOIN stores s ON t.store_id = s.id
            LEFT JOIN users u ON t.lead_user_id = u.id
            {where_sql}
            ORDER BY t.name ASC
            LIMIT ? OFFSET ?;
        """
        cur.execute(query, params + [limit, offset])
        rows = cur.fetchall()

        items = [{
            "id": r["id"],
            "organizationId": r["organization_id"],
            "regionId": r["region_id"] if "region_id" in r.keys() else None,
            "regionName": r["region_name"],
            "storeId": r["store_id"],
            "storeName": r["store_name"],
            "name": r["name"],
            "teamType": r["team_type"],
            "slaTier": r["sla_tier"],
            "contactEmail": r["contact_email"],
            "responsibility": r["responsibility"] if "responsibility" in r.keys() else None,
            "specialization": r["specialization"] if "specialization" in r.keys() else None,
            "escalationContact": r["escalation_contact"] if "escalation_contact" in r.keys() else None,
            "escalationTier": r["escalation_tier"] if "escalation_tier" in r.keys() else "TIER_1",
            "leadUserId": r["lead_user_id"] if "lead_user_id" in r.keys() else None,
            "leadUserName": r["lead_user_name"],
            "status": r["status"] if "status" in r.keys() else "ACTIVE",
            "memberCount": r["member_count"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in rows]

        return items, total

    @staticmethod
    def get_team(conn: sqlite3.Connection, team_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.*,
                   r.name as region_name,
                   s.name as store_name,
                   u.full_name as lead_user_name,
                   (SELECT COUNT(*) FROM team_members WHERE team_id = t.id) as member_count
            FROM operational_teams t
            LEFT JOIN regions r ON t.region_id = r.id
            LEFT JOIN stores s ON t.store_id = s.id
            LEFT JOIN users u ON t.lead_user_id = u.id
            WHERE t.id = ?;
        """, (team_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("OperationalTeam", team_id)

        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "regionId": r["region_id"] if "region_id" in r.keys() else None,
            "regionName": r["region_name"],
            "storeId": r["store_id"],
            "storeName": r["store_name"],
            "name": r["name"],
            "teamType": r["team_type"],
            "slaTier": r["sla_tier"],
            "contactEmail": r["contact_email"],
            "responsibility": r["responsibility"] if "responsibility" in r.keys() else None,
            "specialization": r["specialization"] if "specialization" in r.keys() else None,
            "escalationContact": r["escalation_contact"] if "escalation_contact" in r.keys() else None,
            "escalationTier": r["escalation_tier"] if "escalation_tier" in r.keys() else "TIER_1",
            "leadUserId": r["lead_user_id"] if "lead_user_id" in r.keys() else None,
            "leadUserName": r["lead_user_name"],
            "status": r["status"] if "status" in r.keys() else "ACTIVE",
            "memberCount": r["member_count"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

    @staticmethod
    def create_team(
        conn: sqlite3.Connection,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        HierarchyService.get_organization(conn, data.organizationId)
        if data.regionId:
            HierarchyService.get_region(conn, data.regionId)
        if data.storeId:
            HierarchyService.get_store(conn, data.storeId)

        team_id = f"team-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO operational_teams (
                id, organization_id, region_id, store_id, name, team_type, sla_tier, contact_email,
                responsibility, specialization, escalation_contact, escalation_tier, lead_user_id, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            team_id,
            data.organizationId,
            data.regionId,
            data.storeId,
            data.name.strip(),
            data.teamType.strip(),
            data.slaTier or "STANDARD",
            data.contactEmail,
            data.responsibility,
            data.specialization,
            data.escalationContact,
            data.escalationTier or "TIER_1",
            data.leadUserId,
            data.status or "ACTIVE",
            now,
            now
        ))

        new_team = HierarchyService.get_team(conn, team_id)
        AuditService.record_audit(
            conn=conn,
            organization_id=data.organizationId,
            user_id=user_id,
            entity_type="TEAM",
            entity_id=team_id,
            action="TEAM_CREATED",
            new_state=new_team,
            justification=f"Created operational team {data.name}",
            ip_address=ip,
            user_agent=ua
        )
        return new_team

    @staticmethod
    def update_team(
        conn: sqlite3.Connection,
        team_id: str,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        prev_team = HierarchyService.get_team(conn, team_id)
        cur = conn.cursor()

        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name.strip())
        if data.teamType is not None:
            updates.append("team_type = ?")
            params.append(data.teamType.strip())
        if data.regionId is not None:
            updates.append("region_id = ?")
            params.append(data.regionId)
        if data.storeId is not None:
            updates.append("store_id = ?")
            params.append(data.storeId)
        if data.slaTier is not None:
            updates.append("sla_tier = ?")
            params.append(data.slaTier)
        if data.contactEmail is not None:
            updates.append("contact_email = ?")
            params.append(data.contactEmail)
        if data.responsibility is not None:
            updates.append("responsibility = ?")
            params.append(data.responsibility)
        if data.specialization is not None:
            updates.append("specialization = ?")
            params.append(data.specialization)
        if data.escalationContact is not None:
            updates.append("escalation_contact = ?")
            params.append(data.escalationContact)
        if data.escalationTier is not None:
            updates.append("escalation_tier = ?")
            params.append(data.escalationTier)
        if data.leadUserId is not None:
            updates.append("lead_user_id = ?")
            params.append(data.leadUserId)
        if data.status is not None:
            updates.append("status = ?")
            params.append(data.status)

        if not updates:
            return prev_team

        updates.append("updated_at = ?")
        params.append(now)
        params.append(team_id)

        cur.execute(f"UPDATE operational_teams SET {', '.join(updates)} WHERE id = ?;", params)
        updated_team = HierarchyService.get_team(conn, team_id)

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_team["organizationId"],
            user_id=user_id,
            entity_type="TEAM",
            entity_id=team_id,
            action="TEAM_UPDATED",
            previous_state=prev_team,
            new_state=updated_team,
            justification="Updated operational team properties",
            ip_address=ip,
            user_agent=ua
        )
        return updated_team

    @staticmethod
    def delete_team(
        conn: sqlite3.Connection,
        team_id: str,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> None:
        prev_team = HierarchyService.get_team(conn, team_id)
        cur = conn.cursor()
        cur.execute("DELETE FROM operational_teams WHERE id = ?;", (team_id,))

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_team["organizationId"],
            user_id=user_id,
            entity_type="TEAM",
            entity_id=team_id,
            action="TEAM_DELETED",
            previous_state=prev_team,
            justification=f"Deleted team {prev_team['name']}",
            ip_address=ip,
            user_agent=ua
        )

    # Team Members
    @staticmethod
    def get_team_members(conn: sqlite3.Connection, team_id: str) -> List[Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("""
            SELECT tm.*, t.name as team_name, u.full_name as user_name, u.email as user_email, u.role as user_role
            FROM team_members tm
            JOIN operational_teams t ON tm.team_id = t.id
            JOIN users u ON tm.user_id = u.id
            WHERE tm.team_id = ?
            ORDER BY tm.is_primary DESC, u.full_name ASC;
        """, (team_id,))
        rows = cur.fetchall()
        return [{
            "id": r["id"],
            "teamId": r["team_id"],
            "teamName": r["team_name"],
            "userId": r["user_id"],
            "userName": r["user_name"],
            "userEmail": r["user_email"],
            "userRole": r["user_role"],
            "roleInTeam": r["role_in_team"],
            "isPrimary": bool(r["is_primary"]),
            "createdAt": r["created_at"]
        } for r in rows]

    @staticmethod
    def add_team_member(
        conn: sqlite3.Connection,
        team_id: str,
        user_id: str,
        role_in_team: str = "MEMBER",
        is_primary: bool = True,
        current_user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        team = HierarchyService.get_team(conn, team_id)
        cur = conn.cursor()

        cur.execute("SELECT id, organization_id, full_name, email FROM users WHERE id = ?;", (user_id,))
        user_row = cur.fetchone()
        if not user_row:
            raise NotFoundError("User", user_id)

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("SELECT id FROM team_members WHERE team_id = ? AND user_id = ?;", (team_id, user_id))
        existing = cur.fetchone()

        if existing:
            member_id = existing[0]
            cur.execute("""
                UPDATE team_members
                SET role_in_team = ?, is_primary = ?
                WHERE id = ?;
            """, (role_in_team, 1 if is_primary else 0, member_id))
        else:
            member_id = f"tm-{uuid.uuid4().hex[:8]}"
            cur.execute("""
                INSERT INTO team_members (id, team_id, user_id, role_in_team, is_primary, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (member_id, team_id, user_id, role_in_team, 1 if is_primary else 0, now))

        if is_primary:
            cur.execute("UPDATE users SET team_id = ? WHERE id = ?;", (team_id, user_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=team["organizationId"],
            user_id=current_user_id,
            entity_type="TEAM_MEMBER",
            entity_id=member_id,
            action="TEAM_MEMBER_ASSIGNED",
            new_state={
                "teamId": team_id,
                "userId": user_id,
                "roleInTeam": role_in_team,
                "isPrimary": is_primary
            },
            justification=f"Assigned {user_row['full_name']} to team {team['name']} ({role_in_team})",
            ip_address=ip,
            user_agent=ua
        )

        return {
            "id": member_id,
            "teamId": team_id,
            "teamName": team["name"],
            "userId": user_id,
            "userName": user_row["full_name"],
            "userEmail": user_row["email"],
            "roleInTeam": role_in_team,
            "isPrimary": is_primary,
            "createdAt": now
        }

    @staticmethod
    def remove_team_member(
        conn: sqlite3.Connection,
        team_id: str,
        user_id: str,
        current_user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> None:
        team = HierarchyService.get_team(conn, team_id)
        cur = conn.cursor()
        cur.execute("DELETE FROM team_members WHERE team_id = ? AND user_id = ?;", (team_id, user_id))

        # Reset users.team_id if it pointed to this team
        cur.execute("UPDATE users SET team_id = NULL WHERE id = ? AND team_id = ?;", (user_id, team_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=team["organizationId"],
            user_id=current_user_id,
            entity_type="TEAM_MEMBER",
            entity_id=f"{team_id}:{user_id}",
            action="TEAM_MEMBER_REMOVED",
            justification=f"Removed user {user_id} from team {team['name']}",
            ip_address=ip,
            user_agent=ua
        )

    # =========================================================================
    # Operational Ownership Mappings
    # =========================================================================
    @staticmethod
    def get_ownership_mappings(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        region_id: Optional[str] = None,
        domain: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        where_clauses = ["m.organization_id = ?"]
        params: List[Any] = [organization_id]

        if store_id:
            where_clauses.append("(m.store_id = ? OR m.store_id IS NULL)")
            params.append(store_id)

        if region_id:
            where_clauses.append("(m.region_id = ? OR m.region_id IS NULL)")
            params.append(region_id)

        if domain:
            where_clauses.append("m.operational_domain = ?")
            params.append(domain)

        if q:
            term = f"%{q.strip()}%"
            where_clauses.append("(m.operational_domain LIKE ? OR m.description LIKE ?)")
            params.extend([term, term])

        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM operational_ownership_mappings m {where_sql};", params)
        total = cur.fetchone()[0]

        offset = max(0, (page - 1) * limit)
        query = f"""
            SELECT m.*,
                   r.name as region_name,
                   s.name as store_name,
                   d.name as department_name,
                   pt.name as primary_team_name,
                   st.name as secondary_team_name,
                   eu.full_name as escalation_user_name
            FROM operational_ownership_mappings m
            LEFT JOIN regions r ON m.region_id = r.id
            LEFT JOIN stores s ON m.store_id = s.id
            LEFT JOIN departments d ON m.department_id = d.id
            JOIN operational_teams pt ON m.primary_team_id = pt.id
            LEFT JOIN operational_teams st ON m.secondary_team_id = st.id
            LEFT JOIN users eu ON m.escalation_user_id = eu.id
            {where_sql}
            ORDER BY m.operational_domain ASC, m.store_id ASC
            LIMIT ? OFFSET ?;
        """
        cur.execute(query, params + [limit, offset])
        rows = cur.fetchall()

        items = [{
            "id": r["id"],
            "organizationId": r["organization_id"],
            "regionId": r["region_id"],
            "regionName": r["region_name"],
            "storeId": r["store_id"],
            "storeName": r["store_name"],
            "departmentId": r["department_id"],
            "departmentName": r["department_name"],
            "operationalDomain": r["operational_domain"],
            "primaryTeamId": r["primary_team_id"],
            "primaryTeamName": r["primary_team_name"],
            "secondaryTeamId": r["secondary_team_id"],
            "secondaryTeamName": r["secondary_team_name"],
            "escalationUserId": r["escalation_user_id"],
            "escalationUserName": r["escalation_user_name"],
            "slaMinutes": r["sla_minutes"],
            "autoEscalateHours": r["auto_escalate_hours"],
            "description": r["description"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in rows]

        return items, total

    @staticmethod
    def get_ownership_mapping(conn: sqlite3.Connection, mapping_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT m.*,
                   r.name as region_name,
                   s.name as store_name,
                   d.name as department_name,
                   pt.name as primary_team_name,
                   st.name as secondary_team_name,
                   eu.full_name as escalation_user_name
            FROM operational_ownership_mappings m
            LEFT JOIN regions r ON m.region_id = r.id
            LEFT JOIN stores s ON m.store_id = s.id
            LEFT JOIN departments d ON m.department_id = d.id
            JOIN operational_teams pt ON m.primary_team_id = pt.id
            LEFT JOIN operational_teams st ON m.secondary_team_id = st.id
            LEFT JOIN users eu ON m.escalation_user_id = eu.id
            WHERE m.id = ?;
        """, (mapping_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("OperationalOwnershipMapping", mapping_id)

        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "regionId": r["region_id"],
            "regionName": r["region_name"],
            "storeId": r["store_id"],
            "storeName": r["store_name"],
            "departmentId": r["department_id"],
            "departmentName": r["department_name"],
            "operationalDomain": r["operational_domain"],
            "primaryTeamId": r["primary_team_id"],
            "primaryTeamName": r["primary_team_name"],
            "secondaryTeamId": r["secondary_team_id"],
            "secondaryTeamName": r["secondary_team_name"],
            "escalationUserId": r["escalation_user_id"],
            "escalationUserName": r["escalation_user_name"],
            "slaMinutes": r["sla_minutes"],
            "autoEscalateHours": r["auto_escalate_hours"],
            "description": r["description"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

    @staticmethod
    def create_ownership_mapping(
        conn: sqlite3.Connection,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        HierarchyService.get_organization(conn, data.organizationId)
        HierarchyService.get_team(conn, data.primaryTeamId)
        if data.secondaryTeamId:
            HierarchyService.get_team(conn, data.secondaryTeamId)

        mapping_id = f"map-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO operational_ownership_mappings (
                id, organization_id, region_id, store_id, department_id, operational_domain,
                primary_team_id, secondary_team_id, escalation_user_id, sla_minutes, auto_escalate_hours,
                description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            mapping_id,
            data.organizationId,
            data.regionId,
            data.storeId,
            data.departmentId,
            data.operationalDomain.strip().upper(),
            data.primaryTeamId,
            data.secondaryTeamId,
            data.escalationUserId,
            data.slaMinutes or 60,
            data.autoEscalateHours or 4.0,
            data.description,
            now,
            now
        ))

        new_map = HierarchyService.get_ownership_mapping(conn, mapping_id)
        AuditService.record_audit(
            conn=conn,
            organization_id=data.organizationId,
            user_id=user_id,
            entity_type="OWNERSHIP_MAPPING",
            entity_id=mapping_id,
            action="OWNERSHIP_MAPPING_CREATED",
            new_state=new_map,
            justification=f"Created ownership mapping for domain {data.operationalDomain}",
            ip_address=ip,
            user_agent=ua
        )
        return new_map

    @staticmethod
    def update_ownership_mapping(
        conn: sqlite3.Connection,
        mapping_id: str,
        data: Any,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        prev_map = HierarchyService.get_ownership_mapping(conn, mapping_id)
        cur = conn.cursor()

        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        if data.operationalDomain is not None:
            updates.append("operational_domain = ?")
            params.append(data.operationalDomain.strip().upper())
        if data.regionId is not None:
            updates.append("region_id = ?")
            params.append(data.regionId)
        if data.storeId is not None:
            updates.append("store_id = ?")
            params.append(data.storeId)
        if data.departmentId is not None:
            updates.append("department_id = ?")
            params.append(data.departmentId)
        if data.primaryTeamId is not None:
            HierarchyService.get_team(conn, data.primaryTeamId)
            updates.append("primary_team_id = ?")
            params.append(data.primaryTeamId)
        if data.secondaryTeamId is not None:
            updates.append("secondary_team_id = ?")
            params.append(data.secondaryTeamId)
        if data.escalationUserId is not None:
            updates.append("escalation_user_id = ?")
            params.append(data.escalationUserId)
        if data.slaMinutes is not None:
            updates.append("sla_minutes = ?")
            params.append(data.slaMinutes)
        if data.autoEscalateHours is not None:
            updates.append("auto_escalate_hours = ?")
            params.append(data.autoEscalateHours)
        if data.description is not None:
            updates.append("description = ?")
            params.append(data.description)

        if not updates:
            return prev_map

        updates.append("updated_at = ?")
        params.append(now)
        params.append(mapping_id)

        cur.execute(f"UPDATE operational_ownership_mappings SET {', '.join(updates)} WHERE id = ?;", params)
        updated_map = HierarchyService.get_ownership_mapping(conn, mapping_id)

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_map["organizationId"],
            user_id=user_id,
            entity_type="OWNERSHIP_MAPPING",
            entity_id=mapping_id,
            action="OWNERSHIP_MAPPING_UPDATED",
            previous_state=prev_map,
            new_state=updated_map,
            justification="Updated ownership mapping rules",
            ip_address=ip,
            user_agent=ua
        )
        return updated_map

    @staticmethod
    def delete_ownership_mapping(
        conn: sqlite3.Connection,
        mapping_id: str,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> None:
        prev_map = HierarchyService.get_ownership_mapping(conn, mapping_id)
        cur = conn.cursor()
        cur.execute("DELETE FROM operational_ownership_mappings WHERE id = ?;", (mapping_id,))

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_map["organizationId"],
            user_id=user_id,
            entity_type="OWNERSHIP_MAPPING",
            entity_id=mapping_id,
            action="OWNERSHIP_MAPPING_DELETED",
            previous_state=prev_map,
            justification="Deleted operational ownership mapping",
            ip_address=ip,
            user_agent=ua
        )

    # =========================================================================
    # Operational Lineage & Tracing
    # =========================================================================
    @staticmethod
    def trace_operational_object(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        operational_domain: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Traces any operational entity back through:
        organization -> region -> store -> department/asset -> team -> user (escalation owner / team lead).
        """
        cur = conn.cursor()
        org = HierarchyService.get_organization(conn, organization_id)
        org_node = {
            "id": org["id"],
            "type": "ORGANIZATION",
            "name": org["name"],
            "details": {
                "code": org["code"],
                "status": org.get("status", "ACTIVE"),
                "description": org.get("description")
            }
        }

        # Resolve entity if entity_type and entity_id are supplied
        resolved_store_id = store_id
        resolved_domain = operational_domain
        dept_id = None
        _asset_info = None

        if entity_type and entity_id:
            e_type = entity_type.upper()
            if e_type == "STORE":
                resolved_store_id = entity_id
            elif e_type == "ASSET":
                cur.execute("SELECT * FROM assets WHERE id = ?;", (entity_id,))
                a = cur.fetchone()
                if a:
                    resolved_store_id = a["store_id"]
                    dept_id = a["department_id"]
                    _asset_info = {"id": a["id"], "name": a["name"], "category": a["category"], "tag": a["asset_tag"]}
                    if not resolved_domain:
                        resolved_domain = a["category"]
            elif e_type == "ISSUE":
                cur.execute("SELECT * FROM issues WHERE id = ?;", (entity_id,))
                iss = cur.fetchone()
                if iss:
                    resolved_store_id = iss["store_id"]
                    dept_id = iss["department_id"]
                    if iss["assigned_team_id"] and not resolved_domain:
                        cur.execute("SELECT team_type FROM operational_teams WHERE id = ?;", (iss["assigned_team_id"],))
                        t_row = cur.fetchone()
                        if t_row:
                            resolved_domain = t_row[0]

        # Resolve Store & Region
        store_node = None
        region_node = None
        store = None
        if resolved_store_id:
            try:
                store = HierarchyService.get_store(conn, resolved_store_id)
                store_node = {
                    "id": store["id"],
                    "type": "STORE",
                    "name": store["name"],
                    "details": {
                        "storeNumber": store["storeNumber"],
                        "operatingStatus": store.get("operatingStatus", "OPERATIONAL"),
                        "city": store["address"].get("city"),
                        "state": store["address"].get("state"),
                        "timezone": store["timezone"],
                        "metadata": store.get("metadata")
                    }
                }
                reg = HierarchyService.get_region(conn, store["regionId"])
                region_node = {
                    "id": reg["id"],
                    "type": "REGION",
                    "name": reg["name"],
                    "details": {
                        "code": reg["code"],
                        "leadUserId": reg.get("leadUserId"),
                        "leadUserName": reg.get("leadUserName")
                    }
                }
            except Exception:
                pass

        # Resolve Department
        department_node = None
        if dept_id:
            cur.execute("SELECT * FROM departments WHERE id = ?;", (dept_id,))
            d = cur.fetchone()
            if d:
                department_node = {
                    "id": d["id"],
                    "type": "DEPARTMENT",
                    "name": d["name"],
                    "details": {"floorZone": d["floor_zone"]}
                }

        # Resolve Ownership Mapping
        mapping = None
        if resolved_store_id and resolved_domain:
            cur.execute("""
                SELECT m.*, pt.name as pt_name, pt.specialization as pt_spec, pt.escalation_contact as pt_contact,
                       eu.full_name as eu_name, eu.email as eu_email, eu.role as eu_role
                FROM operational_ownership_mappings m
                JOIN operational_teams pt ON m.primary_team_id = pt.id
                LEFT JOIN users eu ON m.escalation_user_id = eu.id
                WHERE m.organization_id = ? AND m.store_id = ? AND m.operational_domain = ?;
            """, (organization_id, resolved_store_id, resolved_domain))
            m_row = cur.fetchone()
            if not m_row:
                # Fallback to regional or org-level domain mapping
                cur.execute("""
                    SELECT m.*, pt.name as pt_name, pt.specialization as pt_spec, pt.escalation_contact as pt_contact,
                           eu.full_name as eu_name, eu.email as eu_email, eu.role as eu_role
                    FROM operational_ownership_mappings m
                    JOIN operational_teams pt ON m.primary_team_id = pt.id
                    LEFT JOIN users eu ON m.escalation_user_id = eu.id
                    WHERE m.organization_id = ? AND m.operational_domain = ?
                    ORDER BY m.store_id DESC, m.region_id DESC LIMIT 1;
                """, (organization_id, resolved_domain))
                m_row = cur.fetchone()

            if m_row:
                mapping = {
                    "id": m_row["id"],
                    "operationalDomain": m_row["operational_domain"],
                    "primaryTeamId": m_row["primary_team_id"],
                    "primaryTeamName": m_row["pt_name"],
                    "primaryTeamSpecialization": m_row["pt_spec"],
                    "primaryTeamContact": m_row["pt_contact"],
                    "escalationUserId": m_row["escalation_user_id"],
                    "escalationUserName": m_row["eu_name"],
                    "escalationUserRole": m_row["eu_role"],
                    "slaMinutes": m_row["sla_minutes"],
                    "autoEscalateHours": m_row["auto_escalate_hours"]
                }

        # Primary Team & User Nodes
        primary_team_node = None
        escalation_user_node = None

        if mapping:
            primary_team_node = {
                "id": mapping["primaryTeamId"],
                "type": "TEAM",
                "name": mapping["primaryTeamName"],
                "details": {
                    "specialization": mapping.get("primaryTeamSpecialization"),
                    "contact": mapping.get("primaryTeamContact"),
                    "slaTargetMinutes": mapping["slaMinutes"]
                }
            }
            if mapping.get("escalationUserId"):
                escalation_user_node = {
                    "id": mapping["escalationUserId"],
                    "type": "USER",
                    "name": mapping["escalationUserName"] or "Escalation Lead",
                    "details": {
                        "email": mapping.get("escalationUserRole"),
                        "role": mapping.get("escalationUserRole"),
                        "autoEscalateAfterHours": mapping["autoEscalateHours"]
                    }
                }
        elif store:
            # Fallback to primary store lead and general facilities team
            cur.execute("""
                SELECT t.*, u.full_name as lead_name, u.email as lead_email
                FROM operational_teams t
                LEFT JOIN users u ON t.lead_user_id = u.id
                WHERE t.organization_id = ? AND (t.store_id = ? OR t.store_id IS NULL)
                ORDER BY t.created_at ASC LIMIT 1;
            """, (organization_id, store["id"]))
            t_row = cur.fetchone()
            if t_row:
                primary_team_node = {
                    "id": t_row["id"],
                    "type": "TEAM",
                    "name": t_row["name"],
                    "details": {
                        "teamType": t_row["team_type"],
                        "specialization": t_row["specialization"],
                        "slaTier": t_row["sla_tier"]
                    }
                }
                if t_row["lead_user_id"]:
                    escalation_user_node = {
                        "id": t_row["lead_user_id"],
                        "type": "USER",
                        "name": t_row["lead_name"] or "Team Lead",
                        "details": {"email": t_row["lead_email"]}
                    }

        # Construct Lineage Chain
        lineage_chain = [org_node]
        if region_node:
            lineage_chain.append(region_node)
        if store_node:
            lineage_chain.append(store_node)
        if department_node:
            lineage_chain.append(department_node)
        if primary_team_node:
            lineage_chain.append(primary_team_node)
        if escalation_user_node:
            lineage_chain.append(escalation_user_node)

        summary_parts = [org_node["name"]]
        if region_node:
            summary_parts.append(region_node["name"])
        if store_node:
            summary_parts.append(f"{store_node['name']} (#{store_node['details']['storeNumber']})")
        if primary_team_node:
            summary_parts.append(f"Dispatched To: {primary_team_node['name']}")
        if escalation_user_node:
            summary_parts.append(f"Escalation Lead: {escalation_user_node['name']}")

        return {
            "targetEntity": {
                "entityType": entity_type or ("STORE" if store_node else "ORGANIZATION"),
                "entityId": entity_id or (store_node["id"] if store_node else org_node["id"]),
                "domain": resolved_domain
            },
            "lineageChain": lineage_chain,
            "organization": org_node,
            "region": region_node,
            "store": store_node,
            "department": department_node,
            "primaryTeam": primary_team_node,
            "escalationOwner": escalation_user_node,
            "ownershipMapping": mapping,
            "traceSummary": " ➔ ".join(summary_parts)
        }

    # =========================================================================
    # Departments & Assets (Retained for backward compatibility)
    # =========================================================================
    @staticmethod
    def get_departments(conn: sqlite3.Connection, store_id: str) -> List[Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM departments WHERE store_id = ? ORDER BY name ASC;", (store_id,))
        return [{
            "id": r["id"],
            "organizationId": r["organization_id"],
            "storeId": r["store_id"],
            "name": r["name"],
            "floorZone": r["floor_zone"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in cur.fetchall()]

    @staticmethod
    def get_assets(conn: sqlite3.Connection, store_id: str) -> List[Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM assets WHERE store_id = ? ORDER BY name ASC;", (store_id,))
        return [{
            "id": r["id"],
            "organizationId": r["organization_id"],
            "storeId": r["store_id"],
            "departmentId": r["department_id"],
            "name": r["name"],
            "assetTag": r["asset_tag"],
            "category": r["category"],
            "status": r["status"],
            "metadata": json.loads(r["metadata"]) if r["metadata"] else None,
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in cur.fetchall()]

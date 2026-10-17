import uuid
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.app.core.security import hash_password
from backend.app.core.errors import NotFoundError, ConflictError, ValidationError
from backend.app.services.audit_service import AuditService

class UserService:
    @staticmethod
    def get_users(
        conn: sqlite3.Connection,
        organization_id: str,
        region_id: Optional[str] = None,
        store_id: Optional[str] = None,
        team_id: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        where_clauses = ["u.organization_id = ?"]
        params: List[Any] = [organization_id]

        if region_id:
            where_clauses.append("u.region_id = ?")
            params.append(region_id)

        if store_id:
            where_clauses.append("u.store_id = ?")
            params.append(store_id)

        if team_id:
            where_clauses.append("(u.team_id = ? OR EXISTS (SELECT 1 FROM team_members tm WHERE tm.user_id = u.id AND tm.team_id = ?))")
            params.extend([team_id, team_id])

        if role:
            where_clauses.append("u.role = ?")
            params.append(role)

        if is_active is not None:
            where_clauses.append("u.is_active = ?")
            params.append(1 if is_active else 0)

        if q:
            term = f"%{q.strip()}%"
            where_clauses.append("(u.full_name LIKE ? OR u.email LIKE ? OR u.role LIKE ?)")
            params.extend([term, term, term])

        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM users u {where_sql};", params)
        total = cur.fetchone()[0]

        offset = max(0, (page - 1) * limit)
        query = f"""
            SELECT u.*,
                   s.name as store_name,
                   r.name as region_name,
                   t.name as team_name
            FROM users u
            LEFT JOIN stores s ON u.store_id = s.id
            LEFT JOIN regions r ON u.region_id = r.id
            LEFT JOIN operational_teams t ON u.team_id = t.id
            {where_sql}
            ORDER BY u.full_name ASC
            LIMIT ? OFFSET ?;
        """
        cur.execute(query, params + [limit, offset])
        rows = cur.fetchall()

        items = [{
            "id": r["id"],
            "organizationId": r["organization_id"],
            "email": r["email"],
            "fullName": r["full_name"],
            "role": r["role"],
            "storeId": r["store_id"],
            "storeName": r["store_name"],
            "regionId": r["region_id"],
            "regionName": r["region_name"],
            "teamId": r["team_id"],
            "teamName": r["team_name"],
            "isActive": bool(r["is_active"]),
            "lastLoginAt": r["last_login_at"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        } for r in rows]

        return items, total

    @staticmethod
    def get_user(conn: sqlite3.Connection, user_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.*,
                   s.name as store_name,
                   r.name as region_name,
                   t.name as team_name
            FROM users u
            LEFT JOIN stores s ON u.store_id = s.id
            LEFT JOIN regions r ON u.region_id = r.id
            LEFT JOIN operational_teams t ON u.team_id = t.id
            WHERE u.id = ?;
        """, (user_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("User", user_id)

        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "email": r["email"],
            "fullName": r["full_name"],
            "role": r["role"],
            "storeId": r["store_id"],
            "storeName": r["store_name"],
            "regionId": r["region_id"],
            "regionName": r["region_name"],
            "teamId": r["team_id"],
            "teamName": r["team_name"],
            "isActive": bool(r["is_active"]),
            "lastLoginAt": r["last_login_at"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

    @staticmethod
    def create_user(
        conn: sqlite3.Connection,
        data: Any,
        current_user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        email_clean = data.email.strip().lower()

        cur.execute("SELECT id FROM users WHERE email = ?;", (email_clean,))
        if cur.fetchone():
            raise ConflictError(f"User with email '{email_clean}' already exists")

        # Validate store/region if provided
        if data.storeId:
            cur.execute("SELECT id, region_id FROM stores WHERE id = ?;", (data.storeId,))
            store = cur.fetchone()
            if not store:
                raise NotFoundError("Store", data.storeId)
            if not data.regionId and store["region_id"]:
                data.regionId = store["region_id"]

        user_id = f"usr-{uuid.uuid4().hex[:8]}"
        pwd_hash = hash_password(data.password)
        now = datetime.now(timezone.utc).isoformat()

        cur.execute("""
            INSERT INTO users (
                id, organization_id, store_id, region_id, team_id, email, password_hash,
                full_name, role, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            user_id,
            data.organizationId,
            data.storeId,
            data.regionId,
            data.teamId,
            email_clean,
            pwd_hash,
            data.fullName.strip(),
            data.role.strip().upper(),
            1 if data.isActive is not False else 0,
            now,
            now
        ))

        # If teamId specified, assign to team_members
        if data.teamId:
            tm_id = f"tm-{uuid.uuid4().hex[:8]}"
            cur.execute("""
                INSERT OR IGNORE INTO team_members (id, team_id, user_id, role_in_team, is_primary, created_at)
                VALUES (?, ?, ?, 'MEMBER', 1, ?);
            """, (tm_id, data.teamId, user_id, now))

        new_user = UserService.get_user(conn, user_id)
        AuditService.record_audit(
            conn=conn,
            organization_id=data.organizationId,
            user_id=current_user_id,
            entity_type="USER",
            entity_id=user_id,
            action="USER_CREATED",
            new_state={k: v for k, v in new_user.items() if k != "password_hash"},
            justification=f"Created user {new_user['fullName']} ({new_user['role']})",
            ip_address=ip,
            user_agent=ua
        )
        return new_user

    @staticmethod
    def update_user(
        conn: sqlite3.Connection,
        user_id: str,
        data: Any,
        current_user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        prev_user = UserService.get_user(conn, user_id)
        cur = conn.cursor()

        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        if data.email is not None:
            email_clean = data.email.strip().lower()
            cur.execute("SELECT id FROM users WHERE email = ? AND id != ?;", (email_clean, user_id))
            if cur.fetchone():
                raise ConflictError(f"Email '{email_clean}' is already assigned to another user")
            updates.append("email = ?")
            params.append(email_clean)

        if data.password is not None and data.password.strip():
            pwd_hash = hash_password(data.password.strip())
            updates.append("password_hash = ?")
            params.append(pwd_hash)

        if data.fullName is not None:
            updates.append("full_name = ?")
            params.append(data.fullName.strip())

        if data.role is not None:
            updates.append("role = ?")
            params.append(data.role.strip().upper())

        if data.storeId is not None:
            updates.append("store_id = ?")
            params.append(data.storeId if data.storeId != "" else None)

        if data.regionId is not None:
            updates.append("region_id = ?")
            params.append(data.regionId if data.regionId != "" else None)

        if data.teamId is not None:
            new_team = data.teamId if data.teamId != "" else None
            updates.append("team_id = ?")
            params.append(new_team)
            if new_team:
                tm_id = f"tm-{uuid.uuid4().hex[:8]}"
                cur.execute("""
                    INSERT OR IGNORE INTO team_members (id, team_id, user_id, role_in_team, is_primary, created_at)
                    VALUES (?, ?, ?, 'MEMBER', 1, ?);
                """, (tm_id, new_team, user_id, now))

        if data.isActive is not None:
            updates.append("is_active = ?")
            params.append(1 if data.isActive else 0)

        if not updates:
            return prev_user

        updates.append("updated_at = ?")
        params.append(now)
        params.append(user_id)

        cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?;", params)
        updated_user = UserService.get_user(conn, user_id)

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_user["organizationId"],
            user_id=current_user_id,
            entity_type="USER",
            entity_id=user_id,
            action="USER_UPDATED",
            previous_state=prev_user,
            new_state=updated_user,
            justification="Updated user profile and credentials",
            ip_address=ip,
            user_agent=ua
        )
        return updated_user

    @staticmethod
    def delete_user(
        conn: sqlite3.Connection,
        user_id: str,
        current_user_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> None:
        if current_user_id and current_user_id == user_id:
            raise ValidationError("You cannot delete your own active account session")

        prev_user = UserService.get_user(conn, user_id)
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?;", (user_id,))

        AuditService.record_audit(
            conn=conn,
            organization_id=prev_user["organizationId"],
            user_id=current_user_id,
            entity_type="USER",
            entity_id=user_id,
            action="USER_DELETED",
            previous_state=prev_user,
            justification=f"Removed user {prev_user['fullName']} ({prev_user['email']})",
            ip_address=ip,
            user_agent=ua
        )

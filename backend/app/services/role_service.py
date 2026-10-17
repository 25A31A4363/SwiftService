import uuid
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.app.core.rbac import Permission
from backend.app.core.errors import NotFoundError, ConflictError, ValidationError
from backend.app.services.audit_service import AuditService

class RoleService:
    @staticmethod
    def get_roles(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*,
                   (SELECT COUNT(*) FROM users WHERE role = r.name) as user_count
            FROM roles r
            ORDER BY r.is_system DESC, r.name ASC;
        """)
        rows = cur.fetchall()

        result = []
        for r in rows:
            role_id = r["id"]
            cur.execute("SELECT permission FROM role_permissions WHERE role_id = ? ORDER BY permission ASC;", (role_id,))
            perms = [p[0] for p in cur.fetchall()]
            result.append({
                "id": role_id,
                "name": r["name"],
                "description": r["description"],
                "isSystem": bool(r["is_system"]),
                "permissions": perms,
                "userCount": r["user_count"],
                "createdAt": r["created_at"],
                "updatedAt": r["updated_at"]
            })
        return result

    @staticmethod
    def get_role_by_id(conn: sqlite3.Connection, role_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*,
                   (SELECT COUNT(*) FROM users WHERE role = r.name) as user_count
            FROM roles r
            WHERE r.id = ?;
        """, (role_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("Role", role_id)

        cur.execute("SELECT permission FROM role_permissions WHERE role_id = ? ORDER BY permission ASC;", (role_id,))
        perms = [p[0] for p in cur.fetchall()]

        return {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "isSystem": bool(r["is_system"]),
            "permissions": perms,
            "userCount": r["user_count"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"]
        }

    @staticmethod
    def get_permissions_matrix(conn: sqlite3.Connection) -> Dict[str, Any]:
        roles = RoleService.get_roles(conn)
        all_perms = [{
            "key": p.value,
            "domain": p.value.split(":")[0].upper(),
            "action": p.value.split(":")[1].upper(),
            "label": f"{p.value.split(':')[0].capitalize()} {p.value.split(':')[1].capitalize()}"
        } for p in Permission]

        return {
            "roles": roles,
            "allPermissions": all_perms
        }

    @staticmethod
    def create_role(
        conn: sqlite3.Connection,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        role_name_clean = name.strip().upper()
        cur = conn.cursor()

        cur.execute("SELECT id FROM roles WHERE name = ?;", (role_name_clean,))
        if cur.fetchone():
            raise ConflictError(f"Role '{role_name_clean}' already exists")

        role_id = f"role-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        cur.execute("""
            INSERT INTO roles (id, name, description, is_system, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, ?);
        """, (role_id, role_name_clean, description, now, now))

        if permissions:
            # Validate permissions against Permission enum
            valid_keys = {p.value for p in Permission}
            rows = [(role_id, p) for p in permissions if p in valid_keys]
            cur.executemany("INSERT OR IGNORE INTO role_permissions (role_id, permission) VALUES (?, ?);", rows)

        new_role = RoleService.get_role_by_id(conn, role_id)
        AuditService.record_audit(
            conn=conn,
            organization_id=organization_id or "org-apex-01",
            user_id=user_id,
            entity_type="ROLE",
            entity_id=role_id,
            action="ROLE_CREATED",
            new_state=new_role,
            justification=f"Created custom role {role_name_clean}",
            ip_address=ip,
            user_agent=ua
        )
        return new_role

    @staticmethod
    def update_role_permissions(
        conn: sqlite3.Connection,
        role_id: str,
        permissions: List[str],
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        prev_role = RoleService.get_role_by_id(conn, role_id)
        cur = conn.cursor()

        valid_keys = {p.value for p in Permission}
        cleaned_perms = [p for p in permissions if p in valid_keys]

        cur.execute("DELETE FROM role_permissions WHERE role_id = ?;", (role_id,))
        rows = [(role_id, p) for p in cleaned_perms]
        cur.executemany("INSERT INTO role_permissions (role_id, permission) VALUES (?, ?);", rows)

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE roles SET updated_at = ? WHERE id = ?;", (now, role_id))

        updated_role = RoleService.get_role_by_id(conn, role_id)
        AuditService.record_audit(
            conn=conn,
            organization_id=organization_id or "org-apex-01",
            user_id=user_id,
            entity_type="ROLE",
            entity_id=role_id,
            action="ROLE_PERMISSIONS_UPDATED",
            previous_state={"permissions": prev_role["permissions"]},
            new_state={"permissions": updated_role["permissions"]},
            justification=f"Updated permissions for role {prev_role['name']}",
            ip_address=ip,
            user_agent=ua
        )
        return updated_role

    @staticmethod
    def delete_role(
        conn: sqlite3.Connection,
        role_id: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> None:
        role = RoleService.get_role_by_id(conn, role_id)
        if role["isSystem"]:
            raise ValidationError(f"Built-in system role '{role['name']}' cannot be deleted")

        cur = conn.cursor()
        # Verify no users are assigned
        cur.execute("SELECT COUNT(*) FROM users WHERE role = ?;", (role["name"],))
        if cur.fetchone()[0] > 0:
            raise ConflictError(f"Cannot delete role '{role['name']}' because active users are assigned to it")

        cur.execute("DELETE FROM roles WHERE id = ?;", (role_id,))
        AuditService.record_audit(
            conn=conn,
            organization_id=organization_id or "org-apex-01",
            user_id=user_id,
            entity_type="ROLE",
            entity_id=role_id,
            action="ROLE_DELETED",
            previous_state=role,
            justification=f"Deleted custom role {role['name']}",
            ip_address=ip,
            user_agent=ua
        )

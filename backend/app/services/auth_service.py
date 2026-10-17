import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any
from backend.app.core.security import verify_password, hash_password, create_access_token
from backend.app.core.errors import UnauthorizedError, NotFoundError, ConflictError, ValidationError
from backend.app.services.audit_service import AuditService
from backend.app.core.logger import logger
from backend.app.core.config import settings

class AuthService:
    @staticmethod
    def authenticate_user(conn: sqlite3.Connection, email: str, password: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, organization_id, email, password_hash, full_name, role,
                   store_id, region_id, team_id, is_active, last_login_at, created_at, updated_at
            FROM users
            WHERE email = ?;
        """, (email.lower().strip(),))
        user_row = cur.fetchone()

        if not user_row:
            logger.warning(f"Failed login attempt for non-existent email: {email}")
            raise UnauthorizedError("Invalid email or password")

        if not user_row["is_active"]:
            logger.warning(f"Login attempt for deactivated user: {email}")
            raise UnauthorizedError("User account is inactive. Please contact your organization administrator.")

        if not verify_password(password, user_row["password_hash"]):
            logger.warning(f"Invalid password attempt for email: {email}")
            raise UnauthorizedError("Invalid email or password")

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE users SET last_login_at = ? WHERE id = ?;", (now, user_row["id"]))

        user_dict = {
            "id": user_row["id"],
            "organizationId": user_row["organization_id"],
            "email": user_row["email"],
            "fullName": user_row["full_name"],
            "role": user_row["role"],
            "storeId": user_row["store_id"],
            "regionId": user_row["region_id"],
            "teamId": user_row["team_id"],
            "isActive": bool(user_row["is_active"]),
            "lastLoginAt": now,
            "createdAt": user_row["created_at"],
            "updatedAt": user_row["updated_at"]
        }

        token_payload = {
            "userId": user_row["id"],
            "organizationId": user_row["organization_id"],
            "email": user_row["email"],
            "role": user_row["role"],
            "storeId": user_row["store_id"],
            "regionId": user_row["region_id"],
            "teamId": user_row["team_id"]
        }
        token = create_access_token(token_payload)

        return {
            "token": token,
            "user": user_dict,
            "expiresIn": f"{settings.ACCESS_TOKEN_EXPIRE_MINUTES}m"
        }

    @staticmethod
    def get_user_by_id(conn: sqlite3.Connection, user_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, organization_id, email, full_name, role,
                   store_id, region_id, team_id, is_active, last_login_at, created_at, updated_at
            FROM users
            WHERE id = ?;
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("User", user_id)

        return {
            "id": row["id"],
            "organizationId": row["organization_id"],
            "email": row["email"],
            "fullName": row["full_name"],
            "role": row["role"],
            "storeId": row["store_id"],
            "regionId": row["region_id"],
            "teamId": row["team_id"],
            "isActive": bool(row["is_active"]),
            "lastLoginAt": row["last_login_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"]
        }

    @staticmethod
    def update_profile(
        conn: sqlite3.Connection,
        user_id: str,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        user_row = cur.fetchone()
        if not user_row:
            raise NotFoundError("User", user_id)

        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        if email is not None:
            clean_email = email.strip().lower()
            if not clean_email:
                raise ValidationError("Email cannot be empty")
            cur.execute("SELECT id FROM users WHERE email = ? AND id != ?;", (clean_email, user_id))
            if cur.fetchone():
                raise ConflictError(f"Email '{clean_email}' is already assigned to another account")
            updates.append("email = ?")
            params.append(clean_email)

        if full_name is not None:
            clean_name = full_name.strip()
            if len(clean_name) < 2:
                raise ValidationError("Full name must be at least 2 characters")
            updates.append("full_name = ?")
            params.append(clean_name)

        if not updates:
            return AuthService.get_user_by_id(conn, user_id)

        updates.append("updated_at = ?")
        params.append(now)
        params.append(user_id)

        cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?;", params)
        updated_user = AuthService.get_user_by_id(conn, user_id)

        AuditService.record_audit(
            conn=conn,
            organization_id=updated_user["organizationId"],
            user_id=user_id,
            entity_type="USER",
            entity_id=user_id,
            action="PROFILE_UPDATED",
            new_state={
                "email": updated_user["email"],
                "fullName": updated_user["fullName"]
            },
            justification="User self-service profile update",
            ip_address=ip,
            user_agent=ua
        )

        return updated_user

    @staticmethod
    def change_password(
        conn: sqlite3.Connection,
        user_id: str,
        current_password: str,
        new_password: str,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT password_hash, organization_id, email, full_name FROM users WHERE id = ?;", (user_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("User", user_id)

        if not verify_password(current_password, row["password_hash"]):
            logger.warning(f"Password change rejected: incorrect current password for user {user_id}")
            raise UnauthorizedError("Current password is incorrect")

        clean_new = new_password.strip()
        if len(clean_new) < 8:
            raise ValidationError("New password must be at least 8 characters long")

        new_hash = hash_password(clean_new)
        now = datetime.now(timezone.utc).isoformat()

        cur.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?;", (new_hash, now, user_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=row["organization_id"],
            user_id=user_id,
            entity_type="USER",
            entity_id=user_id,
            action="PASSWORD_CHANGED",
            new_state={"email": row["email"], "passwordUpdated": True},
            justification="User authorized password change",
            ip_address=ip,
            user_agent=ua
        )

        return {"message": "Password changed successfully. Please authenticate with your new credentials on future logins."}

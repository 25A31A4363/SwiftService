import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any
from backend.app.core.security import verify_password, create_access_token
from backend.app.core.errors import UnauthorizedError, NotFoundError
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

import uuid
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.app.core.security import verify_password, hash_password, create_access_token
from backend.app.core.errors import UnauthorizedError, NotFoundError, ConflictError, ValidationError
from backend.app.services.audit_service import AuditService
from backend.app.services.otp_service import OtpService
from backend.app.core.logger import logger
from backend.app.core.config import settings

class AuthService:
    @staticmethod
    def authenticate_user(conn: sqlite3.Connection, email: str, password: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, organization_id, email, password_hash, full_name, role,
                   store_id, region_id, team_id, is_active, is_verified, phone,
                   last_login_at, created_at, updated_at
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

        # Gating check for customer email verification
        is_verified = bool(user_row["is_verified"]) if "is_verified" in user_row.keys() else True
        if user_row["role"] == "CUSTOMER" and not is_verified:
            logger.warning(f"Login attempt for unverified customer: {email}")
            raise UnauthorizedError("EMAIL_UNVERIFIED: Please complete email verification before logging in.")

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
            "isVerified": is_verified,
            "phone": user_row["phone"] if "phone" in user_row.keys() else None,
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

    @classmethod
    def register_customer(
        cls,
        conn: sqlite3.Connection,
        full_name: str,
        email: str,
        password: str,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Register a new customer account in pending verification state and dispatch single-use OTP."""
        cur = conn.cursor()
        clean_email = email.lower().strip()
        now = datetime.now(timezone.utc).isoformat()

        cur.execute("SELECT id, is_verified, role FROM users WHERE email = ?;", (clean_email,))
        existing = cur.fetchone()

        if existing:
            if existing["is_verified"]:
                raise ConflictError("An account with this email address already exists. Please log in.")
            user_id = existing["id"]
            pwd_hash = hash_password(password)
            cur.execute("""
                UPDATE users
                SET full_name = ?, password_hash = ?, phone = ?, updated_at = ?
                WHERE id = ?;
            """, (full_name.strip(), pwd_hash, phone, now, user_id))
        else:
            cur.execute("SELECT id FROM organizations LIMIT 1;")
            org_row = cur.fetchone()
            org_id = org_row["id"] if org_row else "org-apex-01"

            user_id = f"usr-{uuid.uuid4().hex[:12]}"
            pwd_hash = hash_password(password)
            cur.execute("""
                INSERT INTO users (
                    id, organization_id, email, password_hash, full_name, role,
                    is_active, is_verified, phone, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                user_id, org_id, clean_email, pwd_hash, full_name.strip(),
                "CUSTOMER", 1, 0, phone, now, now
            ))

        conn.commit()

        # Generate & send OTP
        otp_info = OtpService.generate_and_send_otp(conn, user_id, clean_email, purpose="REGISTRATION")

        return {
            "message": "Account created. A 6-digit verification code has been dispatched to your email.",
            "email": clean_email,
            "isVerified": False,
            "expiresInMinutes": OtpService.EXPIRY_MINUTES,
            "emailDelivery": otp_info.get("emailDelivery", {}),
            "devOtpCode": otp_info.get("devOtpCode")
        }

    @classmethod
    def verify_customer_otp(
        cls,
        conn: sqlite3.Connection,
        email: str,
        otp: str
    ) -> Dict[str, Any]:
        """Verify 6-digit OTP code, mark customer verified, and establish active session."""
        clean_email = email.lower().strip()
        OtpService.verify_otp(conn, clean_email, otp, purpose="REGISTRATION")

        cur = conn.cursor()
        cur.execute("""
            SELECT id, organization_id, email, full_name, role, store_id,
                   region_id, team_id, is_active, is_verified, phone, created_at, updated_at
            FROM users WHERE email = ?;
        """, (clean_email,))
        user_row = cur.fetchone()

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE users SET last_login_at = ? WHERE id = ?;", (now, user_row["id"]))
        conn.commit()

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

        user_dict = {
            "id": user_row["id"],
            "organizationId": user_row["organization_id"],
            "email": user_row["email"],
            "fullName": user_row["full_name"],
            "role": user_row["role"],
            "storeId": user_row["store_id"],
            "regionId": user_row["region_id"],
            "teamId": user_row["team_id"],
            "isActive": True,
            "isVerified": True,
            "phone": user_row["phone"] if "phone" in user_row.keys() else None,
            "lastLoginAt": now,
            "createdAt": user_row["created_at"],
            "updatedAt": user_row["updated_at"]
        }

        return {
            "message": "Email verified successfully! Welcome to RetailWave.",
            "token": token,
            "user": user_dict,
            "expiresIn": f"{settings.ACCESS_TOKEN_EXPIRE_MINUTES}m"
        }

    @classmethod
    def resend_customer_otp(
        cls,
        conn: sqlite3.Connection,
        email: str
    ) -> Dict[str, Any]:
        """Resend OTP to unverified customer respecting cooldown and hourly rate limits."""
        clean_email = email.lower().strip()
        cur = conn.cursor()
        cur.execute("SELECT id, is_verified FROM users WHERE email = ?;", (clean_email,))
        user_row = cur.fetchone()
        if not user_row:
            raise NotFoundError("User", clean_email)
        if user_row["is_verified"]:
            raise ConflictError("This account is already verified. Please log in.")

        otp_info = OtpService.generate_and_send_otp(conn, user_row["id"], clean_email, purpose="REGISTRATION")
        return {
            "message": "A fresh verification code has been dispatched to your email.",
            "email": clean_email,
            "expiresInMinutes": OtpService.EXPIRY_MINUTES,
            "emailDelivery": otp_info.get("emailDelivery", {}),
            "devOtpCode": otp_info.get("devOtpCode")
        }

    @staticmethod
    def get_user_by_id(conn: sqlite3.Connection, user_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, organization_id, email, full_name, role,
                   store_id, region_id, team_id, is_active, is_verified, phone,
                   last_login_at, created_at, updated_at
            FROM users
            WHERE id = ?;
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("User", user_id)

        is_verified = bool(row["is_verified"]) if "is_verified" in row.keys() else True

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
            "isVerified": is_verified,
            "phone": row["phone"] if "phone" in row.keys() else None,
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
        phone: Optional[str] = None,
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
        email_changed = False
        clean_email = None

        if email is not None:
            clean_email = email.strip().lower()
            if not clean_email:
                raise ValidationError("Email cannot be empty")
            if clean_email != user_row["email"].lower():
                cur.execute("SELECT id FROM users WHERE email = ? AND id != ?;", (clean_email, user_id))
                if cur.fetchone():
                    raise ConflictError(f"Email '{clean_email}' is already assigned to another account")
                updates.append("email = ?")
                params.append(clean_email)
                email_changed = True
                if user_row["role"] == "CUSTOMER":
                    updates.append("is_verified = ?")
                    params.append(0)

        if full_name is not None:
            clean_name = full_name.strip()
            if len(clean_name) < 2:
                raise ValidationError("Full name must be at least 2 characters")
            updates.append("full_name = ?")
            params.append(clean_name)

        if phone is not None:
            updates.append("phone = ?")
            params.append(phone.strip())

        if not updates:
            return AuthService.get_user_by_id(conn, user_id)

        updates.append("updated_at = ?")
        params.append(now)
        params.append(user_id)

        cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?;", params)
        conn.commit()

        if email_changed and user_row["role"] == "CUSTOMER" and clean_email:
            OtpService.generate_and_send_otp(conn, user_id, clean_email, purpose="REGISTRATION")
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

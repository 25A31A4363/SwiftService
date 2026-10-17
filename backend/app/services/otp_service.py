"""
Cryptographic Email Verification OTP Service
Enforces single-use token lifecycle, attempt limits, expiry, rate-limiting, and SMTP delivery.
"""
import sqlite3
import secrets
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import os

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.core.errors import BadRequestError, ConflictError, NotFoundError

class OtpService:
    COOLDOWN_SECONDS = 60
    EXPIRY_MINUTES = 10
    MAX_ATTEMPTS = 5
    MAX_HOURLY_REQUESTS = 6

    @staticmethod
    def _hash_otp(code: str) -> str:
        """Hash OTP code with project secret salt."""
        return hashlib.sha256(f"{code}:{settings.SECRET_KEY}".encode("utf-8")).hexdigest()

    @classmethod
    def generate_and_send_otp(
        cls,
        conn: sqlite3.Connection,
        user_id: str,
        email: str,
        purpose: str = "REGISTRATION"
    ) -> Dict[str, Any]:
        """Generate a cryptographically secure 6-digit OTP, persist hashed, and dispatch via email."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # 1. Check resend cooldown (60 seconds)
        cur = conn.cursor()
        cur.execute("""
            SELECT created_at FROM email_verification_otps
            WHERE email = ? AND purpose = ?
            ORDER BY created_at DESC LIMIT 1
        """, (email, purpose))
        last_otp = cur.fetchone()
        if last_otp:
            last_time = datetime.fromisoformat(last_otp["created_at"])
            elapsed = (now - last_time).total_seconds()
            if elapsed < cls.COOLDOWN_SECONDS:
                wait_time = int(cls.COOLDOWN_SECONDS - elapsed)
                raise ConflictError(f"Please wait {wait_time}s before requesting another verification code.")

        # 2. Check rate limits (max 6 requests per 15 mins)
        cutoff_time = (now - timedelta(minutes=15)).isoformat()
        cur.execute("""
            SELECT COUNT(*) as count FROM email_verification_otps
            WHERE email = ? AND created_at >= ?
        """, (email, cutoff_time))
        recent_count = cur.fetchone()["count"]
        if recent_count >= cls.MAX_HOURLY_REQUESTS:
            raise ConflictError("Too many verification requests. Please wait 15 minutes before requesting a new code.")

        # 3. Generate cryptographic 6-digit numeric OTP
        code = str(secrets.randbelow(900000) + 100000)
        otp_hash = cls._hash_otp(code)
        otp_id = f"otp-{secrets.token_hex(8)}"
        expires_at = (now + timedelta(minutes=cls.EXPIRY_MINUTES)).isoformat()

        # 4. Invalidate older pending OTPs for this email & purpose
        conn.execute("""
            UPDATE email_verification_otps
            SET is_used = 1
            WHERE email = ? AND purpose = ? AND is_used = 0
        """, (email, purpose))

        # 5. Persist new hashed OTP
        conn.execute("""
            INSERT INTO email_verification_otps (
                id, user_id, email, otp_code_hash, purpose, expires_at, attempts, max_attempts, is_used, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, 0, ?)
        """, (otp_id, user_id, email, otp_hash, purpose, expires_at, cls.MAX_ATTEMPTS, now_iso))
        conn.commit()

        # 6. Dispatch Email via SMTP
        smtp_delivery = cls._dispatch_email_smtp(email, code, purpose)

        result: Dict[str, Any] = {
            "otpId": otp_id,
            "email": email,
            "expiresInMinutes": cls.EXPIRY_MINUTES,
            "emailDelivery": smtp_delivery
        }

        # In development / sandbox evaluation mode, expose devOtpCode for automated testing
        if settings.ENVIRONMENT == "development":
            result["devOtpCode"] = code

        logger.info(f"Generated secure OTP for {email} ({purpose}). Status: {smtp_delivery['status']}")
        return result

    @classmethod
    def verify_otp(
        cls,
        conn: sqlite3.Connection,
        email: str,
        code: str,
        purpose: str = "REGISTRATION"
    ) -> bool:
        """Validate submitted OTP against hashed record, check attempts and expiry."""
        now = datetime.now(timezone.utc)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, otp_code_hash, expires_at, attempts, max_attempts
            FROM email_verification_otps
            WHERE email = ? AND purpose = ? AND is_used = 0
            ORDER BY created_at DESC LIMIT 1
        """, (email, purpose))
        otp_record = cur.fetchone()

        if not otp_record:
            raise NotFoundError("No active verification code found for this email. Please request a new code.")

        otp_id = otp_record["id"]
        user_id = otp_record["user_id"]
        stored_hash = otp_record["otp_code_hash"]
        expires_at = datetime.fromisoformat(otp_record["expires_at"])
        attempts = otp_record["attempts"]
        max_attempts = otp_record["max_attempts"]

        # Check expiry
        if now > expires_at:
            conn.execute("UPDATE email_verification_otps SET is_used = 1 WHERE id = ?", (otp_id,))
            conn.commit()
            raise BadRequestError("Verification code has expired. Please request a new code.")

        # Check attempt limits
        if attempts >= max_attempts:
            conn.execute("UPDATE email_verification_otps SET is_used = 1 WHERE id = ?", (otp_id,))
            conn.commit()
            raise BadRequestError("Too many failed attempts. This code is invalidated. Please request a new code.")

        # Verify hash
        submitted_hash = cls._hash_otp(code.strip())
        if not secrets.compare_digest(stored_hash, submitted_hash):
            new_attempts = attempts + 1
            conn.execute("UPDATE email_verification_otps SET attempts = ? WHERE id = ?", (new_attempts, otp_id))
            conn.commit()
            remaining = max_attempts - new_attempts
            if remaining <= 0:
                conn.execute("UPDATE email_verification_otps SET is_used = 1 WHERE id = ?", (otp_id,))
                conn.commit()
                raise BadRequestError("Too many failed attempts. Code invalidated. Please request a new code.")
            raise BadRequestError(f"Incorrect verification code. {remaining} attempt(s) remaining.")

        # Mark OTP used and update user verified status
        conn.execute("UPDATE email_verification_otps SET is_used = 1 WHERE id = ?", (otp_id,))
        conn.execute("UPDATE users SET is_verified = 1, is_active = 1, updated_at = ? WHERE id = ?", (now.isoformat(), user_id))
        conn.commit()

        logger.info(f"Successfully verified email OTP for user {user_id} ({email})")
        return True

    @classmethod
    def _dispatch_email_smtp(cls, recipient_email: str, code: str, purpose: str) -> Dict[str, Any]:
        """Dispatch email using configured SMTP provider or log development notice."""
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM", "support@retailwave.com")

        if not smtp_host or not smtp_user or not smtp_pass:
            logger.warning(
                f"[OTP SERVICE] SMTP provider not configured in environment. "
                f"Generated OTP for {recipient_email} in local sandbox: {code}"
            )
            return {
                "provider": "SMTP",
                "status": "NOT_CONFIGURED",
                "notice": "SMTP environment variables (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD) not provided. Live email delivery requires SMTP credentials. Local evaluation code logged to backend console."
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Your RetailWave Verification Code: {code}"
            msg["From"] = f"RetailWave Support <{smtp_from}>"
            msg["To"] = recipient_email

            text_content = f"Your verification code is: {code}\n\nThis code will expire in 10 minutes.\nIf you did not request this code, please ignore this email."
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <div style="font-size: 22px; font-weight: bold; color: #1e293b; margin-bottom: 8px;">RetailWave Customer Support</div>
                <div style="font-size: 14px; color: #64748b; margin-bottom: 20px;">Email Verification Code</div>
                <div style="background-color: #f1f5f9; padding: 16px; border-radius: 6px; text-align: center; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #4338ca;">{code}</span>
                </div>
                <p style="font-size: 13px; color: #475569; line-height: 1.5;">
                    This single-use code will expire in <strong>10 minutes</strong>. Never share your verification code with anyone.
                </p>
            </div>
            """
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            logger.info(f"Delivered verification email to {recipient_email} via {smtp_host}")
            return {
                "provider": "SMTP",
                "status": "DELIVERED",
                "notice": f"Verification code sent to {recipient_email} via SMTP"
            }
        except Exception as e:
            logger.error(f"Failed to deliver verification email via SMTP: {e}")
            return {
                "provider": "SMTP",
                "status": "FAILED",
                "error": str(e),
                "notice": "SMTP transmission failed. Please verify provider credentials."
            }

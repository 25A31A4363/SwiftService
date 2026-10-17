import hmac
import hashlib
import json
import base64
import time
import os
from typing import Optional, Dict, Any
from backend.app.core.config import settings

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ''
    return base64.urlsafe_b64decode((data + padding).encode('utf-8'))

def hash_password(password: str) -> str:
    """Generate secure salted PBKDF2-HMAC-SHA256 password hash."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2:sha256:100000${salt.hex()}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored PBKDF2 hash."""
    try:
        parts = hashed_password.split('$')
        if len(parts) != 3:
            return False
        meta, salt_hex, key_hex = parts
        _, _, iterations_str = meta.split(':')
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(key, expected_key)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    """Create signed HS256 JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    now = int(time.time())
    if expires_delta_seconds:
        payload["exp"] = now + expires_delta_seconds
    else:
        payload["exp"] = now + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    payload["iat"] = now

    header_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    segments = [
        _base64url_encode(header_bytes),
        _base64url_encode(payload_bytes)
    ]
    signing_input = ".".join(segments).encode('utf-8')
    signature = hmac.new(settings.SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    segments.append(_base64url_encode(signature))
    return ".".join(segments)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify signed HS256 JWT token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = _base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_base64url_decode(payload_b64).decode('utf-8'))
        # Check expiration
        if "exp" in payload and payload["exp"] < int(time.time()):
            return None
        return payload
    except Exception:
        return None

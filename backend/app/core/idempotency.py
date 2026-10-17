"""
R5 Operational Intelligence Platform - Database-Backed Idempotency Engine
Prevents duplicate mutations, double-dispatches, and duplicate feedback creation
when clients retry requests using 'Idempotency-Key' or 'X-Idempotency-Key'.
"""

import json
import hashlib
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple
from fastapi import Request
from backend.app.core.errors import ConflictError


class IdempotencyManager:
    DEFAULT_EXPIRY_HOURS = 24

    @staticmethod
    def get_idempotency_key(request: Request) -> Optional[str]:
        return request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")

    @classmethod
    def compute_request_hash(cls, path: str, method: str, body_bytes: bytes) -> str:
        h = hashlib.sha256()
        h.update(method.upper().encode("utf-8"))
        h.update(b":")
        h.update(path.encode("utf-8"))
        h.update(b":")
        h.update(body_bytes)
        return h.hexdigest()

    @classmethod
    def check_idempotency(
        cls,
        conn: sqlite3.Connection,
        key: str,
        path: str,
        method: str,
        body_bytes: bytes
    ) -> Optional[Tuple[int, Dict[str, str], str]]:
        """
        Check if idempotency key exists in the database.
        Returns:
            (status_code, headers_dict, response_body_str) if already processed.
            None if key is fresh.
        Raises:
            ConflictError if key was used with a different request payload or path.
        """
        req_hash = cls.compute_request_hash(path, method, body_bytes)
        now_iso = datetime.now(timezone.utc).isoformat()

        cur = conn.cursor()
        cur.execute("""
            SELECT request_path, request_params_hash, status_code, response_headers, response_body, expires_at
            FROM idempotency_keys
            WHERE idempotency_key = ?;
        """, (key,))
        row = cur.fetchone()

        if not row:
            return None

        # Check expiration
        if row["expires_at"] and row["expires_at"] < now_iso:
            # Expired entry, allow re-use
            cur.execute("DELETE FROM idempotency_keys WHERE idempotency_key = ?;", (key,))
            conn.commit()
            return None

        # Verify payload consistency
        if row["request_params_hash"] != req_hash or row["request_path"] != path:
            raise ConflictError(
                f"Idempotency conflict: key '{key}' has already been used with a differing payload or path."
            )

        headers = json.loads(row["response_headers"]) if row["response_headers"] else {}
        return int(row["status_code"]), headers, row["response_body"]

    @classmethod
    def record_idempotency(
        cls,
        conn: sqlite3.Connection,
        key: str,
        path: str,
        method: str,
        body_bytes: bytes,
        status_code: int,
        response_body: str,
        headers: Optional[Dict[str, str]] = None,
        expiry_hours: int = DEFAULT_EXPIRY_HOURS
    ) -> None:
        """Store idempotent operation result in database with TTL."""
        req_hash = cls.compute_request_hash(path, method, body_bytes)
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=expiry_hours)).isoformat()
        now_iso = now.isoformat()

        safe_headers = {
            k: v for k, v in (headers or {}).items()
            if k.lower() in ("content-type", "x-request-id", "x-trace-id")
        }

        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO idempotency_keys (
                idempotency_key, request_path, request_params_hash, status_code,
                response_headers, response_body, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            key, path, req_hash, status_code,
            json.dumps(safe_headers), response_body, now_iso, expires_at
        ))
        conn.commit()

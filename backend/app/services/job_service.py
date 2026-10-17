"""
R5 Operational Intelligence Platform - Background Job Service
Provides persistent job queuing, failed-job handling, dead-letter storage,
exponential backoff retries, and asynchronous background worker processing.
"""

import uuid
import json
import sqlite3
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from backend.app.core.logger import logger
from backend.app.core.errors import NotFoundError, ValidationError


class JobService:
    # Handler registry for job types
    _handlers: Dict[str, Callable[[sqlite3.Connection, Dict[str, Any]], Any]] = {}

    @classmethod
    def register_handler(cls, job_type: str, handler: Callable[[sqlite3.Connection, Dict[str, Any]], Any]) -> None:
        cls._handlers[job_type] = handler

    @classmethod
    def enqueue_job(
        cls,
        conn: sqlite3.Connection,
        job_type: str,
        payload: Dict[str, Any],
        max_retries: int = 3,
        backoff_seconds: int = 2,
        delay_seconds: int = 0
    ) -> Dict[str, Any]:
        """Enqueue a background job with scheduled execution timestamp."""
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        scheduled_at = (now + timedelta(seconds=delay_seconds)).isoformat()
        now_iso = now.isoformat()

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO background_jobs (
                id, job_type, payload, status, attempts, max_retries,
                backoff_seconds, last_error, scheduled_at, started_at,
                completed_at, created_at, updated_at
            ) VALUES (?, ?, ?, 'PENDING', 0, ?, ?, NULL, ?, NULL, NULL, ?, ?);
        """, (
            job_id, job_type, json.dumps(payload), max_retries,
            backoff_seconds, scheduled_at, now_iso, now_iso
        ))
        conn.commit()

        logger.info(f"Background job enqueued: id={job_id}, type={job_type}, scheduled_at={scheduled_at}")
        return cls.get_job_by_id(conn, job_id)

    @classmethod
    def get_job_by_id(cls, conn: sqlite3.Connection, job_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM background_jobs WHERE id = ?;
        """, (job_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("BackgroundJob", job_id)
        
        return cls._format_job(row)

    @classmethod
    def process_next_job(cls, conn: sqlite3.Connection, job_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Poll and execute the next available job scheduled for execution (or a specific job by id).
        Applies exponential backoff on failure and marks dead-letter jobs as FAILED.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        cur = conn.cursor()
        # Find next ready job or target specific job
        if job_id:
            cur.execute("SELECT * FROM background_jobs WHERE id = ?;", (job_id,))
        else:
            cur.execute("""
                SELECT * FROM background_jobs
                WHERE status IN ('PENDING', 'RETRYING')
                  AND scheduled_at <= ?
                ORDER BY scheduled_at ASC
                LIMIT 1;
            """, (now_iso,))
        row = cur.fetchone()
        if not row:
            return None

        job_id = row["id"]
        job_type = row["job_type"]
        payload = json.loads(row["payload"]) if row["payload"] else {}
        attempts = row["attempts"] + 1
        max_retries = row["max_retries"]
        backoff_seconds = row["backoff_seconds"]

        # Mark job as RUNNING
        cur.execute("""
            UPDATE background_jobs
            SET status = 'RUNNING', started_at = ?, attempts = ?, updated_at = ?
            WHERE id = ?;
        """, (now_iso, attempts, now_iso, job_id))
        conn.commit()

        handler = cls._handlers.get(job_type)
        try:
            if not handler:
                raise ValueError(f"No registered handler for job type '{job_type}'")

            # Execute job handler
            _result = handler(conn, payload)
            
            # Job succeeded!
            completed_iso = datetime.now(timezone.utc).isoformat()
            cur.execute("""
                UPDATE background_jobs
                SET status = 'COMPLETED', completed_at = ?, updated_at = ?
                WHERE id = ?;
            """, (completed_iso, completed_iso, job_id))
            conn.commit()
            logger.info(f"Background job completed successfully: id={job_id}, type={job_type}")
            return cls.get_job_by_id(conn, job_id)

        except Exception as exc:
            error_msg = str(exc)
            logger.error(f"Background job execution failed: id={job_id}, attempt={attempts}/{max_retries}: {error_msg}")

            if attempts < max_retries:
                # Exponential backoff with jitter: backoff * 2^(attempts-1) + jitter
                delay = int(backoff_seconds * (2 ** (attempts - 1)) + random.uniform(0.5, 2.0))
                next_sched = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
                next_iso = datetime.now(timezone.utc).isoformat()
                cur.execute("""
                    UPDATE background_jobs
                    SET status = 'RETRYING', scheduled_at = ?, last_error = ?, updated_at = ?
                    WHERE id = ?;
                """, (next_sched, error_msg, next_iso, job_id))
                conn.commit()
            else:
                # Max retries exceeded; move to dead-letter FAILED status
                fail_iso = datetime.now(timezone.utc).isoformat()
                cur.execute("""
                    UPDATE background_jobs
                    SET status = 'FAILED', last_error = ?, updated_at = ?
                    WHERE id = ?;
                """, (error_msg, fail_iso, job_id))
                conn.commit()
                logger.error(f"Background job permanently failed (max retries exceeded): id={job_id}, error={error_msg}")

            return cls.get_job_by_id(conn, job_id)

    @classmethod
    def retry_failed_job(cls, conn: sqlite3.Connection, job_id: str) -> Dict[str, Any]:
        """Manually trigger retry of a dead-letter failed job."""
        cur = conn.cursor()
        cur.execute("SELECT id, status FROM background_jobs WHERE id = ?;", (job_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("BackgroundJob", job_id)

        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE background_jobs
            SET status = 'PENDING', attempts = 0, scheduled_at = ?, updated_at = ?
            WHERE id = ?;
        """, (now_iso, now_iso, job_id))
        conn.commit()
        logger.info(f"Background job reset for retry: id={job_id}")
        return cls.get_job_by_id(conn, job_id)

    @classmethod
    def cancel_job(cls, conn: sqlite3.Connection, job_id: str) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("SELECT id, status FROM background_jobs WHERE id = ?;", (job_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("BackgroundJob", job_id)

        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE background_jobs
            SET status = 'CANCELLED', updated_at = ?
            WHERE id = ?;
        """, (now_iso, job_id))
        conn.commit()
        return cls.get_job_by_id(conn, job_id)

    @classmethod
    def list_jobs(
        cls,
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        query = "SELECT * FROM background_jobs WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status.upper())
        if job_type:
            query += " AND job_type = ?"
            params.append(job_type)

        # Count total
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cur.execute(count_query, params)
        total = cur.fetchone()[0]

        # Order and paginate
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, (page - 1) * limit])
        cur.execute(query, params)
        rows = cur.fetchall()

        total_pages = max(1, (total + limit - 1) // limit)
        return {
            "items": [cls._format_job(r) for r in rows],
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages
            }
        }

    @classmethod
    def get_failed_jobs(cls, conn: sqlite3.Connection, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        return cls.list_jobs(conn, status="FAILED", page=page, limit=limit)

    @classmethod
    def get_job_stats(cls, conn: sqlite3.Connection) -> Dict[str, Any]:
        cur = conn.cursor()
        cur.execute("""
            SELECT status, COUNT(*) as cnt FROM background_jobs GROUP BY status;
        """)
        counts = {row["status"]: row["cnt"] for row in cur.fetchall()}
        return {
            "pending": counts.get("PENDING", 0),
            "running": counts.get("RUNNING", 0),
            "retrying": counts.get("RETRYING", 0),
            "completed": counts.get("COMPLETED", 0),
            "failed": counts.get("FAILED", 0),
            "cancelled": counts.get("CANCELLED", 0),
            "total": sum(counts.values())
        }

    @staticmethod
    def _format_job(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "jobType": row["job_type"],
            "payload": json.loads(row["payload"]) if row["payload"] else {},
            "status": row["status"],
            "attempts": row["attempts"],
            "maxRetries": row["max_retries"],
            "backoffSeconds": row["backoff_seconds"],
            "lastError": row["last_error"],
            "scheduledAt": row["scheduled_at"],
            "startedAt": row["started_at"],
            "completedAt": row["completed_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"]
        }


# -----------------------------------------------------------------------------
# Default Operational Background Handlers
# -----------------------------------------------------------------------------
def _handle_feedback_reprocessing(conn: sqlite3.Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Re-analyzes feedback item if initially degraded due to AI downtime."""
    feedback_id = payload.get("feedbackId")
    if not feedback_id:
        raise ValidationError("Missing 'feedbackId' in job payload")

    cur = conn.cursor()
    cur.execute("SELECT raw_text, language_code, normalized_text FROM feedback_items WHERE id = ?;", (feedback_id,))
    row = cur.fetchone()
    if not row:
        raise NotFoundError("FeedbackItem", feedback_id)

    from backend.app.services.ai_understanding_service import AIUnderstandingService
    ai_understanding = AIUnderstandingService.extract_understanding(
        raw_text=row["raw_text"],
        normalized_text=row["normalized_text"],
        language_code=row["language_code"]
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    cur.execute("""
        UPDATE feedback_items
        SET ai_interpretation = ?, processing_status = 'analyzed', processing_error = NULL, updated_at = ?
        WHERE id = ?;
    """, (json.dumps(ai_understanding), now_iso, feedback_id))
    conn.commit()
    return {"reprocessed": True, "feedbackId": feedback_id}


def _handle_retention_purge(conn: sqlite3.Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
    from backend.app.services.retention_service import RetentionService
    org_id = payload.get("organizationId") or "org-apex-01"
    dry_run = bool(payload.get("dryRun", False))
    return RetentionService.execute_purge(conn, organization_id=org_id, dry_run=dry_run)


JobService.register_handler("FEEDBACK_REPROCESSING", _handle_feedback_reprocessing)
JobService.register_handler("DATA_RETENTION_PURGE", _handle_retention_purge)

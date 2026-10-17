import sqlite3
import time
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, Response
from backend.app.db.database import get_db, get_connection
from backend.app.schemas.common import ApiResponse
from backend.app.core.config import settings
from backend.app.core.cache import app_cache
from backend.app.core.error_monitor import error_monitor
from backend.app.services.job_service import JobService
from backend.app.services.ingestion_monitoring_service import IngestionMonitoringService

router = APIRouter(prefix="/health", tags=["System Health & Observability"])
START_TIME = time.time()


@router.get("", response_model=ApiResponse[dict])
def health_check():
    """Basic health check and service metadata."""
    uptime_seconds = round(time.time() - START_TIME, 2)
    return ApiResponse(
        success=True,
        data={
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": "1.0.0-phase1",
            "environment": settings.ENVIRONMENT,
            "uptimeSeconds": uptime_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@router.get("/live", response_model=ApiResponse[dict])
def liveness_probe():
    """
    Kubernetes liveness probe.
    Confirms process event loop and worker thread responsiveness.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)
    return ApiResponse(
        success=True,
        data={
            "status": "alive",
            "process": "operational",
            "uptimeSeconds": uptime_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@router.get("/ready", response_model=ApiResponse[dict])
def readiness_probe(response: Response):
    """
    Kubernetes readiness probe.
    Verifies database connectivity, WAL mode, and filesystem write access.
    Returns HTTP 200 when ready to accept traffic, or HTTP 503 if degraded.
    """
    t0 = time.time()
    db_ok = False
    wal_mode = "unknown"
    db_latency_ms = 0.0
    db_error = None

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        res = cur.fetchone()
        db_ok = res is not None and res[0] == 1

        cur.execute("PRAGMA journal_mode;")
        wal_row = cur.fetchone()
        if wal_row:
            wal_mode = str(wal_row[0]).lower()

        conn.close()
        db_latency_ms = round((time.time() - t0) * 1000, 2)
    except Exception as exc:
        db_ok = False
        db_error = str(exc)

    # Check database directory writable
    db_dir = os.path.dirname(os.path.abspath(str(settings.DATABASE_PATH)))
    dir_writable = os.access(db_dir, os.W_OK)

    is_ready = db_ok and dir_writable

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ApiResponse(
        success=is_ready,
        data={
            "status": "ready" if is_ready else "not_ready",
            "database": {
                "connected": db_ok,
                "latencyMs": db_latency_ms,
                "journalMode": wal_mode,
                "error": db_error
            },
            "filesystem": {
                "writable": dir_writable,
                "dbPath": str(settings.DATABASE_PATH)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@router.get("/db", response_model=ApiResponse[dict])
def db_health_check(conn: sqlite3.Connection = Depends(get_db)):
    """Database connectivity and core table row count verification."""
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    one = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM organizations;")
    org_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM stores;")
    store_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM issues;")
    issue_count = cur.fetchone()[0]

    return ApiResponse(
        success=True,
        data={
            "database": "sqlite",
            "connected": one == 1,
            "counts": {
                "organizations": org_count,
                "stores": store_count,
                "issues": issue_count
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@router.get("/deep", response_model=ApiResponse[dict])
def deep_health_check(conn: sqlite3.Connection = Depends(get_db)):
    """
    Comprehensive diagnostic health and observability inspection:
    - Database latency & counts
    - AI Model Gateway circuit breaker status
    - Background job queue telemetry
    - Ingestion channels status
    - Caching telemetry
    - Real-time error monitoring metrics
    """
    t0 = time.time()
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    cur.fetchone()
    db_latency_ms = round((time.time() - t0) * 1000, 2)

    # Core table counts
    cur.execute("SELECT COUNT(*) FROM feedback_items;")
    fb_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM issues;")
    issue_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM alerts;")
    alert_count = cur.fetchone()[0]

    # Background jobs telemetry
    job_stats = JobService.get_job_stats(conn)

    # Ingestion telemetry
    ingestion_stats = IngestionMonitoringService.get_channel_metrics(conn)

    # Cache telemetry
    cache_stats = app_cache.get_stats()

    # Error monitor telemetry
    err_metrics = error_monitor.get_metrics()

    # AI Circuit breaker status
    from backend.app.services.ai_governance_service import AIModelGateway
    cb_local = AIModelGateway.get_circuit_breaker("LOCAL_DETERMINISTIC").get_status()
    cb_ext = AIModelGateway.get_circuit_breaker("EXTERNAL_ENTERPRISE_LLM").get_status()

    uptime_seconds = round(time.time() - START_TIME, 2)

    return ApiResponse(
        success=True,
        data={
            "status": "healthy" if err_metrics["totalErrors"] == 0 or job_stats["failed"] == 0 else "degraded",
            "uptimeSeconds": uptime_seconds,
            "database": {
                "status": "connected",
                "latencyMs": db_latency_ms,
                "counts": {
                    "feedbackItems": fb_count,
                    "issues": issue_count,
                    "alerts": alert_count
                }
            },
            "aiCircuitBreakers": {
                "localDeterministic": cb_local,
                "externalLLM": cb_ext
            },
            "backgroundJobs": job_stats,
            "ingestionHealth": ingestion_stats["summary"],
            "cache": cache_stats,
            "errorMonitoring": {
                "totalErrors": err_metrics["totalErrors"],
                "recentErrorsCount": err_metrics["recentErrorsCount"]
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

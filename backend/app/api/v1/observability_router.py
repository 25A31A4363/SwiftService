"""
R5 Operational Intelligence Platform - Observability Router
Exposes dedicated observability dashboards and API telemetry for ingestion monitoring,
AI processing logs, circuit breakers, cache statistics, and real-time error telemetry.
"""

import sqlite3
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse, PaginationMeta
from backend.app.core.cache import app_cache
from backend.app.core.error_monitor import error_monitor
from backend.app.services.ingestion_monitoring_service import IngestionMonitoringService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/observability", tags=["System Observability & Monitoring"])


@router.get("/status", response_model=ApiResponse[Dict[str, Any]])
def get_observability_status(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.GOVERNANCE_READ))
):
    """Unified system status across ingestion, background jobs, cache, and error monitors."""
    from backend.app.services.job_service import JobService
    from backend.app.services.ai_governance_service import AIModelGateway

    ingestion = IngestionMonitoringService.get_channel_metrics(conn)
    jobs = JobService.get_job_stats(conn)
    cache = app_cache.get_stats()
    errors = error_monitor.get_metrics()
    circuit_breakers = {
        "LOCAL_DETERMINISTIC": AIModelGateway.get_circuit_breaker("LOCAL_DETERMINISTIC").get_status(),
        "EXTERNAL_ENTERPRISE_LLM": AIModelGateway.get_circuit_breaker("EXTERNAL_ENTERPRISE_LLM").get_status(),
    }

    return ApiResponse(
        success=True,
        data={
            "overallStatus": "OPERATIONAL" if errors["totalErrors"] == 0 and jobs["failed"] == 0 else "OBSERVATION_REQUIRED",
            "ingestion": ingestion["summary"],
            "backgroundJobs": jobs,
            "cache": cache,
            "errors": errors,
            "circuitBreakers": circuit_breakers
        }
    )


@router.get("/ingestion", response_model=ApiResponse[Dict[str, Any]])
def get_ingestion_metrics(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_READ))
):
    """Channel-by-channel ingestion throughput, error rates, duplicates, and health status."""
    metrics = IngestionMonitoringService.get_channel_metrics(conn)
    return ApiResponse(success=True, data=metrics)


@router.get("/ai-logs", response_model=ApiResponse[List[Dict[str, Any]]])
def get_ai_processing_logs(
    status: Optional[str] = Query(None, description="SUCCESS, DEGRADED_FALLBACK, DEGRADED"),
    provider: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.GOVERNANCE_READ))
):
    """
    Paginated query of AI processing logs with confidence, uncertainty,
    latency, token counts, request tracing ID, and degradation status.
    """
    org_id = user.get("organizationId")
    cur = conn.cursor()

    query = """
        SELECT id, organization_id, user_id, provider_name, model_name,
               prompt_hash, pii_redacted, prompt_tokens, output_tokens,
               latency_ms, confidence, uncertainty, uncertainty_reason,
               is_overridden, override_by, override_reason, created_at,
               request_id, status, error_message, task_type
        FROM ai_governance_logs
        WHERE organization_id = ?
    """
    params: List[Any] = [org_id]

    if status:
        query += " AND status = ?"
        params.append(status.upper())
    if provider:
        query += " AND provider_name = ?"
        params.append(provider.upper())

    # Count total
    count_query = query.replace("SELECT id, organization_id, user_id, provider_name, model_name,\n               prompt_hash, pii_redacted, prompt_tokens, output_tokens,\n               latency_ms, confidence, uncertainty, uncertainty_reason,\n               is_overridden, override_by, override_reason, created_at,\n               request_id, status, error_message, task_type", "SELECT COUNT(*)")
    cur.execute(count_query, params)
    total = cur.fetchone()[0]

    # Order and paginate
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?;"
    params.extend([limit, (page - 1) * limit])
    cur.execute(query, params)
    rows = cur.fetchall()

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "organizationId": r["organization_id"],
            "userId": r["user_id"],
            "providerName": r["provider_name"],
            "modelName": r["model_name"],
            "promptHash": r["prompt_hash"],
            "piiRedacted": bool(r["pii_redacted"]),
            "promptTokens": r["prompt_tokens"],
            "outputTokens": r["output_tokens"],
            "latencyMs": r["latency_ms"],
            "confidence": r["confidence"],
            "uncertainty": bool(r["uncertainty"]),
            "uncertaintyReason": r["uncertainty_reason"],
            "isOverridden": bool(r["is_overridden"]),
            "overrideBy": r["override_by"],
            "overrideReason": r["override_reason"],
            "createdAt": r["created_at"],
            "requestId": r["request_id"] if "request_id" in r.keys() else None,
            "status": r["status"] if "status" in r.keys() else "SUCCESS",
            "errorMessage": r["error_message"] if "error_message" in r.keys() else None,
            "taskType": r["task_type"] if "task_type" in r.keys() else "INFERENCE"
        })

    total_pages = max(1, (total + limit - 1) // limit)
    meta = PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages)

    return ApiResponse(success=True, data=results, meta=meta)


@router.get("/errors", response_model=ApiResponse[Dict[str, Any]])
def get_error_metrics(
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_permission(Permission.GOVERNANCE_READ))
):
    """Real-time error monitoring metrics and recent sanitized error events."""
    metrics = error_monitor.get_metrics()
    recent = error_monitor.get_recent_errors(limit=limit)
    return ApiResponse(success=True, data={"metrics": metrics, "recentErrors": recent})


@router.get("/cache", response_model=ApiResponse[Dict[str, Any]])
def get_cache_metrics(
    user: dict = Depends(require_permission(Permission.GOVERNANCE_READ))
):
    """In-memory TTL cache statistics, active entries, and hit ratio."""
    stats = app_cache.get_stats()
    return ApiResponse(success=True, data=stats)

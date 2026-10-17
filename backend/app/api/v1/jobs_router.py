"""
R5 Operational Intelligence Platform - Background Jobs Router
API endpoints for inspecting job queues, dead-letter failed jobs, retrying failed jobs,
and triggering background worker processing.
"""

import sqlite3
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse, PaginationMeta
from backend.app.services.job_service import JobService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/jobs", tags=["Background Processing & Failed Jobs"])


@router.get("", response_model=ApiResponse[List[Dict[str, Any]]])
def list_background_jobs(
    status: Optional[str] = Query(None, description="PENDING, RUNNING, COMPLETED, FAILED, RETRYING, CANCELLED"),
    jobType: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.GOVERNANCE_READ))
):
    """List background jobs with filtering and pagination."""
    res = JobService.list_jobs(conn, status=status, job_type=jobType, page=page, limit=limit)
    meta = PaginationMeta(
        page=res["meta"]["page"],
        limit=res["meta"]["limit"],
        total=res["meta"]["total"],
        totalPages=res["meta"]["totalPages"]
    )
    return ApiResponse(success=True, data=res["items"], meta=meta)


@router.get("/failed", response_model=ApiResponse[List[Dict[str, Any]]])
def get_failed_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.GOVERNANCE_READ))
):
    """Retrieve dead-letter failed jobs that exceeded max retries."""
    res = JobService.get_failed_jobs(conn, page=page, limit=limit)
    meta = PaginationMeta(
        page=res["meta"]["page"],
        limit=res["meta"]["limit"],
        total=res["meta"]["total"],
        totalPages=res["meta"]["totalPages"]
    )
    return ApiResponse(success=True, data=res["items"], meta=meta)


@router.get("/{id}", response_model=ApiResponse[Dict[str, Any]])
def get_job(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.GOVERNANCE_READ))
):
    """Inspect background job details, execution history, and error trace."""
    job = JobService.get_job_by_id(conn, id)
    return ApiResponse(success=True, data=job)


@router.post("/{id}/retry", response_model=ApiResponse[Dict[str, Any]])
def retry_failed_job(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.GOVERNANCE_MANAGE))
):
    """Reset a failed or dead-letter job for immediate re-execution."""
    job = JobService.retry_failed_job(conn, id)
    return ApiResponse(success=True, data=job)


@router.post("/{id}/cancel", response_model=ApiResponse[Dict[str, Any]])
def cancel_job(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.GOVERNANCE_MANAGE))
):
    """Cancel a pending or retrying background job."""
    job = JobService.cancel_job(conn, id)
    return ApiResponse(success=True, data=job)


@router.post("/worker/cycle", response_model=ApiResponse[Optional[Dict[str, Any]]])
def process_next_job_cycle(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.GOVERNANCE_MANAGE))
):
    """
    Trigger one background processing worker cycle.
    Picks up the next eligible scheduled job, applies retries with exponential backoff if failed.
    """
    processed = JobService.process_next_job(conn)
    return ApiResponse(success=True, data=processed)

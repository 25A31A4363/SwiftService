"""
R5 Operational Intelligence Platform - Feedback Router
Phase 3 Implementation: Multichannel Ingestion Endpoints (Single, Bulk JSON, Bulk CSV),
3-Stage Lifecycle Inspection, and Processing Status Management.
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Body, status
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse, PaginationMeta
from backend.app.schemas.domain import (
    FeedbackCreate,
    FeedbackResponse,
    BulkFeedbackCreate,
    BulkFeedbackResponse,
    FeedbackStatusUpdate,
    FeedbackReviewRequest,
    FeedbackUnderstandingResponse,
    FollowUpCreate
)
from backend.app.services.feedback_service import FeedbackService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/feedback", tags=["Operational Feedback Ingestion"])

@router.post("", response_model=ApiResponse[FeedbackResponse], status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """
    Ingest single operational feedback record from any channel:
    Manual Entry, Customer Complaints, Employee Suggestions, Maintenance Reports,
    Survey Responses, or Operational Shift Notes.
    """
    org_id = user.get("organizationId")
    result = FeedbackService.ingest_feedback(conn, org_id, payload, operator_user=user)
    return ApiResponse(success=True, data=result)

@router.post("/bulk", response_model=ApiResponse[BulkFeedbackResponse], status_code=status.HTTP_201_CREATED)
def submit_bulk_feedback_json(
    payload: BulkFeedbackCreate,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """
    Ingest batch of feedback records formatted as JSON array.
    Executes connector normalization, duplicate protection, and AI pipeline hooks for each record.
    """
    org_id = user.get("organizationId")
    result = FeedbackService.ingest_bulk(
        conn,
        org_id,
        payload.items,
        reject_duplicates=bool(payload.rejectDuplicates),
        operator_user=user
    )
    return ApiResponse(success=True, data=result)

@router.post("/bulk/csv", response_model=ApiResponse[BulkFeedbackResponse], status_code=status.HTTP_201_CREATED)
def submit_bulk_feedback_csv(
    csv_text: str = Body(..., media_type="text/plain"),
    storeId: Optional[str] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """
    Ingest batch of operational feedback records uploaded as CSV text.
    Expected CSV columns: rawText (or text/message), storeId, channelType, submitterType, languageCode, privacyClassification.
    """
    org_id = user.get("organizationId")
    target_store = storeId or user.get("storeId")
    result = FeedbackService.ingest_bulk_csv(
        conn,
        org_id,
        csv_text,
        default_store_id=target_store,
        operator_user=user
    )
    return ApiResponse(success=True, data=result)

@router.get("", response_model=ApiResponse[List[FeedbackResponse]])
def get_feedback(
    storeId: Optional[str] = Query(None),
    regionId: Optional[str] = Query(None),
    departmentId: Optional[str] = Query(None),
    channelType: Optional[str] = Query(None),
    processingStatus: Optional[str] = Query(None),
    submitterType: Optional[str] = Query(None),
    languageCode: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_READ))
):
    """
    Query feedback stream with multi-dimensional filtering, channel filtering,
    processing status tracking, text search, and pagination.
    """
    org_id = str(user.get("organizationId", ""))
    if user.get("role") in ("STORE_MANAGER", "MAINTENANCE_TEAM") and user.get("storeId"):
        storeId = user.get("storeId")

    query_res = FeedbackService.get_feedback(
        conn=conn,
        organization_id=org_id,
        store_id=storeId,
        region_id=regionId,
        department_id=departmentId,
        channel_type=channelType,
        processing_status=processingStatus,
        submitter_type=submitterType,
        language_code=languageCode,
        q=q,
        page=page,
        page_size=limit
    )

    meta = PaginationMeta(
        page=query_res["meta"]["page"],
        limit=query_res["meta"]["pageSize"],
        total=query_res["meta"]["totalItems"],
        totalPages=query_res["meta"]["totalPages"]
    )

    return ApiResponse(success=True, data=query_res["items"], meta=meta)

@router.get("/{feedback_id}", response_model=ApiResponse[FeedbackResponse])
def get_feedback_by_id(
    feedback_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_READ))
):
    """
    Inspect single feedback item across all 3 representation tiers:
    Tier 1: Verbatim Raw Input
    Tier 2: Normalized Representation (PII scrubbed & Duplicate Hash)
    Tier 3: AI-Derived Operational Interpretation
    """
    result = FeedbackService.get_feedback_by_id(conn, feedback_id)
    return ApiResponse(success=True, data=result)

@router.patch("/{feedback_id}/status", response_model=ApiResponse[FeedbackResponse])
def update_feedback_status(
    feedback_id: str,
    payload: FeedbackStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """
    Advance processing state (e.g., mark as 'reviewed' or 'failed')
    and update operational lifecycle status with manager review notes.
    """
    result = FeedbackService.update_processing_status(
        conn=conn,
        feedback_id=feedback_id,
        status_update=payload,
        operator_user=user
    )
    return ApiResponse(success=True, data=result)

@router.get("/{feedback_id}/understanding", response_model=ApiResponse[FeedbackUnderstandingResponse])
def get_feedback_understanding(
    feedback_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_READ))
):
    """
    Phase 4: Inspect complete grounded AI extraction breakdown.
    Strictly separates:
    - Deterministic system facts
    - AI-derived facts (with confidence, evidence spans, and uncertainty)
    - Human operator overrides
    - Effective merged interpretation
    """
    result = FeedbackService.get_feedback_understanding(conn, feedback_id)
    return ApiResponse(success=True, data=result)

@router.post("/{feedback_id}/review", response_model=ApiResponse[FeedbackResponse])
def review_and_override_feedback(
    feedback_id: str,
    payload: FeedbackReviewRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """
    Phase 4: Submit authorized human review and field corrections/overrides.
    Does not overwrite raw text or AI facts; stores overrides with reviewer identity,
    timestamp, and audit trail.
    """
    result = FeedbackService.submit_human_review_and_overrides(
        conn=conn,
        feedback_id=feedback_id,
        review_request=payload,
        operator_user=user
    )
    return ApiResponse(success=True, data=result)

@router.post("/{feedback_id}/analyze", response_model=ApiResponse[FeedbackResponse])
def reanalyze_feedback(
    feedback_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """
    Phase 4: Trigger fresh grounded AI Understanding extraction on a feedback record.
    """
    result = FeedbackService.reanalyze_feedback(
        conn=conn,
        feedback_id=feedback_id,
        operator_user=user
    )
    return ApiResponse(success=True, data=result)

@router.post("/follow-up", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
def record_follow_up(
    payload: FollowUpCreate,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """Record conversational follow-up turns for ambiguous feedback."""
    result = FeedbackService.record_follow_up(conn, payload)
    return ApiResponse(success=True, data=result)


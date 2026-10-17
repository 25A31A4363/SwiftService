import sqlite3
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends

from backend.app.db.database import get_db
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission
from backend.app.schemas.domain import (
    InvestigationSummaryResponse,
    QuestionAnswerRequest,
    AddCustomQuestionRequest,
    DismissQuestionRequest
)
from backend.app.services.investigation_service import InvestigationService

router = APIRouter(prefix="/investigation", tags=["Phase 5: Dynamic Investigation & Follow-Up"])

@router.get("/feedback/{feedback_id}", response_model=InvestigationSummaryResponse)
def get_feedback_investigation(
    feedback_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.FEEDBACK_READ))
):
    """Retrieve dynamic follow-up questions, missing fields, and enrichment status."""
    return InvestigationService.get_investigation_summary(conn, feedback_id)

@router.post("/questions/{question_id}/answer", response_model=InvestigationSummaryResponse)
def answer_investigation_question(
    question_id: str,
    payload: QuestionAnswerRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """
    Capture response to an investigation question.
    Automatically enriches canonical feedback text and triggers grounded re-analysis.
    """
    return InvestigationService.record_answer(
        conn=conn,
        question_id=question_id,
        answer=payload.answer,
        user_id=user["id"]
    )

@router.post("/feedback/{feedback_id}/custom-question", response_model=InvestigationSummaryResponse)
def add_custom_investigation_question(
    feedback_id: str,
    payload: AddCustomQuestionRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """Authorized operator adds a targeted clarification question."""
    return InvestigationService.add_custom_question(
        conn=conn,
        feedback_id=feedback_id,
        question_text=payload.questionText,
        reason=payload.reason or "Operator requested operational details",
        question_type=payload.questionType or "text",
        options=payload.options,
        user_id=user["id"]
    )

@router.post("/questions/{question_id}/dismiss", response_model=InvestigationSummaryResponse)
def dismiss_investigation_question(
    question_id: str,
    payload: Optional[DismissQuestionRequest] = None,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """Dismiss an unnecessary or redundant question."""
    reason = payload.reason if payload else "Dismissed by operator"
    return InvestigationService.dismiss_question(
        conn=conn,
        question_id=question_id,
        reason=reason,
        user_id=user["id"]
    )

@router.post("/feedback/{feedback_id}/enrich-reanalyze", response_model=InvestigationSummaryResponse)
def trigger_enrichment_and_reanalyze(
    feedback_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(require_permission(Permission.FEEDBACK_SUBMIT))
):
    """Force re-assembly of answered clarification questions into enriched text and re-extract."""
    return InvestigationService.enrich_and_reanalyze(
        conn=conn,
        feedback_id=feedback_id,
        user_id=user["id"]
    )

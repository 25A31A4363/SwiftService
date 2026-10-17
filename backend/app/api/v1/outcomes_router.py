import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query

from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import (
    OutcomeMeasurementResponse,
    OutcomeEvaluationRequest,
    OutcomeDashboardSummary,
    BaselineSnapshot,
)
from backend.app.services.outcome_service import OutcomeService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/outcomes", tags=["Phase 12: Post-Intervention Outcome Measurement"])


@router.get("/dashboard", response_model=ApiResponse[OutcomeDashboardSummary])
def get_outcomes_dashboard(
    storeId: Optional[str] = Query(None, description="Optional store filter"),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.RESOLUTION_READ))
):
    """Retrieve operational outcome dashboard metrics, KPIs, and recent measured issues."""
    org_id = user.get("organizationId", "org-apex-01")
    # Store-scoped user constraint
    if user.get("storeId"):
        storeId = user["storeId"]

    summary = OutcomeService.get_outcomes_dashboard_summary(conn, org_id, store_id=storeId)
    return ApiResponse(success=True, data=summary)


@router.get("", response_model=ApiResponse[List[OutcomeMeasurementResponse]])
def list_outcomes(
    storeId: Optional[str] = Query(None, description="Optional store filter"),
    outcomeStatus: Optional[str] = Query(None, description="Filter by outcome state (Improved, No significant change, Worsened, Inconclusive)"),
    limit: int = Query(100, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.RESOLUTION_READ))
):
    """List historical and evaluated outcome measurements with deterministic evidence."""
    org_id = user.get("organizationId", "org-apex-01")
    if user.get("storeId"):
        storeId = user["storeId"]

    results = OutcomeService.list_outcomes(
        conn,
        org_id,
        store_id=storeId,
        outcome_status=outcomeStatus,
        limit=limit
    )
    return ApiResponse(success=True, data=results)


@router.get("/issues/{issueId}", response_model=ApiResponse[OutcomeMeasurementResponse])
def get_issue_outcome(
    issueId: str = Path(..., description="Unique issue identifier"),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.RESOLUTION_READ))
):
    """Get the latest deterministic outcome measurement for a specific issue."""
    result = OutcomeService.get_issue_outcome(conn, issueId)
    if not result:
        # Evaluate on-demand
        result = OutcomeService.evaluate_issue_outcome(conn, issueId, actor_user_id=user.get("id"))
    return ApiResponse(success=True, data=result)


@router.post("/issues/{issueId}/evaluate", response_model=ApiResponse[OutcomeMeasurementResponse])
def evaluate_issue_outcome(
    issueId: str = Path(..., description="Unique issue identifier"),
    payload: Optional[OutcomeEvaluationRequest] = None,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.RESOLUTION_VERIFY))
):
    """
    Execute or re-evaluate deterministic outcome measurement for a resolved issue.
    Compares baseline snapshot (BEFORE) against observation window (AFTER).
    Guards against fabricated improvements: returns 'outcome cannot yet be determined.' if data is insufficient.
    """
    obs_hours = payload.observationHours if payload else None
    min_hours = payload.minObservationHours if payload else None
    force = bool(payload.forceReevaluate) if payload and payload.forceReevaluate is not None else False

    result = OutcomeService.evaluate_issue_outcome(
        conn=conn,
        issue_id=issueId,
        observation_hours=obs_hours,
        min_observation_hours=min_hours,
        force_reevaluate=force,
        actor_user_id=user.get("id")
    )
    return ApiResponse(success=True, data=result)


@router.post("/issues/{issueId}/baseline", response_model=ApiResponse[BaselineSnapshot])
def capture_baseline_snapshot(
    issueId: str = Path(..., description="Unique issue identifier"),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.RESOLUTION_VERIFY))
):
    """Capture pre-intervention operational baseline snapshot for an issue."""
    snapshot = OutcomeService.record_baseline_snapshot(conn, issueId)
    return ApiResponse(success=True, data=snapshot)

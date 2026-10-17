import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import (
    ActionPlanResponse, ActionApprovalUpdate, ActionOverrideUpdate
)
from backend.app.services.action_service import ActionService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/actions", tags=["Operational Actions & Work Orders"])

@router.get("", response_model=ApiResponse[List[ActionPlanResponse]])
def get_actions(
    issueId: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ACTION_READ))
):
    org_id = str(user.get("organizationId", ""))
    data = ActionService.get_actions(conn, org_id, issueId, limit)
    return ApiResponse(success=True, data=data)

@router.post("/{id}/approve", response_model=ApiResponse[ActionPlanResponse])
def approve_action(
    payload: ActionApprovalUpdate,
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ACTION_APPROVE))
):
    result = ActionService.approve_action(conn, id, payload, user_id=str(user.get("id", "")))
    return ApiResponse(success=True, data=result)

@router.post("/{id}/override", response_model=ApiResponse[ActionPlanResponse])
def override_action_routing(
    payload: ActionOverrideUpdate,
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ACTION_OVERRIDE))
):
    result = ActionService.override_routing(conn, id, payload, user_id=str(user.get("id", "")))
    return ApiResponse(success=True, data=result)

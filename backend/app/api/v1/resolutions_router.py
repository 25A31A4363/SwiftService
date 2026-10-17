import sqlite3
from typing import List
from fastapi import APIRouter, Depends, Path, status
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import ResolutionCreate, ResolutionResponse
from backend.app.services.resolution_service import ResolutionService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/resolutions", tags=["Resolutions & Verification"])

@router.post("", response_model=ApiResponse[ResolutionResponse], status_code=status.HTTP_201_CREATED)
def create_resolution(
    payload: ResolutionCreate,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.RESOLUTION_CREATE))
):
    result = ResolutionService.create_resolution(conn, payload, user_id=str(user.get("id", "")))
    return ApiResponse(success=True, data=result)

@router.get("/issue/{issueId}", response_model=ApiResponse[List[ResolutionResponse]])
def get_issue_resolutions(
    issueId: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.RESOLUTION_READ))
):
    data = ResolutionService.get_resolutions_for_issue(conn, issueId)
    return ApiResponse(success=True, data=data)

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse, PaginationMeta
from backend.app.schemas.auth import UserResponse, UserCreate, UserUpdate
from backend.app.services.user_service import UserService
from backend.app.api.deps import require_permission, get_current_user
from backend.app.core.rbac import Permission, has_permission
from backend.app.core.errors import ForbiddenError

router = APIRouter(prefix="/users", tags=["User Directory & Access Management"])

@router.get("", response_model=ApiResponse[List[UserResponse]])
def get_users(
    regionId: Optional[str] = Query(None),
    storeId: Optional[str] = Query(None),
    teamId: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.USER_READ))
):
    org_id = str(user.get("organizationId", ""))
    items, total = UserService.get_users(
        conn,
        organization_id=org_id,
        region_id=regionId,
        store_id=storeId,
        team_id=teamId,
        role=role,
        is_active=isActive,
        q=q,
        page=page,
        limit=limit
    )
    total_pages = max(1, (total + limit - 1) // limit)
    return ApiResponse(
        success=True,
        data=items,
        meta=PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages)
    )

@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
def get_user(
    user_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.USER_READ))
):
    data = UserService.get_user(conn, user_id)
    return ApiResponse(success=True, data=data)

@router.post("", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.USER_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = UserService.create_user(conn, payload, current_user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.put("/{user_id}", response_model=ApiResponse[UserResponse])
def update_user(
    user_id: str,
    payload: UserUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    is_self = user["id"] == user_id
    has_manage = has_permission(user["role"], Permission.USER_MANAGE)

    if not is_self and not has_manage:
        raise ForbiddenError("Permission 'USER_MANAGE' required to update other user accounts")

    # If updating self and not admin, reject attempts to escalate role or change structural assignment
    if is_self and not has_manage:
        if payload.role is not None and payload.role != user["role"]:
            raise ForbiddenError("Forbidden: Cannot modify role without USER_MANAGE permission")
        if payload.isActive is not None or payload.storeId is not None or payload.regionId is not None:
            raise ForbiddenError("Forbidden: Cannot modify organization assignments without USER_MANAGE permission")
        payload.role = None
        payload.isActive = None
        payload.storeId = None
        payload.regionId = None
        payload.teamId = None

    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = UserService.update_user(conn, user_id, payload, current_user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.delete("/{user_id}", response_model=ApiResponse[dict])
def delete_user(
    user_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.USER_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    UserService.delete_user(conn, user_id, current_user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data={"message": f"User account '{user_id}' removed successfully."})

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, Request, status
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import (
    RoleResponse, RoleCreate, RolePermissionsUpdate, RolePermissionsMatrixResponse
)
from backend.app.services.role_service import RoleService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/roles", tags=["Role Governance & Permissions Matrix"])

@router.get("", response_model=ApiResponse[List[RoleResponse]])
def get_roles(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.USER_READ))
):
    roles = RoleService.get_roles(conn)
    return ApiResponse(success=True, data=roles)

@router.get("/permissions-matrix", response_model=ApiResponse[RolePermissionsMatrixResponse])
def get_permissions_matrix(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.USER_READ))
):
    matrix = RoleService.get_permissions_matrix(conn)
    return ApiResponse(success=True, data=matrix)

@router.post("", response_model=ApiResponse[RoleResponse], status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ORG_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = RoleService.create_role(
        conn,
        name=payload.name,
        description=payload.description,
        permissions=payload.permissions,
        user_id=user["id"],
        organization_id=user.get("organizationId"),
        ip=ip,
        ua=ua
    )
    return ApiResponse(success=True, data=data)

@router.put("/{role_id}/permissions", response_model=ApiResponse[RoleResponse])
def update_role_permissions(
    role_id: str,
    payload: RolePermissionsUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ORG_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = RoleService.update_role_permissions(
        conn,
        role_id=role_id,
        permissions=payload.permissions,
        user_id=user["id"],
        organization_id=user.get("organizationId"),
        ip=ip,
        ua=ua
    )
    return ApiResponse(success=True, data=data)

@router.delete("/{role_id}", response_model=ApiResponse[dict])
def delete_role(
    role_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ORG_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    RoleService.delete_role(
        conn,
        role_id=role_id,
        user_id=user["id"],
        organization_id=user.get("organizationId"),
        ip=ip,
        ua=ua
    )
    return ApiResponse(success=True, data={"message": f"Role '{role_id}' removed successfully."})

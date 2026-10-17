import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse, PaginationMeta
from backend.app.schemas.domain import (
    OperationalOwnershipMappingResponse,
    OperationalOwnershipMappingCreate,
    OperationalOwnershipMappingUpdate
)
from backend.app.services.hierarchy_service import HierarchyService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/ownership-mappings", tags=["Operational Ownership & Escalation Matrix"])

@router.get("", response_model=ApiResponse[List[OperationalOwnershipMappingResponse]])
def get_ownership_mappings(
    storeId: Optional[str] = Query(None),
    regionId: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_READ))
):
    org_id = str(user.get("organizationId", ""))
    items, total = HierarchyService.get_ownership_mappings(
        conn,
        organization_id=org_id,
        store_id=storeId,
        region_id=regionId,
        domain=domain,
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

@router.get("/{mapping_id}", response_model=ApiResponse[OperationalOwnershipMappingResponse])
def get_ownership_mapping(
    mapping_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_READ))
):
    data = HierarchyService.get_ownership_mapping(conn, mapping_id)
    return ApiResponse(success=True, data=data)

@router.post("", response_model=ApiResponse[OperationalOwnershipMappingResponse], status_code=status.HTTP_201_CREATED)
def create_ownership_mapping(
    payload: OperationalOwnershipMappingCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.create_ownership_mapping(conn, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.put("/{mapping_id}", response_model=ApiResponse[OperationalOwnershipMappingResponse])
def update_ownership_mapping(
    mapping_id: str,
    payload: OperationalOwnershipMappingUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.update_ownership_mapping(conn, mapping_id, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.delete("/{mapping_id}", response_model=ApiResponse[dict])
def delete_ownership_mapping(
    mapping_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    HierarchyService.delete_ownership_mapping(conn, mapping_id, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data={"message": f"Ownership mapping '{mapping_id}' deleted successfully."})

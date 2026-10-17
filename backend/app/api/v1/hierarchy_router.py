import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse, PaginationMeta
from backend.app.schemas.domain import (
    OrganizationResponse, OrganizationCreate, OrganizationUpdate,
    RegionResponse, RegionCreate, RegionUpdate,
    StoreResponse, StoreCreate, StoreUpdate, StoreStatusUpdate,
    DepartmentResponse, AssetResponse,
    OperationalTeamResponse, OperationalTeamCreate, OperationalTeamUpdate,
    TeamMemberResponse, TeamMemberCreate,
    OperationalTraceResponse
)
from backend.app.services.hierarchy_service import HierarchyService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(tags=["Enterprise Hierarchy"])

# =============================================================================
# Organizations
# =============================================================================
@router.get("/organizations", response_model=ApiResponse[List[OrganizationResponse]])
def get_organizations(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ORG_READ))
):
    items, total = HierarchyService.get_organizations(conn, q, status, page, limit)
    total_pages = max(1, (total + limit - 1) // limit)
    return ApiResponse(
        success=True,
        data=items,
        meta=PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages)
    )

@router.get("/organizations/{org_id}", response_model=ApiResponse[OrganizationResponse])
def get_organization(
    org_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ORG_READ))
):
    org = HierarchyService.get_organization(conn, org_id)
    return ApiResponse(success=True, data=org)

@router.post("/organizations", response_model=ApiResponse[OrganizationResponse], status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ORG_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.create_organization(conn, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.put("/organizations/{org_id}", response_model=ApiResponse[OrganizationResponse])
def update_organization(
    org_id: str,
    payload: OrganizationUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ORG_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.update_organization(conn, org_id, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.delete("/organizations/{org_id}", response_model=ApiResponse[dict])
def delete_organization(
    org_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ORG_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    HierarchyService.delete_organization(conn, org_id, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data={"message": f"Organization '{org_id}' removed successfully."})

# =============================================================================
# Regions
# =============================================================================
@router.get("/regions", response_model=ApiResponse[List[RegionResponse]])
def get_regions(
    organizationId: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.REGION_READ))
):
    org_id = str(organizationId or user.get("organizationId", ""))
    items, total = HierarchyService.get_regions(conn, org_id, q, page, limit)
    total_pages = max(1, (total + limit - 1) // limit)
    return ApiResponse(
        success=True,
        data=items,
        meta=PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages)
    )

@router.get("/regions/{reg_id}", response_model=ApiResponse[RegionResponse])
def get_region(
    reg_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.REGION_READ))
):
    data = HierarchyService.get_region(conn, reg_id)
    return ApiResponse(success=True, data=data)

@router.post("/regions", response_model=ApiResponse[RegionResponse], status_code=status.HTTP_201_CREATED)
def create_region(
    payload: RegionCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.REGION_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.create_region(conn, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.put("/regions/{reg_id}", response_model=ApiResponse[RegionResponse])
def update_region(
    reg_id: str,
    payload: RegionUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.REGION_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.update_region(conn, reg_id, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.delete("/regions/{reg_id}", response_model=ApiResponse[dict])
def delete_region(
    reg_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.REGION_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    HierarchyService.delete_region(conn, reg_id, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data={"message": f"Region '{reg_id}' removed successfully."})

# =============================================================================
# Stores
# =============================================================================
@router.get("/stores", response_model=ApiResponse[List[StoreResponse]])
def get_stores(
    organizationId: Optional[str] = Query(None),
    regionId: Optional[str] = Query(None),
    operatingStatus: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_READ))
):
    org_id = str(organizationId or user.get("organizationId", ""))

    # If regional manager, constrain to user region
    if user.get("role") == "REGIONAL_MANAGER" and user.get("regionId"):
        regionId = user.get("regionId")

    items, total = HierarchyService.get_stores(conn, org_id, regionId, operatingStatus, q, page, limit)

    # If store manager or tech, constrain to their store
    if user.get("role") in ("STORE_MANAGER", "MAINTENANCE_TEAM") and user.get("storeId"):
        items = [s for s in items if s["id"] == user["storeId"]]
        total = len(items)

    total_pages = max(1, (total + limit - 1) // limit)
    return ApiResponse(
        success=True,
        data=items,
        meta=PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages)
    )

@router.get("/stores/{store_id}", response_model=ApiResponse[StoreResponse])
def get_store(
    store_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_READ))
):
    data = HierarchyService.get_store(conn, store_id)
    return ApiResponse(success=True, data=data)

@router.post("/stores", response_model=ApiResponse[StoreResponse], status_code=status.HTTP_201_CREATED)
def create_store(
    payload: StoreCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.create_store(conn, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.put("/stores/{store_id}", response_model=ApiResponse[StoreResponse])
def update_store(
    store_id: str,
    payload: StoreUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.update_store(conn, store_id, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.patch("/stores/{store_id}/status", response_model=ApiResponse[StoreResponse])
def update_store_status(
    store_id: str,
    payload: StoreStatusUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.update_store_status(
        conn,
        store_id,
        payload.operatingStatus,
        payload.justification,
        user_id=user["id"],
        ip=ip,
        ua=ua
    )
    return ApiResponse(success=True, data=data)

@router.delete("/stores/{store_id}", response_model=ApiResponse[dict])
def delete_store(
    store_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    HierarchyService.delete_store(conn, store_id, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data={"message": f"Store '{store_id}' deleted successfully."})

# =============================================================================
# Teams & Members
# =============================================================================
@router.get("/teams", response_model=ApiResponse[List[OperationalTeamResponse]])
def get_teams(
    storeId: Optional[str] = Query(None),
    regionId: Optional[str] = Query(None),
    specialization: Optional[str] = Query(None),
    teamType: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.TEAM_READ))
):
    org_id = str(user.get("organizationId", ""))
    items, total = HierarchyService.get_teams(conn, org_id, storeId, regionId, specialization, teamType, q, page, limit)
    total_pages = max(1, (total + limit - 1) // limit)
    return ApiResponse(
        success=True,
        data=items,
        meta=PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages)
    )

@router.get("/teams/{team_id}", response_model=ApiResponse[OperationalTeamResponse])
def get_team(
    team_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.TEAM_READ))
):
    data = HierarchyService.get_team(conn, team_id)
    return ApiResponse(success=True, data=data)

@router.post("/teams", response_model=ApiResponse[OperationalTeamResponse], status_code=status.HTTP_201_CREATED)
def create_team(
    payload: OperationalTeamCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.TEAM_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.create_team(conn, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.put("/teams/{team_id}", response_model=ApiResponse[OperationalTeamResponse])
def update_team(
    team_id: str,
    payload: OperationalTeamUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.TEAM_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.update_team(conn, team_id, payload, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data=data)

@router.delete("/teams/{team_id}", response_model=ApiResponse[dict])
def delete_team(
    team_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.TEAM_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    HierarchyService.delete_team(conn, team_id, user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data={"message": f"Team '{team_id}' deleted successfully."})

@router.get("/teams/{team_id}/members", response_model=ApiResponse[List[TeamMemberResponse]])
def get_team_members(
    team_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.TEAM_READ))
):
    data = HierarchyService.get_team_members(conn, team_id)
    return ApiResponse(success=True, data=data)

@router.post("/teams/{team_id}/members", response_model=ApiResponse[TeamMemberResponse], status_code=status.HTTP_201_CREATED)
def add_team_member(
    team_id: str,
    payload: TeamMemberCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.TEAM_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    data = HierarchyService.add_team_member(
        conn,
        team_id,
        payload.userId,
        payload.roleInTeam or "MEMBER",
        payload.isPrimary if payload.isPrimary is not None else True,
        current_user_id=user["id"],
        ip=ip,
        ua=ua
    )
    return ApiResponse(success=True, data=data)

@router.delete("/teams/{team_id}/members/{user_id}", response_model=ApiResponse[dict])
def remove_team_member(
    team_id: str,
    user_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.TEAM_MANAGE))
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    HierarchyService.remove_team_member(conn, team_id, user_id, current_user_id=user["id"], ip=ip, ua=ua)
    return ApiResponse(success=True, data={"message": f"User '{user_id}' removed from team '{team_id}'."})

# =============================================================================
# Lineage & Operational Tracing
# =============================================================================
@router.get("/hierarchy/trace", response_model=ApiResponse[OperationalTraceResponse])
def trace_operational_lineage(
    storeId: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    entityType: Optional[str] = Query(None),
    entityId: Optional[str] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ORG_READ))
):
    org_id = str(user.get("organizationId", ""))
    trace = HierarchyService.trace_operational_object(
        conn,
        org_id,
        store_id=storeId,
        operational_domain=domain,
        entity_type=entityType,
        entity_id=entityId
    )
    return ApiResponse(success=True, data=trace)

# =============================================================================
# Legacy/Existing Store Departments and Assets
# =============================================================================
@router.get("/departments", response_model=ApiResponse[List[DepartmentResponse]])
def get_departments(
    storeId: str = Query(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_READ))
):
    data = HierarchyService.get_departments(conn, storeId)
    return ApiResponse(success=True, data=data)

@router.get("/assets", response_model=ApiResponse[List[AssetResponse]])
def get_assets(
    storeId: str = Query(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.STORE_READ))
):
    data = HierarchyService.get_assets(conn, storeId)
    return ApiResponse(success=True, data=data)

import os
import uuid
import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Request, UploadFile, File, Query, HTTPException

from backend.app.db.database import get_db
from backend.app.core.errors import BadRequestError, NotFoundError, ForbiddenError
from backend.app.core.rbac import Permission, Role
from backend.app.api.deps import get_current_user, require_permission
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.complaints import (
    ComplaintCreate,
    ComplaintStatusUpdate,
    ComplaintResponse,
    ComplaintPublicTracking
)
from backend.app.services.complaints_service import ComplaintsService

router = APIRouter(prefix="/complaints", tags=["Customer Complaints"])

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

@router.post("", response_model=ApiResponse[ComplaintResponse])
def submit_complaint(
    payload: ComplaintCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.COMPLAINT_SUBMIT))
):
    """Customer submits a retail complaint, ingested into unified R5 operations."""
    ip = request.client.host if request.client else None
    try:
        complaint = ComplaintsService.create_complaint(
            conn=conn,
            customer_id=current_user["id"],
            data=payload,
            ip_address=ip
        )
        return ApiResponse(success=True, data=complaint)
    except ValueError as ve:
        raise BadRequestError(str(ve))

@router.get("/my", response_model=ApiResponse[List[ComplaintResponse]])
def get_my_complaints(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.COMPLAINT_READ))
):
    """Authenticated customer retrieves all their submitted complaints."""
    complaints = ComplaintsService.get_customer_complaints(conn, customer_id=current_user["id"])
    return ApiResponse(success=True, data=complaints)

@router.get("/track/{reference_number}", response_model=ApiResponse[ComplaintPublicTracking])
def track_complaint(
    reference_number: str,
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Public tracking by unique complaint reference number (REF-2026-XXXXX).
    Customer privacy is strictly protected: personal email, phone, and internal notes are omitted.
    """
    tracking_data = ComplaintsService.track_by_reference(conn, reference_number=reference_number)
    if not tracking_data:
        raise NotFoundError("Complaint", reference_number)
    return ApiResponse(success=True, data=tracking_data)

@router.get("", response_model=ApiResponse[Dict[str, Any]])
def list_complaints_for_staff(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    storeId: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.COMPLAINT_MANAGE))
):
    """Authorized R5 operations staff view and filter all incoming retail complaints."""
    data = ComplaintsService.get_all_complaints_for_staff(
        conn=conn,
        status=status,
        category=category,
        search=search,
        store_id=storeId,
        limit=limit,
        offset=offset
    )
    return ApiResponse(success=True, data=data)

@router.get("/{complaint_id}", response_model=ApiResponse[ComplaintResponse])
def get_complaint_details(
    complaint_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.COMPLAINT_READ))
):
    """
    View complaint details with RBAC isolation:
    Customers can only access their own complaints; authorized staff can access all.
    """
    try:
        complaint = ComplaintsService.get_complaint_by_id(
            conn=conn,
            complaint_id=complaint_id,
            requesting_user_id=current_user["id"],
            requesting_role=current_user["role"]
        )
        if not complaint:
            raise NotFoundError("Complaint", complaint_id)
        return ApiResponse(success=True, data=complaint)
    except PermissionError as pe:
        raise ForbiddenError(str(pe))

@router.patch("/{complaint_id}/status", response_model=ApiResponse[ComplaintResponse])
def update_complaint_status(
    complaint_id: str,
    payload: ComplaintStatusUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.COMPLAINT_MANAGE))
):
    """Authorized R5 staff updates complaint status, assigns teams, records notes, and provides resolution summary."""
    ip = request.client.host if request.client else None
    staff_name = current_user.get("fullName") or current_user.get("email") or "Operations Staff"
    try:
        updated = ComplaintsService.update_complaint_status(
            conn=conn,
            complaint_id=complaint_id,
            update=payload,
            staff_user_id=current_user["id"],
            staff_name=staff_name,
            ip_address=ip
        )
        return ApiResponse(success=True, data=updated)
    except ValueError as ve:
        raise BadRequestError(str(ve))

@router.post("/upload", response_model=ApiResponse[Dict[str, str]])
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_permission(Permission.COMPLAINT_SUBMIT))
):
    """Secure attachment upload for complaint evidence (images and PDF)."""
    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequestError(f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Read contents with size check
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise BadRequestError(f"File exceeds maximum allowed size of 10 MB ({len(contents)} bytes).")

    # Generate safe random filename
    safe_name = f"cmp_{uuid.uuid4().hex[:12]}{ext}"
    upload_dir = os.path.join("frontend", "static", "uploads", "complaints")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    relative_url = f"/static/uploads/complaints/{safe_name}"
    return ApiResponse(
        success=True,
        data={
            "url": relative_url,
            "filename": file.filename or safe_name
        }
    )

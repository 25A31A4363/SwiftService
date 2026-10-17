from fastapi import APIRouter, Depends, Request
from backend.app.db.database import get_db
from backend.app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserResponse,
    ProfileUpdateRequest,
    ChangePasswordRequest
)
from backend.app.schemas.common import ApiResponse
from backend.app.services.auth_service import AuthService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=ApiResponse[LoginResponse])
def login(payload: LoginRequest, conn: sqlite3.Connection = Depends(get_db)):
    result = AuthService.authenticate_user(conn, payload.email, payload.password)
    return ApiResponse(success=True, data=result)

@router.get("/me", response_model=ApiResponse[UserResponse])
def get_me(current_user: dict = Depends(get_current_user)):
    return ApiResponse(success=True, data=current_user)

@router.put("/me", response_model=ApiResponse[UserResponse])
@router.put("/profile", response_model=ApiResponse[UserResponse])
def update_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    updated_user = AuthService.update_profile(
        conn=conn,
        user_id=current_user["id"],
        full_name=payload.fullName,
        email=payload.email,
        ip=ip,
        ua=ua
    )
    return ApiResponse(success=True, data=updated_user)

@router.post("/change-password", response_model=ApiResponse[dict])
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    res = AuthService.change_password(
        conn=conn,
        user_id=current_user["id"],
        current_password=payload.currentPassword,
        new_password=payload.newPassword,
        ip=ip,
        ua=ua
    )
    return ApiResponse(success=True, data=res)

@router.post("/logout", response_model=ApiResponse[dict])
def logout(current_user: dict = Depends(get_current_user)):
    # Stateless JWT logout acknowledged
    return ApiResponse(success=True, data={"message": "Logged out successfully."})

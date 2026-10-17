import sqlite3
from fastapi import APIRouter, Depends
from backend.app.db.database import get_db
from backend.app.schemas.auth import LoginRequest, LoginResponse, UserResponse
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

@router.post("/logout", response_model=ApiResponse[dict])
def logout(current_user: dict = Depends(get_current_user)):
    # Stateless JWT logout acknowledged
    return ApiResponse(success=True, data={"message": "Logged out successfully."})

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, status
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.personal_home import (
    PersonalApplianceCreate, PersonalApplianceResponse,
    PersonalTicketCreate, PersonalTicketResponse
)
from backend.app.services.personal_home_service import PersonalHomeService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/personal-home", tags=["Personal / Home Mode (Segregated Scope)"])

@router.post("/appliances", response_model=ApiResponse[PersonalApplianceResponse], status_code=status.HTTP_201_CREATED)
def register_appliance(
    payload: PersonalApplianceCreate,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    result = PersonalHomeService.register_appliance(conn, str(user.get("id", "")), payload)
    return ApiResponse(success=True, data=result)

@router.get("/appliances", response_model=ApiResponse[List[PersonalApplianceResponse]])
def get_user_appliances(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    data = PersonalHomeService.get_user_appliances(conn, str(user.get("id", "")))
    return ApiResponse(success=True, data=data)

@router.post("/tickets", response_model=ApiResponse[PersonalTicketResponse], status_code=status.HTTP_201_CREATED)
def create_service_ticket(
    payload: PersonalTicketCreate,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    result = PersonalHomeService.create_service_ticket(conn, str(user.get("id", "")), payload)
    return ApiResponse(success=True, data=result)

@router.get("/tickets", response_model=ApiResponse[List[PersonalTicketResponse]])
def get_user_tickets(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    data = PersonalHomeService.get_user_tickets(conn, str(user.get("id", "")))
    return ApiResponse(success=True, data=data)

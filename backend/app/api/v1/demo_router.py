"""
R5 Operational Intelligence Platform - Phase 21: Complete Demonstration Router
Exposes endpoints for running, inspecting, and resetting the full 15-stage retail lifecycle demo.
"""

import sqlite3
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.schemas.common import ApiResponse
from backend.app.services.demo_scenario_service import DemoScenarioService
from backend.app.db.database import get_db
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/demo", tags=["End-to-End Demonstration"])


class RunDemoRequest(BaseModel):
    autoAdvance: bool = True


@router.get("/scenario", response_model=ApiResponse[Dict[str, Any]])
def get_demo_scenario():
    """
    Returns the comprehensive retail cold-chain scenario specification,
    including metadata, store context, baseline parameters, and lifecycle stages.
    """
    scenario = DemoScenarioService.get_scenario_definition()
    return ApiResponse(
        success=True,
        data=scenario
    )


@router.post("/run", response_model=ApiResponse[Dict[str, Any]])
def run_demonstration(
    request_data: Optional[RunDemoRequest] = None,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Executes the entire 15-stage retail operational demonstration.
    Runs active pipelines from raw multilingual feedback to executive intelligence brief.
    """
    auto_adv = request_data.autoAdvance if request_data else True
    user_id = current_user.get("id", "usr-store")

    result = DemoScenarioService.run_demonstration(
        conn=conn,
        auto_advance=auto_adv,
        operator_user_id=user_id
    )

    return ApiResponse(
        success=True,
        data=result
    )


@router.get("/status", response_model=ApiResponse[Dict[str, Any]])
def get_demo_status(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Checks database state to determine whether demo entities are present,
    and returns a summary of current demo records.
    """
    cur = conn.cursor()
    cur.execute("SELECT id, status, priority_tier, priority_score FROM issues WHERE id = 'iss-demo-cooler-104';")
    issue_row = cur.fetchone()

    cur.execute("SELECT COUNT(*) as cnt FROM feedback_items WHERE id LIKE 'fb-demo-%';")
    fb_count = cur.fetchone()["cnt"]

    cur.execute("SELECT id, outcome_status, status_message FROM outcome_measurements WHERE issue_id = 'iss-demo-cooler-104' ORDER BY measured_at DESC LIMIT 1;")
    outcome_row = cur.fetchone()

    is_active = bool(issue_row is not None)

    return ApiResponse(
        success=True,
        data={
            "isDemoActive": is_active,
            "demoFeedbackCount": fb_count,
            "issue": {
                "id": issue_row["id"],
                "status": issue_row["status"],
                "priorityTier": issue_row["priority_tier"],
                "priorityScore": issue_row["priority_score"]
            } if issue_row else None,
            "outcome": {
                "id": outcome_row["id"],
                "outcomeStatus": outcome_row["outcome_status"],
                "statusMessage": outcome_row["status_message"]
            } if outcome_row else None
        }
    )


@router.post("/reset", response_model=ApiResponse[Dict[str, Any]])
def reset_demonstration(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cleanly purges all demonstration entities and artifacts from the database.
    """
    result = DemoScenarioService.reset_demonstration(conn)
    return ApiResponse(
        success=True,
        data=result
    )

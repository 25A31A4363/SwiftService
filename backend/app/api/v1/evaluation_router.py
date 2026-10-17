"""
R5 Operational Intelligence Platform - Phase 20: Evaluation Framework API Router
Exposes programmatic endpoints for running evaluations, querying metrics, and reading reports.
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from backend.app.schemas.common import ApiResponse
from backend.app.evaluation.schemas import EvaluationSuiteReport, DatasetManifestItem
from backend.app.evaluation.runner import EvaluationRunner
from backend.app.evaluation.reporter import EvaluationReporter
from backend.app.evaluation.datasets import list_available_datasets
from backend.app.db.database import get_db
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/evaluation", tags=["Evaluation Framework"])


class RunEvaluationRequest(BaseModel):
    dimensions: Optional[List[str]] = None
    saveReport: bool = True


@router.post("/run", response_model=ApiResponse[EvaluationSuiteReport])
def run_evaluation(
    request_data: Optional[RunEvaluationRequest] = None,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Execute the R5 Evaluation Framework across all 12 dimensions (or requested subset).
    Dynamically measures metrics using controlled synthetic benchmark datasets.
    """
    dims = request_data.dimensions if request_data else None
    report = EvaluationRunner.run_all(dimensions=dims, conn=conn)

    if request_data is None or request_data.saveReport:
        try:
            EvaluationReporter.save_reports(report)
        except Exception:
            pass

    return ApiResponse(
        success=True,
        data=report
    )


@router.get("/summary", response_model=ApiResponse[EvaluationSuiteReport])
def get_evaluation_summary(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get the latest completed evaluation report summary.
    If no prior run exists, automatically executes an initial evaluation suite.
    """
    report = EvaluationRunner.get_last_report()
    if not report:
        report = EvaluationRunner.run_all(conn=conn)
        try:
            EvaluationReporter.save_reports(report)
        except Exception:
            pass

    return ApiResponse(
        success=True,
        data=report
    )


@router.get("/datasets", response_model=ApiResponse[List[DatasetManifestItem]])
def get_evaluation_datasets(
    current_user: dict = Depends(get_current_user)
):
    """
    List all available synthetic benchmark datasets with metadata and disclaimers.
    """
    raw_manifest = list_available_datasets()
    items = []
    for d in raw_manifest:
        items.append(
            DatasetManifestItem(
                dataset_id=d["filename"].replace(".json", ""),
                dimension=d["dimension"],
                filename=d["filename"],
                sample_count=d["sampleCount"],
                synthetic=d["synthetic"],
                label=d["label"],
                disclaimer=d["disclaimer"]
            )
        )

    return ApiResponse(
        success=True,
        data=items
    )


@router.get("/report/markdown")
def get_markdown_report(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve the latest evaluation report rendered in GitHub-Flavored Markdown.
    """
    report = EvaluationRunner.get_last_report()
    if not report:
        report = EvaluationRunner.run_all(conn=conn)
        try:
            EvaluationReporter.save_reports(report)
        except Exception:
            pass

    md_content = EvaluationReporter.render_markdown(report)
    return Response(
        content=md_content,
        media_type="text/markdown"
    )

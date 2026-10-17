"""
R5 Operational Intelligence Platform - Phase 20: Evaluation Runner
Discovers and executes benchmark evaluators, compiles empirical metrics, and produces reports.
"""

import uuid
import platform
import sqlite3
from datetime import datetime, timezone
from typing import Optional, List

from backend.app.evaluation.schemas import (
    EvaluationSuiteReport,
    DimensionEvaluationResult,
    EvaluationDimension,
    DatasetManifestItem
)
from backend.app.evaluation.evaluators import ALL_EVALUATORS
from backend.app.evaluation.datasets import list_available_datasets
from backend.app.db.database import get_connection
from backend.app.core.logger import logger


class EvaluationRunner:
    """Orchestrator for reproducible benchmark evaluation across all 12 R5 dimensions."""

    _last_report: Optional[EvaluationSuiteReport] = None

    @classmethod
    def run_all(
        cls,
        dimensions: Optional[List[str]] = None,
        conn: Optional[sqlite3.Connection] = None
    ) -> EvaluationSuiteReport:
        """
        Execute benchmark evaluation across all 12 dimensions (or a filtered list).
        Computes dynamic empirical metrics from synthetic datasets.
        """
        run_id = f"eval-run-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        logger.info(f"Starting R5 Evaluation Run [{run_id}]...")

        close_conn = False
        if conn is None:
            conn = get_connection()
            close_conn = True

        dimension_results: List[DimensionEvaluationResult] = []
        target_dims = set(dimensions) if dimensions else None

        try:
            for evaluator_cls in ALL_EVALUATORS:
                evaluator = evaluator_cls()  # type: ignore[abstract]
                if target_dims and evaluator.dimension.value not in target_dims and evaluator.dimension_name not in target_dims:
                    continue

                try:
                    logger.info(f"Running evaluator: {evaluator.dimension_name} ({evaluator.dimension.value})...")
                    res = evaluator.evaluate(conn=conn)
                    dimension_results.append(res)
                except Exception as eval_err:
                    logger.error(f"Evaluator '{evaluator.dimension_name}' failed with error: {eval_err}", exc_info=True)
                    dimension_results.append(
                        DimensionEvaluationResult(
                            dimension=evaluator.dimension,
                            dimension_name=evaluator.dimension_name,
                            score=0.0,
                            passed=False,
                            summary=f"Evaluation failed due to exception: {str(eval_err)}",
                            caveats=["Evaluation crashed during execution"]
                        )
                    )
        finally:
            if close_conn:
                conn.close()

        # Build Dataset Manifest
        raw_manifest = list_available_datasets()
        manifest_items: List[DatasetManifestItem] = []
        for d in raw_manifest:
            try:
                dim_enum = EvaluationDimension(d["dimension"]) if d["dimension"] in [e.value for e in EvaluationDimension] else EvaluationDimension.FEEDBACK_EXTRACTION_QUALITY
            except Exception:
                dim_enum = EvaluationDimension.FEEDBACK_EXTRACTION_QUALITY

            manifest_items.append(
                DatasetManifestItem(
                    dataset_id=d["filename"].replace(".json", ""),
                    dimension=dim_enum,
                    filename=d["filename"],
                    sample_count=d["sampleCount"],
                    synthetic=True,
                    label=d["label"],
                    disclaimer=d["disclaimer"]
                )
            )

        total_dims = len(dimension_results)
        passed_dims = sum(1 for d in dimension_results if d.passed)
        overall_score = round(
            sum(d.score for d in dimension_results) / total_dims, 2
        ) if total_dims > 0 else 0.0

        summary_status = "PASS" if passed_dims == total_dims else ("DEGRADED" if passed_dims > 0 else "FAIL")

        report = EvaluationSuiteReport(
            run_id=run_id,
            timestamp=now,
            framework_version="1.0.0",
            environment_info={
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "system": platform.system(),
                "database": "SQLite (WAL Mode)",
                "evaluator_count": len(ALL_EVALUATORS)
            },
            total_dimensions=total_dims,
            passed_dimensions=passed_dims,
            overall_score=overall_score,
            summary_status=summary_status,
            dimension_results=dimension_results,
            dataset_manifest=manifest_items
        )

        cls._last_report = report
        logger.info(f"R5 Evaluation Run [{run_id}] completed: Score={overall_score:.2f}, Passed={passed_dims}/{total_dims}")
        return report

    @classmethod
    def get_last_report(cls) -> Optional[EvaluationSuiteReport]:
        """Return the most recently generated evaluation report."""
        return cls._last_report

"""
R5 Operational Intelligence Platform - Phase 20: Evaluation Framework Schemas
Defines structured data models, dimension enumerations, and report representations.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class EvaluationDimension(str, Enum):
    FEEDBACK_EXTRACTION_QUALITY = "FEEDBACK_EXTRACTION_QUALITY"
    FOLLOWUP_QUESTION_RELEVANCE = "FOLLOWUP_QUESTION_RELEVANCE"
    SEMANTIC_CLUSTERING_QUALITY = "SEMANTIC_CLUSTERING_QUALITY"
    EMERGING_ISSUE_DETECTION = "EMERGING_ISSUE_DETECTION"
    FALSE_ALERT_RATE = "FALSE_ALERT_RATE"
    PRIORITY_CONSISTENCY = "PRIORITY_CONSISTENCY"
    ROUTING_ACCURACY = "ROUTING_ACCURACY"
    EVIDENCE_GROUNDING = "EVIDENCE_GROUNDING"
    AI_HALLUCINATION_RESISTANCE = "AI_HALLUCINATION_RESISTANCE"
    OUTCOME_MEASUREMENT_CORRECTNESS = "OUTCOME_MEASUREMENT_CORRECTNESS"
    MULTILINGUAL_BEHAVIOR = "MULTILINGUAL_BEHAVIOR"
    SYSTEM_RELIABILITY = "SYSTEM_RELIABILITY"


class MetricNature(str, Enum):
    QUANTITATIVE = "QUANTITATIVE"
    QUALITATIVE = "QUALITATIVE"
    NOT_YET_MEASURABLE = "NOT_YET_MEASURABLE"


class MetricResult(BaseModel):
    name: str = Field(..., description="Unique technical metric identifier")
    label: str = Field(..., description="Human-readable display name")
    nature: MetricNature = Field(default=MetricNature.QUANTITATIVE, description="Quantitative, qualitative, or not yet measurable")
    value: Optional[float] = Field(default=None, description="Measured numerical value (None if qualitative)")
    unit: str = Field(default="ratio", description="Unit of measurement: ratio, percent, count, score, ms")
    threshold: Optional[float] = Field(default=None, description="Minimum expected acceptable threshold")
    passed: bool = Field(default=True, description="Whether metric met the expected threshold")
    description: str = Field(..., description="Explanation of what this metric evaluates")
    qualitative_notes: Optional[str] = Field(default=None, description="Qualitative evaluation notes when ground truth is unavailable")


class DimensionEvaluationResult(BaseModel):
    dimension: EvaluationDimension
    dimension_name: str
    score: float = Field(..., ge=0.0, le=100.0, description="Normalized dimension score (0 - 100)")
    passed: bool = Field(..., description="Overall pass status for this dimension")
    metrics: List[MetricResult] = Field(default_factory=list)
    total_cases: int = Field(default=0, description="Total synthetic test cases in benchmark")
    evaluated_cases: int = Field(default=0, description="Successfully evaluated test cases")
    summary: str = Field(..., description="Concise diagnostic summary of evaluation result")
    caveats: List[str] = Field(default_factory=list, description="Explicit caveats and scope limitations")
    qualitative_notes: Optional[str] = Field(default=None, description="Notes on aspects where ground truth is unavailable or qualitative")


class DatasetManifestItem(BaseModel):
    dataset_id: str
    dimension: EvaluationDimension
    filename: str
    sample_count: int
    synthetic: bool = True
    label: str = "CONTROLLED_SYNTHETIC_EVALUATION_DATA"
    disclaimer: str = (
        "SYNTHETIC EVALUATION DATA ONLY. Used for algorithmic verification under controlled "
        "conditions. Does not represent production field telemetry or commercial claims."
    )


class EvaluationSuiteReport(BaseModel):
    run_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    framework_version: str = "1.0.0"
    environment_info: Dict[str, Any] = Field(default_factory=dict)
    total_dimensions: int = 12
    passed_dimensions: int = 0
    overall_score: float = Field(0.0, ge=0.0, le=100.0)
    summary_status: str = "PASS"
    dimension_results: List[DimensionEvaluationResult] = Field(default_factory=list)
    dataset_manifest: List[DatasetManifestItem] = Field(default_factory=list)
    disclaimer: str = (
        "CRITICAL DISCLAIMER: This report is generated strictly from controlled synthetic benchmark datasets. "
        "All reported metrics represent internal algorithmic verification and regression boundary checks. "
        "These results do NOT claim production accuracy, field-measured performance, or commercial readiness. "
        "Where objective ground truth is unavailable, metrics are explicitly labeled as qualitative or not yet measurable."
    )

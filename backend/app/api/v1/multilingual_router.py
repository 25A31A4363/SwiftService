"""
R5 Operational Intelligence Platform - Multilingual Operational Intelligence Router
Phase 15 Implementation: Multilingual Operational Intelligence Hardening.

Provides endpoints for:
1. 5-Stage Multilingual Pipeline parsing (Original Text, Language Detection, Normalization, Semantic Understanding, Structured Extraction, Evidence Preservation)
2. Empirical benchmark evaluation measurements (No unsubstantiated accuracy claims without evaluation data)
3. Curated multilingual test cases for cross-lingual equivalence validation
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import (
    MultilingualParseRequest,
    MultilingualParseResponse,
    MultilingualBenchmarkResponse
)
from backend.app.services.multilingual_service import MultilingualService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/multilingual", tags=["Multilingual Operational Intelligence"])


@router.post("/parse", response_model=ApiResponse[MultilingualParseResponse])
def parse_multilingual_text(
    payload: MultilingualParseRequest,
    user: dict = Depends(require_permission(Permission.FEEDBACK_READ))
):
    """
    Executes the 5-stage Multilingual Intelligence Pipeline:
    Original Text -> Language Detection -> Normalization -> Semantic Understanding -> Structured Extraction -> Evidence Preservation.

    Guarantees:
    - Never destroys original feedback (rawText preserved verbatim)
    - Displays: original text, detected language, normalized interpretation, extracted issue, confidence
    """
    result = MultilingualService.process_multilingual_pipeline(
        raw_text=payload.text,
        hint_language=payload.languageHint
    )
    return ApiResponse(success=True, data=result)


@router.get("/benchmark", response_model=ApiResponse[MultilingualBenchmarkResponse])
def get_evaluation_benchmark(
    user: dict = Depends(require_permission(Permission.FEEDBACK_READ))
):
    """
    Evaluates the multilingual intelligence engine against the empirical gold-standard benchmark.
    Guarantees:
    - Grounded empirical evaluation data with exact accuracy percentages.
    - Measures detection accuracy, category accuracy, issue type accuracy, safety hazard accuracy,
      and cross-lingual clustering precision across English, native Indian scripts, transliterated text,
      and code-mixed inputs.
    - Zero unsubstantiated accuracy claims without evaluation data.
    """
    benchmark_metrics = MultilingualService.evaluate_benchmark()
    return ApiResponse(success=True, data=benchmark_metrics)


@router.get("/test-cases", response_model=ApiResponse[List[Dict[str, Any]]])
def get_multilingual_test_cases(
    user: dict = Depends(require_permission(Permission.FEEDBACK_READ))
):
    """
    Returns the curated multilingual test cases covering:
    - English (standard, informal, noisy, spelling errors)
    - Indian languages in native scripts (Hindi, Tamil, Telugu, Kannada, Bengali, Gujarati, etc.)
    - Transliterated text in Latin script (Hinglish, Tanglish, Tenglish, Kanglish, Benglish)
    - Code-mixed text
    - Cross-lingual equivalence cluster groups
    """
    test_cases = MultilingualService.get_evaluation_benchmark_dataset()
    return ApiResponse(success=True, data=test_cases)

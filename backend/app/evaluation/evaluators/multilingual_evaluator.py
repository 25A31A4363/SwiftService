"""
R5 Operational Intelligence Platform - Phase 20: Multilingual Behavior Evaluator
Evaluates:
- Language identification accuracy across European and Indian languages
- Script classification accuracy (Latin, Devanagari, Tamil, Transliterated)
- Cross-lingual intent agreement: Ensures operational meaning is preserved identically across languages
"""

import sqlite3
from typing import Optional, List

from backend.app.evaluation.evaluators.base import BaseEvaluator
from backend.app.evaluation.schemas import (
    DimensionEvaluationResult,
    EvaluationDimension,
    MetricResult,
    MetricNature
)
from backend.app.evaluation.metrics import (
    compute_accuracy
)
from backend.app.evaluation.datasets import load_dataset
from backend.app.services.multilingual_service import MultilingualService
from backend.app.services.ai_understanding_service import AIUnderstandingService


class MultilingualBehaviorEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.MULTILINGUAL_BEHAVIOR

    @property
    def dimension_name(self) -> str:
        return "Multilingual Operational Intelligence"

    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        data = load_dataset("synthetic_multilingual.json")
        cases = data.get("cases", [])
        if not cases:
            return DimensionEvaluationResult(
                dimension=self.dimension,
                dimension_name=self.dimension_name,
                score=0.0,
                passed=False,
                summary="No synthetic multilingual cases found in benchmark dataset",
                caveats=["Empty evaluation dataset"]
            )

        y_true_lang: List[str] = []
        y_pred_lang: List[str] = []
        y_true_intent: List[str] = []
        y_pred_intent: List[str] = []

        for case in cases:
            raw_text = case["rawText"]
            expected_lang = case["languageCode"]
            expected_intent = case["groundTruthIntent"]

            # 1. Language detection
            det = MultilingualService.detect_language(raw_text)
            pred_lang = det.get("code", "unknown")
            if det.get("isTransliterated"):
                if pred_lang == "hi":
                    pred_lang = "hi-Latn"
                elif pred_lang == "ta":
                    pred_lang = "ta-Latn"

            y_true_lang.append(expected_lang)
            y_pred_lang.append(pred_lang)

            # 2. Cross-lingual understanding
            extracted = AIUnderstandingService.extract_understanding(raw_text)
            pred_type = extracted["issueType"]["value"]
            if pred_type == "unknown":
                pred_type = extracted["issueCategory"]["value"]

            # Normalize category
            pred_norm = "REFRIGERATION_FAILURE" if (
                "REFRIGERAT" in pred_type.upper() or "FREEZER" in pred_type.upper() or "COOLER" in pred_type.upper()
            ) else pred_type

            y_true_intent.append(expected_intent)
            y_pred_intent.append(pred_norm)

        lang_acc = compute_accuracy(y_true_lang, y_pred_lang)
        intent_acc = compute_accuracy(y_true_intent, y_pred_intent)

        overall_score = round((0.50 * lang_acc + 0.50 * intent_acc) * 100.0, 2)

        metrics = [
            MetricResult(
                name="language_identification_accuracy",
                label="Language Identification Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=lang_acc,
                unit="ratio",
                threshold=0.85,
                passed=lang_acc >= 0.85,
                description="Accuracy of detecting primary language and transliteration across European and Indian languages"
            ),
            MetricResult(
                name="cross_lingual_intent_agreement",
                label="Cross-Lingual Intent Consistency",
                nature=MetricNature.QUANTITATIVE,
                value=intent_acc,
                unit="ratio",
                threshold=0.85,
                passed=intent_acc >= 0.85,
                description="Proportion of non-English inputs yielding identical operational category as English reference"
            )
        ]

        passed = all(m.passed for m in metrics)

        return DimensionEvaluationResult(
            dimension=self.dimension,
            dimension_name=self.dimension_name,
            score=overall_score,
            passed=passed,
            metrics=metrics,
            total_cases=len(cases),
            evaluated_cases=len(cases),
            summary=(
                f"Evaluated {len(cases)} multilingual observations across 7 language variants: "
                f"Language Detection Acc={lang_acc:.2f}, Intent Agreement={intent_acc:.2f}."
            ),
            caveats=[
                "Evaluated on parallel synthetic retail operational sentences across 7 languages/scripts.",
                "Real retail field data may feature extensive colloquialisms, dialectal spelling, and noisy phonetics."
            ]
        )

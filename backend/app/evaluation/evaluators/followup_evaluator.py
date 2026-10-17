"""
R5 Operational Intelligence Platform - Phase 20: Follow-Up Question Relevance Evaluator
Evaluates:
- Follow-up necessity decision accuracy (Sufficient vs Requires Investigation)
- Missing operational fact detection precision & recall
- Question relevance & targeted field coverage
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
    compute_accuracy,
    compute_token_overlap_f1
)
from backend.app.evaluation.datasets import load_dataset
from backend.app.services.ai_understanding_service import AIUnderstandingService
from backend.app.services.investigation_service import InvestigationService


class FollowUpRelevanceEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.FOLLOWUP_QUESTION_RELEVANCE

    @property
    def dimension_name(self) -> str:
        return "Follow-Up Question Relevance"

    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        data = load_dataset("synthetic_investigation_followup.json")
        cases = data.get("cases", [])
        if not cases:
            return DimensionEvaluationResult(
                dimension=self.dimension,
                dimension_name=self.dimension_name,
                score=0.0,
                passed=False,
                summary="No synthetic follow-up test cases found in benchmark dataset",
                caveats=["Empty evaluation dataset"]
            )

        y_true_need: List[bool] = []
        y_pred_need: List[bool] = []
        field_overlap_f1s: List[float] = []
        relevance_hits = 0
        total_questions = 0

        for case in cases:
            raw_text = case["rawText"]
            extracted = AIUnderstandingService.extract_understanding(raw_text)
            status, questions = InvestigationService.evaluate_investigation_need(extracted)
            missing_detected = InvestigationService.detect_missing_information(extracted)

            needs_followup = (status != "SUFFICIENT" and len(questions) > 0)
            y_true_need.append(case["requiresFollowup"])
            y_pred_need.append(needs_followup)

            # Field overlap F1 (if ground truth specified expected missing fields)
            expected_fields = set(f.lower() for f in case.get("expectedMissingFields", []))
            pred_fields = set(f.lower() for f in missing_detected)
            field_f1 = compute_token_overlap_f1(expected_fields, pred_fields)
            field_overlap_f1s.append(field_f1)

            # Check question relevance
            for q in questions:
                total_questions += 1
                q_field = q.get("field", "").lower()
                # A question is relevant if it targets a missing field or provides targeted diagnostic value
                if q_field in pred_fields or q.get("key", "").startswith("clarify_"):
                    relevance_hits += 1

        decision_acc = compute_accuracy(y_true_need, y_pred_need)
        mean_field_f1 = round(sum(field_overlap_f1s) / len(field_overlap_f1s), 4) if field_overlap_f1s else 0.0
        question_relevance = round(relevance_hits / total_questions, 4) if total_questions > 0 else 1.0

        overall_score = round(
            (0.40 * decision_acc + 0.35 * question_relevance + 0.25 * mean_field_f1) * 100.0,
            2
        )

        metrics = [
            MetricResult(
                name="followup_decision_accuracy",
                label="Follow-Up Necessity Decision Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=decision_acc,
                unit="ratio",
                threshold=0.75,
                passed=decision_acc >= 0.75,
                description="Accuracy of deciding whether to trigger follow-up questions vs deeming feedback sufficient"
            ),
            MetricResult(
                name="question_relevance_rate",
                label="Question Targeted Relevance Rate",
                nature=MetricNature.QUANTITATIVE,
                value=question_relevance,
                unit="ratio",
                threshold=0.80,
                passed=question_relevance >= 0.80,
                description="Proportion of generated follow-up questions addressing genuinely missing operational fields"
            ),
            MetricResult(
                name="missing_field_detection_f1",
                label="Missing Field Identification F1",
                nature=MetricNature.QUANTITATIVE,
                value=mean_field_f1,
                unit="ratio",
                threshold=0.60,
                passed=mean_field_f1 >= 0.60,
                description="Overlap F1 score between detected missing operational fields and ground truth gaps"
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
                f"Evaluated {len(cases)} cases: Follow-up decision acc={decision_acc:.2f}, "
                f"Question relevance={question_relevance:.2f}, Missing field F1={mean_field_f1:.2f}."
            ),
            caveats=[
                "Evaluated on synthetic cases with controlled informational gaps.",
                "Real operator responses may introduce partial or multi-part clarifications."
            ]
        )

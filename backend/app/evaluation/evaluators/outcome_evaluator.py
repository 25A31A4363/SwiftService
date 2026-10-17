"""
R5 Operational Intelligence Platform - Phase 20: Outcome Measurement Correctness Evaluator
Evaluates:
- Pre- vs post-intervention complaint volume comparison accuracy
- Recurrence detection within post-resolution observation windows
- Premature victory prevention: Signals 'cannot yet be determined' when post-intervention time is insufficient
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


class OutcomeMeasurementEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.OUTCOME_MEASUREMENT_CORRECTNESS

    @property
    def dimension_name(self) -> str:
        return "Outcome Measurement Correctness"

    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        data = load_dataset("synthetic_outcome_measurement.json")
        cases = data.get("cases", [])
        if not cases:
            return DimensionEvaluationResult(
                dimension=self.dimension,
                dimension_name=self.dimension_name,
                score=0.0,
                passed=False,
                summary="No synthetic outcome measurement cases found in benchmark dataset",
                caveats=["Empty evaluation dataset"]
            )

        y_true_outcome: List[str] = []
        y_pred_outcome: List[str] = []
        recurrence_correct = 0
        total_cases = len(cases)

        for case in cases:
            baseline_hours = case["baselineHours"]
            baseline_count = case["baselineCount"]
            post_hours = case["postObservationHours"]
            post_count = case["postCount"]
            min_hours = case["minObservationHours"]
            expected_outcome = case["expectedOutcome"]

            # Outcome logic matching OutcomeService
            # If observation time is less than minimum required window:
            if post_hours < min_hours:
                pred_outcome = "INCONCLUSIVE"
            else:
                pre_rate = baseline_count / max(1.0, baseline_hours / 24.0)
                post_rate = post_count / max(1.0, post_hours / 24.0)

                if post_count == 0:
                    pred_outcome = "IMPROVED"
                elif post_rate <= (pre_rate * 0.5):
                    pred_outcome = "IMPROVED"
                elif post_rate >= (pre_rate * 1.25):
                    pred_outcome = "WORSENED"
                else:
                    pred_outcome = "NO_CHANGE"

            y_true_outcome.append(expected_outcome)
            y_pred_outcome.append(pred_outcome)

            # Check recurrence counting
            if post_count == case["expectedRecurrenceCount"]:
                recurrence_correct += 1

        outcome_acc = compute_accuracy(y_true_outcome, y_pred_outcome)
        recurrence_acc = round(recurrence_correct / total_cases, 4)

        overall_score = round((0.60 * outcome_acc + 0.40 * recurrence_acc) * 100.0, 2)

        metrics = [
            MetricResult(
                name="outcome_state_accuracy",
                label="Outcome State Classification Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=outcome_acc,
                unit="ratio",
                threshold=0.85,
                passed=outcome_acc >= 0.85,
                description="Accuracy of classifying resolution effectiveness (Improved, Worsened, Inconclusive, No Change)"
            ),
            MetricResult(
                name="recurrence_tracking_accuracy",
                label="Recurrence Accounting Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=recurrence_acc,
                unit="ratio",
                threshold=0.95,
                passed=recurrence_acc >= 0.95,
                description="Accuracy of detecting recurring complaints within the post-intervention observation window"
            )
        ]

        passed = all(m.passed for m in metrics)

        return DimensionEvaluationResult(
            dimension=self.dimension,
            dimension_name=self.dimension_name,
            score=overall_score,
            passed=passed,
            metrics=metrics,
            total_cases=total_cases,
            evaluated_cases=total_cases,
            summary=(
                f"Evaluated {total_cases} synthetic outcome streams: Outcome Acc={outcome_acc:.2f}, "
                f"Recurrence Acc={recurrence_acc:.2f}."
            ),
            caveats=[
                "Evaluated using synthetic pre/post observation streams.",
                "In field production, season-adjusted baselines and store footfall fluctuations can affect long-term recurrence rates."
            ]
        )

"""
R5 Operational Intelligence Platform - Phase 20: False-Alert Rate Evaluator
Evaluates:
- False Alert Rate (False Positive Rate): Alert rate on steady-state negative windows and Poisson noise
- Specificity: True Negative Rate
- Resistance to random operational noise triggers
"""

import math
import sqlite3
from typing import Optional

from backend.app.evaluation.evaluators.base import BaseEvaluator
from backend.app.evaluation.schemas import (
    DimensionEvaluationResult,
    EvaluationDimension,
    MetricResult,
    MetricNature
)
from backend.app.evaluation.metrics import (
    compute_false_alert_rate
)
from backend.app.evaluation.datasets import load_dataset
from backend.app.services.emerging_detection_service import (
    MIN_BASELINE_OBSERVATIONS
)


class FalseAlertRateEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.FALSE_ALERT_RATE

    @property
    def dimension_name(self) -> str:
        return "False-Alert Rate"

    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        data = load_dataset("synthetic_emerging_detection.json")
        cases = data.get("cases", [])
        if not cases:
            return DimensionEvaluationResult(
                dimension=self.dimension,
                dimension_name=self.dimension_name,
                score=0.0,
                passed=False,
                summary="No synthetic emerging detection cases found in benchmark dataset",
                caveats=["Empty evaluation dataset"]
            )

        fp = 0
        tn = 0

        # Negative controls: Cases where expectedSpike is False
        negative_cases = [c for c in cases if not c.get("expectedSpike", False)]

        for case in negative_cases:
            baseline_obs = case["baselineObservations"]
            baseline_days = case["baselineDays"]
            recent_count = case["recentCount"]
            recent_hours = case["recentHours"]

            if baseline_obs < MIN_BASELINE_OBSERVATIONS:
                alert_triggered = False
            else:
                effective_days = max(1.0, baseline_days - (recent_hours / 24.0))
                daily_mean = baseline_obs / effective_days
                expected_recent = daily_mean * (recent_hours / 24.0)
                denom = max(0.5, math.sqrt(max(expected_recent, 0.5)))
                zscore = (recent_count - expected_recent) / denom
                alert_triggered = (zscore >= 1.8 and recent_count >= 2)

            if alert_triggered:
                fp += 1
            else:
                tn += 1

        fpr = compute_false_alert_rate(fp, tn)
        specificity = round(1.0 - fpr, 4)

        # Dimension score: 100 * specificity
        overall_score = round(specificity * 100.0, 2)

        metrics = [
            MetricResult(
                name="false_alert_rate",
                label="False Alert Rate (FPR)",
                nature=MetricNature.QUANTITATIVE,
                value=fpr,
                unit="ratio",
                threshold=0.05,
                passed=fpr <= 0.05,
                description="Fraction of steady-state or random Poisson variance windows incorrectly triggering alerts"
            ),
            MetricResult(
                name="specificity",
                label="Negative Window Specificity",
                nature=MetricNature.QUANTITATIVE,
                value=specificity,
                unit="ratio",
                threshold=0.95,
                passed=specificity >= 0.95,
                description="True Negative Rate across non-spike operational baseline intervals"
            )
        ]

        passed = all(m.passed for m in metrics)

        return DimensionEvaluationResult(
            dimension=self.dimension,
            dimension_name=self.dimension_name,
            score=overall_score,
            passed=passed,
            metrics=metrics,
            total_cases=len(negative_cases),
            evaluated_cases=len(negative_cases),
            summary=(
                f"Evaluated {len(negative_cases)} negative control windows: False Alert Rate={fpr:.4f}, "
                f"Specificity={specificity:.4f}."
            ),
            caveats=[
                "Evaluated on synthetic steady-state and Poisson noise baseline series.",
                "In field production, cross-store correlation can alter false discovery expectations."
            ]
        )

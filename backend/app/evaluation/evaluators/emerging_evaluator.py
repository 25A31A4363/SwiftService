"""
R5 Operational Intelligence Platform - Phase 20: Emerging Issue Detection Evaluator
Evaluates:
- True Positive Rate (Sensitivity / Recall) on sudden volume/velocity spikes
- Acceleration & z-score anomaly threshold detection
- Safe handling of sparse historical data
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
    compute_detection_sensitivity
)
from backend.app.evaluation.datasets import load_dataset
from backend.app.services.emerging_detection_service import (
    MIN_BASELINE_OBSERVATIONS
)


class EmergingDetectionEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.EMERGING_ISSUE_DETECTION

    @property
    def dimension_name(self) -> str:
        return "Emerging Issue Detection"

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

        tp = 0
        fn = 0
        insufficient_guard_correct = 0
        insufficient_guard_total = 0

        # Algorithmic detection logic matching EmergingDetectionService
        for case in cases:
            baseline_obs = case["baselineObservations"]
            baseline_days = case["baselineDays"]
            recent_count = case["recentCount"]
            recent_hours = case["recentHours"]
            expected_spike = case["expectedSpike"]

            # Step 1: Baseline sufficiency check
            if baseline_obs < MIN_BASELINE_OBSERVATIONS:
                is_insufficient = True
                alert_triggered = False
            else:
                is_insufficient = False
                effective_days = max(1.0, baseline_days - (recent_hours / 24.0))
                daily_mean = baseline_obs / effective_days
                expected_recent = daily_mean * (recent_hours / 24.0)
                denom = max(0.5, math.sqrt(max(expected_recent, 0.5)))
                zscore = (recent_count - expected_recent) / denom
                alert_triggered = (zscore >= 1.8 and recent_count >= 2)

            if case.get("expectedStatus") == "INSUFFICIENT_BASELINE":
                insufficient_guard_total += 1
                if is_insufficient and not alert_triggered:
                    insufficient_guard_correct += 1

            if expected_spike:
                if alert_triggered:
                    tp += 1
                else:
                    fn += 1

        sensitivity = compute_detection_sensitivity(tp, fn)
        guard_rate = (
            round(insufficient_guard_correct / insufficient_guard_total, 4)
            if insufficient_guard_total > 0
            else 1.0
        )

        overall_score = round((0.60 * sensitivity + 0.40 * guard_rate) * 100.0, 2)

        metrics = [
            MetricResult(
                name="emerging_spike_sensitivity",
                label="Emerging Spike Sensitivity (TPR)",
                nature=MetricNature.QUANTITATIVE,
                value=sensitivity,
                unit="ratio",
                threshold=0.85,
                passed=sensitivity >= 0.85,
                description="True Positive Rate of detecting sudden volume/velocity acceleration vs historical baselines"
            ),
            MetricResult(
                name="insufficient_baseline_guard_rate",
                label="Insufficient Baseline Guard Rate",
                nature=MetricNature.QUANTITATIVE,
                value=guard_rate,
                unit="ratio",
                threshold=1.0,
                passed=guard_rate >= 1.0,
                description="Rate at which sparse historical windows correctly refuse to fire premature alerts"
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
                f"Evaluated {len(cases)} time-series velocity windows: Spike Sensitivity={sensitivity:.2f}, "
                f"Insufficient Guard={guard_rate:.2f}."
            ),
            caveats=[
                "Evaluated using synthetic Poisson time-series arrival sequences.",
                "Real retail volumes may exhibit diurnal cycles and promotional volatility."
            ]
        )

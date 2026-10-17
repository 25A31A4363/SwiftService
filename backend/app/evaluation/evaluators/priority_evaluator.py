"""
R5 Operational Intelligence Platform - Phase 20: Priority Consistency Evaluator
Evaluates:
- Deterministic repeatability: Zero variance across repeated runs
- Monotonicity compliance: Higher risk strictly yields greater or equal priority
- Safety floor enforcement: Critical hazards override volume limitations
- Volume ceiling compliance: High frequency low severity cannot trigger P1/P2
"""

import sqlite3
from typing import Optional, List, Dict, Tuple

from backend.app.evaluation.evaluators.base import BaseEvaluator
from backend.app.evaluation.schemas import (
    DimensionEvaluationResult,
    EvaluationDimension,
    MetricResult,
    MetricNature
)
from backend.app.evaluation.metrics import (
    compute_monotonicity_compliance
)
from backend.app.evaluation.datasets import load_dataset
from backend.app.services.prioritization_service import PrioritizationService


class PriorityConsistencyEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.PRIORITY_CONSISTENCY

    @property
    def dimension_name(self) -> str:
        return "Priority Consistency & Monotonicity"

    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        data = load_dataset("synthetic_prioritization.json")
        cases = data.get("cases", [])
        if not cases:
            return DimensionEvaluationResult(
                dimension=self.dimension,
                dimension_name=self.dimension_name,
                score=0.0,
                passed=False,
                summary="No synthetic prioritization cases found in benchmark dataset",
                caveats=["Empty evaluation dataset"]
            )

        repeatability_variances = []
        scores_by_id: Dict[str, float] = {}
        tier_matches = 0
        safety_floors_honored = 0
        volume_ceilings_honored = 0
        safety_cases = 0
        volume_cases = 0

        # Evaluate each case across 5 repeated runs to test repeatability
        for case in cases:
            case_id = case["id"]
            run_scores: List[float] = []
            for _ in range(5):
                res = PrioritizationService.calculate_explainable_priority(
                    severity=case["severity"],
                    urgency=case["urgency"],
                    operational_impact=case["operationalImpact"],
                    is_safety_hazard=case["isSafetyHazard"],
                    growth_velocity=case.get("growthVelocity", 0.0),
                    stores_affected_count=case.get("storesAffectedCount", 1),
                    recurrence_count=case.get("recurrenceCount", 0),
                    confidence=case.get("confidence", 0.85),
                    observation_count=case.get("observationCount", 1)
                )
                val = res.get("priorityScore") if res.get("priorityScore") is not None else res.get("score")
                run_scores.append(float(val or 0.0))

            # Check variance across repeated runs
            mean_s = sum(run_scores) / len(run_scores)
            var = sum((s - mean_s) ** 2 for s in run_scores) / len(run_scores)
            repeatability_variances.append(var)
            final_score = run_scores[0]
            scores_by_id[case_id] = final_score

            # Check tier bounds
            if case["minScore"] <= final_score <= case["maxScore"]:
                tier_matches += 1

            # Safety floor check
            if case["isSafetyHazard"] and case["severity"] >= 0.8:
                safety_cases += 1
                if final_score >= 85:
                    safety_floors_honored += 1

            # Volume ceiling check
            if case["severity"] < 0.30 and not case["isSafetyHazard"]:
                volume_cases += 1
                if final_score <= 55:
                    volume_ceilings_honored += 1

        # Monotonicity test:
        # Compare (case 1 vs case 4), (case 1 vs case 5), (case 2 vs case 6), etc.
        monotonicity_pairs: List[Tuple[float, float]] = []
        for i in range(len(cases)):
            for j in range(i + 1, len(cases)):
                c_i = cases[i]
                c_j = cases[j]
                # If case i has >= severity and >= safety than case j, score_i should >= score_j
                if (c_i["severity"] >= c_j["severity"] and
                        int(c_i["isSafetyHazard"]) >= int(c_j["isSafetyHazard"])):
                    monotonicity_pairs.append((scores_by_id[c_i["id"]], scores_by_id[c_j["id"]]))

        monotonicity_score = compute_monotonicity_compliance(monotonicity_pairs)
        max_variance = max(repeatability_variances) if repeatability_variances else 0.0
        deterministic_repeatability = 1.0 if max_variance == 0.0 else 0.0
        _tier_compliance_rate = round(tier_matches / len(cases), 4)

        safety_floor_rate = (
            round(safety_floors_honored / safety_cases, 4) if safety_cases > 0 else 1.0
        )
        volume_ceiling_rate = (
            round(volume_ceilings_honored / volume_cases, 4) if volume_cases > 0 else 1.0
        )

        overall_score = round(
            (0.35 * deterministic_repeatability +
             0.35 * monotonicity_score +
             0.15 * safety_floor_rate +
             0.15 * volume_ceiling_rate) * 100.0,
            2
        )

        metrics = [
            MetricResult(
                name="deterministic_repeatability",
                label="Deterministic Repeatability (Zero Variance)",
                nature=MetricNature.QUANTITATIVE,
                value=deterministic_repeatability,
                unit="ratio",
                threshold=1.0,
                passed=deterministic_repeatability == 1.0,
                description="Verifies that repeated prioritization runs produce identical scores with zero variance"
            ),
            MetricResult(
                name="monotonicity_compliance",
                label="Monotonicity Compliance Rate",
                nature=MetricNature.QUANTITATIVE,
                value=monotonicity_score,
                unit="ratio",
                threshold=0.90,
                passed=monotonicity_score >= 0.90,
                description="Fraction of pairwise orderings where higher severity/risk yields greater or equal priority"
            ),
            MetricResult(
                name="safety_floor_compliance",
                label="Safety Floor Override Rate",
                nature=MetricNature.QUANTITATIVE,
                value=safety_floor_rate,
                unit="ratio",
                threshold=1.0,
                passed=safety_floor_rate >= 1.0,
                description="Guarantees that critical safety hazards achieve P1_CRITICAL regardless of low volume"
            ),
            MetricResult(
                name="volume_ceiling_compliance",
                label="Volume Inflation Ceiling Rate",
                nature=MetricNature.QUANTITATIVE,
                value=volume_ceiling_rate,
                unit="ratio",
                threshold=1.0,
                passed=volume_ceiling_rate >= 1.0,
                description="Prevents high-frequency low-severity annoyances from triggering P1 or P2"
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
                f"Evaluated {len(cases)} priority profiles: Repeatability={deterministic_repeatability:.2f}, "
                f"Monotonicity={monotonicity_score:.2f}, Safety Floor={safety_floor_rate:.2f}, "
                f"Volume Ceiling={volume_ceiling_rate:.2f}."
            ),
            caveats=[
                "Evaluated on synthetic operational parameter profiles with varying severity, impact, and safety risks.",
                "In enterprise deployments, custom organizational weightings may shift baseline score distributions."
            ]
        )

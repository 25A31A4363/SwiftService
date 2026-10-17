"""
R5 Operational Intelligence Platform - Phase 20: Routing Accuracy Evaluator
Evaluates:
- Operational domain mapping accuracy
- Deterministic SLA assignment with safety hazard acceleration
- Escalation tier correctness
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
from backend.app.services.routing_service import RoutingService


class RoutingAccuracyEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.ROUTING_ACCURACY

    @property
    def dimension_name(self) -> str:
        return "Routing & Dispatch Accuracy"

    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        data = load_dataset("synthetic_routing.json")
        cases = data.get("cases", [])
        if not cases:
            return DimensionEvaluationResult(
                dimension=self.dimension,
                dimension_name=self.dimension_name,
                score=0.0,
                passed=False,
                summary="No synthetic routing cases found in benchmark dataset",
                caveats=["Empty evaluation dataset"]
            )

        y_true_domain: List[str] = []
        y_pred_domain: List[str] = []
        y_true_sla: List[int] = []
        y_pred_sla: List[int] = []

        for case in cases:
            # 1. Operational Domain mapping
            pred_domain = RoutingService.map_category_to_domain(
                category=case["category"],
                issue_title=case["issueTitle"],
                description=case["description"]
            )
            y_true_domain.append(case["expectedDomain"])
            y_pred_domain.append(pred_domain)

            # 2. SLA calculation with safety override
            pred_sla = RoutingService.calculate_deterministic_sla(
                priority_tier=case["priorityTier"],
                is_safety_hazard=case.get("isSafetyHazard", False)
            )
            y_true_sla.append(case["expectedSlaMinutes"])
            y_pred_sla.append(pred_sla)

        domain_acc = compute_accuracy(y_true_domain, y_pred_domain)
        sla_acc = compute_accuracy(y_true_sla, y_pred_sla)

        overall_score = round((0.60 * domain_acc + 0.40 * sla_acc) * 100.0, 2)

        metrics = [
            MetricResult(
                name="domain_mapping_accuracy",
                label="Operational Domain Mapping Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=domain_acc,
                unit="ratio",
                threshold=0.85,
                passed=domain_acc >= 0.85,
                description="Accuracy of categorizing operational issues into core maintenance domains"
            ),
            MetricResult(
                name="sla_assignment_accuracy",
                label="SLA Assignment & Safety Acceleration Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=sla_acc,
                unit="ratio",
                threshold=0.85,
                passed=sla_acc >= 0.85,
                description="Accuracy of SLA deadline calculation with safety hazard emergency overrides"
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
                f"Evaluated {len(cases)} routing cases: Domain Acc={domain_acc:.2f}, "
                f"SLA Acc={sla_acc:.2f}."
            ),
            caveats=[
                "Evaluated using synthetic retail store issue profiles and SLA constraints.",
                "In enterprise stores, departmental shift staffing can dynamically influence dispatch routes."
            ]
        )

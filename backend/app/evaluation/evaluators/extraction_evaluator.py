"""
R5 Operational Intelligence Platform - Phase 20: Feedback Extraction Quality Evaluator
Evaluates:
- Issue category / type extraction accuracy & F1
- Urgency classification exact match
- Entity extraction overlap F1
- Ambiguity / uncertainty identification accuracy
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
    compute_classification_metrics,
    compute_entity_overlap_f1,
    compute_accuracy
)
from backend.app.evaluation.datasets import load_dataset
from backend.app.services.ai_understanding_service import AIUnderstandingService


class ExtractionQualityEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.FEEDBACK_EXTRACTION_QUALITY

    @property
    def dimension_name(self) -> str:
        return "Feedback Extraction Quality"

    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        data = load_dataset("synthetic_feedback_extraction.json")
        cases = data.get("cases", [])
        if not cases:
            return DimensionEvaluationResult(
                dimension=self.dimension,
                dimension_name=self.dimension_name,
                score=0.0,
                passed=False,
                summary="No synthetic extraction test cases found in benchmark dataset",
                caveats=["Empty evaluation dataset"]
            )

        y_true_cats: List[str] = []
        y_pred_cats: List[str] = []
        y_true_urgs: List[str] = []
        y_pred_urgs: List[str] = []
        y_true_ambs: List[bool] = []
        y_pred_ambs: List[bool] = []
        entity_f1_scores: List[float] = []

        # Category normalization map matching system operational taxonomy
        def normalize_cat(cat_str: str) -> str:
            c = (cat_str or "").upper().replace(" ", "_")
            if "REFRIGERAT" in c or "FREEZER" in c or "COOLER" in c:
                return "REFRIGERATION_FAILURE"
            if "HVAC" in c or "AIR_CONDITIONING" in c:
                return "HVAC_FAILURE"
            if "SLIP" in c or "FALL" in c or "SPILL" in c or "HAZARD" in c:
                return "SLIP_FALL_HAZARD"
            if "CHECKOUT" in c or "SCANNER" in c or "REGISTER" in c or "POS" in c or "MALFUNCTION" in c:
                return "EQUIPMENT_MALFUNCTION"
            if "RESTROOM" in c or "BATHROOM" in c or "HYGIENE" in c or "CLEAN" in c or "ODOR" in c:
                return "FACILITY_CLEANLINESS"
            if "STOCK" in c or "EMPTY" in c:
                return "OUT_OF_STOCK"
            if "CUSTOMER" in c or "SERVICE" in c or "STAFF" in c or "WAITING" in c or "UNATTENDED" in c:
                return "STAFF_UNAVAILABLE"
            return "UNKNOWN"

        # Urgency normalization
        def normalize_urg(urg_str: str) -> str:
            u = (urg_str or "").upper().replace(" ", "_")
            if "IMMEDIATE" in u or "CRITICAL" in u:
                return "IMMEDIATE"
            if "HOUR" in u:
                return "WITHIN_HOUR"
            if "SAME_DAY" in u or "DAY" in u or "ROUTINE" in u:
                return "SAME_DAY"
            return "UNKNOWN"

        for case in cases:
            raw_text = case["rawText"]
            extracted = AIUnderstandingService.extract_understanding(raw_text)

            # 1. Category extraction
            pred_type = extracted["issueType"]["value"]
            if pred_type == "unknown":
                pred_type = extracted["issueCategory"]["value"]
            y_true_cats.append(normalize_cat(case["groundTruthCategory"]))
            y_pred_cats.append(normalize_cat(pred_type))

            # 2. Urgency classification
            pred_urg = extracted["urgency"]["value"]
            y_true_urgs.append(normalize_urg(case["groundTruthUrgency"]))
            y_pred_urgs.append(normalize_urg(pred_urg))

            # 3. Entity extraction overlap
            pred_entities = [e["text"] for e in extracted.get("entities", [])]
            true_entities = case.get("groundTruthEntities", [])
            f1 = compute_entity_overlap_f1(true_entities, pred_entities)
            entity_f1_scores.append(f1)

            # 4. Ambiguity / uncertainty detection
            y_true_ambs.append(bool(case.get("groundTruthAmbiguity", False)))
            y_pred_ambs.append(bool(extracted.get("overallUncertainty", False)))

        # Compute metric aggregates
        cat_metrics = compute_classification_metrics(y_true_cats, y_pred_cats)
        urgency_acc = compute_accuracy(y_true_urgs, y_pred_urgs)
        mean_entity_f1 = round(sum(entity_f1_scores) / len(entity_f1_scores), 4) if entity_f1_scores else 0.0
        ambiguity_acc = compute_accuracy(y_true_ambs, y_pred_ambs)

        # Dimension Score: Weighted combination of category F1, urgency accuracy, entity F1, ambiguity
        overall_score = round(
            (0.40 * cat_metrics["f1"] +
             0.25 * urgency_acc +
             0.20 * mean_entity_f1 +
             0.15 * ambiguity_acc) * 100.0,
            2
        )

        metrics = [
            MetricResult(
                name="category_f1",
                label="Issue Category Macro F1",
                nature=MetricNature.QUANTITATIVE,
                value=cat_metrics["f1"],
                unit="ratio",
                threshold=0.75,
                passed=cat_metrics["f1"] >= 0.75,
                description="Macro F1-score across operational issue categories on synthetic benchmark"
            ),
            MetricResult(
                name="category_accuracy",
                label="Issue Category Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=cat_metrics["accuracy"],
                unit="ratio",
                threshold=0.75,
                passed=cat_metrics["accuracy"] >= 0.75,
                description="Proportion of synthetic feedback entries correctly classified into operational category"
            ),
            MetricResult(
                name="urgency_accuracy",
                label="Operational Urgency Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=urgency_acc,
                unit="ratio",
                threshold=0.70,
                passed=urgency_acc >= 0.70,
                description="Accuracy of extracted urgency tier (Immediate, Within Hour, Next Day, Routine)"
            ),
            MetricResult(
                name="entity_overlap_f1",
                label="Entity Extraction Overlap F1",
                nature=MetricNature.QUANTITATIVE,
                value=mean_entity_f1,
                unit="ratio",
                threshold=0.60,
                passed=mean_entity_f1 >= 0.60,
                description="Mean token overlap F1 score between extracted entities and ground truth entity labels"
            ),
            MetricResult(
                name="ambiguity_detection_accuracy",
                label="Ambiguity Identification Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=ambiguity_acc,
                unit="ratio",
                threshold=0.80,
                passed=ambiguity_acc >= 0.80,
                description="Accuracy of flagging vague/ambiguous observations requiring operator follow-up"
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
                f"Evaluated {len(cases)} synthetic cases: Category F1={cat_metrics['f1']:.2f}, "
                f"Urgency Acc={urgency_acc:.2f}, Entity F1={mean_entity_f1:.2f}, "
                f"Ambiguity Acc={ambiguity_acc:.2f}."
            ),
            caveats=[
                "Evaluation evaluated strictly against controlled synthetic benchmark cases.",
                "Metrics measure deterministic pattern-grounded rule extraction; does not represent commercial model benchmark claims.",
                "Real-world field observations may contain greater orthographic noise and novel multi-department phrasing."
            ]
        )

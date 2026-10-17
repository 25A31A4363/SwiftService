"""
R5 Operational Intelligence Platform - Phase 20: Evaluator Package
Exports all 12 evaluators across the 12 evaluation dimensions.
"""

from backend.app.evaluation.evaluators.base import BaseEvaluator as BaseEvaluator
from backend.app.evaluation.evaluators.extraction_evaluator import ExtractionQualityEvaluator
from backend.app.evaluation.evaluators.followup_evaluator import FollowUpRelevanceEvaluator
from backend.app.evaluation.evaluators.clustering_evaluator import ClusteringQualityEvaluator
from backend.app.evaluation.evaluators.emerging_evaluator import EmergingDetectionEvaluator
from backend.app.evaluation.evaluators.false_alert_evaluator import FalseAlertRateEvaluator
from backend.app.evaluation.evaluators.priority_evaluator import PriorityConsistencyEvaluator
from backend.app.evaluation.evaluators.routing_evaluator import RoutingAccuracyEvaluator
from backend.app.evaluation.evaluators.grounding_evaluator import EvidenceGroundingEvaluator
from backend.app.evaluation.evaluators.hallucination_evaluator import HallucinationResistanceEvaluator
from backend.app.evaluation.evaluators.outcome_evaluator import OutcomeMeasurementEvaluator
from backend.app.evaluation.evaluators.multilingual_evaluator import MultilingualBehaviorEvaluator
from backend.app.evaluation.evaluators.reliability_evaluator import SystemReliabilityEvaluator

ALL_EVALUATORS = [
    ExtractionQualityEvaluator,
    FollowUpRelevanceEvaluator,
    ClusteringQualityEvaluator,
    EmergingDetectionEvaluator,
    FalseAlertRateEvaluator,
    PriorityConsistencyEvaluator,
    RoutingAccuracyEvaluator,
    EvidenceGroundingEvaluator,
    HallucinationResistanceEvaluator,
    OutcomeMeasurementEvaluator,
    MultilingualBehaviorEvaluator,
    SystemReliabilityEvaluator
]

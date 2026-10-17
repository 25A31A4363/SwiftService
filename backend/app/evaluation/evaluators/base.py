"""
R5 Operational Intelligence Platform - Phase 20: Base Evaluator Interface
"""

import abc
import sqlite3
from typing import Optional
from backend.app.evaluation.schemas import DimensionEvaluationResult, EvaluationDimension


class BaseEvaluator(abc.ABC):
    """Abstract base evaluator for reproducible benchmarking of an R5 dimension."""

    @property
    @abc.abstractmethod
    def dimension(self) -> EvaluationDimension:
        """The evaluation dimension evaluated by this class."""
        pass

    @property
    @abc.abstractmethod
    def dimension_name(self) -> str:
        """Human-readable dimension name."""
        pass

    @abc.abstractmethod
    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        """Execute evaluation against synthetic benchmark dataset and return measured metrics."""
        pass

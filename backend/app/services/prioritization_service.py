from typing import Dict, Any, Optional

class PrioritizationService:
    DEFAULT_WEIGHTS = {
        "severity": 0.25,
        "urgency": 0.20,
        "operational_impact": 0.15,
        "safety": 0.20,
        "growth": 0.10,
        "geographic_spread": 0.05,
        "recurrence": 0.05
    }

    @staticmethod
    def calculate_explainable_priority(
        severity: float,                # 0.0 to 1.0
        urgency: float,                 # 0.0 to 1.0
        operational_impact: float,      # 0.0 to 1.0
        is_safety_hazard: bool,         # True / False
        growth_velocity: float = 0.0,   # Z-score or normalized rate 0.0 to 3.0+
        stores_affected_count: int = 1, # 1, 2, 3+
        recurrence_count: int = 0,      # 0, 1, 2+
        confidence: float = 0.85,       # 0.0 to 1.0
        observation_count: int = 1,     # Raw report count
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Deterministic, explainable operational prioritization engine.
        Ensures frequency alone never dictates priority.
        Safety and severity override raw volume.
        """
        w = weights or PrioritizationService.DEFAULT_WEIGHTS

        # Normalize components to 0.0 - 1.0 scale
        norm_severity = max(0.0, min(1.0, severity))
        norm_urgency = max(0.0, min(1.0, urgency))
        norm_impact = max(0.0, min(1.0, operational_impact))
        norm_safety = 1.0 if is_safety_hazard else 0.0

        # Growth signal (capped at 1.0 for z-score >= 3.0)
        norm_growth = max(0.0, min(1.0, growth_velocity / 3.0))

        # Geographic spread (1 store = 0.2, 2 stores = 0.6, 3+ stores = 1.0)
        norm_geo = min(1.0, (stores_affected_count - 1) * 0.4 + 0.2)

        # Recurrence (0 = 0.0, 1 = 0.5, 2+ = 1.0)
        norm_recurrence = min(1.0, recurrence_count * 0.5)

        # Calculate factor contributions (each contributes up to 100 * weight)
        contrib_severity = round(100.0 * w["severity"] * norm_severity, 2)
        contrib_urgency = round(100.0 * w["urgency"] * norm_urgency, 2)
        contrib_impact = round(100.0 * w["operational_impact"] * norm_impact, 2)
        contrib_safety = round(100.0 * w["safety"] * norm_safety, 2)
        contrib_growth = round(100.0 * w["growth"] * norm_growth, 2)
        contrib_geo = round(100.0 * w["geographic_spread"] * norm_geo, 2)
        contrib_recurrence = round(100.0 * w["recurrence"] * norm_recurrence, 2)

        raw_score = (
            contrib_severity +
            contrib_urgency +
            contrib_impact +
            contrib_safety +
            contrib_growth +
            contrib_geo +
            contrib_recurrence
        )

        # Confidence and uncertainty adjustments:
        # If confidence is low (< 0.70), apply a dampening discount because evidence is weak/unconfirmed
        confidence_discount = 0.0
        uncertainty_score = round(max(0.0, 1.0 - confidence), 2)
        if confidence < 0.70:
            confidence_discount = round((0.70 - confidence) * 30.0, 2)
            raw_score -= confidence_discount

        # Direct Safety Floor:
        # A confirmed safety hazard with high severity MUST guarantee at least P2_HIGH (score >= 70)
        # regardless of whether observation_count is only 1
        if is_safety_hazard and norm_severity >= 0.8:
            raw_score = max(raw_score, 85.0)
        elif is_safety_hazard and norm_severity >= 0.5:
            raw_score = max(raw_score, 72.0)

        # Frequency ceiling for low severity:
        # If severity is low (< 0.3) and safety is false, frequency alone CANNOT trigger P1 or P2
        if norm_severity < 0.30 and not is_safety_hazard:
            raw_score = min(raw_score, 55.0)  # Capped at P3_MEDIUM

        final_score = max(1, min(100, round(raw_score)))

        # Determine Priority Tier
        if final_score >= 85:
            tier = "P1_CRITICAL"
        elif final_score >= 70:
            tier = "P2_HIGH"
        elif final_score >= 45:
            tier = "P3_MEDIUM"
        else:
            tier = "P4_LOW"

        # Generate deterministic, traceable natural language explanation
        explanation_parts = []
        if is_safety_hazard:
            explanation_parts.append(f"Confirmed safety hazard (+{contrib_safety:.1f} pts)")
        if norm_severity >= 0.7:
            explanation_parts.append(f"high operational severity (+{contrib_severity:.1f} pts)")
        elif norm_severity < 0.3:
            explanation_parts.append("low severity (score capped to prevent volume inflation)")

        if norm_growth >= 0.5:
            explanation_parts.append(f"rapid acceleration vs baseline (+{contrib_growth:.1f} pts, velocity +{growth_velocity:.1f}z)")

        if stores_affected_count > 1:
            explanation_parts.append(f"cross-store propagation across {stores_affected_count} stores (+{contrib_geo:.1f} pts)")

        if recurrence_count > 0:
            explanation_parts.append(f"recurrent failure pattern (+{contrib_recurrence:.1f} pts)")

        if confidence < 0.70:
            explanation_parts.append(f"dampened by high uncertainty / low confidence (-{confidence_discount:.1f} pts discount)")

        if not explanation_parts:
            explanation_parts.append(f"routine operational telemetry ({observation_count} observation(s))")

        explanation = f"Priority {tier} ({final_score}/100) driven by: " + "; ".join(explanation_parts) + "."

        return {
            "priorityScore": final_score,
            "priorityTier": tier,
            "factorContributions": {
                "severity": contrib_severity,
                "urgency": contrib_urgency,
                "operationalImpact": contrib_impact,
                "safety": contrib_safety,
                "growth": contrib_growth,
                "geographicSpread": contrib_geo,
                "recurrence": contrib_recurrence
            },
            "confidenceDiscount": confidence_discount,
            "uncertaintyScore": uncertainty_score,
            "explainableSummary": explanation,
            "evidenceMetrics": {
                "rawSeverity": severity,
                "rawUrgency": urgency,
                "rawImpact": operational_impact,
                "isSafetyHazard": is_safety_hazard,
                "growthVelocityZ": growth_velocity,
                "storesCount": stores_affected_count,
                "recurrenceCount": recurrence_count,
                "observationCount": observation_count,
                "confidence": confidence
            }
        }

"""
Transparent Land Intelligence Risk Scoring Engine.

Calculates an objective, explainable risk score (0 to 100) based on documented
discrepancies, statutory restrictions, and data reliability factors:

Risk Weights:
- Document Inconsistency / Hash Mismatch: +25
- Identity / Record Mismatch:            +20
- Area Mismatch Across Sources:          +20
- Statutory Restriction Indicator:       +20
- Recent Unexplained Physical Change:    +10
- Source Reliability / Provenance Issue: +10

Categories:
0–20:   LOW
21–50:  MEDIUM
51–75:  HIGH
76–100: CRITICAL

CRITICAL PRINCIPLE:
The risk score is strictly an investigative prioritization tool.
It NEVER declares 'FRAUD CONFIRMED'. It highlights potential inconsistencies
requiring manual verification by qualified revenue officers.
"""

from typing import List, Optional

from app.osint.schemas import (
    ConflictRecord,
    RestrictionFlag,
    RiskAssessment,
    RiskCategory,
    RiskFactor,
    SourceRecordEntry,
    TimelineEvent,
)


class RiskEngine:
    """Computes transparent, itemized risk scores for land parcels."""

    def evaluate_risk(
        self,
        conflicts: List[ConflictRecord],
        restrictions: List[RestrictionFlag],
        timeline: List[TimelineEvent],
        sources: List[SourceRecordEntry],
        document_matched: Optional[bool] = None,
    ) -> RiskAssessment:
        factors: List[RiskFactor] = []
        score = 0

        # 1. Document Inconsistency (+25)
        if document_matched is False:
            points = 25
            score += points
            factors.append(
                RiskFactor(
                    category="Document Inconsistency",
                    points_added=points,
                    description="Uploaded document details or fingerprint do not reconcile with verified public records.",
                    evidence_reference="Document OCR Cross-Check Engine",
                )
            )

        # 2. Area Mismatch (+20)
        has_area_conflict = any(c.field_name == "area_hectares" for c in conflicts)
        if has_area_conflict:
            points = 20
            score += points
            factors.append(
                RiskFactor(
                    category="Area Mismatch",
                    points_added=points,
                    description="Recorded land extent varies significantly between revenue database and physical/OSM footprint.",
                    evidence_reference="Cross-Source Conflict Detection Matrix",
                )
            )

        # 3. Identity / Classification / Tenure Record Mismatch (+20)
        has_identity_or_class = any(c.field_name in ("land_classification", "tenure_type") for c in conflicts)
        if has_identity_or_class:
            points = 20
            score += points
            factors.append(
                RiskFactor(
                    category="Classification / Tenure Mismatch",
                    points_added=points,
                    description="Discrepancy detected between statutory land classification and observed physical land use.",
                    evidence_reference="Cadastral vs Remote-Sensing Classification Check",
                )
            )

        # 4. Statutory Restriction Indicator (+20)
        if restrictions:
            points = 20
            score += points
            factors.append(
                RiskFactor(
                    category="Statutory Restriction Indicator",
                    points_added=points,
                    description=f"{len(restrictions)} jurisdiction restrictions active (e.g., tribal land protection, highway corridor, or forest buffer).",
                    evidence_reference=f"LandRestrictionRuleEngine: {restrictions[0].rule_id}",
                )
            )

        # 5. Recent Unexplained Physical Change (+10)
        recent_changes = [e for e in timeline if e.significant_change_flag and e.year >= 2021]
        if recent_changes:
            points = 10
            score += points
            factors.append(
                RiskFactor(
                    category="Recent Physical Change Detected",
                    points_added=points,
                    description="Satellite time-series indicates recent ground-clearing, road carving, or structural changes.",
                    evidence_reference=f"Sentinel-2 Historical Epoch Analysis ({recent_changes[0].year})",
                )
            )

        # 6. Source Reliability Issue (+10)
        if not sources or any(s.provenance.confidence_stars <= 2 for s in sources):
            points = 10
            score += points
            factors.append(
                RiskFactor(
                    category="Source Reliability Limitation",
                    points_added=points,
                    description="One or more records depend on low-confidence or third-party datasets requiring primary field verification.",
                    evidence_reference="Data Provenance Engine",
                )
            )

        # Clamp score to 100 max
        final_score = min(100, max(0, score))

        # Categorize
        if final_score <= 20:
            category = RiskCategory.LOW
            summary = "LOW RISK: Public revenue records appear generally consistent with minor normal survey variances."
        elif final_score <= 50:
            category = RiskCategory.MEDIUM
            summary = "MODERATE INCONSISTENCY: Discrepancies observed in area or physical changes requiring routine verification."
        elif final_score <= 75:
            category = RiskCategory.HIGH
            summary = "ELEVATED RISK: Significant area variance or statutory land-use restrictions require formal revenue clearance."
        else:
            category = RiskCategory.CRITICAL
            summary = "CRITICAL INCONSISTENCY: Multiple conflicts, unverified document details, or severe statutory restrictions detected."

        return RiskAssessment(
            score=final_score,
            category=category,
            risk_factors=factors,
            summary=summary,
        )

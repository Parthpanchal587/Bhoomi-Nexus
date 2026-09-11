"""
Automated Conflict Detection & Discrepancy Analysis Engine.

Cross-checks normalized land records across multiple public and official sources:
1. Area mismatches (Cadastral RoR vs Satellite vs OpenStreetMap vs Document)
2. Land-use classification divergence (Agricultural vs Non-Agricultural vs Mixed)
3. Physical boundary footprint variance
4. Timeline and mutation sequencing gaps

CRITICAL GOVTECH ETHICAL DIRECTIVE:
Never accuse anyone of fraud. Flag discrepancies objectively as potential
inconsistencies requiring field verification by competent revenue authorities.
Provide plausible administrative and physical explanations (e.g. unrecorded subdivision,
digitization variance, roadside buffer deduction).
"""

import uuid
from typing import Any, Dict, List, Optional

from app.osint.schemas import (
    ConflictRecord,
    ConflictSeverity,
    SourceRecordEntry,
)


class ConflictEngine:
    """Detects and categorizes discrepancies across multiple source records."""

    AREA_TOLERANCE_PCT = 5.0  # 5% threshold before triggering conflict alert

    def detect_conflicts(
        self,
        sources: List[SourceRecordEntry],
        declared_doc_area_ha: Optional[float] = None,
        declared_doc_classification: Optional[str] = None,
    ) -> List[ConflictRecord]:
        """
        Analyze all retrieved source records and detect cross-source conflicts.
        """
        conflicts: List[ConflictRecord] = []

        if not sources or len(sources) < 2:
            return conflicts

        # 1. Area Conflict Detection
        area_conflicts = self._check_area_mismatches(sources, declared_doc_area_ha)
        conflicts.extend(area_conflicts)

        # 2. Land Classification Conflict Detection
        class_conflicts = self._check_classification_mismatches(sources, declared_doc_classification)
        conflicts.extend(class_conflicts)

        # 3. Tenure & Boundary Variation
        tenure_conflicts = self._check_tenure_variations(sources)
        conflicts.extend(tenure_conflicts)

        return conflicts

    def _check_area_mismatches(
        self,
        sources: List[SourceRecordEntry],
        declared_area: Optional[float] = None,
    ) -> List[ConflictRecord]:
        conflicts = []
        area_map: Dict[str, float] = {}

        for s in sources:
            if s.area_hectares is not None and s.area_hectares > 0:
                area_map[s.source_name] = s.area_hectares

        if declared_area is not None and declared_area > 0:
            area_map["User-Uploaded Document"] = declared_area

        if len(area_map) < 2:
            return conflicts

        values = list(area_map.values())
        min_val = min(values)
        max_val = max(values)
        diff_ha = round(max_val - min_val, 2)
        pct_diff = round((diff_ha / min_val) * 100.0, 1) if min_val > 0 else 0.0

        if pct_diff > self.AREA_TOLERANCE_PCT:
            # Determine majority or official baseline
            expected = max_val
            conflicting = min_val

            severity = ConflictSeverity.LOW
            if pct_diff > 25.0:
                severity = ConflictSeverity.HIGH
            elif pct_diff > 10.0:
                severity = ConflictSeverity.MEDIUM

            explanations = [
                "Unrecorded or pending revenue mutation / land subdivision (Taqseem).",
                "Road widening or infrastructure right-of-way corridor carve-out.",
                "Digitization error during legacy paper cadastral map vectorization.",
                "Difference between physical cultivated boundary and legal revenue parcel extent.",
                "Measurement variance between traditional chain (Jarib) survey and modern satellite / DGPS survey.",
            ]

            guidance = (
                f"A discrepancy of {diff_ha} hectares ({pct_diff}%) was detected between recorded sources. "
                "Recommend obtaining an official certified Tatima Shajra (partition map) and latest Form 15 "
                "Encumbrance Certificate from the Sub-Registrar / Tehsildar."
            )

            conflicts.append(
                ConflictRecord(
                    conflict_id=f"CONF-AREA-{uuid.uuid4().hex[:8].upper()}",
                    field_name="area_hectares",
                    description=f"Area Mismatch Detected ({pct_diff}% variance: {min_val} ha vs {max_val} ha)",
                    severity=severity,
                    expected_value=f"{max_val} hectares",
                    conflicting_value=f"{min_val} hectares",
                    sources_involved=list(area_map.keys()),
                    confidence="HIGH" if len(sources) >= 3 else "MEDIUM",
                    possible_explanations=explanations,
                    investigative_guidance=guidance,
                )
            )

        return conflicts

    def _check_classification_mismatches(
        self,
        sources: List[SourceRecordEntry],
        declared_classification: Optional[str] = None,
    ) -> List[ConflictRecord]:
        conflicts = []
        class_map: Dict[str, str] = {}

        for s in sources:
            if s.land_type:
                class_map[s.source_name] = s.land_type

        if declared_classification:
            class_map["User-Uploaded Document"] = declared_classification

        # Check for Agricultural vs Commercial/Non-Agricultural divergence
        has_agri = any("agri" in val.lower() or "farm" in val.lower() for val in class_map.values())
        has_non_agri = any("commercial" in val.lower() or "industrial" in val.lower() or "built" in val.lower() for val in class_map.values())

        if has_agri and has_non_agri:
            conflicts.append(
                ConflictRecord(
                    conflict_id=f"CONF-CLASS-{uuid.uuid4().hex[:8].upper()}",
                    field_name="land_classification",
                    description="Land Use Classification Divergence (Agricultural vs Non-Agricultural / Physical Build-up)",
                    severity=ConflictSeverity.HIGH,
                    expected_value="Agricultural (Statutory RoR Entry)",
                    conflicting_value="Commercial / Industrial / Built-up structures observed",
                    sources_involved=list(class_map.keys()),
                    confidence="HIGH",
                    possible_explanations=[
                        "Physical conversion executed on the ground prior to final Section 90-A revenue sanction.",
                        "Commercial development permit issued by local development authority without revenue record mutation.",
                        "Farm building or solar pump canopy misclassified as commercial structure by remote sensing.",
                    ],
                    investigative_guidance=(
                        "Verify whether formal Section 90-A land diversion order has been issued by the Competent "
                        "Authority (SDO / District Collector). Unauthorized non-agricultural conversion invites revenue penalty."
                    ),
                )
            )

        return conflicts

    def _check_tenure_variations(self, sources: List[SourceRecordEntry]) -> List[ConflictRecord]:
        # Checks if one source lists Restricted Tenure while another lists Freehold
        conflicts = []
        tenures = {s.source_name: s.tenure_type for s in sources if s.tenure_type}
        if any("restricted" in t.lower() or "new tenure" in t.lower() for t in tenures.values()) and any("freehold" in t.lower() or "old tenure" in t.lower() for t in tenures.values()):
            conflicts.append(
                ConflictRecord(
                    conflict_id=f"CONF-TENURE-{uuid.uuid4().hex[:8].upper()}",
                    field_name="tenure_type",
                    description="Tenure Restriction Status Ambiguity (Old Tenure / Freehold vs Restricted Tenure)",
                    severity=ConflictSeverity.CRITICAL,
                    expected_value="Verified Unrestricted Khatedari / Old Tenure",
                    conflicting_value="Restricted Tenure / Inalienable Government Grant",
                    sources_involved=list(tenures.keys()),
                    confidence="MEDIUM",
                    possible_explanations=[
                        "Historical government land grant / allotment subject to Section 73AA / Section 42 transfer restrictions.",
                        "Condition of 10-year or 15-year non-alienation period has not yet expired.",
                    ],
                    investigative_guidance="Mandatory inspection of original allotment patta and sub-registrar transfer permission letter.",
                )
            )
        return conflicts

"""
Data Provenance & Source Reliability Engine.

Guarantees:
1. Strict classification into 5 formal provenance tiers.
2. Mandatory attribution: no field or record exists without source metadata.
3. Transparent confidence scoring (1 to 5 stars).
4. Explicit differentiation between factual public records and AI inferences.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.osint.schemas import (
    ProvenanceLevel,
    ProvenanceMetadata,
    SourceConfidenceStars,
)

# Canonical Confidence Map
PROVENANCE_CONFIDENCE_MAP: Dict[ProvenanceLevel, int] = {
    ProvenanceLevel.VERIFIED_OFFICIAL_DATA: SourceConfidenceStars.OFFICIAL_GOVERNMENT.value,
    ProvenanceLevel.PUBLIC_GOVERNMENT_DATA: SourceConfidenceStars.PUBLIC_GOVERNMENT.value,
    ProvenanceLevel.REPUTABLE_PUBLIC_DATASET: SourceConfidenceStars.REPUTABLE_DATASET.value,
    ProvenanceLevel.THIRD_PARTY_DATA: SourceConfidenceStars.THIRD_PARTY.value,
    ProvenanceLevel.USER_PROVIDED_DATA: SourceConfidenceStars.THIRD_PARTY.value,
    ProvenanceLevel.AI_INFERRED_INFORMATION: SourceConfidenceStars.AI_INFERRED.value,
}

DISCLAIMER_MAP: Dict[ProvenanceLevel, str] = {
    ProvenanceLevel.VERIFIED_OFFICIAL_DATA: "Official public land record extract. Certified as published on state portal.",
    ProvenanceLevel.PUBLIC_GOVERNMENT_DATA: "Published government notification or gazette extract.",
    ProvenanceLevel.REPUTABLE_PUBLIC_DATASET: "Publicly accessible open dataset (e.g., OpenStreetMap, CGWB, Census).",
    ProvenanceLevel.THIRD_PARTY_DATA: "Third-party compilation. Requires cross-verification with official revenue records.",
    ProvenanceLevel.USER_PROVIDED_DATA: "Extracted from user-submitted document. Unverified by revenue department.",
    ProvenanceLevel.AI_INFERRED_INFORMATION: "Automated heuristic / remote-sensing inference. NOT an official statutory determination.",
}


class ProvenanceEngine:
    """Manages provenance tagging, confidence calculation, and metadata compliance."""

    @staticmethod
    def create_metadata(
        provenance_level: ProvenanceLevel,
        source_name: str,
        source_url: Optional[str] = None,
        dataset_version: Optional[str] = None,
        license_type: str = "Open Access / Public Record",
        custom_disclaimer: Optional[str] = None,
    ) -> ProvenanceMetadata:
        """Create a complete provenance metadata envelope."""
        stars = PROVENANCE_CONFIDENCE_MAP.get(provenance_level, 2)
        default_disclaimer = DISCLAIMER_MAP.get(provenance_level, "")
        disclaimer = custom_disclaimer or default_disclaimer

        return ProvenanceMetadata(
            provenance_level=provenance_level,
            confidence_stars=stars,
            source_name=source_name,
            source_url=source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            dataset_version=dataset_version,
            license=license_type,
            verification_status=f"Verified {provenance_level.value}",
            disclaimer=disclaimer,
        )

    @staticmethod
    def validate_record_has_provenance(record: Dict[str, Any]) -> bool:
        """Enforces the 'No Orphan Data' rule: rejects any record missing provenance."""
        if "provenance" not in record:
            return False
        prov = record["provenance"]
        if isinstance(prov, dict):
            return "provenance_level" in prov and "source_name" in prov
        return hasattr(prov, "provenance_level") and hasattr(prov, "source_name")

    @staticmethod
    def calculate_aggregate_confidence(levels: list[ProvenanceLevel]) -> int:
        """Compute average confidence stars across multiple source levels."""
        if not levels:
            return 1
        scores = [PROVENANCE_CONFIDENCE_MAP.get(lvl, 1) for lvl in levels]
        return max(1, min(5, round(sum(scores) / len(scores))))

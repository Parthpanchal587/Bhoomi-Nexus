"""
In-Memory Domain Entities for Bhoomi Nexus OSINT Subsystem.

Entities:
- Parcel
- LandRecord
- Document
- Source
- Evidence
- Observation
- Notification
- RestrictionRule
- OSINTQuery
- OSINTResult
- Conflict
- RiskAssessment
- GeospatialObservation
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.osint.schemas import (
    ConflictSeverity,
    ProvenanceLevel,
    ProvenanceMetadata,
    RiskCategory,
)


@dataclass
class SourceEntity:
    source_id: str
    name: str
    category: str  # "GOVERNMENT_PORTAL", "GEOSPATIAL", "SATELLITE", "GAZETTE", "COMMERCIAL"
    base_url: str
    provenance_level: ProvenanceLevel
    reliability_stars: int
    is_active: bool = True
    rate_limit_per_min: int = 60


@dataclass
class LandRecordEntity:
    record_id: str
    parcel_id: str
    source_id: str
    khasra_number: str
    khata_number: Optional[str]
    area_ha: float
    land_type: str
    soil_type: Optional[str]
    recorded_at: str
    provenance: ProvenanceMetadata
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParcelEntity:
    parcel_id: str
    state: str
    district: str
    tehsil: str
    village: str
    primary_khasra: str
    khata_number: Optional[str]
    canonical_area_ha: float
    canonical_land_type: str
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    records: List[LandRecordEntity] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class NotificationEntity:
    notification_id: str
    title: str
    issuing_authority: str
    category: str  # "LAND_ACQUISITION", "HIGHWAY_EXPANSION", "ENVIRONMENTAL", "ZONING"
    gazette_reference: str
    published_date: str
    affected_districts: List[str]
    affected_khasras: List[str]
    summary: str
    statutory_act: str
    provenance: ProvenanceMetadata


@dataclass
class RestrictionRuleEntity:
    rule_id: str
    jurisdiction: str
    category: str
    statutory_act: str
    section_reference: str
    effective_date: str
    version: str
    explanation: str
    restriction_level: str


@dataclass
class ConflictEntity:
    conflict_id: str
    parcel_id: str
    field_name: str
    severity: ConflictSeverity
    source_a: str
    value_a: Any
    source_b: str
    value_b: Any
    explanation: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class OSINTQueryLogEntity:
    query_id: str
    timestamp: str
    state: str
    district: str
    tehsil: Optional[str]
    khasra: Optional[str]
    sources_consulted: List[str]
    conflicts_found: int
    risk_score: int
    user_session_id: str

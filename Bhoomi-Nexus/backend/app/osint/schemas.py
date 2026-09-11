"""
OSINT & Public-Source Land Intelligence Schemas.

Strictly typed Pydantic data contracts for:
- Data Provenance Levels (Public, Official, Third-party, User-provided, AI-inferred)
- Land Parcel Queries
- Canonical Normalized Land Parcel Records
- Evidence Graph Nodes & Edges
- Conflict Detection Records
- Risk Assessments & Breakdown
- Jurisdiction Restriction Rules
- Temporal Timeline Events
- Satellite Remote-Sensing Observations
- Comprehensive Land Intelligence Evidence Reports
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Provenance Taxonomy ───────────────────────────────────────────────────

class ProvenanceLevel(str, Enum):
    """
    Formal classification of data provenance.
    Strictly distinguishes facts from inferences.
    """
    VERIFIED_OFFICIAL_DATA = "VERIFIED_OFFICIAL_DATA"  # Direct official state revenue record
    PUBLIC_GOVERNMENT_DATA = "PUBLIC_GOVERNMENT_DATA"  # Gazettes, notifications, published portals
    REPUTABLE_PUBLIC_DATASET = "REPUTABLE_PUBLIC_DATASET"  # OpenStreetMap, ISRO SAC, CGWB, Census
    THIRD_PARTY_DATA = "THIRD_PARTY_DATA"              # Aggregated indices, municipal listings
    USER_PROVIDED_DATA = "USER_PROVIDED_DATA"          # Uploaded deeds, submitted survey numbers
    AI_INFERRED_INFORMATION = "AI_INFERRED_INFORMATION"# Machine learning classification or heuristic


class SourceConfidenceStars(int, Enum):
    """Confidence rating rubric based on source provenance."""
    OFFICIAL_GOVERNMENT = 5      # ★★★★★
    PUBLIC_GOVERNMENT = 4        # ★★★★☆
    REPUTABLE_DATASET = 4        # ★★★★☆
    SATELLITE_OBSERVATION = 3    # ★★★☆☆
    THIRD_PARTY = 2              # ★★☆☆☆
    AI_INFERRED = 1              # ★☆☆☆☆


class ProvenanceMetadata(BaseModel):
    """Provenance tracking envelope for every data point."""
    provenance_level: ProvenanceLevel
    confidence_stars: int = Field(ge=1, le=5)
    source_name: str
    source_url: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dataset_version: Optional[str] = None
    license: str = "Open Access / Public Record"
    verification_status: str = "Verified Source Match"
    disclaimer: Optional[str] = None


# ── Search & Parcel Queries ───────────────────────────────────────────────

class OSINTSearchQuery(BaseModel):
    """Input query for land intelligence search."""
    state: str = Field(..., description="Indian State (e.g., Rajasthan, Madhya Pradesh, Gujarat)")
    district: str = Field(..., description="District name")
    tehsil: Optional[str] = Field(None, description="Tehsil / Taluk name")
    village: Optional[str] = Field(None, description="Village / Mouza name")
    khasra_number: Optional[str] = Field(None, description="Khasra / Survey Number (e.g. 124/2 or KHA-7829)")
    khata_number: Optional[str] = Field(None, description="Khata / Account Number")
    plot_number: Optional[str] = Field(None, description="Plot / Property Identifier")
    property_id: Optional[str] = Field(None, description="Unique Property ID or ULPIN")
    latitude: Optional[float] = Field(None, description="Centroid Latitude")
    longitude: Optional[float] = Field(None, description="Centroid Longitude")
    document_reference: Optional[str] = Field(None, description="Deed, mutation, or registration reference")
    use_demo_fallback: bool = Field(True, description="Use clearly labelled demo data if live portal unreachable")


# ── Canonical Land Parcel ─────────────────────────────────────────────────

class SourceRecordEntry(BaseModel):
    """Snapshot of land parcel data retrieved from a specific provider."""
    source_id: str
    source_name: str
    provenance: ProvenanceMetadata
    khasra_number: str
    khata_number: Optional[str] = None
    area_hectares: Optional[float] = None
    area_acres: Optional[float] = None
    land_type: Optional[str] = None
    soil_type: Optional[str] = None
    tenure_type: Optional[str] = None
    recorded_date: Optional[str] = None
    coordinates: Optional[List[List[float]]] = None
    raw_attributes: Dict[str, Any] = Field(default_factory=dict)


class CanonicalLandParcel(BaseModel):
    """
    Normalized, cross-source canonical representation of a land parcel.
    """
    parcel_id: str
    state: str
    district: str
    tehsil: str
    village: str
    primary_khasra: str
    khata_number: Optional[str] = None
    normalized_area_ha: float
    normalized_area_acres: float
    land_classification: str
    soil_category: Optional[str] = None
    boundary_coordinates: List[List[float]] = Field(default_factory=list)
    centroid: Optional[Dict[str, float]] = None
    provenance: ProvenanceMetadata
    sources_consulted: List[str] = Field(default_factory=list)


# ── Conflict Detection ────────────────────────────────────────────────────

class ConflictSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConflictRecord(BaseModel):
    """Automated discrepancy detected across multiple sources."""
    conflict_id: str
    field_name: str  # e.g., "area_hectares", "land_classification", "boundary_closure"
    description: str
    severity: ConflictSeverity
    expected_value: Any
    conflicting_value: Any
    sources_involved: List[str]
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    possible_explanations: List[str]
    investigative_guidance: str


# ── Risk Assessment ───────────────────────────────────────────────────────

class RiskCategory(str, Enum):
    LOW = "LOW"            # 0–20
    MEDIUM = "MEDIUM"      # 21–50
    HIGH = "HIGH"          # 51–75
    CRITICAL = "CRITICAL"  # 76–100


class RiskFactor(BaseModel):
    """Individual risk contribution item."""
    category: str
    points_added: int
    description: str
    evidence_reference: str


class RiskAssessment(BaseModel):
    """Transparent risk scoring evaluation."""
    score: int = Field(ge=0, le=100)
    category: RiskCategory
    risk_factors: List[RiskFactor]
    summary: str
    investigative_notice: str = (
        "This risk score is an automated investigative prioritization indicator. "
        "It reflects documented discrepancies and restrictions requiring manual verification. "
        "It does NOT constitute legal proof of fraud or irregular title."
    )


# ── Land Restrictions ─────────────────────────────────────────────────────

class RestrictionFlag(BaseModel):
    """Statutory or regulatory land-use restriction flag."""
    rule_id: str
    jurisdiction: str
    category: str  # "SC_ST_TRIBAL_LAND", "HIGHWAY_BUFFER", "FOREST_ECO_SENSITIVE", "WATER_BODY"
    title: str
    statutory_reference: str
    effective_date: str
    version: str
    explanation: str
    restriction_level: str  # "PROHIBITED", "STATUTORY_SANCTION_REQUIRED", "BUFFER_OFFSET"
    verification_status: str = "Requires Competent Authority Verification"


# ── Geospatial & Satellite Observations ───────────────────────────────────

class GeospatialObservation(BaseModel):
    """Physical observation from satellite or open geospatial sources."""
    observation_id: str
    layer_name: str
    source: str
    observation_date: str
    resolution: str
    coordinates: List[List[float]]
    observed_land_use: str
    vegetation_index_ndvi: Optional[float] = None
    water_presence: bool = False
    built_up_structures_detected: bool = False
    license: str
    disclaimer: str = "Remote-sensing physical observation — requires official revenue verification."


# ── Temporal Timeline ─────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    """Chronological event in the parcel's lifecycle."""
    year: int
    event_date: str
    event_type: str  # "SURVEY_RECORD", "MUTATION", "SUBDIVISION", "DIVERSION", "SATELLITE_CHANGE"
    title: str
    recorded_area_ha: Optional[float] = None
    description: str
    source: str
    provenance: ProvenanceLevel
    significant_change_flag: bool = False


# ── Evidence Graph ────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    node_type: str  # "PARCEL", "KHASRA_RECORD", "MUTATION", "REGISTRATION", "NOTIFICATION", "SATELLITE_EVIDENCE", "DOCUMENT"
    source: str
    date: Optional[str] = None
    confidence_stars: int
    data: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str  # "RECORDS", "MODIFIED_BY", "BOUNDED_BY", "NOTIFIED_IN", "EVIDENCED_BY", "CONFLICTS_WITH"
    label: str


class EvidenceGraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ── Document Intelligence ─────────────────────────────────────────────────

class DocumentCrossCheckRequest(BaseModel):
    document_text: str
    filename: str
    file_bytes_base64: Optional[str] = None
    declared_khasra: Optional[str] = None
    declared_area_ha: Optional[float] = None


class DocumentCrossCheckResult(BaseModel):
    document_hash_sha256: str
    ocr_fingerprint_sha256: str
    extracted_fields: Dict[str, Any]
    public_record_match: bool
    status: str  # "MATCH", "DATA_CONFLICT", "RECORD_NOT_FOUND"
    match_details: List[str]
    conflicts_detected: List[ConflictRecord]
    hash_disclaimer: str = (
        "SHA-256 fingerprint validates the cryptographic uniqueness of this uploaded file. "
        "It does NOT prove legal validity or statutory registration."
    )


# ── Full Land Intelligence Report ─────────────────────────────────────────

class LandIntelligenceReport(BaseModel):
    """Complete compiled public-source intelligence dossier."""
    report_id: str
    generated_at: str
    query: OSINTSearchQuery
    parcel: CanonicalLandParcel
    source_snapshots: List[SourceRecordEntry]
    conflicts: List[ConflictRecord]
    restrictions: List[RestrictionFlag]
    risk_assessment: RiskAssessment
    geospatial_observations: List[GeospatialObservation]
    timeline: List[TimelineEvent]
    evidence_graph: EvidenceGraphData
    overall_confidence_stars: int
    provenance_summary: Dict[str, int]
    legal_notice: str = (
        "AUTOMATED INTELLIGENCE NOTICE: This dossier is compiled from publicly accessible records, "
        "satellite observations, and open datasets for research and due-diligence prioritization. "
        "It does NOT constitute an official title certificate or judicial determination. "
        "Final verification must be obtained from the competent Sub-Registrar and Revenue Authorities."
    )

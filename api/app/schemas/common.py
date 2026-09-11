"""
Shared / common Pydantic schemas used across multiple modules.
These were extracted from the original monolithic main.py.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Health ────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    node_id: str
    service: str
    version: str
    timestamp: str
    uptime_seconds: float
    blockchain_blocks: int
    latest_block_hash: str


# ── Geo Search ────────────────────────────────────────────────────────────

class GeoSearchResult(BaseModel):
    place_id: int | str
    name: str
    display_name: str
    lat: float
    lon: float
    type: str
    importance: float
    boundingbox: list[str]


# ── Telemetry ─────────────────────────────────────────────────────────────

class TelemetryResponse(BaseModel):
    latitude: float
    longitude: float
    timestamp: str
    surface_temperature_c: Optional[float] = None
    soil_temperature_10cm_c: Optional[float] = None
    soil_moisture_volumetric: Optional[float] = None
    soil_moisture_percentage: Optional[float] = None
    ambient_temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    precipitation_mm: Optional[float] = 0.0
    rain_mm: Optional[float] = 0.0
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    soil_moisture_depths: Optional[dict[str, Any]] = None
    soil_temperature_depths: Optional[dict[str, Any]] = None
    elevation_m: float = 0.0
    aridity_status: str
    cadastral_crop_suitability: str
    data_source: str
    provenance: Optional[dict[str, Any]] = None
    status: str = "success"


# ── Land Conversion Simulation ────────────────────────────────────────────

class SimulationRequest(BaseModel):
    parcel_id: str = Field(default="PARCEL-CUSTOM")
    total_hectares: float = Field(default=10.0, ge=0.1)
    converted_hectares: float = Field(default=4.0, ge=0.0)
    conversion_type: str = Field(default="industrial")
    baseline_yield_per_ha: float = Field(default=38.5, ge=1.0)
    crop_type: str = Field(default="Wheat / Mustard")
    water_table_depth_m: float = Field(default=32.0, ge=0.5)


class SimulationResponse(BaseModel):
    parcel_id: str
    total_hectares: float
    converted_hectares: float
    retained_agricultural_ha: float
    conversion_type: str
    crop_type: str
    yield_deficit_quintals: float
    yield_deficit_metric_tons: float
    economic_crop_loss_inr: float
    groundwater_daily_consumption_kl: float
    groundwater_pressure_index: float
    aquifer_drawdown_risk: str
    base_stamp_duty_inr: float
    infrastructure_cess_inr: float
    total_tariff_inr: float
    statutory_clearance_code: str
    compliance_advisory: str


# ── Blockchain Notarization ───────────────────────────────────────────────

class NotarizeRequest(BaseModel):
    parcel_id: str
    owner_name: str = "Shri R. K. Sharma"
    state: str = "Rajasthan"
    district: str = "Jaipur"
    coordinates: dict[str, float] = Field(default_factory=lambda: {"lat": 26.8392, "lon": 75.6811})
    area_hectares: float = 18.0
    zoning_status: str = "NON-AGRICULTURAL (INDUSTRIAL DIVERSION APPROVED)"
    simulation_summary: Optional[dict[str, Any]] = None
    telemetry_snapshot: Optional[dict[str, Any]] = None
    notarized_by: str = "NIC Cadastral Officer - Class I"


class Block(BaseModel):
    index: int
    block_index: Optional[int] = None
    timestamp: str
    parcel_id: str
    data: dict[str, Any]
    previous_hash: str
    hash: str
    nonce: int

    def __init__(self, **data: Any):
        if "block_index" not in data or data["block_index"] is None:
            data["block_index"] = data.get("index")
        super().__init__(**data)


class LedgerResponse(BaseModel):
    chain_valid: bool
    total_blocks: int
    latest_block_hash: str
    blocks: list[Block]


# ── AI Search (Ask BHOOMI — existing) ────────────────────────────────────

class AIQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language query, e.g., 'Why is land degradation increasing in some areas of Rajasthan?'")
    focus_region: Optional[str] = "Rajasthan"
    api_key: Optional[str] = None


class SourceCitation(BaseModel):
    id: str
    title: str
    agency: str
    year: int
    doi_or_doc: str
    category: str
    key_finding: str


class CompetitiveAdvantage(BaseModel):
    legacy_platform: str
    current_limitation: str
    bhoomi_nexus_advantage: str


class AIQueryResponse(BaseModel):
    query: str
    summary: str
    insight: str
    key_findings: list[str]
    evidence_coverage: dict[str, Any]
    sources: list[SourceCitation]
    related_regions: list[dict[str, Any]]
    suggested_policies: list[str]
    competitive_comparison: list[CompetitiveAdvantage]
    confidence_score: float


# ── Policy Simulator V2 (existing) ───────────────────────────────────────

class PolicySimRequest(BaseModel):
    target_district: str = Field(default="Jaisalmer")
    policy_name: str = Field(default="micro_irrigation", description="'micro_irrigation', 'agroforestry_shelterbelts', 'canal_lining', 'soil_carbon_banking'")
    intensity_increase_pct: float = Field(default=20.0, ge=1.0, le=100.0, description="Intervention coverage increase (e.g. +20%)")
    target_hectares: Optional[float] = 50000.0


class PolicyMetric(BaseModel):
    label: str
    current: float
    projected: float
    unit: str
    change_pct: float
    status: str


class PolicySimResponse(BaseModel):
    target_district: str
    policy_name: str
    intensity_increase_pct: float
    metrics: list[PolicyMetric]
    land_degraded_hectares_reclaimed: float
    water_saved_million_liters_annual: float
    estimated_budget_crores_inr: float
    roi_economic_multiplier: float
    model_assumptions: list[str]
    scheme_alignment: str


# ── Blockchain Dataset Verification (existing) ───────────────────────────

class VerifyDatasetRequest(BaseModel):
    dataset_id: str = "DS-RAJ-DES-2024"
    provided_hash: Optional[str] = None
    simulate_tampering: bool = False


class VerifyDatasetResponse(BaseModel):
    dataset_id: str
    dataset_title: str
    verification_status: str
    integrity_confirmed: bool
    registered_hash: str
    computed_hash: str
    transaction_id: str
    timestamp: str
    block_index: int
    message: str

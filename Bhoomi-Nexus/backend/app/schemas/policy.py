"""
Pydantic schemas for the Policy & Zoning Analytics module.

Endpoint served:
  POST /api/v1/policy/evaluate
"""

from typing import Optional
from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────

class PolicyEvaluateRequest(BaseModel):
    """Property attributes to evaluate against zoning and land-use regulations."""
    land_type: str = Field(
        default="Agricultural",
        description="Current land classification: Agricultural, Residential, Commercial, Industrial, Forest, Wasteland"
    )
    proposed_use: str = Field(
        default="Residential",
        description="Intended land use after conversion"
    )
    area_hectares: float = Field(default=2.5, ge=0.01)
    district: str = Field(default="Jaipur")
    state: str = Field(default="Rajasthan")
    location_type: str = Field(
        default="Urban",
        description="Urban, Peri-Urban, Rural, Coastal, Heritage, Hill"
    )
    proposed_floors: Optional[int] = Field(default=3, ge=1, le=100)
    plot_width_meters: Optional[float] = Field(default=30.0, ge=1.0)
    plot_depth_meters: Optional[float] = Field(default=40.0, ge=1.0)
    near_water_body: bool = Field(default=False)
    near_heritage_site: bool = Field(default=False)
    near_highway: bool = Field(default=False)


# ── Response components ──────────────────────────────────────────────────

class ZoningCompliance(BaseModel):
    """Whether the proposed use complies with the current zoning."""
    is_compliant: bool
    current_zone: str
    proposed_zone: str
    conversion_required: bool
    conversion_type: Optional[str] = None   # e.g., "AG-to-NAG (Section 90-A)"
    conversion_feasibility: str = Field(..., description="PERMITTED / CONDITIONAL / RESTRICTED / PROHIBITED")
    conditions: list[str]


class FARAnalysis(BaseModel):
    """Floor Area Ratio compliance check."""
    max_allowed_far: float
    proposed_far: float
    is_within_limit: bool
    max_buildable_area_sqm: float
    proposed_buildable_area_sqm: float
    excess_area_sqm: float


class SetbackRequirement(BaseModel):
    """Required setback distances from plot boundaries."""
    front_meters: float
    rear_meters: float
    left_side_meters: float
    right_side_meters: float
    is_compliant: bool
    notes: str


class RestrictionFlag(BaseModel):
    """A specific restriction or special condition."""
    restriction_type: str = Field(..., description="e.g., 'Coastal Regulation Zone', 'Heritage Buffer', 'Forest Clearance'")
    description: str
    authority: str
    severity: str = Field(..., description="INFO / ADVISORY / MANDATORY / PROHIBITIVE")
    action_required: str


class PolicyEvaluateResponse(BaseModel):
    """Complete policy and zoning evaluation result."""
    status: str = "EVALUATION_COMPLETE"
    overall_compliance: str = Field(..., description="COMPLIANT / CONDITIONALLY_COMPLIANT / NON_COMPLIANT")
    compliance_score: float = Field(..., ge=0.0, le=100.0)

    zoning: ZoningCompliance
    far_analysis: FARAnalysis
    setback_requirements: SetbackRequirement
    restriction_flags: list[RestrictionFlag]

    applicable_regulations: list[str]
    recommended_actions: list[str]
    estimated_approval_timeline_days: int
    authority_contacts: list[str]

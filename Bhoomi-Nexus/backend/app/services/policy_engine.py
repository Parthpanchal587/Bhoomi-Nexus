"""
Policy & Zoning Analytics Engine.

Maps property attributes against municipal master plan policies and
land-use regulations including:
- Agricultural-to-Non-Agricultural (AG-to-NAG) conversion limits
- Floor Area Ratio (FAR)
- Building setbacks
- Coastal/Heritage/Forest restrictions
"""

from app.schemas.policy import (
    PolicyEvaluateRequest,
    PolicyEvaluateResponse,
    ZoningCompliance,
    FARAnalysis,
    SetbackRequirement,
    RestrictionFlag,
)


# ── Zoning Rule Database ─────────────────────────────────────────────────

ZONE_CONVERSION_MATRIX: dict[str, dict[str, str]] = {
    # current_type → proposed_type → feasibility
    "Agricultural": {
        "Residential": "CONDITIONAL",
        "Commercial": "CONDITIONAL",
        "Industrial": "CONDITIONAL",
        "Forest": "PROHIBITED",
        "Agricultural": "PERMITTED",
    },
    "Residential": {
        "Commercial": "CONDITIONAL",
        "Industrial": "RESTRICTED",
        "Agricultural": "PERMITTED",
        "Residential": "PERMITTED",
        "Forest": "PROHIBITED",
    },
    "Commercial": {
        "Residential": "CONDITIONAL",
        "Industrial": "CONDITIONAL",
        "Agricultural": "RESTRICTED",
        "Commercial": "PERMITTED",
        "Forest": "PROHIBITED",
    },
    "Industrial": {
        "Residential": "RESTRICTED",
        "Commercial": "CONDITIONAL",
        "Agricultural": "RESTRICTED",
        "Industrial": "PERMITTED",
        "Forest": "PROHIBITED",
    },
    "Forest": {
        "Residential": "PROHIBITED",
        "Commercial": "PROHIBITED",
        "Industrial": "PROHIBITED",
        "Agricultural": "RESTRICTED",
        "Forest": "PERMITTED",
    },
    "Wasteland": {
        "Residential": "CONDITIONAL",
        "Commercial": "CONDITIONAL",
        "Industrial": "CONDITIONAL",
        "Agricultural": "PERMITTED",
        "Forest": "CONDITIONAL",
        "Wasteland": "PERMITTED",
    },
}

# FAR limits by location type and proposed use
FAR_LIMITS: dict[str, dict[str, float]] = {
    "Urban": {"Residential": 2.5, "Commercial": 3.5, "Industrial": 1.5, "default": 2.0},
    "Peri-Urban": {"Residential": 1.75, "Commercial": 2.0, "Industrial": 1.25, "default": 1.5},
    "Rural": {"Residential": 1.0, "Commercial": 1.25, "Industrial": 1.0, "default": 1.0},
    "Coastal": {"Residential": 1.0, "Commercial": 0.5, "Industrial": 0.0, "default": 0.5},
    "Heritage": {"Residential": 1.25, "Commercial": 1.0, "Industrial": 0.0, "default": 0.75},
    "Hill": {"Residential": 1.0, "Commercial": 0.75, "Industrial": 0.5, "default": 0.75},
}

# Setback requirements by location type (in meters)
SETBACK_RULES: dict[str, dict[str, float]] = {
    "Urban": {"front": 4.5, "rear": 3.0, "left": 2.0, "right": 2.0},
    "Peri-Urban": {"front": 6.0, "rear": 4.5, "left": 3.0, "right": 3.0},
    "Rural": {"front": 6.0, "rear": 6.0, "left": 4.5, "right": 4.5},
    "Coastal": {"front": 9.0, "rear": 9.0, "left": 6.0, "right": 6.0},
    "Heritage": {"front": 9.0, "rear": 6.0, "left": 4.5, "right": 4.5},
    "Hill": {"front": 6.0, "rear": 6.0, "left": 4.5, "right": 4.5},
}


# ── Evaluation Engine ────────────────────────────────────────────────────

def evaluate_policy(request: PolicyEvaluateRequest) -> PolicyEvaluateResponse:
    """
    Evaluate property attributes against zoning regulations and policies.
    Returns comprehensive compliance assessment.
    """
    # 1. Zoning compliance
    zoning = _evaluate_zoning(request)

    # 2. FAR analysis
    far = _evaluate_far(request)

    # 3. Setback requirements
    setback = _evaluate_setbacks(request)

    # 4. Restriction flags
    restrictions = _evaluate_restrictions(request)

    # 5. Overall compliance score
    compliance_score = _calculate_compliance_score(zoning, far, setback, restrictions)
    if compliance_score >= 80:
        overall = "COMPLIANT"
    elif compliance_score >= 50:
        overall = "CONDITIONALLY_COMPLIANT"
    else:
        overall = "NON_COMPLIANT"

    # 6. Applicable regulations
    regulations = _get_applicable_regulations(request)

    # 7. Recommended actions
    actions = _get_recommended_actions(zoning, far, setback, restrictions)

    # 8. Timeline estimate
    timeline = _estimate_timeline(zoning, restrictions)

    # 9. Authority contacts
    contacts = _get_authority_contacts(request)

    return PolicyEvaluateResponse(
        status="EVALUATION_COMPLETE",
        overall_compliance=overall,
        compliance_score=round(compliance_score, 1),
        zoning=zoning,
        far_analysis=far,
        setback_requirements=setback,
        restriction_flags=restrictions,
        applicable_regulations=regulations,
        recommended_actions=actions,
        estimated_approval_timeline_days=timeline,
        authority_contacts=contacts,
    )


def _evaluate_zoning(req: PolicyEvaluateRequest) -> ZoningCompliance:
    """Check if the proposed use is compatible with current zoning."""
    current = req.land_type
    proposed = req.proposed_use
    conversion_needed = current.lower() != proposed.lower()

    matrix = ZONE_CONVERSION_MATRIX.get(current, {})
    feasibility = matrix.get(proposed, "CONDITIONAL")

    conditions: list[str] = []
    conversion_type = None

    if conversion_needed:
        if current == "Agricultural":
            conversion_type = "AG-to-NAG (Section 90-A Revenue Diversion)"
            conditions.append("Section 90-A conversion order required from Revenue Department")
            conditions.append(f"Maximum AG-to-NAG conversion limit: {min(req.area_hectares, 8.0)} hectares per application")
            if req.area_hectares > 4.0:
                conditions.append("Environmental Impact Assessment (EIA) required for plots > 4 hectares")
            conditions.append("Compensatory green belt of 15% of converted area mandatory")
        elif current == "Forest":
            conversion_type = "Forest Diversion (Forest Conservation Act 1980)"
            conditions.append("Stage-I and Stage-II forest clearance from MoEFCC required")
            conditions.append("Compensatory afforestation on equivalent non-forest land mandatory")
        else:
            conversion_type = f"{current}-to-{proposed} Land Use Change"
            conditions.append("Municipal Corporation zoning change application required")
            conditions.append("Public hearing and notification period of 30 days")

        if feasibility == "RESTRICTED":
            conditions.append("Additional State-level approval required due to restricted conversion category")
        elif feasibility == "PROHIBITED":
            conditions.append("This conversion is PROHIBITED under current regulations")
    else:
        conditions.append("No conversion required — proposed use matches current zoning")

    return ZoningCompliance(
        is_compliant=not conversion_needed or feasibility == "PERMITTED",
        current_zone=current,
        proposed_zone=proposed,
        conversion_required=conversion_needed,
        conversion_type=conversion_type,
        conversion_feasibility=feasibility if conversion_needed else "PERMITTED",
        conditions=conditions,
    )


def _evaluate_far(req: PolicyEvaluateRequest) -> FARAnalysis:
    """Calculate Floor Area Ratio compliance."""
    location_fars = FAR_LIMITS.get(req.location_type, FAR_LIMITS["Urban"])
    max_far = location_fars.get(req.proposed_use, location_fars.get("default", 2.0))

    plot_area_sqm = req.area_hectares * 10_000  # Convert hectares to sq meters
    if req.plot_width_meters and req.plot_depth_meters:
        effective_plot = req.plot_width_meters * req.plot_depth_meters
        plot_area_sqm = min(plot_area_sqm, effective_plot)

    max_buildable = plot_area_sqm * max_far
    proposed_floors = req.proposed_floors or 3
    # Assume 70% ground coverage
    ground_coverage = plot_area_sqm * 0.7
    proposed_buildable = ground_coverage * proposed_floors
    excess = max(0, proposed_buildable - max_buildable)

    return FARAnalysis(
        max_allowed_far=max_far,
        proposed_far=round(proposed_buildable / plot_area_sqm, 2) if plot_area_sqm > 0 else 0,
        is_within_limit=proposed_buildable <= max_buildable,
        max_buildable_area_sqm=round(max_buildable, 2),
        proposed_buildable_area_sqm=round(proposed_buildable, 2),
        excess_area_sqm=round(excess, 2),
    )


def _evaluate_setbacks(req: PolicyEvaluateRequest) -> SetbackRequirement:
    """Determine required setback distances."""
    rules = SETBACK_RULES.get(req.location_type, SETBACK_RULES["Urban"])

    # Increase setbacks for specific conditions
    multiplier = 1.0
    if req.near_highway:
        multiplier = max(multiplier, 2.0)
    if req.near_heritage_site:
        multiplier = max(multiplier, 1.5)

    front = round(rules["front"] * multiplier, 1)
    rear = round(rules["rear"] * multiplier, 1)
    left = round(rules["left"] * multiplier, 1)
    right = round(rules["right"] * multiplier, 1)

    # Check if plot is large enough for the required setbacks
    width_ok = True
    depth_ok = True
    notes_parts = []

    if req.plot_width_meters:
        usable_width = req.plot_width_meters - left - right
        if usable_width < 3.0:
            width_ok = False
            notes_parts.append(f"Plot width ({req.plot_width_meters}m) insufficient after setbacks ({left}m + {right}m)")

    if req.plot_depth_meters:
        usable_depth = req.plot_depth_meters - front - rear
        if usable_depth < 3.0:
            depth_ok = False
            notes_parts.append(f"Plot depth ({req.plot_depth_meters}m) insufficient after setbacks ({front}m + {rear}m)")

    if not notes_parts:
        notes_parts.append("Setback requirements are satisfiable with current plot dimensions")

    return SetbackRequirement(
        front_meters=front,
        rear_meters=rear,
        left_side_meters=left,
        right_side_meters=right,
        is_compliant=width_ok and depth_ok,
        notes=". ".join(notes_parts),
    )


def _evaluate_restrictions(req: PolicyEvaluateRequest) -> list[RestrictionFlag]:
    """Check for special restrictions based on location and property attributes."""
    flags: list[RestrictionFlag] = []

    if req.location_type == "Coastal":
        flags.append(RestrictionFlag(
            restriction_type="Coastal Regulation Zone (CRZ)",
            description="Property falls within Coastal Regulation Zone. CRZ-II/III norms apply based on proximity to High Tide Line.",
            authority="Ministry of Environment, Forest and Climate Change (MoEFCC)",
            severity="MANDATORY",
            action_required="Obtain CRZ clearance from State Coastal Zone Management Authority (SCZMA)",
        ))

    if req.near_heritage_site:
        flags.append(RestrictionFlag(
            restriction_type="Heritage Buffer Zone",
            description="Property is near a protected heritage site. Archaeological Survey of India (ASI) regulated zone — 100m prohibited, 200m regulated.",
            authority="Archaeological Survey of India (ASI)",
            severity="MANDATORY",
            action_required="Obtain ASI NOC for any construction, renovation, or land modification within 200m of protected monument",
        ))

    if req.near_water_body:
        flags.append(RestrictionFlag(
            restriction_type="Water Body Buffer",
            description="Property is near a water body. Minimum 30m green buffer zone required. No construction within 15m of water body edge.",
            authority="State Pollution Control Board / National Green Tribunal",
            severity="MANDATORY",
            action_required="Maintain prescribed buffer zone. Submit Environmental Compliance Report.",
        ))

    if req.near_highway:
        flags.append(RestrictionFlag(
            restriction_type="National Highway Control Area",
            description="Property is near a National Highway. Building line restrictions apply per NH Act 1956.",
            authority="National Highways Authority of India (NHAI)",
            severity="MANDATORY",
            action_required="Obtain NHAI NOC. Maintain 60m building line from highway centerline.",
        ))

    if req.land_type == "Agricultural" and req.area_hectares > 8.0:
        flags.append(RestrictionFlag(
            restriction_type="Large Agricultural Holding Restriction",
            description=f"Conversion of agricultural land > 8 hectares ({req.area_hectares} ha requested) requires state-level committee approval.",
            authority="State Revenue Department & District Collector",
            severity="MANDATORY",
            action_required="File application with District Collector. Mandatory public hearing and environmental assessment.",
        ))

    if req.proposed_use == "Industrial" and req.location_type in ("Residential", "Heritage", "Coastal"):
        flags.append(RestrictionFlag(
            restriction_type="Industrial Zoning Incompatibility",
            description=f"Industrial development in {req.location_type} zones is restricted or prohibited under master plan regulations.",
            authority="Town Planning Department / Municipal Corporation",
            severity="PROHIBITIVE",
            action_required="Identify alternative site in designated industrial zone. Apply for special exemption if critical.",
        ))

    if req.location_type == "Hill":
        flags.append(RestrictionFlag(
            restriction_type="Hill Area Development Regulation",
            description="Hill area development subject to slope stability analysis and reduced ground coverage norms.",
            authority="State Hill Development Authority",
            severity="ADVISORY",
            action_required="Submit geo-technical slope stability report. Maximum 40% ground coverage applies.",
        ))

    return flags


def _calculate_compliance_score(
    zoning: ZoningCompliance,
    far: FARAnalysis,
    setback: SetbackRequirement,
    restrictions: list[RestrictionFlag],
) -> float:
    """Calculate an overall compliance score (0-100)."""
    score = 100.0

    # Zoning
    if zoning.conversion_feasibility == "PROHIBITED":
        score -= 50.0
    elif zoning.conversion_feasibility == "RESTRICTED":
        score -= 30.0
    elif zoning.conversion_feasibility == "CONDITIONAL":
        score -= 10.0

    # FAR
    if not far.is_within_limit:
        excess_ratio = far.excess_area_sqm / max(far.max_buildable_area_sqm, 1)
        score -= min(25.0, excess_ratio * 25.0)

    # Setbacks
    if not setback.is_compliant:
        score -= 15.0

    # Restrictions
    for flag in restrictions:
        if flag.severity == "PROHIBITIVE":
            score -= 20.0
        elif flag.severity == "MANDATORY":
            score -= 5.0
        elif flag.severity == "ADVISORY":
            score -= 2.0

    return max(0.0, score)


def _get_applicable_regulations(req: PolicyEvaluateRequest) -> list[str]:
    """Return list of regulations applicable to this property."""
    regs = [
        f"{req.state} Town and Country Planning Act",
        f"{req.district} District Master Plan / Development Plan",
        "Building Bye-Laws and Construction Regulations",
    ]
    if req.land_type == "Agricultural":
        regs.append("Revenue Land Conversion Rules (Section 90-A)")
        regs.append("Rajasthan Land Revenue Act 1956")
    if req.near_water_body:
        regs.append("National Green Tribunal (NGT) Water Body Protection Orders")
    if req.near_heritage_site:
        regs.append("Ancient Monuments and Archaeological Sites and Remains Act 1958")
    if req.location_type == "Coastal":
        regs.append("Coastal Regulation Zone Notification 2019")
    if req.proposed_use == "Industrial":
        regs.append("Environmental Impact Assessment Notification 2006")
        regs.append("Factories Act 1948 - Site Approval Requirements")
    return regs


def _get_recommended_actions(
    zoning: ZoningCompliance,
    far: FARAnalysis,
    setback: SetbackRequirement,
    restrictions: list[RestrictionFlag],
) -> list[str]:
    """Generate recommended actions based on evaluation."""
    actions: list[str] = []

    if zoning.conversion_required:
        actions.append(f"Apply for {zoning.conversion_type} through the Revenue Department")

    if not far.is_within_limit:
        actions.append(f"Reduce proposed built-up area by {round(far.excess_area_sqm, 1)} sq.m to comply with FAR limits")

    if not setback.is_compliant:
        actions.append("Redesign building footprint to meet minimum setback requirements")

    for flag in restrictions:
        if flag.severity in ("MANDATORY", "PROHIBITIVE"):
            actions.append(flag.action_required)

    if not actions:
        actions.append("All parameters are within compliance. Proceed with building plan submission.")
        actions.append("Obtain latest approved building plan from Town Planning Department.")

    return actions


def _estimate_timeline(zoning: ZoningCompliance, restrictions: list[RestrictionFlag]) -> int:
    """Estimate approval timeline in days."""
    days = 30  # Base processing time

    if zoning.conversion_required:
        if zoning.conversion_feasibility == "CONDITIONAL":
            days += 60
        elif zoning.conversion_feasibility == "RESTRICTED":
            days += 120

    for flag in restrictions:
        if flag.severity == "MANDATORY":
            days += 30
        elif flag.severity == "PROHIBITIVE":
            days += 180

    return days


def _get_authority_contacts(req: PolicyEvaluateRequest) -> list[str]:
    """Return relevant authority contacts."""
    return [
        f"District Collector, {req.district} — Revenue Land Conversion",
        f"Town Planning Department, {req.district} — Building Plan Approval",
        f"Sub-Registrar Office, {req.district} — Property Registration",
        f"{req.state} Pollution Control Board — Environmental Clearance",
        "National Informatics Centre (NIC) — Online Application Portal",
    ]

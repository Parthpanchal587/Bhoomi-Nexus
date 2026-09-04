"""
Executive insights and briefings endpoint.
Extracted from original main.py — logic identical.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Insights"])


@router.get("/api/insights/briefings")
def get_executive_briefings():
    return {
        "briefings": [
            {
                "id": "BRF-2026-01",
                "priority": "HIGH PRIORITY",
                "badge_color": "danger",
                "title": "Accelerated Sand Dune Encroachment Along Western NH-11 & NH-68 Corridors",
                "region": "Jaisalmer & Barmer Districts",
                "date": "September 2026",
                "summary": "Multi-temporal satellite imagery from Sentinel-2 shows an eastward migration of active barchan dunes at 14.2 meters/year, threatening arterial transportation corridors and agricultural land.",
                "evidence": {
                    "datasets": 3,
                    "research_papers": 2,
                    "affected_area_ha": 482000,
                    "confidence": "98.2%",
                },
                "impacts": ["Transportation Infrastructure", "Kharif Bajra Yield Loss", "Fallow Land Desertification"],
                "recommended_action": "Immediate sanction of 150km biological shelterbelts under MGNREGS and Desert Development Programme.",
            },
            {
                "id": "BRF-2026-02",
                "priority": "HIGH PRIORITY",
                "badge_color": "danger",
                "title": "Critical Aquifer Over-Exploitation in Peri-Urban Industrial Clusters",
                "region": "Jaipur & Jodhpur Rural",
                "date": "August 2026",
                "summary": "Central Ground Water Board dynamic assessment confirms stage of extraction exceeding 180% across Sanganer and Mandore tehsils. Section 90-A commercial conversions are accelerating localized cone drawdown.",
                "evidence": {
                    "datasets": 4,
                    "research_papers": 1,
                    "affected_area_ha": 124000,
                    "confidence": "95.6%",
                },
                "impacts": ["Drinking Water Security", "Fluoride Ingress", "Soil Subsidence"],
                "recommended_action": "Mandatory installation of dual-purpose injection wells and 100% industrial wastewater recycling before issuing conversion clearance.",
            },
            {
                "id": "BRF-2026-03",
                "priority": "MEDIUM PRIORITY",
                "badge_color": "warning",
                "title": "Secondary Salinization in Indira Gandhi Nahar Pariyojana (IGNP) Command Area",
                "region": "Bikaner & Hanumangarh",
                "date": "July 2026",
                "summary": "Unlined distributary seepage combined with shallow geological gypsum strata has caused waterlogging across 145,000 hectares, dropping wheat and mustard productivity by 38%.",
                "evidence": {
                    "datasets": 2,
                    "research_papers": 2,
                    "affected_area_ha": 145000,
                    "confidence": "94.0%",
                },
                "impacts": ["Wheat & Mustard Yield Deficit", "Soil Alkalinity", "Farmer Out-Migration"],
                "recommended_action": "Execute Phase II canal bed concrete relining and distribute subsidized gypsum amendments.",
            },
        ]
    }


# ── Policy Simulator V2 (existing — extracted from main.py) ──────────────

from app.config import DISTRICT_PROFILES
from app.schemas.common import PolicySimRequest, PolicySimResponse, PolicyMetric


@router.post("/api/policy/simulate-v2", response_model=PolicySimResponse)
def simulate_policy_intervention(req: PolicySimRequest):
    """
    Decision-support policy simulation engine calculating Current vs Projected
    impact of land management, agroforestry, and irrigation interventions.
    """
    district_data = DISTRICT_PROFILES.get(req.target_district, DISTRICT_PROFILES["Jaisalmer"])
    base_degradation = district_data["land_degradation_pct"]
    base_gw_stress = district_data["groundwater_stress_pct"]
    base_agri = district_data["agricultural_productivity_pct"]

    scale_factor = req.intensity_increase_pct / 100.0

    if req.policy_name == "micro_irrigation":
        projected_agri = round(min(95.0, base_agri + (18.5 * scale_factor)), 1)
        projected_gw_stress = round(max(20.0, base_gw_stress - (24.0 * scale_factor)), 1)
        projected_degradation = round(max(15.0, base_degradation - (12.0 * scale_factor)), 1)
        water_saved_ml = round(4200.0 * scale_factor, 1)
        reclaimed_ha = round(28000.0 * scale_factor, 1)
        budget = round(45.0 * scale_factor * 1.8, 1)
        roi = 3.2
        scheme = "Pradhan Mantri Krishi Sinchayee Yojana (PMKSY - Per Drop More Crop)"
        assumptions = [
            "Assumes 75% subsidy adoption among small and marginal farmers.",
            "Water saving rate calibrated at 4.2 kL/ha/season based on CAZRI drip trials.",
            "Electrical feeder solarization reduces daytime peak draw.",
        ]
    elif req.policy_name == "agroforestry_shelterbelts":
        projected_agri = round(min(95.0, base_agri + (14.0 * scale_factor)), 1)
        projected_gw_stress = round(max(20.0, base_gw_stress - (10.0 * scale_factor)), 1)
        projected_degradation = round(max(15.0, base_degradation - (28.0 * scale_factor)), 1)
        water_saved_ml = round(1800.0 * scale_factor, 1)
        reclaimed_ha = round(45000.0 * scale_factor, 1)
        budget = round(32.0 * scale_factor * 1.5, 1)
        roi = 2.9
        scheme = "Sub-Mission on Agroforestry (SMAF) & National Afforestation Programme"
        assumptions = [
            "3-tier planting of Prosopis cineraria (Khejri) and Acacia along 500km wind corridor.",
            "Wind velocity reduction of 35% within 15x tree height distance.",
            "Soil Organic Carbon baseline increases by 0.12% within 36 months.",
        ]
    elif req.policy_name == "canal_lining":
        projected_agri = round(min(95.0, base_agri + (22.0 * scale_factor)), 1)
        projected_gw_stress = round(max(20.0, base_gw_stress - (15.0 * scale_factor)), 1)
        projected_degradation = round(max(15.0, base_degradation - (32.0 * scale_factor)), 1)
        water_saved_ml = round(6400.0 * scale_factor, 1)
        reclaimed_ha = round(38000.0 * scale_factor, 1)
        budget = round(68.0 * scale_factor * 2.1, 1)
        roi = 3.5
        scheme = "Rajasthan Water Sector Restructuring Project (RWSRP) for Desert Areas"
        assumptions = [
            "Seepage reduction of 65% across 220km of feeder distributaries in IGNP stage II.",
            "Subsurface tile drainage lowers perched water table below 2.0m root zone.",
            "Secondary soil salinity reduced by 40% in reclaimed patches.",
        ]
    else:
        projected_agri = round(min(95.0, base_agri + (16.0 * scale_factor)), 1)
        projected_gw_stress = round(max(20.0, base_gw_stress - (8.0 * scale_factor)), 1)
        projected_degradation = round(max(15.0, base_degradation - (20.0 * scale_factor)), 1)
        water_saved_ml = round(2100.0 * scale_factor, 1)
        reclaimed_ha = round(30000.0 * scale_factor, 1)
        budget = round(28.0 * scale_factor * 1.2, 1)
        roi = 2.6
        scheme = "Paramparagat Krishi Vikas Yojana (PKVY) & UNCCD Land Degradation Neutrality"
        assumptions = [
            "Green manuring and biochar application at 2.5 tonnes/ha.",
            "Soil water holding capacity improved by 18% in sandy loam tracts.",
            "Targeting complete restoration of fallow lands in 3 seasons.",
        ]

    metrics = [
        PolicyMetric(
            label="Agricultural Productivity Index",
            current=base_agri,
            projected=projected_agri,
            unit="%",
            change_pct=round(((projected_agri - base_agri) / base_agri) * 100, 1),
            status="POSITIVE IMPROVEMENT",
        ),
        PolicyMetric(
            label="Groundwater Aquifer Stress",
            current=base_gw_stress,
            projected=projected_gw_stress,
            unit="%",
            change_pct=round(((projected_gw_stress - base_gw_stress) / base_gw_stress) * 100, 1),
            status="PRESSURE REDUCTION",
        ),
        PolicyMetric(
            label="Land Degradation Footprint",
            current=base_degradation,
            projected=projected_degradation,
            unit="%",
            change_pct=round(((projected_degradation - base_degradation) / base_degradation) * 100, 1),
            status="ARRESTED / RECLAIMED",
        ),
        PolicyMetric(
            label="Topsoil Moisture Retention",
            current=district_data["soil_moisture_pct"],
            projected=round(district_data["soil_moisture_pct"] * (1 + (0.35 * scale_factor)), 1),
            unit="%",
            change_pct=round(35.0 * scale_factor, 1),
            status="ENHANCED HYDRATION",
        ),
    ]

    return PolicySimResponse(
        target_district=req.target_district,
        policy_name=req.policy_name,
        intensity_increase_pct=req.intensity_increase_pct,
        metrics=metrics,
        land_degraded_hectares_reclaimed=reclaimed_ha,
        water_saved_million_liters_annual=water_saved_ml,
        estimated_budget_crores_inr=budget,
        roi_economic_multiplier=roi,
        model_assumptions=assumptions,
        scheme_alignment=scheme,
    )

"""
Land conversion simulation endpoint.
Extracted from original main.py — logic identical.
"""

import time

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas.common import SimulationRequest, SimulationResponse

router = APIRouter(tags=["Simulation"])


@router.post("/api/simulate", response_model=SimulationResponse)
def simulate_land_conversion(payload: SimulationRequest):
    conv_type = payload.conversion_type.lower()
    if conv_type not in ["commercial", "industrial", "residential"]:
        conv_type = "industrial"

    if payload.converted_hectares > payload.total_hectares:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Converted hectares cannot exceed total hectares.",
        )

    retained_ha = round(max(0.0, payload.total_hectares - payload.converted_hectares), 2)
    yield_deficit_quintals = round(payload.converted_hectares * payload.baseline_yield_per_ha, 2)
    yield_deficit_metric_tons = round(yield_deficit_quintals * 0.1, 2)
    economic_loss_inr = round(yield_deficit_quintals * 2300.0, 2)

    extraction_coeff = settings.GROUNDWATER_EXTRACTION_COEFFICIENT.get(conv_type, 30.0)
    daily_consumption_kl = round(payload.converted_hectares * extraction_coeff, 2)

    depth_factor = min(50.0, (payload.water_table_depth_m / 60.0) * 50.0)
    load_factor = min(50.0, (daily_consumption_kl / 1000.0) * 50.0)
    gw_pressure_index = round(depth_factor + load_factor, 1)

    if gw_pressure_index < 35.0:
        aquifer_risk = "LOW RISK (SAFE RECHARGE ZONE)"
    elif gw_pressure_index < 60.0:
        aquifer_risk = "MODERATE (SEMI-CRITICAL DRAWDOWN)"
    elif gw_pressure_index < 80.0:
        aquifer_risk = "CRITICAL (OVER-EXPLOITED SHALLOW AQUIFER)"
    else:
        aquifer_risk = "SEVERE OVER-EXPLOITATION (MANDATORY RAINWATER RECHARGE REQUIRED)"

    if conv_type == "commercial":
        rate = settings.TARIFF_COMMERCIAL_RATE_PER_HA
    elif conv_type == "industrial":
        rate = settings.TARIFF_INDUSTRIAL_RATE_PER_HA
    else:
        rate = settings.TARIFF_RESIDENTIAL_RATE_PER_HA

    base_stamp_duty = round(payload.converted_hectares * rate, 2)
    infrastructure_cess = round(base_stamp_duty * 0.08, 2)
    total_tariff = round(base_stamp_duty + infrastructure_cess, 2)

    statutory_code = f"CAD-CONV-{conv_type[:3].upper()}-{int(time.time()) % 10000:04d}"
    advisory = (
        f"Statutory clearance approved for {payload.converted_hectares} ha under Section 90-A. "
        f"Compensatory green belt of {round(payload.converted_hectares * 0.15, 2)} ha mandated. "
        f"Water recycling plan mandatory for {daily_consumption_kl} kL/day load."
    )

    return SimulationResponse(
        parcel_id=payload.parcel_id,
        total_hectares=payload.total_hectares,
        converted_hectares=payload.converted_hectares,
        retained_agricultural_ha=retained_ha,
        conversion_type=conv_type.upper(),
        crop_type=payload.crop_type,
        yield_deficit_quintals=yield_deficit_quintals,
        yield_deficit_metric_tons=yield_deficit_metric_tons,
        economic_crop_loss_inr=economic_loss_inr,
        groundwater_daily_consumption_kl=daily_consumption_kl,
        groundwater_pressure_index=gw_pressure_index,
        aquifer_drawdown_risk=aquifer_risk,
        base_stamp_duty_inr=base_stamp_duty,
        infrastructure_cess_inr=infrastructure_cess,
        total_tariff_inr=total_tariff,
        statutory_clearance_code=statutory_code,
        compliance_advisory=advisory,
    )

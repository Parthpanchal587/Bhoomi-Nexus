"""
Policy & Zoning Analytics Router.

Endpoint:
  POST /api/v1/policy/evaluate — Zoning and regulation compliance check
"""

from fastapi import APIRouter

from app.schemas.policy import PolicyEvaluateRequest, PolicyEvaluateResponse
from app.services.policy_engine import evaluate_policy

router = APIRouter(prefix="/api/v1/policy", tags=["Policy & Zoning Analytics (v1)"])


@router.post("/evaluate", response_model=PolicyEvaluateResponse)
def policy_evaluate_endpoint(req: PolicyEvaluateRequest):
    """
    Evaluate property attributes against municipal master plan policies
    and land-use regulations.

    Checks:
    - Zoning compliance and conversion feasibility
    - Floor Area Ratio (FAR) limits
    - Building setback requirements
    - Special restrictions (Coastal/Heritage/Forest/Highway zones)
    - Agricultural-to-Non-Agricultural conversion limits (Section 90-A)

    Returns:
    - Overall compliance status and score (0–100)
    - Detailed zoning, FAR, setback, and restriction analysis
    - Applicable regulations and recommended actions
    - Estimated approval timeline and authority contacts
    """
    return evaluate_policy(req)

"""
Blockchain notarization and verification endpoints.
Extracted from original main.py — logic identical.
"""

import hashlib
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import DATASET_CATALOG
from app.schemas.common import (
    NotarizeRequest,
    Block,
    LedgerResponse,
    VerifyDatasetRequest,
    VerifyDatasetResponse,
)
from app.services.blockchain import ledger

router = APIRouter(tags=["Blockchain"])


@router.post("/api/blockchain/verify-dataset", response_model=VerifyDatasetResponse)
def verify_dataset_integrity(req: VerifyDatasetRequest):
    """
    Verifies dataset SHA-256 hash against the immutable blockchain registry.
    Supports demonstrating tampering detection when simulate_tampering is enabled.
    """
    target = None
    for d in DATASET_CATALOG:
        if d["id"].upper() == req.dataset_id.upper():
            target = d
            break

    if not target:
        target = DATASET_CATALOG[0]

    registered_hash = target["hash"]

    if req.simulate_tampering:
        tampered_hash = hashlib.sha256(
            f"TAMPERED_DATA_PAYLOAD_{time.time()}".encode("utf-8")
        ).hexdigest()
        return VerifyDatasetResponse(
            dataset_id=target["id"],
            dataset_title=target["title"],
            verification_status="TAMPERING_DETECTED",
            integrity_confirmed=False,
            registered_hash=registered_hash,
            computed_hash=tampered_hash,
            transaction_id=f"0xALERT_{int(time.time())}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            block_index=2,
            message="CRITICAL WARNING: Dataset file hash does NOT match the sovereign blockchain registry record! Unauthorized modifications detected.",
        )

    computed_hash = req.provided_hash or registered_hash

    if computed_hash.lower() == registered_hash.lower():
        return VerifyDatasetResponse(
            dataset_id=target["id"],
            dataset_title=target["title"],
            verification_status="VERIFIED",
            integrity_confirmed=True,
            registered_hash=registered_hash,
            computed_hash=computed_hash,
            transaction_id=f"0xTXN_{int(time.time())}_{target['id'][:8]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            block_index=1,
            message="SUCCESS: Dataset integrity confirmed. SHA-256 hash matches the immutable block notarized by NIC Cadastral Trust Authority.",
        )
    else:
        return VerifyDatasetResponse(
            dataset_id=target["id"],
            dataset_title=target["title"],
            verification_status="TAMPERING_DETECTED",
            integrity_confirmed=False,
            registered_hash=registered_hash,
            computed_hash=computed_hash,
            transaction_id=f"0xALERT_{int(time.time())}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            block_index=1,
            message="INTEGRITY BREACH: Provided hash does not match the registered ledger hash.",
        )


@router.post("/api/blockchain/notarize", response_model=Block)
def notarize_parcel(payload: NotarizeRequest):
    block_payload = {
        "parcel_id": payload.parcel_id,
        "owner_name": payload.owner_name,
        "state": payload.state,
        "district": payload.district,
        "coordinates": payload.coordinates,
        "area_hectares": payload.area_hectares,
        "zoning_status": payload.zoning_status,
        "simulation_summary": payload.simulation_summary or {},
        "telemetry_snapshot": payload.telemetry_snapshot or {},
        "notarized_by": payload.notarized_by,
        "certified_at": datetime.now(timezone.utc).isoformat(),
    }
    return ledger.notarize(parcel_id=payload.parcel_id, payload=block_payload)


@router.get("/api/blockchain/ledger", response_model=LedgerResponse)
def get_blockchain_ledger():
    return LedgerResponse(
        chain_valid=ledger.validate_chain(),
        total_blocks=len(ledger.chain),
        latest_block_hash=ledger.latest_block.hash,
        blocks=ledger.chain,
    )

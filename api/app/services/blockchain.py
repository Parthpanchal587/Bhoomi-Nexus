"""
In-Memory Blockchain Ledger Service.

Extracted from the original monolithic main.py — logic is identical.
Provides SHA-256 hash-linked block chain for cadastral notarization.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any

from app.schemas.common import Block
from app.config import settings, DATASET_CATALOG


class BlockchainLedger:
    """Simple in-memory blockchain for land record notarization."""

    def __init__(self) -> None:
        self.chain: list[Block] = []
        self._create_genesis_block()
        self._seed_registered_datasets()

    @staticmethod
    def calculate_hash(
        index: int,
        timestamp: str,
        parcel_id: str,
        data: dict,
        previous_hash: str,
        nonce: int,
    ) -> str:
        try:
            from app.secure_enclave.service import enclave_gateway
            from app.secure_enclave.schemas import EnclaveRole
            res = enclave_gateway.dispatch(
                operation="notary.sign_record",
                payload={
                    "index": index,
                    "timestamp": timestamp,
                    "parcel_id": parcel_id,
                    "data": data,
                    "previous_hash": previous_hash,
                    "nonce": nonce,
                },
                caller_id="blockchain-service",
                caller_role=EnclaveRole.OPERATOR,
                auth_token=enclave_gateway.system_token,
            )
            if res.status == "SUCCESS" and res.data and "block_hash" in res.data:
                return res.data["block_hash"]
        except Exception:
            pass

        serialized_data = json.dumps(data, sort_keys=True)
        block_string = f"{index}|{timestamp}|{parcel_id}|{serialized_data}|{previous_hash}|{nonce}"
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    def _create_genesis_block(self) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        genesis_data = {
            "authority": "Ministry of Rural Development & NIC Sovereign Cadastral Trust",
            "protocol": "BHOOMI-NEXUS-SHA256-LEDGER-V2",
            "message": "Genesis Block: National Cadastral & Land Intelligence Registry Initialized",
            "node_id": settings.NODE_ID,
        }
        genesis_hash = self.calculate_hash(
            index=0,
            timestamp=timestamp,
            parcel_id="GENESIS-PARCEL-0000",
            data=genesis_data,
            previous_hash="0" * 64,
            nonce=108,
        )
        genesis_block = Block(
            index=0,
            timestamp=timestamp,
            parcel_id="GENESIS-PARCEL-0000",
            data=genesis_data,
            previous_hash="0" * 64,
            hash=genesis_hash,
            nonce=108,
        )
        self.chain.append(genesis_block)

    def _seed_registered_datasets(self) -> None:
        """Pre-seed official dataset records in blockchain."""
        for ds in DATASET_CATALOG[:3]:
            payload = {
                "dataset_id": ds["id"],
                "title": ds["title"],
                "source": ds["source"],
                "registered_hash": ds["hash"],
                "records_count": ds["records_count"],
                "certified_by": "NIC Geospatial Data Trust Authority",
            }
            self.notarize(parcel_id=ds["id"], payload=payload)

    @property
    def latest_block(self) -> Block:
        return self.chain[-1]

    def notarize(self, parcel_id: str, payload: dict[str, Any]) -> Block:
        index = len(self.chain)
        timestamp = datetime.now(timezone.utc).isoformat()
        previous_hash = self.latest_block.hash
        nonce = 0

        while True:
            candidate_hash = self.calculate_hash(
                index, timestamp, parcel_id, payload, previous_hash, nonce
            )
            if candidate_hash.startswith("0") or nonce > 500:
                break
            nonce += 1

        new_block = Block(
            index=index,
            timestamp=timestamp,
            parcel_id=parcel_id,
            data=payload,
            previous_hash=previous_hash,
            hash=candidate_hash,
            nonce=nonce,
        )
        self.chain.append(new_block)
        return new_block

    def validate_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]
            if current.previous_hash != prev.hash:
                return False
            recomputed_hash = self.calculate_hash(
                current.index,
                current.timestamp,
                current.parcel_id,
                current.data,
                current.previous_hash,
                current.nonce,
            )
            if current.hash != recomputed_hash:
                return False
        return True


# Module-level singleton (shared across all router imports)
ledger = BlockchainLedger()

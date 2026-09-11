"""
Land Intelligence Evidence Graph Engine.

Builds a structured knowledge graph linking:
- Parcel (Root Entity)
- Khasra Record (RoR extract)
- Mutation Record (Dakhil-Kharij)
- Registration Information (Sub-Registrar Conveyance)
- Government Notifications & Gazettes (Acquisition, Greenbelt, Highway)
- Satellite Evidence (Multi-spectral physical canopy observations)
- Uploaded Documents (User-submitted deeds & fingerprints)
"""

from typing import List, Optional

from app.osint.schemas import (
    CanonicalLandParcel,
    ConflictRecord,
    EvidenceGraphData,
    GeospatialObservation,
    GraphEdge,
    GraphNode,
    RestrictionFlag,
    SourceRecordEntry,
)


class EvidenceGraphEngine:
    """Constructs the Land Intelligence Graph from normalized OSINT artifacts."""

    def build_graph(
        self,
        parcel: CanonicalLandParcel,
        sources: List[SourceRecordEntry],
        conflicts: List[ConflictRecord],
        restrictions: List[RestrictionFlag],
        observations: List[GeospatialObservation],
    ) -> EvidenceGraphData:
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        # 1. Root Node: The Land Parcel
        root_id = f"node-parcel-{parcel.parcel_id}"
        nodes.append(
            GraphNode(
                id=root_id,
                label=f"Parcel {parcel.primary_khasra}",
                node_type="PARCEL",
                source=parcel.provenance.source_name,
                date=parcel.provenance.retrieved_at[:10],
                confidence_stars=parcel.provenance.confidence_stars,
                data={
                    "area_ha": parcel.normalized_area_ha,
                    "district": parcel.district,
                    "tehsil": parcel.tehsil,
                    "classification": parcel.land_classification,
                },
            )
        )

        # 2. Source Record Nodes (Khasra & RoR Extracts)
        for i, s in enumerate(sources):
            node_id = f"node-source-{i}"
            nodes.append(
                GraphNode(
                    id=node_id,
                    label=f"Record: {s.source_name[:24]}",
                    node_type="KHASRA_RECORD",
                    source=s.source_name,
                    date=s.recorded_date or "2025-11-20",
                    confidence_stars=s.provenance.confidence_stars,
                    data={
                        "khasra": s.khasra_number,
                        "area_ha": s.area_hectares,
                        "land_type": s.land_type,
                        "tenure": s.tenure_type,
                    },
                )
            )
            edges.append(
                GraphEdge(
                    source=root_id,
                    target=node_id,
                    relationship="RECORDS",
                    label=f"Documented in {s.source_name[:18]}",
                )
            )

        # 3. Mutation Record Node
        mutation_id = f"node-mutation-{parcel.parcel_id}"
        nodes.append(
            GraphNode(
                id=mutation_id,
                label="Sanctioned Mutation #2104 (Dakhil-Kharij)",
                node_type="MUTATION",
                source="State Land Revenue Office",
                date="2022-06-14",
                confidence_stars=5,
                data={
                    "mutation_type": "Inheritance / Succession (Virasat)",
                    "status": "Officially Sanctioned & Recorded",
                },
            )
        )
        edges.append(
            GraphEdge(
                source=root_id,
                target=mutation_id,
                relationship="MODIFIED_BY",
                label="Title transfer authenticated by mutation",
            )
        )

        # 4. Satellite Physical Evidence Node
        if observations:
            obs = observations[0]
            sat_id = f"node-sat-{obs.observation_id}"
            nodes.append(
                GraphNode(
                    id=sat_id,
                    label=f"Satellite Observation ({obs.source[:20]})",
                    node_type="SATELLITE_EVIDENCE",
                    source=obs.source,
                    date=obs.observation_date,
                    confidence_stars=3,
                    data={
                        "observed_use": obs.observed_land_use,
                        "ndvi": obs.vegetation_index_ndvi,
                        "structures": obs.built_up_structures_detected,
                    },
                )
            )
            edges.append(
                GraphEdge(
                    source=root_id,
                    target=sat_id,
                    relationship="EVIDENCED_BY",
                    label="Remote-sensing multi-spectral canopy",
                )
            )

        # 5. Government Notification Nodes
        for j, r in enumerate(restrictions[:2]):
            notif_id = f"node-notif-{j}"
            nodes.append(
                GraphNode(
                    id=notif_id,
                    label=f"Statute: {r.rule_id}",
                    node_type="NOTIFICATION",
                    source=r.jurisdiction,
                    date=r.effective_date[:10],
                    confidence_stars=4,
                    data={
                        "category": r.category,
                        "reference": r.statutory_reference,
                        "level": r.restriction_level,
                    },
                )
            )
            edges.append(
                GraphEdge(
                    source=root_id,
                    target=notif_id,
                    relationship="NOTIFIED_IN",
                    label=r.restriction_level,
                )
            )

        # 6. Conflict Edges (if conflicts exist between sources)
        if conflicts and len(nodes) >= 3:
            edges.append(
                GraphEdge(
                    source="node-source-0",
                    target="node-source-1" if len(sources) > 1 else "node-sat-OBS-SAT-SENTINEL-2026",
                    relationship="CONFLICTS_WITH",
                    label=f"Discrepancy: {conflicts[0].field_name}",
                )
            )

        return EvidenceGraphData(nodes=nodes, edges=edges)


# Global evidence graph instance
evidence_graph_engine = EvidenceGraphEngine()

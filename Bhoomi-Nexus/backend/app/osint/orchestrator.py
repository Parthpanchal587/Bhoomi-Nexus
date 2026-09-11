"""
BHOOMI NEXUS - OSINT / Public-Source Land Intelligence
OSINT Orchestrator Service

The central intelligence pipeline coordinating provider discovery, data ingestion,
normalization, cross-source conflict detection, statutory restrictions analysis,
risk assessment, graph synthesis, temporal reconstruction, and report generation.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.osint.conflict_engine import ConflictEngine
from app.osint.document_intelligence import DocumentIntelligenceEngine
from app.osint.graph_engine import EvidenceGraphEngine
from app.osint.provenance import ProvenanceEngine
from app.osint.providers.registry import provider_registry
from app.osint.report_generator import ReportGenerator
from app.osint.restrictions import LandRestrictionRuleEngine
from app.osint.risk_engine import RiskEngine
from app.osint.schemas import (
    CanonicalLandParcel,
    ConflictRecord,
    DocumentCrossCheckRequest,
    DocumentCrossCheckResult,
    EvidenceGraphData,
    GeospatialObservation,
    LandIntelligenceReport,
    OSINTSearchQuery,
    ProvenanceLevel,
    ProvenanceMetadata,
    RestrictionFlag,
    RiskAssessment,
    SourceRecordEntry,
    TimelineEvent,
)
from app.osint.temporal_engine import TemporalTimelineEngine


class OSINTOrchestrator:
    """
    Central Coordinator for the Bhoomi Nexus Public-Source Intelligence Engine.
    """

    def __init__(self) -> None:
        self.provenance_engine = ProvenanceEngine()
        self.conflict_engine = ConflictEngine()
        self.risk_engine = RiskEngine()
        self.restriction_engine = LandRestrictionRuleEngine()
        self.temporal_engine = TemporalTimelineEngine()
        self.graph_engine = EvidenceGraphEngine()
        self.report_generator = ReportGenerator()
        self.document_engine = DocumentIntelligenceEngine()
        self.query_audit_logs: List[Dict[str, Any]] = []

    async def execute_intelligence_search(
        self, query: OSINTSearchQuery
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end intelligence query across all relevant public sources.
        """
        query_id = f"QRY-{uuid.uuid4().hex[:12].upper()}"
        start_time = datetime.now(timezone.utc)

        # 1. State Record Lookup
        state_provider = provider_registry.get_state_provider(query.state)
        state_record: Optional[SourceRecordEntry] = None
        if state_provider:
            state_record = await state_provider.search_parcel(query)

        # 2. OpenStreetMap Geo Lookup
        osm_provider = provider_registry._general_providers.get("SRC-GEOSPATIAL-OSM")
        osm_record: Optional[SourceRecordEntry] = None
        osm_obs: Optional[GeospatialObservation] = None
        if osm_provider:
            osm_record = await osm_provider.search_parcel(query)
            osm_obs = await osm_provider.get_geospatial_data(query)

        # 3. Satellite Observation History Lookup
        sat_provider = provider_registry._general_providers.get("SRC-SATELLITE-SENTINEL-ISRO")
        sat_record: Optional[SourceRecordEntry] = None
        sat_obs: Optional[GeospatialObservation] = None
        if sat_provider:
            sat_record = await sat_provider.search_parcel(query)
            sat_obs = await sat_provider.get_geospatial_data(query)

        # 4. Government Gazette / Statutory Notifications
        notif_provider = provider_registry._general_providers.get("SRC-GOVT-GAZETTES-NOTIFICATIONS")
        notifications: List[Dict[str, Any]] = []
        if notif_provider:
            notifications = await notif_provider.get_public_notifications(query)

        # Collate all retrieved source entries
        sources: List[SourceRecordEntry] = []
        if state_record:
            sources.append(state_record)
        if osm_record:
            sources.append(osm_record)
        if sat_record:
            sources.append(sat_record)

        # Collate geospatial observations
        observations: List[GeospatialObservation] = []
        if osm_obs:
            observations.append(osm_obs)
        if sat_obs:
            observations.append(sat_obs)

        # 5. Build Canonical Land Parcel
        canonical_parcel = self._build_canonical_parcel(query, state_record, sources)

        # 6. Detect Cross-Source Inconsistencies
        conflicts = self.conflict_engine.detect_conflicts(sources)

        # 7. Evaluate Statutory & Environmental Restrictions
        restrictions = self.restriction_engine.evaluate_restrictions(query)

        # 8. Construct Chronological Timeline & Anomaly Detection
        mutations_data = (
            state_record.raw_attributes.get("mutations", [])
            if state_record and state_record.raw_attributes
            else []
        )
        timeline = self.temporal_engine.build_timeline(
            parcel_id=canonical_parcel.parcel_id,
            revenue_mutations=mutations_data,
            satellite_observations=observations,
            gazette_notifications=notifications,
        )
        temporal_anomalies = self.temporal_engine.detect_temporal_anomalies(timeline)

        # 9. Calculate Composite Risk Score (0-100)
        risk = self.risk_engine.evaluate_risk(
            conflicts=conflicts,
            restrictions=restrictions,
            timeline=timeline,
            sources=sources,
        )

        # 10. Synthesize Evidence Graph
        graph = self.graph_engine.build_graph(
            parcel=canonical_parcel,
            sources=sources,
            conflicts=conflicts,
            restrictions=restrictions,
            observations=observations,
        )

        # 11. Generate Full Audit Report & Markdown Export
        report = self.report_generator.generate_report(
            query=query,
            parcel=canonical_parcel,
            sources=sources,
            conflicts=conflicts,
            restrictions=restrictions,
            risk=risk,
            observations=observations,
            timeline=timeline,
            graph=graph,
        )
        markdown_dossier = self.report_generator.generate_markdown(report)

        # Log query to audit trail
        log_entry = {
            "query_id": query_id,
            "timestamp": start_time.isoformat(),
            "operator": "authorized_analyst",
            "state": query.state,
            "district": query.district,
            "khasra": query.khasra_number or "N/A",
            "risk_score": risk.score,
            "risk_level": risk.category.value,
            "conflicts_count": len(conflicts),
            "sources_count": len(sources),
        }
        self.query_audit_logs.append(log_entry)

        return {
            "query_id": query_id,
            "parcel": canonical_parcel,
            "sources": sources,
            "conflicts": conflicts,
            "restrictions": restrictions,
            "risk_assessment": risk,
            "observations": observations,
            "timeline": timeline,
            "temporal_anomalies": temporal_anomalies,
            "graph": graph,
            "report": report,
            "markdown_dossier": markdown_dossier,
            "sources_consulted": [s.source_name for s in sources],
        }

    def _build_canonical_parcel(
        self,
        query: OSINTSearchQuery,
        primary_source: Optional[SourceRecordEntry],
        all_sources: List[SourceRecordEntry],
    ) -> CanonicalLandParcel:
        """
        Synthesizes a normalized, unified CanonicalLandParcel from disparate sources.
        """
        khasra = query.khasra_number or (primary_source.khasra_number if primary_source else "UNKNOWN")
        state_name = query.state.capitalize()
        dist_name = query.district.capitalize()
        tehsil_name = (query.tehsil or "Tehsil HQ").capitalize()
        village_name = (query.village or "Village Central").capitalize()

        # Determine normalized area
        area_ha = 1.0
        if primary_source and primary_source.area_hectares:
            area_ha = primary_source.area_hectares
        elif all_sources:
            valid_areas = [s.area_hectares for s in all_sources if s.area_hectares]
            if valid_areas:
                area_ha = valid_areas[0]

        # Determine classification
        classification = "Agricultural (Chahi / Irrigated)"
        if primary_source and primary_source.land_type:
            classification = primary_source.land_type

        # Boundary coordinates
        coords: List[List[float]] = []
        if primary_source and primary_source.coordinates:
            coords = primary_source.coordinates
        elif all_sources:
            for s in all_sources:
                if s.coordinates:
                    coords = s.coordinates
                    break

        # Provenance metadata
        prov = (
            primary_source.provenance
            if primary_source
            else ProvenanceEngine.create_metadata(
                provenance_level=ProvenanceLevel.PUBLIC_GOVERNMENT_DATA,
                source_name="Synthesized Public Inquiries",
            )
        )

        parcel_id = f"{state_name[:2].upper()}-{dist_name[:3].upper()}-{khasra.replace('/', '_')}"

        return CanonicalLandParcel(
            parcel_id=parcel_id,
            state=state_name,
            district=dist_name,
            tehsil=tehsil_name,
            village=village_name,
            primary_khasra=khasra,
            khata_number=primary_source.khata_number if primary_source else query.khata_number,
            normalized_area_ha=area_ha,
            normalized_area_acres=round(area_ha * 2.47105, 2),
            land_classification=classification,
            soil_category=primary_source.soil_type if primary_source else "Alluvial Loam",
            boundary_coordinates=coords,
            centroid={"lat": query.latitude or 26.9124, "lon": query.longitude or 75.7873},
            provenance=prov,
            sources_consulted=[s.source_name for s in all_sources],
        )

    async def cross_check_document(
        self,
        request: DocumentCrossCheckRequest,
    ) -> DocumentCrossCheckResult:
        """
        Cross-checks an uploaded deed, mutation slip, or jamabandi with public registries.
        """
        # Extract structured fields
        extracted = self.document_engine.extract_structured_fields(request.document_text)

        # File bytes
        file_bytes = request.file_bytes_base64.encode("utf-8") if request.file_bytes_base64 else request.document_text.encode("utf-8")

        # Determine query attributes
        khasra = request.declared_khasra or extracted.get("khasra_number") or "241/1"
        district = extracted.get("district") or "Jaipur"
        query = OSINTSearchQuery(
            state="Rajasthan",
            district=district,
            khasra_number=khasra,
        )

        state_provider = provider_registry.get_state_provider("Rajasthan")
        public_record = await state_provider.search_parcel(query) if state_provider else None

        return self.document_engine.cross_check_with_public_record(
            extracted_fields=extracted,
            public_record=public_record,
            file_bytes=file_bytes,
            raw_text=request.document_text,
        )

    def get_registered_providers(self) -> List[Dict[str, Any]]:
        """
        Returns list of all active registered OSINT providers with status metadata.
        """
        providers = provider_registry.get_all_providers()
        result = []
        for p in providers:
            meta = p.get_source_metadata()
            result.append({
                "provider_id": p.provider_id,
                "display_name": p.display_name,
                "category": p.category,
                "is_available": p.is_available(),
                "provenance_level": meta.provenance_level.value,
                "confidence_stars": meta.confidence_stars,
                "source_url": meta.source_url,
                "dataset_version": meta.dataset_version,
                "license": meta.license,
            })
        return result

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """
        Returns log of all executed OSINT queries.
        """
        return self.query_audit_logs


# Global orchestrator singleton
osint_orchestrator = OSINTOrchestrator()

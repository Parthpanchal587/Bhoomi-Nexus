"""
BHOOMI NEXUS - OSINT / Public-Source Land Intelligence
Land Intelligence Evidence Report Generator

Produces comprehensive, official-grade Land Intelligence Reports in Markdown
and structured JSON formats, strictly maintaining prototype safety disclaimers,
explicit data provenance, conflict matrices, and risk scoring breakdowns.
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.osint.schemas import (
    OSINTSearchQuery,
    CanonicalLandParcel,
    SourceRecordEntry,
    ConflictRecord,
    RestrictionFlag,
    RiskAssessment,
    GeospatialObservation,
    TimelineEvent,
    EvidenceGraphData,
    LandIntelligenceReport,
)

LEGAL_NOTICE_TEXT = (
    "AUTOMATED INTELLIGENCE NOTICE: This dossier is compiled from publicly accessible records, "
    "satellite observations, and open datasets for research and due-diligence prioritization. "
    "It does NOT constitute an official title certificate, judicial determination, or government cadastral clearance. "
    "Physical observations from satellite sensors reflect physical ground condition and are not proof of lawful entitlement. "
    "Final verification must be obtained from the competent Sub-Registrar and Revenue Authorities."
)


class ReportGenerator:
    """
    Assembles synthesized multi-source intelligence into an exportable, audited report.
    """

    def generate_report(
        self,
        query: OSINTSearchQuery,
        parcel: CanonicalLandParcel,
        sources: List[SourceRecordEntry],
        conflicts: List[ConflictRecord],
        restrictions: List[RestrictionFlag],
        risk: RiskAssessment,
        observations: List[GeospatialObservation],
        timeline: List[TimelineEvent],
        graph: EvidenceGraphData,
    ) -> LandIntelligenceReport:
        now_str = datetime.now(timezone.utc).isoformat()
        report_id = f"DOSSIER-{parcel.parcel_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Provenance summary count
        prov_summary: Dict[str, int] = {}
        for s in sources:
            level = s.provenance.provenance_level.value
            prov_summary[level] = prov_summary.get(level, 0) + 1

        # Average star rating
        stars = [s.provenance.confidence_stars for s in sources] if sources else [parcel.provenance.confidence_stars]
        avg_stars = round(sum(stars) / len(stars)) if stars else 4

        return LandIntelligenceReport(
            report_id=report_id,
            generated_at=now_str,
            query=query,
            parcel=parcel,
            source_snapshots=sources,
            conflicts=conflicts,
            restrictions=restrictions,
            risk_assessment=risk,
            geospatial_observations=observations,
            timeline=timeline,
            evidence_graph=graph,
            overall_confidence_stars=avg_stars,
            provenance_summary=prov_summary,
            legal_notice=LEGAL_NOTICE_TEXT,
        )

    def generate_markdown(self, report: LandIntelligenceReport) -> str:
        """
        Compiles the dossier into a human-readable Markdown format.
        """
        lines = []
        lines.append("# BHOOMI NEXUS - LAND INTELLIGENCE EVIDENCE REPORT")
        lines.append(f"**Report Reference:** `{report.report_id}`  ")
        lines.append(f"**Generated UTC:** `{report.generated_at}`  ")
        lines.append(f"**Target Parcel:** Khasra #{report.parcel.primary_khasra}, {report.parcel.village}, {report.parcel.tehsil}, {report.parcel.district}, {report.parcel.state}  ")
        lines.append(f"**Overall Confidence Rating:** {'★' * report.overall_confidence_stars}{'☆' * (5 - report.overall_confidence_stars)} ({report.overall_confidence_stars}/5 Stars)  ")
        lines.append("")
        lines.append("> ⚠️ **MANDATORY LEGAL & REGULATORY NOTICE**  ")
        lines.append(f"> {report.legal_notice}")
        lines.append("")
        lines.append("---")
        lines.append("## 1. Executive Summary & Composite Risk Triage")
        lines.append(f"- **Risk Level:** **{report.risk_assessment.category.value}** ({report.risk_assessment.score}/100)")
        lines.append(f"- **Summary:** {report.risk_assessment.summary}")
        lines.append(f"- **Total Inconsistencies:** {len(report.conflicts)}")
        lines.append(f"- **Applicable Statutory Restrictions:** {len(report.restrictions)}")
        lines.append(f"- **Multi-Year Timeline Entries:** {len(report.timeline)}")
        lines.append("")
        if report.risk_assessment.risk_factors:
            lines.append("### Risk Factor Breakdown:")
            for f in report.risk_assessment.risk_factors:
                lines.append(f"- **[{f.category}]** (+{f.points_added} pts): {f.description} *(Evidence: {f.evidence_reference})*")
            lines.append("")
        lines.append("---")
        lines.append("## 2. Canonical Parcel Attributes & Multi-Source Alignment")
        lines.append(f"- **Primary Khasra Number:** `{report.parcel.primary_khasra}`")
        if report.parcel.khata_number:
            lines.append(f"- **Khata / Account Number:** `{report.parcel.khata_number}`")
        lines.append(f"- **Normalized Area:** {report.parcel.normalized_area_ha:.4f} Ha ({report.parcel.normalized_area_acres:.2f} Acres)")
        lines.append(f"- **Land Classification:** {report.parcel.land_classification}")
        if report.parcel.soil_category:
            lines.append(f"- **Soil Category:** {report.parcel.soil_category}")
        lines.append(f"- **Consulted Data Sources:** {', '.join(report.parcel.sources_consulted)}")
        lines.append("")
        lines.append("### Source Records Consulted:")
        lines.append("| Source Name | Provenance Level | Stars | Area (Ha) | Classification |")
        lines.append("| :--- | :--- | :---: | :---: | :--- |")
        for s in report.source_snapshots:
            ha_str = f"{s.area_hectares:.4f}" if s.area_hectares else "N/A"
            lines.append(f"| {s.source_name} | `{s.provenance.provenance_level.value}` | {'★' * s.provenance.confidence_stars} | {ha_str} | {s.land_type or 'N/A'} |")
        lines.append("")
        lines.append("---")
        lines.append("## 3. Cross-Source Conflict Matrix")
        if not report.conflicts:
            lines.append("✅ No cross-source discrepancies identified across queried public registries.")
        else:
            lines.append("| Field | Expected (Primary) | Conflicting Value | Severity | Finding & Guidance |")
            lines.append("| :--- | :--- | :--- | :---: | :--- |")
            for c in report.conflicts:
                lines.append(
                    f"| `{c.field_name}` | {c.expected_value} | {c.conflicting_value} | **{c.severity.value}** | {c.description} *({c.investigative_guidance})* |"
                )
        lines.append("")
        lines.append("---")
        lines.append("## 4. Statutory & Environmental Restrictions")
        if not report.restrictions:
            lines.append("✅ No immediate statutory buffer or alienation restrictions identified in queried databases.")
        else:
            lines.append("| Rule / Statutory Act | Category | Level | Description |")
            lines.append("| :--- | :--- | :---: | :--- |")
            for r in report.restrictions:
                lines.append(f"| {r.statutory_reference} | `{r.category}` | **{r.restriction_level}** | {r.explanation} |")
        lines.append("")
        lines.append("---")
        lines.append("## 5. Physical Observations & Multi-Year Timeline")
        lines.append("| Date | Type | Description | Source | Provenance |")
        lines.append("| :--- | :--- | :--- | :--- | :---: |")
        for ev in report.timeline:
            lines.append(f"| `{ev.event_date}` | {ev.event_type} | {ev.description} | {ev.source} | `{ev.provenance.value}` |")
        lines.append("")
        lines.append("---")
        lines.append("## 6. Land Intelligence Evidence Graph")
        lines.append(f"- **Total Graph Nodes:** {len(report.evidence_graph.nodes)}")
        lines.append(f"- **Total Corroborating Edges:** {len(report.evidence_graph.edges)}")
        lines.append("")
        lines.append("---")
        report_hash = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
        lines.append(f"*Dossier Integrity Fingerprint: SHA256({report_hash})*")
        return "\n".join(lines)

"""
Comprehensive Test Suite for Bhoomi Nexus OSINT & Public-Source Land Intelligence Subsystem.
"""

import unittest
import asyncio

from app.osint.schemas import (
    ProvenanceLevel,
    SourceConfidenceStars,
    ProvenanceMetadata,
    OSINTSearchQuery,
    SourceRecordEntry,
    CanonicalLandParcel,
    ConflictSeverity,
    ConflictRecord,
    RiskCategory,
    RiskFactor,
    RiskAssessment,
    RestrictionFlag,
    GeospatialObservation,
    TimelineEvent,
    EvidenceGraphData,
    DocumentCrossCheckRequest,
    DocumentCrossCheckResult,
    LandIntelligenceReport,
)
from app.osint.provenance import ProvenanceEngine
from app.osint.providers.registry import provider_registry
from app.osint.providers.rajasthan import RajasthanSourceProvider
from app.osint.providers.madhya_pradesh import MadhyaPradeshSourceProvider
from app.osint.providers.gujarat import GujaratSourceProvider
from app.osint.providers.osm_provider import OpenStreetMapProvider
from app.osint.providers.satellite_provider import PublicSatelliteProvider
from app.osint.providers.notification_provider import GovernmentNotificationProvider
from app.osint.conflict_engine import ConflictEngine
from app.osint.restrictions import LandRestrictionRuleEngine
from app.osint.temporal_engine import TemporalTimelineEngine
from app.osint.risk_engine import RiskEngine
from app.osint.graph_engine import EvidenceGraphEngine
from app.osint.document_intelligence import DocumentIntelligenceEngine
from app.osint.report_generator import ReportGenerator
from app.osint.security import is_ip_allowed, validate_osint_url
from app.osint.rate_limiter import OSINTRateLimiter
from app.osint.orchestrator import osint_orchestrator


class TestProvenanceEngine(unittest.TestCase):
    def test_create_metadata(self):
        meta = ProvenanceEngine.create_metadata(
            provenance_level=ProvenanceLevel.VERIFIED_OFFICIAL_DATA,
            source_name="Apna Khata Rajasthan",
            source_url="https://apnakhata.rajasthan.gov.in",
            dataset_version="RoR 2025",
        )
        self.assertEqual(meta.provenance_level, ProvenanceLevel.VERIFIED_OFFICIAL_DATA)
        self.assertEqual(meta.confidence_stars, 5)
        self.assertIn("Official public land record", meta.disclaimer)

    def test_star_ratings_across_tiers(self):
        m_official = ProvenanceEngine.create_metadata(ProvenanceLevel.VERIFIED_OFFICIAL_DATA, "Gov")
        self.assertEqual(m_official.confidence_stars, 5)

        m_pub = ProvenanceEngine.create_metadata(ProvenanceLevel.PUBLIC_GOVERNMENT_DATA, "GovPub")
        self.assertEqual(m_pub.confidence_stars, 4)

        m_dataset = ProvenanceEngine.create_metadata(ProvenanceLevel.REPUTABLE_PUBLIC_DATASET, "OSM")
        self.assertEqual(m_dataset.confidence_stars, 4)

        m_third = ProvenanceEngine.create_metadata(ProvenanceLevel.THIRD_PARTY_DATA, "Index")
        self.assertEqual(m_third.confidence_stars, 2)

        m_ai = ProvenanceEngine.create_metadata(ProvenanceLevel.AI_INFERRED_INFORMATION, "AI")
        self.assertEqual(m_ai.confidence_stars, 1)


class TestProviders(unittest.IsolatedAsyncioTestCase):
    def test_state_providers_registration(self):
        rj = provider_registry.get_state_provider("Rajasthan")
        self.assertIsInstance(rj, RajasthanSourceProvider)
        mp = provider_registry.get_state_provider("Madhya Pradesh")
        self.assertIsInstance(mp, MadhyaPradeshSourceProvider)
        gj = provider_registry.get_state_provider("Gujarat")
        self.assertIsInstance(gj, GujaratSourceProvider)

    async def test_rajasthan_fetch(self):
        rj = RajasthanSourceProvider()
        query = OSINTSearchQuery(
            state="Rajasthan",
            district="Jaipur",
            tehsil="Amber",
            village="Kukas",
            khasra_number="241/1",
        )
        rec = await rj.search_parcel(query)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.khasra_number, "241/1")
        self.assertGreater(rec.area_hectares, 0)
        self.assertEqual(rec.provenance.confidence_stars, 5)

    async def test_osm_provider_features(self):
        osm = OpenStreetMapProvider()
        query = OSINTSearchQuery(state="Rajasthan", district="Jaipur", latitude=26.9124, longitude=75.7873)
        rec = await osm.search_parcel(query)
        self.assertIsNotNone(rec)
        self.assertGreater(rec.area_hectares, 0)
        obs = await osm.get_geospatial_data(query)
        self.assertIsNotNone(obs)

    async def test_satellite_provider_history(self):
        sat = PublicSatelliteProvider()
        query = OSINTSearchQuery(state="Rajasthan", district="Jaipur", latitude=26.9124, longitude=75.7873)
        rec = await sat.search_parcel(query)
        self.assertIsNotNone(rec)
        obs = await sat.get_geospatial_data(query)
        self.assertIsNotNone(obs)
        self.assertIn("Sentinel-2", obs.layer_name)

    async def test_notification_provider_search(self):
        notif = GovernmentNotificationProvider()
        query = OSINTSearchQuery(state="Rajasthan", district="Jaipur", khasra_number="241/1")
        results = await notif.get_public_notifications(query)
        self.assertGreaterEqual(len(results), 1)


class TestConflictDetectionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ConflictEngine()

    def test_detect_area_conflict(self):
        prov1 = ProvenanceEngine.create_metadata(ProvenanceLevel.VERIFIED_OFFICIAL_DATA, "State RoR")
        prov2 = ProvenanceEngine.create_metadata(ProvenanceLevel.REPUTABLE_PUBLIC_DATASET, "OSM Field Trace")

        s1 = SourceRecordEntry(
            source_id="1",
            source_name="State RoR",
            provenance=prov1,
            khasra_number="241/1",
            area_hectares=1.0,
        )
        s2 = SourceRecordEntry(
            source_id="2",
            source_name="OSM Field Trace",
            provenance=prov2,
            khasra_number="241/1",
            area_hectares=1.2,  # 20% mismatch > 5% tolerance
        )
        conflicts = self.engine.detect_conflicts([s1, s2])
        self.assertGreaterEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].field_name, "area_hectares")
        self.assertIn(conflicts[0].severity, [ConflictSeverity.MEDIUM, ConflictSeverity.HIGH])


class TestLandRestrictions(unittest.TestCase):
    def setUp(self):
        self.engine = LandRestrictionRuleEngine()

    def test_evaluate_restrictions(self):
        query_rj = OSINTSearchQuery(state="Rajasthan", district="Jaipur")
        res_rj = self.engine.evaluate_restrictions(query_rj)
        self.assertTrue(any("Section 42" in r.statutory_reference for r in res_rj))

        query_mp = OSINTSearchQuery(state="Madhya Pradesh", district="Indore")
        res_mp = self.engine.evaluate_restrictions(query_mp)
        self.assertTrue(any("Section 165" in r.statutory_reference for r in res_mp))

        query_gj = OSINTSearchQuery(state="Gujarat", district="Ahmedabad")
        res_gj = self.engine.evaluate_restrictions(query_gj)
        self.assertTrue(any("Section 73AA" in r.statutory_reference for r in res_gj))


class TestTemporalEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TemporalTimelineEngine()

    def test_build_timeline_and_detect_anomalies(self):
        mutations = [
            {"mutation_number": "101", "date": "2023-01-10", "remarks": "Transfer to A"},
            {"mutation_number": "102", "date": "2023-02-15", "remarks": "Transfer to B"},  # 36 days later
        ]
        timeline = self.engine.build_timeline("RJ-JPR-241_1", revenue_mutations=mutations)
        self.assertEqual(len(timeline), 2)
        anomalies = self.engine.detect_temporal_anomalies(timeline)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["anomaly_type"], "RAPID_SUCCESSIVE_MUTATIONS")


class TestRiskEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RiskEngine()

    def test_risk_calculation(self):
        prov = ProvenanceEngine.create_metadata(ProvenanceLevel.VERIFIED_OFFICIAL_DATA, "State")
        source = SourceRecordEntry(source_id="1", source_name="State", provenance=prov, khasra_number="241/1")
        risk = self.engine.evaluate_risk(conflicts=[], restrictions=[], timeline=[], sources=[source])
        self.assertGreaterEqual(risk.score, 0)
        self.assertLessEqual(risk.score, 100)
        self.assertIn(risk.category.value, ["LOW", "MEDIUM", "HIGH", "CRITICAL"])


class TestEvidenceGraphEngine(unittest.TestCase):
    def setUp(self):
        self.engine = EvidenceGraphEngine()

    def test_graph_synthesis(self):
        prov = ProvenanceEngine.create_metadata(ProvenanceLevel.VERIFIED_OFFICIAL_DATA, "State")
        parcel = CanonicalLandParcel(
            parcel_id="RJ-JPR-241_1",
            state="Rajasthan",
            district="Jaipur",
            tehsil="Amber",
            village="Kukas",
            primary_khasra="241/1",
            normalized_area_ha=1.0,
            normalized_area_acres=2.47,
            land_classification="Agricultural",
            provenance=prov,
        )
        source = SourceRecordEntry(source_id="1", source_name="State", provenance=prov, khasra_number="241/1")
        graph = self.engine.build_graph(parcel, [source], [], [], [])
        self.assertGreaterEqual(len(graph.nodes), 2)
        self.assertGreaterEqual(len(graph.edges), 1)


class TestDocumentIntelligence(unittest.TestCase):
    def setUp(self):
        self.engine = DocumentIntelligenceEngine()

    def test_document_hashing_and_extraction(self):
        sample_deed = (
            "SALE DEED REGISTRATION\n"
            "State of Rajasthan, District Jaipur, Tehsil Amber\n"
            "Khasra Number: 241/1\n"
            "Total Area: 10000 sq. meters\n"
            "Consideration: Rs 25,00,000\n"
        )
        fields = self.engine.extract_structured_fields(sample_deed)
        self.assertEqual(fields.get("khasra_number"), "241/1")
        self.assertEqual(fields.get("district"), "Jaipur")

        h = self.engine.compute_sha256(sample_deed.encode("utf-8"))
        self.assertEqual(len(h), 64)


class TestSecurityControls(unittest.TestCase):
    def test_ssrf_blocking(self):
        self.assertFalse(is_ip_allowed("127.0.0.1"))
        self.assertFalse(is_ip_allowed("10.0.0.5"))
        self.assertFalse(is_ip_allowed("192.168.1.1"))
        self.assertFalse(is_ip_allowed("169.254.169.254"))
        self.assertFalse(is_ip_allowed("::1"))

        self.assertTrue(is_ip_allowed("8.8.8.8"))
        self.assertTrue(is_ip_allowed("1.1.1.1"))

    def test_url_validator(self):
        is_safe, err, _ = validate_osint_url("http://127.0.0.1:8000/secret")
        self.assertFalse(is_safe)

        is_safe, err, _ = validate_osint_url("ftp://example.com")
        self.assertFalse(is_safe)

    def test_rate_limiter(self):
        limiter = OSINTRateLimiter()
        allowed, wait = limiter.check_rate_limit("test-portal.gov.in")
        self.assertTrue(allowed)
        self.assertEqual(wait, 0.0)


class TestReportGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = ReportGenerator()

    def test_report_generation_and_markdown(self):
        prov = ProvenanceEngine.create_metadata(ProvenanceLevel.VERIFIED_OFFICIAL_DATA, "State")
        parcel = CanonicalLandParcel(
            parcel_id="RJ-JPR-241_1",
            state="Rajasthan",
            district="Jaipur",
            tehsil="Amber",
            village="Kukas",
            primary_khasra="241/1",
            normalized_area_ha=1.0,
            normalized_area_acres=2.47,
            land_classification="Agricultural",
            provenance=prov,
        )
        query = OSINTSearchQuery(state="Rajasthan", district="Jaipur", khasra_number="241/1")
        risk = RiskAssessment(score=15, category=RiskCategory.LOW, risk_factors=[], summary="Low risk")
        graph = EvidenceGraphData(nodes=[], edges=[])

        report = self.generator.generate_report(
            query=query,
            parcel=parcel,
            sources=[],
            conflicts=[],
            restrictions=[],
            risk=risk,
            observations=[],
            timeline=[],
            graph=graph,
        )
        self.assertIn("AUTOMATED INTELLIGENCE NOTICE", report.legal_notice)
        md = self.generator.generate_markdown(report)
        self.assertIn("BHOOMI NEXUS - LAND INTELLIGENCE EVIDENCE REPORT", md)


class TestOSINTOrchestrator(unittest.IsolatedAsyncioTestCase):
    async def test_orchestrator_search_flow(self):
        query = OSINTSearchQuery(
            state="Rajasthan",
            district="Jaipur",
            tehsil="Amber",
            village="Kukas",
            khasra_number="241/1",
        )
        results = await osint_orchestrator.execute_intelligence_search(query)
        self.assertIn("query_id", results)
        self.assertIsNotNone(results["parcel"])
        self.assertIsNotNone(results["risk_assessment"])
        self.assertGreaterEqual(len(results["timeline"]), 1)
        self.assertGreaterEqual(len(results["graph"].nodes), 2)
        self.assertIsNotNone(results["report"])
        self.assertIn("markdown_dossier", results)

        # Check audit trail
        logs = osint_orchestrator.get_audit_trail()
        self.assertGreaterEqual(len(logs), 1)

    async def test_cross_check_document_flow(self):
        sample_deed = (
            "SALE DEED REGISTRATION\n"
            "State of Rajasthan, District Jaipur, Tehsil Amber\n"
            "Khasra Number: 241/1\n"
            "Area: 1.25 hectares\n"
        )
        req = DocumentCrossCheckRequest(
            document_text=sample_deed,
            filename="deed.txt",
            declared_khasra="241/1",
        )
        res = await osint_orchestrator.cross_check_document(req)
        self.assertIsNotNone(res.document_hash_sha256)
        self.assertEqual(len(res.document_hash_sha256), 64)
        self.assertIn("SHA-256 fingerprint", res.hash_disclaimer)


if __name__ == "__main__":
    unittest.main()

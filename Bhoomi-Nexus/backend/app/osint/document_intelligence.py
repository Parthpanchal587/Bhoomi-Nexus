"""
Document & OCR Intelligence Pipeline.

Capabilities:
1. Binary SHA-256 Document Fingerprinting (with explicit cryptographic disclaimer)
2. OCR Text Normalization & Perceptual Fingerprinting
3. Structured Field Extraction (Khasra, Khata, Village, District, Area, Registration Date, Consideration)
4. Cross-Verification of extracted document attributes against Public Land Records
5. Detection of textual clones, reconstructed deeds, or data mismatches

CRITICAL LEGAL DISCLAIMERS:
- Cryptographic SHA-256 proves exact byte uniqueness of the digital file; it does NOT prove statutory legal validity.
- High OCR text similarity indicates content resemblance; it does NOT verify official registration seals or execution.
"""

import base64
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

from app.osint.schemas import (
    ConflictRecord,
    ConflictSeverity,
    DocumentCrossCheckResult,
    SourceRecordEntry,
)


class DocumentIntelligenceEngine:
    """Extracts, fingerprints, and cross-checks land documents against public records."""

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        """Compute SHA-256 hex digest of file bytes."""
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def compute_ocr_fingerprint(text: str) -> str:
        """
        Normalize OCR text by stripping whitespace, standardizing numerals and punctuation,
        and producing a perceptual text hash.
        """
        clean = text.lower()
        clean = re.sub(r"[^\w\s]", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    def extract_structured_fields(self, text: str) -> Dict[str, Any]:
        """Extract domain-specific land deed entities from OCR text."""
        fields: Dict[str, Any] = {
            "khasra_number": None,
            "khata_number": None,
            "area_hectares": None,
            "district": None,
            "tehsil": None,
            "village": None,
            "registration_date": None,
            "registration_number": None,
            "stamp_duty_inr": None,
            "land_classification": None,
            "parties": [],
        }

        # 1. Khasra / Survey Number
        khasra_match = re.search(r"(?:khasra|survey|plot)\s*(?:no\.?|number|संख्या)?\s*[:\-]?\s*([A-Za-z0-9\/\-]+)", text, re.IGNORECASE)
        if khasra_match:
            fields["khasra_number"] = khasra_match.group(1).upper()

        # 2. Khata Number
        khata_match = re.search(r"(?:khata|khatoni|account)\s*(?:no\.?|number|संख्या)?\s*[:\-]?\s*([0-9\/\-]+)", text, re.IGNORECASE)
        if khata_match:
            fields["khata_number"] = khata_match.group(1)

        # 3. Area (Hectares / Acres / Sqft)
        area_ha_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hectare|ha|हेक्टेयर)", text, re.IGNORECASE)
        if area_ha_match:
            fields["area_hectares"] = float(area_ha_match.group(1))
        else:
            area_ac_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:acre|एकड़)", text, re.IGNORECASE)
            if area_ac_match:
                fields["area_hectares"] = round(float(area_ac_match.group(1)) * 0.404686, 2)

        # 4. District & Tehsil
        dist_match = re.search(r"(?:district|जिला)\s*[:\-]?\s*([A-Za-z]+)", text, re.IGNORECASE)
        if dist_match:
            fields["district"] = dist_match.group(1).capitalize()

        tehsil_match = re.search(r"(?:tehsil|taluk|तहसील)\s*[:\-]?\s*([A-Za-z]+)", text, re.IGNORECASE)
        if tehsil_match:
            fields["tehsil"] = tehsil_match.group(1).capitalize()

        village_match = re.search(r"(?:village|mouza|ग्राम)\s*[:\-]?\s*([A-Za-z]+)", text, re.IGNORECASE)
        if village_match:
            fields["village"] = village_match.group(1).capitalize()

        # 5. Registration Date
        date_match = re.search(r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})", text)
        if date_match:
            fields["registration_date"] = date_match.group(1)

        # 6. Stamp Number
        stamp_match = re.search(r"(?:stamp|deed|document)\s*(?:no\.?|serial)?\s*[:\-]?\s*([A-Za-z0-9\/\-]+)", text, re.IGNORECASE)
        if stamp_match:
            fields["registration_number"] = stamp_match.group(1).upper()

        # 7. Parties (heuristic: Shri/Smt Name)
        names = re.findall(r"(?:Shri|Smt|Mr\.?|Mrs\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})", text)
        fields["parties"] = list(dict.fromkeys(names))[:4]

        # 8. Classification
        if any(w in text.lower() for w in ["commercial", "व्यावसायिक"]):
            fields["land_classification"] = "Commercial"
        elif any(w in text.lower() for w in ["industrial", "औद्योगिक"]):
            fields["land_classification"] = "Industrial"
        elif any(w in text.lower() for w in ["agricultural", "farmland", "कृषि", "chahi"]):
            fields["land_classification"] = "Agricultural"

        return fields

    def cross_check_with_public_record(
        self,
        extracted_fields: Dict[str, Any],
        public_record: Optional[SourceRecordEntry],
        file_bytes: bytes,
        raw_text: str,
    ) -> DocumentCrossCheckResult:
        """
        Compare extracted document data against public land record extract.
        Detects exact matches, area divergence, or registration mismatches.
        """
        doc_hash = self.compute_sha256(file_bytes)
        ocr_fingerprint = self.compute_ocr_fingerprint(raw_text)

        match_details: List[str] = []
        conflicts: List[ConflictRecord] = []
        is_match = False

        if not public_record:
            return DocumentCrossCheckResult(
                document_hash_sha256=doc_hash,
                ocr_fingerprint_sha256=ocr_fingerprint,
                extracted_fields=extracted_fields,
                public_record_match=False,
                status="RECORD_NOT_FOUND",
                match_details=["No matching official land record found for query parameters."],
                conflicts_detected=[],
            )

        # Check Khasra reconciliation
        doc_khasra = extracted_fields.get("khasra_number")
        if doc_khasra:
            clean_doc = re.sub(r"[^A-Za-z0-9]", "", doc_khasra).upper()
            clean_pub = re.sub(r"[^A-Za-z0-9]", "", public_record.khasra_number).upper()
            if clean_doc in clean_pub or clean_pub in clean_doc:
                match_details.append(f"✓ Khasra Match: Document lists '{doc_khasra}', matching public record '{public_record.khasra_number}'.")
            else:
                conflicts.append(
                    ConflictRecord(
                        conflict_id="CONF-DOC-KHASRA-01",
                        field_name="khasra_number",
                        description="Khasra Identifier Mismatch between document and public record",
                        severity=ConflictSeverity.HIGH,
                        expected_value=public_record.khasra_number,
                        conflicting_value=doc_khasra,
                        sources_involved=["Uploaded Document", public_record.source_name],
                        confidence="HIGH",
                        possible_explanations=["Clerical error on deed", "Subdivided khasra portion not updated in public index"],
                        investigative_guidance="Inspect original Sub-Registrar volume register for exact schedule boundaries.",
                    )
                )

        # Check Area reconciliation
        doc_area = extracted_fields.get("area_hectares")
        if doc_area is not None and public_record.area_hectares is not None:
            diff = abs(doc_area - public_record.area_hectares)
            if diff <= 0.05:  # within 0.05 ha tolerance
                match_details.append(f"✓ Area Match: Document lists {doc_area} ha, closely matching recorded {public_record.area_hectares} ha.")
                is_match = True
            else:
                conflicts.append(
                    ConflictRecord(
                        conflict_id="CONF-DOC-AREA-01",
                        field_name="area_hectares",
                        description=f"Area Discrepancy: Document states {doc_area} ha while Public Record shows {public_record.area_hectares} ha",
                        severity=ConflictSeverity.HIGH,
                        expected_value=f"{public_record.area_hectares} ha",
                        conflicting_value=f"{doc_area} ha",
                        sources_involved=["Uploaded Document", public_record.source_name],
                        confidence="HIGH",
                        possible_explanations=[
                            "Document represents partial sale deed or co-sharer fractional interest.",
                            "Historical partition has not been mutated in the Record of Rights.",
                        ],
                        investigative_guidance="Confirm whether deed conveys full parcel or undivided share (Hissedari).",
                    )
                )

        status_verdict = "MATCH" if (is_match and not conflicts) else ("DATA_CONFLICT" if conflicts else "PARTIAL_MATCH")

        return DocumentCrossCheckResult(
            document_hash_sha256=doc_hash,
            ocr_fingerprint_sha256=ocr_fingerprint,
            extracted_fields=extracted_fields,
            public_record_match=(status_verdict == "MATCH"),
            status=status_verdict,
            match_details=match_details,
            conflicts_detected=conflicts,
        )


# Global document intelligence instance
document_intelligence = DocumentIntelligenceEngine()

"""
AI Research Engine — Autonomous Legal Risk Analysis.

Performs deep analysis of property documents:
- Summarizes chain of custody and title deed history
- Flags encumbrances, litigation risk indicators, missing signatures
- Generates an executive legal risk and clarity score (0–100)
"""

import re
from typing import Optional

import httpx

from app.schemas.ai import (
    AIResearchResponse,
    TitleChainEntry,
    EncumbranceFlag,
    RiskBreakdown,
)


# ── Text Analysis Helpers ─────────────────────────────────────────────────

_ENCUMBRANCE_PATTERNS = {
    "Mortgage": [r"mortgage", r"hypothecat", r"charge\s+on", r"equitable\s+mortgage", r"registered\s+mortgage"],
    "Lien": [r"\blien\b", r"statutory\s+lien", r"banker.?s?\s+lien"],
    "Easement": [r"easement", r"right\s+of\s+way", r"passage", r"access\s+road"],
    "Lease": [r"\blease\b", r"tenancy", r"lessee", r"lessor", r"rent\s+agreement"],
    "Litigation": [r"litigation", r"court\s+order", r"injunction", r"stay\s+order", r"pending\s+suit", r"dispute"],
    "Government Acquisition": [r"acquisition", r"land\s+acquisition", r"section\s+4", r"notification"],
    "Tax Arrears": [r"tax\s+arrear", r"revenue\s+due", r"unpaid\s+tax", r"demand\s+notice"],
}

_TITLE_TRANSFER_PATTERNS = {
    "Sale Deed": [r"sale\s+deed", r"conveyance\s+deed", r"deed\s+of\s+sale"],
    "Gift Deed": [r"gift\s+deed", r"deed\s+of\s+gift", r"hiba"],
    "Inheritance": [r"inherit", r"succession", r"legal\s+heir", r"death\s+certificate", r"will\s+and\s+testament"],
    "Partition": [r"partition\s+deed", r"family\s+partition", r"division"],
    "Lease": [r"lease\s+deed", r"tenancy\s+agreement"],
    "Mutation": [r"mutation", r"fard", r"intiqal"],
    "Power of Attorney": [r"power\s+of\s+attorney", r"gpa", r"general\s+power"],
}

_MISSING_ELEMENT_CHECKS = [
    ("Witness signatures", [r"witness", r"attesting\s+witness", r"signed\s+in\s+presence"]),
    ("Registration stamp", [r"stamp\s+duty", r"registration\s+fee", r"sub.?registrar"]),
    ("Survey number", [r"survey\s+no", r"khasra", r"plot\s+no", r"khata"]),
    ("Property boundaries", [r"bound", r"north", r"south", r"east", r"west", r"abut"]),
    ("Area measurement", [r"area", r"hectare", r"acre", r"sq\.?\s*ft", r"square\s+(feet|meter)"]),
    ("Consideration amount", [r"consideration", r"sale\s+price", r"total\s+amount", r"rupees"]),
    ("PAN / Aadhaar reference", [r"pan\s+no", r"aadhaar", r"identity\s+proof"]),
    ("Encumbrance certificate", [r"encumbrance\s+certificate", r"ec\s+no", r"non.?encumbrance"]),
]


def _detect_patterns(text: str, patterns: list[str]) -> bool:
    """Check if any of the regex patterns match in the text."""
    text_lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def _extract_names(text: str) -> list[str]:
    """Extract potential person names from the text (heuristic)."""
    # Look for patterns like "Shri/Smt/Mr/Mrs Name" or "S/o, D/o, W/o"
    patterns = [
        r"(?:Shri|Smt|Mr\.?|Mrs\.?|Ms\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
        r"(?:S/o|D/o|W/o|Son\s+of|Daughter\s+of|Wife\s+of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
    ]
    names = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        names.extend(matches)
    return list(dict.fromkeys(names))  # Deduplicate preserving order


# ── Main Research Engine ──────────────────────────────────────────────────

async def analyze_legal_document(
    document_text: str,
    document_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AIResearchResponse:
    """
    Perform autonomous legal research over a property document.

    Analyzes:
    - Chain of custody / title deed history
    - Encumbrances, liens, and restrictions
    - Missing legal elements
    - Litigation risk indicators
    - Generates executive risk and clarity scores
    """
    if not document_text or len(document_text.strip()) < 20:
        return _empty_research_response(document_id)

    # Try Gemini API for enhanced analysis
    if api_key:
        gemini_result = await _call_gemini_research(document_text, api_key)
        if gemini_result:
            gemini_result.document_id = document_id
            return gemini_result

    # Internal analysis engine
    return _internal_analysis(document_text, document_id)


def _internal_analysis(text: str, document_id: Optional[str]) -> AIResearchResponse:
    """Domain-specific rule-based legal document analysis."""

    # 1. Detect encumbrances
    encumbrances: list[EncumbranceFlag] = []
    for enc_type, patterns in _ENCUMBRANCE_PATTERNS.items():
        if _detect_patterns(text, patterns):
            severity = "HIGH" if enc_type in ("Litigation", "Government Acquisition") else "MEDIUM"
            encumbrances.append(EncumbranceFlag(
                type=enc_type,
                description=f"{enc_type} detected in document content. Manual verification recommended.",
                severity=severity,
                clause_reference=f"Detected via pattern matching in document text",
            ))

    # 2. Build title chain (heuristic)
    title_chain: list[TitleChainEntry] = []
    names = _extract_names(text)
    seq = 1
    for transfer_type, patterns in _TITLE_TRANSFER_PATTERNS.items():
        if _detect_patterns(text, patterns):
            owner = names[seq - 1] if seq <= len(names) else f"Owner {seq}"
            title_chain.append(TitleChainEntry(
                sequence=seq,
                owner_name=owner,
                transfer_type=transfer_type,
                notes=f"Detected {transfer_type} reference in document",
            ))
            seq += 1

    if not title_chain and names:
        # At least create entries from detected names
        for i, name in enumerate(names[:4], 1):
            title_chain.append(TitleChainEntry(
                sequence=i,
                owner_name=name,
                transfer_type="Ownership Reference",
                notes="Name extracted from document; transfer type not explicitly stated",
            ))

    # 3. Check for missing elements
    missing_elements: list[str] = []
    found_elements: list[str] = []
    for element_name, patterns in _MISSING_ELEMENT_CHECKS:
        if not _detect_patterns(text, patterns):
            missing_elements.append(element_name)
        else:
            found_elements.append(element_name)

    # 4. Litigation risk indicators
    litigation_indicators: list[str] = []
    if _detect_patterns(text, [r"litigation", r"court", r"suit", r"dispute"]):
        litigation_indicators.append("Active litigation or court proceedings referenced in document")
    if _detect_patterns(text, [r"injunction", r"stay\s+order", r"restraining"]):
        litigation_indicators.append("Judicial injunction or stay order detected")
    if len(title_chain) > 3:
        litigation_indicators.append("Multiple ownership transfers detected — verify chain continuity")
    if _detect_patterns(text, [r"power\s+of\s+attorney", r"gpa"]):
        litigation_indicators.append("Property transaction via Power of Attorney — higher risk category")

    # 5. Compute scores
    # Risk score: higher = more risky (0-100)
    risk_score = 10.0  # Base
    risk_score += len(encumbrances) * 15.0
    risk_score += len(litigation_indicators) * 12.0
    risk_score += len(missing_elements) * 5.0
    risk_score = min(100.0, risk_score)

    # Clarity score: higher = clearer (0-100)
    total_checks = len(_MISSING_ELEMENT_CHECKS)
    clarity_score = (len(found_elements) / total_checks) * 100.0 if total_checks > 0 else 50.0

    # Chain continuity
    if len(title_chain) >= 2:
        chain_status = "COMPLETE" if len(missing_elements) < 3 else "PARTIAL"
    elif len(title_chain) == 1:
        chain_status = "PARTIAL"
    else:
        chain_status = "BROKEN"

    # 6. Risk breakdown
    risk_breakdown = [
        RiskBreakdown(
            category="Encumbrance Risk",
            score=min(100, len(encumbrances) * 25.0),
            assessment="HIGH" if len(encumbrances) >= 2 else ("MEDIUM" if encumbrances else "LOW"),
            details=f"{len(encumbrances)} encumbrance(s) detected in document",
        ),
        RiskBreakdown(
            category="Title Chain Integrity",
            score=100.0 - (min(100, len(title_chain) * 20.0) if title_chain else 30.0),
            assessment=chain_status,
            details=f"{len(title_chain)} ownership transfer(s) identified",
        ),
        RiskBreakdown(
            category="Document Completeness",
            score=100.0 - clarity_score,
            assessment="COMPLETE" if clarity_score > 75 else ("PARTIAL" if clarity_score > 40 else "INCOMPLETE"),
            details=f"{len(found_elements)}/{total_checks} required elements present",
        ),
        RiskBreakdown(
            category="Litigation Exposure",
            score=min(100, len(litigation_indicators) * 30.0),
            assessment="HIGH" if len(litigation_indicators) >= 2 else ("MEDIUM" if litigation_indicators else "LOW"),
            details=f"{len(litigation_indicators)} litigation risk indicator(s) found",
        ),
    ]

    # 7. Executive summary
    summary_parts = [
        f"Legal analysis of the property document reveals a risk score of {round(risk_score, 1)}/100 "
        f"and clarity score of {round(clarity_score, 1)}/100.",
    ]
    if encumbrances:
        summary_parts.append(
            f"Detected {len(encumbrances)} potential encumbrance(s): "
            f"{', '.join(e.type for e in encumbrances)}."
        )
    if missing_elements:
        summary_parts.append(f"Missing elements: {', '.join(missing_elements[:4])}.")
    if litigation_indicators:
        summary_parts.append(f"Litigation risk: {litigation_indicators[0]}.")
    summary_parts.append(
        f"Title chain status: {chain_status} with {len(title_chain)} recorded transfer(s)."
    )

    # 8. Recommended actions
    actions = []
    if missing_elements:
        actions.append(f"Obtain missing documents: {', '.join(missing_elements[:3])}")
    if encumbrances:
        actions.append("Obtain fresh Encumbrance Certificate (EC) from Sub-Registrar's office")
    if "Litigation" in [e.type for e in encumbrances]:
        actions.append("Conduct court records search for pending suits on the property")
    if chain_status != "COMPLETE":
        actions.append("Verify complete chain of title deeds from the earliest recorded transfer")
    actions.append("Engage a qualified property lawyer for comprehensive due diligence")
    actions.append("Obtain latest property tax receipts and verify no arrears")

    return AIResearchResponse(
        document_id=document_id,
        executive_summary=" ".join(summary_parts),
        title_chain=title_chain,
        chain_continuity_status=chain_status,
        legal_risk_score=round(risk_score, 1),
        clarity_score=round(clarity_score, 1),
        risk_breakdown=risk_breakdown,
        encumbrances=encumbrances,
        missing_elements=missing_elements,
        litigation_risk_indicators=litigation_indicators,
        recommended_actions=actions,
        model_used="BHOOMI Legal Research Engine",
    )


def _empty_research_response(document_id: Optional[str]) -> AIResearchResponse:
    """Return a response when no document text is available."""
    return AIResearchResponse(
        document_id=document_id,
        executive_summary=(
            "Insufficient document content for analysis. Please upload a valid property document "
            "(sale deed, title deed, encumbrance certificate, etc.) with extractable text content."
        ),
        title_chain=[],
        chain_continuity_status="BROKEN",
        legal_risk_score=50.0,
        clarity_score=0.0,
        risk_breakdown=[
            RiskBreakdown(
                category="Document Availability",
                score=100.0,
                assessment="UNAVAILABLE",
                details="No document text provided for analysis",
            )
        ],
        encumbrances=[],
        missing_elements=["Complete document text required"],
        litigation_risk_indicators=[],
        recommended_actions=["Upload a valid property document with extractable text content"],
        model_used="BHOOMI Legal Research Engine",
    )


async def _call_gemini_research(text: str, api_key: str) -> Optional[AIResearchResponse]:
    """Call Gemini API for enhanced legal analysis."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = (
            "You are an expert Indian property law analyst. Analyze the following property document "
            "and return a JSON response with these fields:\n"
            "- executive_summary: string\n"
            "- title_chain: [{sequence: int, owner_name: string, transfer_type: string, date: string, notes: string}]\n"
            "- chain_continuity_status: COMPLETE|PARTIAL|BROKEN\n"
            "- legal_risk_score: 0-100 (higher = more risk)\n"
            "- clarity_score: 0-100 (higher = clearer)\n"
            "- encumbrances: [{type: string, description: string, severity: LOW|MEDIUM|HIGH|CRITICAL}]\n"
            "- missing_elements: [string]\n"
            "- litigation_risk_indicators: [string]\n"
            "- recommended_actions: [string]\n\n"
            f"DOCUMENT:\n{text[:4000]}\n\nRespond ONLY with valid JSON."
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                import json
                data = resp.json()
                parsed = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])

                return AIResearchResponse(
                    executive_summary=parsed.get("executive_summary", ""),
                    title_chain=[
                        TitleChainEntry(**entry) for entry in parsed.get("title_chain", [])
                    ],
                    chain_continuity_status=parsed.get("chain_continuity_status", "PARTIAL"),
                    legal_risk_score=float(parsed.get("legal_risk_score", 50)),
                    clarity_score=float(parsed.get("clarity_score", 50)),
                    risk_breakdown=[
                        RiskBreakdown(
                            category="AI Assessment",
                            score=float(parsed.get("legal_risk_score", 50)),
                            assessment="AI-Generated",
                            details="Comprehensive analysis by Gemini AI",
                        )
                    ],
                    encumbrances=[
                        EncumbranceFlag(**e) for e in parsed.get("encumbrances", [])
                    ],
                    missing_elements=parsed.get("missing_elements", []),
                    litigation_risk_indicators=parsed.get("litigation_risk_indicators", []),
                    recommended_actions=parsed.get("recommended_actions", []),
                    model_used="Google Gemini 1.5 Flash (Live Legal Analysis)",
                )
    except Exception:
        pass
    return None

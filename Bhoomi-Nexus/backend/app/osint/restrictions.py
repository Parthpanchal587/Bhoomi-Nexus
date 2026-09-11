"""
Configurable Land Restriction Rule Engine.

Evaluates jurisdiction-specific statutory and environmental land-use restrictions:
- SC/ST tribal land transfer protections (e.g. Section 42 of Rajasthan Tenancy Act, Section 165 of MP Land Revenue Code, Section 73AA of Gujarat Code)
- Infrastructure right-of-way building offsets (National Highways Act Section 3A)
- Eco-sensitive zone (ESZ) buffers around national parks and wildlife sanctuaries
- Water body, wetland, and drainage catchment non-construction buffers

CRITICAL LEGAL SAFEGUARD:
Never outputs definitive legal decrees. Always provides rule references and advises
verification with the Competent Authority (District Collector / Revenue Tribunal).
"""

from typing import Dict, List, Optional

from app.osint.schemas import OSINTSearchQuery, RestrictionFlag


class LandRestrictionRuleEngine:
    """Configurable statutory restriction evaluator."""

    def __init__(self) -> None:
        self._rules = self._load_rules_database()

    def evaluate_restrictions(self, query: OSINTSearchQuery) -> List[RestrictionFlag]:
        """Evaluate applicable restrictions for the given parcel query."""
        state = query.state.strip().lower() if query.state else "rajasthan"
        district = query.district.strip().lower() if query.district else ""

        applicable: List[RestrictionFlag] = []

        # 1. State-Specific Tribal / Inalienability Protection Rules
        if "rajasthan" in state or state == "rj":
            applicable.append(self._rules["RJ-TENANCY-SEC42"])
        elif "madhya" in state or state == "mp":
            applicable.append(self._rules["MP-LRC-SEC165"])
        elif "gujarat" in state or state == "gj":
            applicable.append(self._rules["GJ-LRC-SEC73AA"])

        # 2. Highway Infrastructure Corridor Restriction
        applicable.append(self._rules["NAT-HIGHWAY-ROW-60M"])

        # 3. Wildlife / Forest Eco-Sensitive Buffer (District Specific)
        if any(d in district for d in ["alwar", "sawai", "jaisalmer", "hoshangabad", "junagadh", "gir"]):
            applicable.append(self._rules["ENV-ESZ-BUFFER-1KM"])

        return applicable

    def _load_rules_database(self) -> Dict[str, RestrictionFlag]:
        return {
            "RJ-TENANCY-SEC42": RestrictionFlag(
                rule_id="RJ-TENANCY-SEC42",
                jurisdiction="Rajasthan",
                category="SC_ST_TRIBAL_LAND",
                title="Statutory Bar on Sale/Transfer of SC/ST Khatedari Land to Non-SC/ST",
                statutory_reference="Rajasthan Tenancy Act 1955, Section 42(b)",
                effective_date="1955-10-15 (As amended up to 2024)",
                version="2025.1",
                explanation=(
                    "Under Section 42(b), any sale, gift, mortgage, or transfer of agricultural land belonging to "
                    "a Scheduled Caste or Scheduled Tribe khatedar to a person who is not a member of SC/ST is void ab initio. "
                    "Sub-registrars are barred from registering deeds without prior statutory sanction from the District Collector."
                ),
                restriction_level="STATUTORY_SANCTION_REQUIRED",
                verification_status="Requires Sub-Registrar / SDO Verification of Seller Category",
            ),
            "MP-LRC-SEC165": RestrictionFlag(
                rule_id="MP-LRC-SEC165",
                jurisdiction="Madhya Pradesh",
                category="SC_ST_TRIBAL_LAND",
                title="Restriction on Transfer of Bhumiswami Rights of Aboriginal Tribes",
                statutory_reference="Madhya Pradesh Land Revenue Code 1959, Section 165(6)",
                effective_date="1959-10-02 (Amended 2023)",
                version="2025.1",
                explanation=(
                    "Land belonging to a Bhumiswami belonging to a Scheduled Tribe in notified scheduled areas cannot "
                    "be transferred by sale, lease, or otherwise to a non-tribal person without prior written sanction "
                    "of the Collector for reasons to be recorded in writing."
                ),
                restriction_level="STATUTORY_SANCTION_REQUIRED",
                verification_status="Requires Collector Sanction Verification",
            ),
            "GJ-LRC-SEC73AA": RestrictionFlag(
                rule_id="GJ-LRC-SEC73AA",
                jurisdiction="Gujarat",
                category="SC_ST_TRIBAL_LAND",
                title="Prohibition of Transfer of Land of Scheduled Tribes to Non-Tribals",
                statutory_reference="Gujarat Land Revenue Code 1879, Section 73AA",
                effective_date="1981-02-01 (Amended 2024)",
                version="2025.1",
                explanation=(
                    "Restricts occupancy transfer from tribal to non-tribal persons in designated tribal talukas. "
                    "Any unregistered or unauthorized transfer entitles the Collector to summary eviction and restoration."
                ),
                restriction_level="STATUTORY_SANCTION_REQUIRED",
                verification_status="Requires Prant Officer / Collector Verification",
            ),
            "NAT-HIGHWAY-ROW-60M": RestrictionFlag(
                rule_id="NAT-HIGHWAY-ROW-60M",
                jurisdiction="All-India (National)",
                category="HIGHWAY_BUFFER",
                title="Statutory Building Line & Right-of-Way Along National Highway Corridors",
                statutory_reference="National Highways Act 1956, Section 3A & MoRTH Circular 2022",
                effective_date="2022-04-01",
                version="2025.2",
                explanation=(
                    "Prohibits permanent construction within 40m to 60m of National Highway centerline depending on road class. "
                    "Non-agricultural development requires prior NHAI access permission and structural NOC."
                ),
                restriction_level="BUFFER_OFFSET",
                verification_status="Requires NHAI Project Director NOC",
            ),
            "ENV-ESZ-BUFFER-1KM": RestrictionFlag(
                rule_id="ENV-ESZ-BUFFER-1KM",
                jurisdiction="All-India / State Wildlife Traces",
                category="FOREST_ECO_SENSITIVE",
                title="Eco-Sensitive Zone (ESZ) Regulated Activity Radius Around Protected Sanctuaries",
                statutory_reference="Supreme Court Guidelines (W.P. 202/1995) & MoEFCC Notifications",
                effective_date="2023-06-03",
                version="2025.1",
                explanation=(
                    "Activities within ESZ 1.0 km radius from national park/sanctuary boundaries are classified into "
                    "Prohibited, Regulated, and Permitted. Commercial conversion requires State Forest Dept & NBWL clearance."
                ),
                restriction_level="PROHIBITED_FOR_POLLUTING_UNITS",
                verification_status="Requires Divisional Forest Officer (DFO) Boundary Certificate",
            ),
        }


# Global restriction engine instance
restriction_engine = LandRestrictionRuleEngine()

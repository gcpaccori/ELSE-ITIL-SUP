"""Small deterministic Pareto evidence router for the 2026-01 ITIL QA cohort.

This module does NOT act as a SQL Hand. It routes cases to explicit evidence
needs, and prevents a generic model plan from being called a verified diagnosis
when a source-specific read or case-to-domain binding is absent.

Cohort used to choose lanes: Jan 1-10 2026, 638 unique cases.
No historical resolution is consulted for routing. The classification is
keyword-assisted prioritization, NOT an authoritative corporate service map.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any

SCHEMA="else.itil.pareto-evidence-routing.v1"

# Pattern order is intentional. The SAP family includes business records,
# but must not be silently routed to the commercial SQL schema.
PATTERNS={
    "SAP_INTEGRATION":re.compile(
        r"\b(?:SAP|BAPI|RFC|HANA|pedido\s+(?:de\s+)?almac[eé]n)\b",re.I),
    "COMMERCIAL_OT":re.compile(
        r"\b(?:suministro|medidor|lectura(?:s)?|facturaci[oó]n|cobranza|"
        r"comprobante|recibo|saldo|refacturaci[oó]n|"
        r"orden\s+(?:de\s+)?trabajo|OT|material(?:es)?|liquidaci[oó]n)\b",re.I),
    "ACCESS_PERMISSIONS":re.compile(
        r"\b(?:contrase[nñ]a|clave|permisos?|perfil(?:es)?|habilitar|"
        r"acceso|autorizaci[oó]n|rol(?:es)?)\b",re.I),
    "APPLICATION":re.compile(
        r"\b(?:error|falla|sistema|aplicaci[oó]n|m[oó]dulo|pantalla|proceso)\b",re.I),
}
# Terms are only hints for a potential OT. The returned routing record NEVER
# contains a numeric OT or user identifier from the incident description.
OT_RE=re.compile(
    r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]d(?:igo)?\s*OT)"
    r"\s*[:#-]?\s*\d{4,19}\b",re.I)

# These are evidence categories, not automatically available Hands.
LANE_REQUIRED={
    "SAP_INTEGRATION":("ITIL_CASE_EXACT","SAP_OT_BINDING",
                       "SAP_ORDER_AND_RESPONSE"),
    "COMMERCIAL_OT":("ITIL_CASE_EXACT","COMMERCIAL_OT_EXACT"),
    "ACCESS_PERMISSIONS":("ITIL_CASE_EXACT","SEC_EFFECTIVE_PERMISSION"),
    "APPLICATION":("ITIL_CASE_EXACT","APPLICATION_LOG_OR_CONFIG"),
    "ITIL_TRIAGE":("ITIL_CASE_EXACT",),
}
SERVICE_PARETO=("1","3","2")
DATE_START="2026-01-01"
DATE_END_EXCLUSIVE="2026-01-11"
HEX64=re.compile(r"[0-9a-f]{64}\Z")
CODE=re.compile(r"[\x20-\x7e]{1,40}\Z")


@dataclass(frozen=True)
class EvidenceRoute:
    lane:str
    service_code:str
    case_sha256:str
    required_receipts:tuple[str,...]
    missing_receipts:tuple[str,...]
    ot_identifier_reported:bool
    case_in_pareto_services:bool

    def public(self)->dict[str,Any]:
        return {"schema":SCHEMA,"lane":self.lane,
                "service_code":self.service_code,
                "case_sha256":self.case_sha256,
                "required_receipts":list(self.required_receipts),
                "missing_receipts":list(self.missing_receipts),
                "ot_identifier_reported_not_verified":self.ot_identifier_reported,
                "in_pareto_service_codes":self.case_in_pareto_services,
                "root_cause_certified":False,
                "repair_certified":False,
                "human_review_required":True}


def decide_lane(*,service_code:str,description:str)->str:
    """Avoid interpreting the service code as its corporate description."""
    if type(service_code) is not str or not CODE.fullmatch(service_code):
        raise ValueError("SERVICE_CODE_INVALID")
    if type(description) is not str or not 1<=len(description)<=5000:
        raise ValueError("DESCRIPTION_INVALID")
    if PATTERNS["SAP_INTEGRATION"].search(description):
        return "SAP_INTEGRATION"
    if PATTERNS["COMMERCIAL_OT"].search(description):
        return "COMMERCIAL_OT"
    # Within the observed high-access family 70, explicit user/access
    # references route to permissions, never infer permissions from HTTP 403.
    if PATTERNS["ACCESS_PERMISSIONS"].search(description):
        return "ACCESS_PERMISSIONS"
    if PATTERNS["APPLICATION"].search(description):
        return "APPLICATION"
    return "ITIL_TRIAGE"


def route_case(*,case_sha256:str,service_code:str,description:str,
               verified_receipt_categories=frozenset())->EvidenceRoute:
    if type(case_sha256) is not str or HEX64.fullmatch(case_sha256) is None:
        raise ValueError("CASE_SHA_INVALID")
    if type(verified_receipt_categories) not in (frozenset,set,tuple):
        raise ValueError("RECEIPT_CATEGORY_TYPE_INVALID")
    if not all(type(c) is str and c in {
            item for seq in LANE_REQUIRED.values() for item in seq}
               for c in verified_receipt_categories):
        raise ValueError("RECEIPT_CATEGORY_INVALID")
    lane=decide_lane(service_code=service_code,description=description)
    needed=LANE_REQUIRED[lane]
    verified=frozenset(verified_receipt_categories)
    missing=tuple(c for c in needed if c not in verified)
    return EvidenceRoute(lane,service_code,case_sha256,needed,missing,
                         bool(OT_RE.search(description)),
                         service_code in SERVICE_PARETO)


def evidence_gate(*,route:EvidenceRoute,model_completed:bool,
                  original_contract_pass:bool,
                  claimed_sql_sources:bool=False)->dict:
    """No model-asserted evidence can satisfy this gate.

    Previous source-bound pass is only a text/contract check, NOT a live read.
    The caller must supply genuinely verified receipts from actual Hands.
    """
    if not model_completed:
        status="MODEL_INCOMPLETE"
    elif not original_contract_pass:
        status="MODEL_CONTRACT_REJECTED"
    elif route.missing_receipts:
        status="MISSING_VERIFIED_EVIDENCE"
    elif claimed_sql_sources:
        status="SQL_PROVENANCE_REVIEW_REQUIRED"
    else:
        status="REVIEWABLE_NOT_CERTIFIED"
    return {"schema":SCHEMA,"status":status,
            "lane":route.lane,
            "missing_receipts":list(route.missing_receipts),
            "contract_passed":bool(model_completed and original_contract_pass),
            "domain_evidence_complete":not bool(route.missing_receipts),
            "repair_certified":False,
            "root_cause_certified":False,
            "human_review_required":True,
            "automatic_training":False}

"""Fail-closed intake of independent diagnostic audits, never a repair oracle.

The verifier accepts externally pinned, immutable audit bytes. It does not
execute SQL, train models, authorize actions or validate root causes.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import json
import re

SCHEMA = "else.itil.causal-calibration-independent-audit.v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX16 = re.compile(r"[0-9a-f]{16}\Z")
RELATIONS = {"SUPPORTED", "PARTIAL", "CONFLICT", "INDETERMINATE"}
HISTORY = {"ACTIONABLE", "VAGUE", "INSUFFICIENT", "CONTRADICTORY"}
GAPS = {"NONE", "MISSING_EVIDENCE", "WRONG_SOURCE", "NO_CAUSAL_TEST",
        "UNSUPPORTED_MUTATION", "HISTORY_VAGUE", "OTHER"}

class CausalAuditDenied(ValueError):
    pass

def require(cond: bool, reason: str) -> None:
    if not cond:
        raise CausalAuditDenied(reason)

def verify_audit(raw: bytes, *, pinned_sha256: str) -> dict:
    require(type(raw) is bytes and 1 <= len(raw) <= 100000,
            "AUDIT_BYTES_INVALID")
    require(type(pinned_sha256) is str and HEX64.fullmatch(pinned_sha256) is not None,
            "AUDIT_PIN_INVALID")
    require(sha256(raw).hexdigest() == pinned_sha256, "AUDIT_BYTES_DRIFT")
    try:
        audit = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise CausalAuditDenied("AUDIT_JSON_INVALID") from exc
    require(type(audit) is dict and audit.get("schema") == SCHEMA, "AUDIT_SCHEMA_INVALID")
    require(audit.get("scope") == "CALIBRATION_ONLY_NOT_FRESH_BLIND_EXAM", "AUDIT_PURPOSE_INVALID")
    require(str(audit.get("source", "")).startswith("ELSE70/dbITIL_D/"), "AUDIT_SOURCE_INVALID")
    for field in ("training_performed", "corporate_mutations", "gold_exposed_to_generator"):
        require(audit.get(field) is False, "FORBIDDEN_TRUE_" + field)
    for field in ("repairs_certified", "functional_root_causes_certified",
                  "supervision_examples_authorized"):
        require(type(audit.get(field)) is int and audit[field] == 0,
                "FALSE_CERTIFICATION_" + field)
    require(audit.get("human_review_pending") == audit.get("total"), "HUMAN_REVIEW_MISSING")
    require(type(audit.get("independent_negative_tests_passed")) is int and
            audit["independent_negative_tests_passed"] >= 3, "NEGATIVE_GATES_MISSING")
    cases = audit.get("cases")
    require(type(cases) is list and 1 <= len(cases) <= 50 and
            type(audit.get("total")) is int and audit["total"] == len(cases),
            "AUDIT_CASE_COUNT_INVALID")
    seen = set()
    for case in cases:
        require(type(case) is dict, "CASE_NOT_OBJECT")
        digest = case.get("digest_prefix")
        require(type(digest) is str and HEX16.fullmatch(digest) is not None and
                digest not in seen, "CASE_ID_INVALID_OR_DUPLICATE")
        seen.add(digest)
        for field in ("plan_sha256", "review_sha256"):
            value = case.get(field)
            require(type(value) is str and HEX64.fullmatch(value) is not None,
                    "CASE_SHA_MISSING_" + field)
        require(type(case.get("service")) is str and bool(case["service"]), "SERVICE_MISSING")
        require(type(case.get("gate_pass")) is bool, "QA_GATE_NOT_BOOLEAN")
        require(case.get("relation") in RELATIONS and
                case.get("history_quality") in HISTORY and
                case.get("technical_gap") in GAPS, "JUDGE_ENUM_INVALID")
        require(case.get("repair_certified") is False, "FALSE_CASE_REPAIR")
        if not case["gate_pass"]:
            require(case.get("decision") == "INVALID_PLAN", "INVALID_PLAN_FALSE_PASS")
        elif case["relation"] == "SUPPORTED":
            require(case.get("decision") == "DOCUMENTARY_COMPATIBILITY_ONLY" and
                    case["history_quality"] == "ACTIONABLE", "DOCUMENTARY_PASS_UNJUSTIFIED")
        else:
            require(case.get("decision") == "NEEDS_REVIEW", "REVIEW_STATUS_UNJUSTIFIED")
    require(type(audit.get("gate_pass")) is int and
            audit["gate_pass"] == sum(c["gate_pass"] for c in cases), "QA_COUNT_DRIFT")
    require(type(audit.get("gate_failed")) is int and
            audit["gate_failed"] == len(cases)-audit["gate_pass"], "QA_FAIL_COUNT_DRIFT")
    require(audit.get("documentary_relation_counts") == dict(Counter(c["relation"] for c in cases)),
            "JUDGE_COUNT_DRIFT")
    require(audit.get("decisions") == dict(Counter(c["decision"] for c in cases)),
            "DECISION_COUNT_DRIFT")
    return audit

def make_review_queue(raw: bytes, *, pinned_sha256: str) -> dict:
    audit=verify_audit(raw,pinned_sha256=pinned_sha256)
    entries=[]
    for c in audit["cases"]:
        if not c["gate_pass"]:
            next_action="FIX_SOURCE_BINDING_AND_REEVALUATE"
        elif c["relation"] == "SUPPORTED" and c["history_quality"] == "ACTIONABLE":
            next_action="GET_INDEPENDENT_FUNCTIONAL_QA_AND_HUMAN_SIGNOFF"
        else:
            next_action="COLLECT_CAUSAL_EVIDENCE_AND_EXPERT_REVIEW"
        entries.append({"case_digest_prefix":c["digest_prefix"], "service":c["service"],
          "plan_sha256":c["plan_sha256"], "review_sha256":c["review_sha256"],
          "next_action":next_action, "state":"UNDER_REVIEW",
          "eligible_for_training":False,"repair_certified":False,
          "root_cause_certified":False})
    return {"schema":"else.itil.causal-review-queue.v1","audit_sha256":pinned_sha256,
            "source":"PRIVATE_QA_AUDIT", "cases":entries,
            "promotion_decision":"BLOCKED",
            "training_performed":False, "certified_repairs":0}

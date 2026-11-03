"""ELSE-ITIL V1: strictly 2025-only curriculum and unverified draft generation.

Historical analyst solutions are *weak labels*, never ground truth. This module
never mutates corporate systems, promotes adapters or certifies repairs.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import re

from .resolution_batch import KNOWN_SOURCES, evaluate_response
from .support_desk import SYSTEM

YEAR = 2025
MONTHS = tuple(f"2025-{month:02d}" for month in range(1, 13))
CASE_SHA = re.compile(r"[0-9a-f]{64}")
PRIVACY_MARKER = re.compile(
    r"\[(?:EMAIL|PHONE|NAME|PATH|DOMAIN|URL|SECRET|PERSONAL_ID)\]|"
    r"(?i:password\s*[:=]|token\s*[:=]|contrase(?:na|ña)\s*[:=])"
)


def validated_input(row: dict) -> dict:
    """Validate provenance and keep the historical answer sealed."""
    if not isinstance(row, dict):
        raise ValueError("CASE_NOT_OBJECT")
    if type(row.get("year")) is not int or row["year"] != YEAR:
        raise ValueError("ONLY_2025_TRAINING")
    if row.get("month") not in MONTHS:
        raise ValueError("INVALID_2025_MONTH")
    if row.get("label_status") != "UNVERIFIED_HISTORIC_2025":
        raise ValueError("HISTORICAL_LABEL_STATUS_REQUIRED")
    digest = str(row.get("case_sha256", ""))
    if not CASE_SHA.fullmatch(digest):
        raise ValueError("CASE_DIGEST_REQUIRED")
    incident = str(row.get("user") or "").strip()
    historic = str(row.get("assistant_target") or "").strip()
    if len(incident) < 40 or len(incident) > 2500:
        raise ValueError("INVALID_INCIDENT")
    if len(historic) < 30 or len(historic) > 3000:
        raise ValueError("INVALID_HISTORICAL_WEAK_LABEL")
    if PRIVACY_MARKER.search(incident + historic):
        raise ValueError("PRIVACY_REVIEW_REQUIRED")
    return {
        "case_sha256": digest, "year": YEAR, "month": row["month"],
        "incident": incident,
        "historical_solution_unverified": historic,
        "training_approved": False,
    }


def select_2025_curriculum(rows, *, per_month: int = 20) -> list[dict]:
    """Balanced, reproducible 12-month curriculum; fail on missing months."""
    if not 1 <= per_month <= 100:
        raise ValueError("INVALID_MONTH_QUOTA")
    buckets = defaultdict(list)
    seen = set()
    for original in rows:
        item = validated_input(original)
        if item["case_sha256"] in seen:
            raise ValueError("DUPLICATE_CASE_DIGEST")
        seen.add(item["case_sha256"])
        buckets[item["month"]].append(item)
    if any(len(buckets[month]) < per_month for month in MONTHS):
        raise ValueError("INCOMPLETE_2025_CURRICULUM")
    result = []
    for month in MONTHS:
        candidates = sorted(
            buckets[month],
            key=lambda item: hashlib.sha256(
                (item["case_sha256"] + ":V1_CURRICULUM").encode()
            ).digest(),
        )
        result.extend(candidates[:per_month])
    return result


def learning_messages(row: dict) -> list[dict]:
    """Do not expose the historical solution to the trainee."""
    item = validated_input(row)
    payload = {
        "case_ref": item["case_sha256"][:16],
        "service_and_incident": item["incident"],
        "available_sources": sorted(KNOWN_SOURCES),
        "source_year": YEAR,
        "historical_solution_available": False,
        "required_output": "Un plan condicionado, nunca un cierre confirmado",
    }
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def draft_2025_case(row: dict, model) -> dict:
    """A real LLM diagnosis, still ONLY a proposal needing human verification."""
    item = validated_input(row)
    raw = model.complete(learning_messages(row))
    response = json.loads(raw)
    assessment = evaluate_response(response)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return {
        "case_sha256": item["case_sha256"],
        "month": item["month"],
        "schema_ok": assessment["valid"],
        "schema_flags": assessment["flags"],
        "proposal_sha256": digest,
        "proposal": response,  # PRIVATE data; callers must not put this in Git.
        "state": "DRAFT_NEEDS_REVIEW" if assessment["valid"] else "REJECTED_DRAFT",
        "training_approved": False,
        "repair_certified": False,
        "historical_answer_shown_to_student": False,
        "requires_verified_outcome_receipt": True,
    }

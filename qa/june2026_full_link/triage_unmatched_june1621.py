"""Source-only triage of unresolved June tickets; never an object-certification gate.

Consumes original June descriptions already redacted for research plus the signed
retrospective link graph. Does not read historical solutions, customer identities,
business primary-key values, or run SQL. Public output is strictly aggregated.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

REPORT_SCHEMA = "else.itil.qa.june1621-unresolved-source-triage.v1"
FAMILIES = {
    "OT": r"\b(?:OT|ORDEN(?:ES)? DE TRABAJO)\b",
    "SUMINISTRO": r"SUMINISTR",
    "COBRANZA_CAJA": r"COBRAN|ARQUEO|\bCAJA\b",
    "FACTURACION": r"FACTUR|RECIBO|COMPROBANTE",
    "RECLAMO": r"RECLAM|DENUNCIA",
    "ACCESO_USUARIO": r"USUARIO|ACCESO|CONTRASE|PERMISO|PASSWORD",
    "DOCUMENTAL": r"DOCUMENT|ARCHIVO|FIRMA|MGD",
    "LECTURA_MEDIDOR": r"LECTURA|MEDIDOR",
    "SOLICITUD": r"SOLICITUD",
}
PATTERNS = {name: re.compile(expr, re.IGNORECASE) for name, expr in FAMILIES.items()}


def source_hints(redacted_description: str) -> list[str]:
    if not isinstance(redacted_description, str):
        raise ValueError("REDACTED_DESCRIPTION_NOT_TEXT")
    return [name for name, pattern in PATTERNS.items()
            if pattern.search(redacted_description)]


def triage_state(candidate_count: int, link_count: int) -> str:
    if type(candidate_count) is not int or type(link_count) is not int:
        raise ValueError("INVALID_COUNT_TYPE")
    if candidate_count < 0 or link_count < 0:
        raise ValueError("INVALID_NEGATIVE_COUNT")
    if link_count > 0:
        return "ONE_QA_PK" if link_count == 1 else "MULTIPLE_QA_PKS"
    return "NO_19_DIGIT_CANDIDATE" if candidate_count == 0 else "19_DIGIT_WITHOUT_SAME_BRANCH_PK"


def verified_sha(path: Path, proof_path: Path) -> str:
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    digest = sha256(path.read_bytes()).hexdigest()
    if proof.get("receipt_sha256") != digest:
        raise ValueError("RECEIPT_SHA256_MISMATCH")
    # This only checks byte integrity against the published receipt hash.
    # HMAC authenticity was independently verified in the preceding #43 QA.
    return digest


def summarize(original_cases: list, linked_cases: list, *, expected_total: int = 1621) -> dict:
    if len(original_cases) != len(linked_cases) or len(original_cases) != expected_total:
        raise ValueError("COHORT_LENGTH_MISMATCH")
    statuses = Counter()
    hints_by_status = defaultdict(Counter)
    modules_by_status = defaultdict(Counter)
    no_keyword = Counter()
    total_hints = Counter()
    for index, (source, graph) in enumerate(zip(original_cases, linked_cases), start=1):
        if (source["rank"] != index or graph["rank"] != index or
                source["case_sha256"] != graph["case_sha256"] or
                source["description_sha256"] != graph["request_sha256"] or
                source["module_code"] != graph["module_code"] or
                source["service_code"] != graph["service_code"] or
                source["opened_at"] != graph["opened_at"] or
                source.get("historical_solution_not_read") is not True):
            raise ValueError("SOURCE_GRAPH_CASE_MISMATCH")
        status = triage_state(graph["source_numeric_candidate_count"], len(graph["links"]))
        if status.startswith("NO_") or status.startswith("19_DIGIT"):
            if graph["links"]:
                raise ValueError("UNRESOLVED_CASE_HAS_LINKS")
        else:
            if not graph["links"]:
                raise ValueError("LINKED_CASE_HAS_NO_LINKS")
        statuses[status] += 1
        modules_by_status[status][str(graph["module_code"])] += 1
        labels = source_hints(source["description_redacted"])
        if not labels:
            no_keyword[status] += 1
        for label in labels:
            hints_by_status[status][label] += 1
            total_hints[label] += 1
    unresolved = statuses["NO_19_DIGIT_CANDIDATE"] + statuses["19_DIGIT_WITHOUT_SAME_BRANCH_PK"]
    report = {
        "schema": REPORT_SCHEMA,
        "period": "2026-06",
        "evaluated_requests": len(original_cases),
        "input_source_only": True,
        "historical_solutions_or_gold_labels_consulted": False,
        "business_sql_executed_in_this_stage": 0,
        "business_writes": 0,
        "triage_is_not_historical_business_state_or_repair_evidence": True,
        "counts": {
            "no_19_digit_candidate": statuses["NO_19_DIGIT_CANDIDATE"],
            "19_digit_no_same_branch_pk": statuses["19_DIGIT_WITHOUT_SAME_BRANCH_PK"],
            "one_retrospective_qa_pk": statuses["ONE_QA_PK"],
            "multiple_retrospective_qa_pks": statuses["MULTIPLE_QA_PKS"],
            "unresolved_total": unresolved,
            "retrospectively_linked_total":
                statuses["ONE_QA_PK"] + statuses["MULTIPLE_QA_PKS"],
        },
        "textual_hints_from_redacted_requests": {
            key: {name: hints_by_status[key][name] for name in PATTERNS}
            for key in ("NO_19_DIGIT_CANDIDATE",
                        "19_DIGIT_WITHOUT_SAME_BRANCH_PK",
                        "ONE_QA_PK", "MULTIPLE_QA_PKS")
        },
        "without_any_textual_hint": dict(sorted(no_keyword.items())),
        "modules_with_most_unresolved": [
            {"module_code": module, "unresolved_cases": count}
            for module, count in (modules_by_status["NO_19_DIGIT_CANDIDATE"] +
                                  modules_by_status["19_DIGIT_WITHOUT_SAME_BRANCH_PK"]).most_common(15)
        ],
        "recommendation": (
            "Investigate non-19-digit, typed corporate identifiers and module-specific "
            "sources on new QA reads; never treat lexical hints as business-object keys."
        ),
        "no_factual_claim_that_unmatched_records_do_not_exist": True,
    }
    if expected_total == 1621 and report["counts"] != {
        "no_19_digit_candidate": 1162,
        "19_digit_no_same_branch_pk": 126,
        "one_retrospective_qa_pk": 158,
        "multiple_retrospective_qa_pks": 175,
        "unresolved_total": 1288,
        "retrospectively_linked_total": 333,
    }:
        raise ValueError("FROZEN_COHORT_TRIAGE_COUNTS_CHANGED")
    return report


def classify_unmatched_search_outcome(linked_cases: list, raw_matches: list) -> dict:
    # An observed PK in another branch is not a verified link to this ticket.
    ranks_with_any_pk = set()
    ranks_with_valid_branch = set()
    for row in raw_matches:
        rank = row["rank"]
        ranks_with_any_pk.add(rank)
        if row["business_branch_matches_itil"] is True:
            ranks_with_valid_branch.add(rank)
    wrong_branch_only = 0
    no_pk_anywhere_queried = 0
    for case in linked_cases:
        if case["source_numeric_candidate_count"] <= 0 or case["links"]:
            continue
        rank = case["rank"]
        if rank in ranks_with_valid_branch:
            raise ValueError("GHOST_VALID_BRANCH_MATCH_IN_UNLINKED_CASE")
        if rank in ranks_with_any_pk:
            wrong_branch_only += 1
        else:
            no_pk_anywhere_queried += 1
    if len(linked_cases) == 1621 and (wrong_branch_only, no_pk_anywhere_queried) != (113, 13):
        raise ValueError("UNMATCHED_CASE_REASON_COUNTS_DRIFT")
    return {
        "candidate_pk_found_only_in_wrong_branch": wrong_branch_only,
        "candidate_pk_not_found_in_queried_pk_tables": no_pk_anywhere_queried,
        "wrong_branch_matches_are_not_ticket_object_links": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--raw-discovery", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    args = parser.parse_args()
    source_hash = verified_sha(args.source, args.source.with_name(args.source.name + ".proof.json"))
    graph_hash = verified_sha(args.graph, args.graph.with_name(args.graph.name + ".proof.json"))
    raw_hash = verified_sha(args.raw_discovery, args.raw_discovery.with_name(args.raw_discovery.name + ".proof.json"))
    original = json.loads(args.source.read_text(encoding="utf-8"))
    graph = json.loads(args.graph.read_text(encoding="utf-8"))
    raw = json.loads(args.raw_discovery.read_text(encoding="utf-8"))
    if (original.get("period") != "2026-06" or
            original.get("history_or_resolution_read") is not False or
            graph.get("period") != "2026-06" or
            raw.get("source_cases") != 1621 or
            raw.get("input_request_only") is not True or
            raw.get("known_history_not_read") is not True or
            graph.get("retrospective_only") is not True or
            graph.get("writes") != 0 or
            graph.get("official_application_business_fk_certified") is not False):
        raise ValueError("INVALID_SOURCE_ONLY_SCOPE")
    report = summarize(original["results"], graph["linked_cases"])
    report["unmatched_19_digit_search_breakdown"] = classify_unmatched_search_outcome(
        graph["linked_cases"], raw["business_key_matches"])
    report["source_receipt_sha256"] = source_hash
    report["graph_receipt_sha256"] = graph_hash
    report["raw_discovery_receipt_sha256"] = raw_hash
    report["receipt_sha256_integrity_checked"] = True
    report["hmac_independently_reverified_this_stage"] = False
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    print("JUNE1621_SOURCE_TRIAGE=PASS CASES=1621 NO_19_DIGIT=1162 "
          "UNMATCHED_19_DIGIT=126 LINKED=333 HISTORICAL_CAUSES_CERTIFIED=0")


if __name__ == "__main__":
    main()

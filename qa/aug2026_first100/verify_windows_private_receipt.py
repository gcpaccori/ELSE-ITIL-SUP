"""Independent receipt verification on ELSE62. Never prints private identifiers."""
from __future__ import annotations
import hashlib, hmac, json
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Temp\ELSE_ITIL_AUG_FIRST100_20261117")
SIGNER = Path(r"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private")
SCHEMA = "else.itil.qa.aug2026-first100-live-dual-pk.v1"
PRIVATE = ROOT / "aug_first100_qa_pk.private.json"
PROOF = Path(str(PRIVATE) + ".proof.json")


def read_and_verify(payload_path: Path, proof_path: Path, script_path: Path, signer_path: Path) -> dict:
    raw = payload_path.read_bytes()
    obj = json.loads(raw)
    proof = json.loads(proof_path.read_bytes())
    digest = hashlib.sha256(raw).hexdigest()
    source_digest = hashlib.sha256(script_path.read_bytes()).hexdigest()
    key = signer_path.read_bytes()
    if len(key) != 32:
        raise ValueError("SIGNER_KEY_SIZE")
    expected_hmac = hmac.new(key, f"{SCHEMA}:{source_digest}:{digest}".encode(), hashlib.sha256).hexdigest()
    if (obj["schema"] != SCHEMA or obj["source_sha256"] != source_digest
            or proof["schema"] != SCHEMA + "-hmac.v1"
            or proof["receipt_sha256"] != digest
            or proof["source_sha256"] != source_digest
            or not hmac.compare_digest(proof["hmac_sha256"], expected_hmac)
            or proof["read_only"] is not True
            or obj["business_writes"] != 0 or obj["history_not_read"] is not True):
        raise ValueError("AUG100_SIGNED_RECEIPT_NOT_AUTHENTIC")
    cases = obj["case_metadata"]
    matches = obj["matches"]
    if len(cases) != 100 or len({x["case_sha256"] for x in cases}) != 100:
        raise ValueError("AUG100_CASE_DUPLICATE_OR_MISSING")
    ids_by_rank = {x["rank"]: x for x in cases}
    valid_by_rank = {x["rank"]: set() for x in cases}
    wrong_branches = set()
    observed = Counter()
    for row in matches:
        rank = row["rank"]
        if row["case_sha256"] != ids_by_rank[rank]["case_sha256"]:
            raise ValueError("AUG100_CROSS_TICKET_PK")
        if hashlib.sha256(row["business_pk_private"].encode()).hexdigest() != row["pk_sha256"]:
            raise ValueError("AUG100_PK_SHA_MISMATCH")
        if row["same_branch"] != (row["business_branch"] == row["itil_branch"]):
            raise ValueError("AUG100_BRANCH_MISMATCH")
        if row["itil_branch"] != ids_by_rank[rank]["itil_branch"]:
            raise ValueError("AUG100_TICKET_BRANCH_MISMATCH")
        if row["same_branch"]:
            valid_by_rank[rank].add((row["kind"], row["pk_sha256"]))
            observed["same_branch"] += 1
        else:
            wrong_branches.add(rank)
            observed["other_branch"] += 1
    counts = Counter()
    for case in cases:
        rank = case["rank"]
        links = valid_by_rank[rank]
        if not links:
            if case["candidate_19_digit_count"] == 0:
                counts["without_19_digit"] += 1
            elif rank in wrong_branches:
                counts["wrong_branch_only"] += 1
            else:
                counts["candidate_no_queried_pk"] += 1
        elif len(links) == 1:
            counts["one_pk"] += 1
        else:
            counts["multiple_pk"] += 1
        if len({kind for kind, _ in links}) > 1:
            counts["both_kinds"] += 1
    report = obj["report"]
    expected = {
        "cases_no_19digit_candidate": counts["without_19_digit"],
        "cases_wrong_branch_only": counts["wrong_branch_only"],
        "cases_19digit_no_pk_anywhere_queried": counts["candidate_no_queried_pk"],
        "cases_one_valid_pk": counts["one_pk"],
        "cases_multiple_valid_pk": counts["multiple_pk"],
        "cases_with_both_kinds": counts["both_kinds"],
        "same_branch_observations": observed["same_branch"],
        "wrong_branch_observations": observed["other_branch"],
    }
    for key, value in expected.items():
        if report[key] != value:
            raise ValueError("AUG100_PUBLIC_AGGREGATE_MISMATCH_" + key)
    return {
        "status": "AUG100_HMAC_AND_COUNTS_INDEPENDENT_PASS",
        "cases": len(cases),
        "verified_pk_observations": len(matches),
        "linked_cases": sum(bool(x) for x in valid_by_rank.values()),
        "counts": expected,
        "business_writes": 0,
        "private_receipt_sha256": digest,
    }


if __name__ == "__main__":
    result = read_and_verify(
        PRIVATE, PROOF, ROOT / "AugFirst100PkRead.cs", SIGNER)
    print(json.dumps(result, sort_keys=True))

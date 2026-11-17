"""Independent HMAC/code/source/company/branch checks for all 1,819 private QA receipts.

Prints only aggregates; never discloses ticket IDs, PKs, original request
content, HMAC secret, original source identities, or historical gold.
"""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT=Path(r"C:\Temp\ELSE_ITIL_AUG_FULL1819_20261117")
sys.path.insert(0,str(ROOT))
from qa_august_full1819_identity_authority import from_fullmonth_windows_paths


def main():
    validator=from_fullmonth_windows_paths(
        receipt=ROOT/"aug_full1819_company_typed.private.json",
        proof=ROOT/"aug_full1819_company_typed.private.json.proof.json",
        source_reader=ROOT/"AugFullMonthTypedRead.cs",
        signer=Path(r"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private")
    )
    report=validator.summary
    decisions=validator.decisions
    counts=Counter(x["status"] for x in decisions.values())
    assert len(decisions)==1819
    assert dict(counts)==report["per_case_statuses"]
    assert sum(counts.values())==1819
    assert sum(x["typed_business_link_count"] for x in decisions.values())==11
    assert sum(x["typed_business_link_count"]>0 for x in decisions.values())==10
    assert report["source_cases"]==1819
    assert report["typed_company_route_supported_cases"]==1703
    assert report["typed_cases_with_any_pk"]==10
    assert report["causes_certified"]==0 and report["repairs_certified"]==0
    assert report["business_writes"]==0 and report["solution_read"] is False
    print(json.dumps({
        "status":"AUG_FULL1819_WINDOWS_INDEPENDENT_HMAC_AND_CASE_BINDING_PASS",
        "month":"2026-08",
        "cases":1819,
        "qa_company_routes_verified_for_cases":report["typed_company_route_supported_cases"],
        "business_pk_typed_read_batches":report["typed_company_provider_select_batches"],
        "typed_business_pk_observations":report["typed_pk_observations"],
        "cases_with_exact_typed_business_pk":report["typed_cases_with_any_pk"],
        "decisions":dict(sorted(counts.items())),
        "verified_receipt_sha256":validator.receipt_sha,
        "business_writes":0,
        "repairs_certified":0,
        "historical_gold_was_used_to_select_keys":False,
        "private_identifiers_disclosed":False,
    },sort_keys=True))

if __name__=="__main__":
    main()

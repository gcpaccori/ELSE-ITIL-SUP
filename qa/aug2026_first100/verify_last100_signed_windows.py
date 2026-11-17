"""Windows-only independent last100 HMAC, company and case-link verification.

This only prints public aggregate counts and the SHA256 of the private
receipt. No customer IDs, ITIL ticket IDs, raw PKs or original request text.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT=Path(r"C:\Temp\ELSE_ITIL_AUG_LAST100_20261117")
sys.path.insert(0,str(ROOT))
from qa_august_last100_identity_authority import from_last100_windows_paths

def main():
    authority=from_last100_windows_paths(
      receipt=ROOT/"aug_last100_company_typed.private.json",
      proof=ROOT/"aug_last100_company_typed.private.json.proof.json",
      source_reader=ROOT/"AugLast100TypedRead.cs",
      signer=Path(r"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private")
    )
    obj=json.loads((ROOT/"aug_last100_company_typed.private.json").read_text())
    summary=obj["report"]
    decisions=obj["case_decisions"]
    old_matches=obj["matches"]
    code_cases={x["rank"]:x for x in obj["case_metadata"]}
    assert len(code_cases)==len(decisions)==100
    assert all(x["history_not_read"] is True for x in code_cases.values())
    assert all(x["repair_certified"] is False for x in decisions)
    by_dec=Counter(x["status"] for x in decisions)
    assert by_dec==summary["per_case_statuses"]
    assert by_dec.get("SINGLE_EXACT_TYPED_PK_QA_OBSERVATION",0)==1
    assert summary["typed_cases_with_any_pk"]==1
    valid_legacy=set()
    legacy_db=Counter()
    company_verified_legacy=set()
    for old in old_matches:
        rank=old["rank"]
        assert old["case_sha256"]==code_cases[rank]["case_sha256"]
        if old["same_branch"]:
            valid_legacy.add(rank)
            legacy_db[old["source_database"]]+=1
            company=code_cases[rank]["itil_company"]
            official={"1":"dbComercial001_D","3":"dbComercial003_D"}.get(company)
            if official==old["source_database"]:
                company_verified_legacy.add(rank)
    assert len(valid_legacy)==summary["cases_one_valid_pk"]+summary["cases_multiple_valid_pk"]
    assert sum(legacy_db.values())==summary["same_branch_observations"]
    strictly_typed_by_kind=Counter(x["business_kind"] for x in obj["typed_matches"] if x["branch_matches"])
    assert sum(strictly_typed_by_kind.values())==summary["typed_company_branch_match_observations"]
    report={
      "status":"AUG_LAST100_WINDOWS_INDEPENDENT_HMAC_SCOPE_PASS",
      "evaluated_cases":100,
      "typed_pk_confirmed_cases":summary["typed_cases_with_any_pk"],
      "typed_pk_kinds":dict(sorted(strictly_typed_by_kind.items())),
      "legacy_same_branch_cases":len(valid_legacy),
      "legacy_same_branch_observations_by_database":dict(sorted(legacy_db.items())),
      "legacy_company_route_matching_cases":len(company_verified_legacy),
      "decisions":dict(sorted(by_dec.items())),
      "receipt_sha256":authority.receipt_sha,
      "raw_ticket_or_business_identifiers_exported":False,
      "business_writes":0,
      "historical_solution_read":False,
    }
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":
    main()

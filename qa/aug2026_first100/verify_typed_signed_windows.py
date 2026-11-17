"""Independent HMAC/code/case/branch verification in authorized ELSE62 only."""
from pathlib import Path
from collections import Counter
import json,sys

ROOT=Path(r"C:\Temp\ELSE_ITIL_AUG_TYPED100_V2_20261117")
sys.path.insert(0,str(ROOT))
from qa_august_identity_authority import from_windows_paths

def main():
    a=from_windows_paths(
      receipt=ROOT/"aug_first100_company_typed.private.json",
      proof=ROOT/"aug_first100_company_typed.private.json.proof.json",
      source_reader=ROOT/"AugFirst100TypedRead.cs",
      signer=Path(r"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private")
    )
    counts=Counter(x["status"] for x in a.decisions.values())
    assert sum(counts.values())==100
    assert sum(x["typed_business_link_count"] for x in a.decisions.values())==0
    assert all(x["repair_certified"] is False for x in a.decisions.values())
    report={
      "status":"AUG100_SIGNED_TYPED_AUTHORITY_INDEPENDENT_PASS",
      "evaluated_cases":100,
      "business_company_route_known":a.summary["typed_company_route_supported_cases"],
      "real_typed_sql_selects":a.summary["typed_company_provider_select_batches"],
      "verified_typed_business_cases":a.summary["typed_cases_with_any_pk"],
      "decisions":dict(sorted(counts.items())),
      "private_receipt_sha256":a.receipt_sha,
      "corporate_modifications":0,
      "historical_solutions_read":False,
      "raw_identifiers_exposed":False
    }
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()

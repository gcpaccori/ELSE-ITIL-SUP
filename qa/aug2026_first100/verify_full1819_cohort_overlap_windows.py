"""Independently compare the signed full-month source with earlier signed 100-case pilots.

Never exports private case IDs, customer PKs or HMAC key.
"""
from pathlib import Path
import hashlib,hmac,json

SIGNER=Path(r"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110\worker_hmac.private")
COHORTS={
    "FIRST100":(Path(r"C:\Temp\ELSE_ITIL_AUG_TYPED100_V2_20261117"),"AugFirst100TypedRead.cs","aug_first100_company_typed.private.json"),
    "LAST100":(Path(r"C:\Temp\ELSE_ITIL_AUG_LAST100_20261117"),"AugLast100TypedRead.cs","aug_last100_company_typed.private.json"),
    "FULL1819":(Path(r"C:\Temp\ELSE_ITIL_AUG_FULL1819_20261117"),"AugFullMonthTypedRead.cs","aug_full1819_company_typed.private.json"),
}
def read_verified(root:Path,reader:str,filename:str,key:bytes):
    source_hash=hashlib.sha256((root/reader).read_bytes()).hexdigest()
    payload=(root/filename).read_bytes()
    obj=json.loads(payload)
    proof=json.loads((root/(filename+".proof.json")).read_bytes())
    digest=hashlib.sha256(payload).hexdigest()
    schema=obj["schema"]
    expected=hmac.new(key,f"{schema}:{source_hash}:{digest}".encode(),"sha256").hexdigest()
    assert proof["source_sha256"]==source_hash==obj["source_sha256"]
    assert proof["schema"]==schema+"-hmac.v1"
    assert proof["receipt_sha256"]==digest
    assert hmac.compare_digest(proof["hmac_sha256"],expected)
    assert obj["business_writes"]==0 and obj["history_not_read"] is True
    return obj,digest

def links(obj):
    return {(
        x["case_sha256"],x["business_kind"],x["pk_sha256"],
        x["branch_matches"],x["qa_database"])
        for x in obj["typed_matches"]
    }

def main():
    key=SIGNER.read_bytes()
    assert len(key)==32
    loaded={k:read_verified(*v,key) for k,v in COHORTS.items()}
    whole=loaded["FULL1819"][0]
    assert len(whole["case_metadata"])==len(whole["case_decisions"])==1819
    overlap_count=0
    for name,start in (("FIRST100",0),("LAST100",1719)):
        pilot=loaded[name][0]
        for idx,(left,right) in enumerate(zip(pilot["case_metadata"],whole["case_metadata"][start:start+100])):
            assert left["case_sha256"]==right["case_sha256"],"COHORT_SOURCE_ORDER_DRIFT"
            assert left["module_code"]==right["module_code"],"MODULE_COHORT_DRIFT"
            assert left["itil_company"]==right["itil_company"],"COMPANY_COHORT_DRIFT"
            assert left["itil_branch"]==right["itil_branch"],"BRANCH_COHORT_DRIFT"
            assert left["request_sha256"]==right["request_sha256"],"SOURCE_TEXT_COHORT_DRIFT"
            decision=pilot["case_decisions"][idx]
            full_decision=whole["case_decisions"][start+idx]
            assert decision["status"]==full_decision["status"],"DECISION_COHORT_DRIFT"
            assert decision["typed_business_link_count"]==full_decision["typed_business_link_count"],"LINK_COUNT_DRIFT"
            overlap_count+=1
        whole_set=links(whole)
        selected_cases={x["case_sha256"] for x in pilot["case_metadata"]}
        assert links(pilot)=={x for x in whole_set if x[0] in selected_cases},"PK_COHORT_DRIFT"
    assert overlap_count==200
    print(json.dumps({
       "status":"AUG_FULL1819_FIRST_LAST100_OVERLAP_HMAC_INDEPENDENT_PASS",
       "case_overlaps_checked":overlap_count,
       "all_three_receipts_hmac_valid":True,
       "full_cases":1819,
       "first100_exact_typed_link_cases":loaded["FIRST100"][0]["report"]["typed_cases_with_any_pk"],
       "last100_exact_typed_link_cases":loaded["LAST100"][0]["report"]["typed_cases_with_any_pk"],
       "full1819_exact_typed_link_cases":whole["report"]["typed_cases_with_any_pk"],
       "full1819_receipt_sha256":loaded["FULL1819"][1],
       "business_writes":0,
       "historical_solution_access":False,
       "private_identifiers_exported":False
    },sort_keys=True))

if __name__=="__main__":
    main()

"""Independent native O5/O13/O15 reinspection of the 16 real Feb SAP/OT receipts.

No SQL query, no token, no historical solution, no model run. Each original
Windows receipt is byte-for-byte pinned and bound to one owner-allowed case
and one uniquely reported OT, with no assertion of an official ITIL↔OT join.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,zipfile

from else_core.hand_kernel import Outcome
from else_core.itil_feb100_sap_ot_o5_hand import (
    AuthorizedSapOtReceipt,build_sap_ot_router)

QA=Path("/home/u23u/else_itil_feb100_qa_20261110")
REPO=Path("/home/u23u/else_itil_beta_vslice_20261110")
OUT=Path("/home/u23u/else_itil_beta_vslice_qa_20261110")
SRC=REPO/"qa/Feb100SapOtRead.cs"
PACK=QA/"feb100_ot_sap_receipts.private.zip"
ALLOWED=QA/"feb100_allowlist.private.jsonl"
AUDIT=OUT/"sap_ot_o5_real16_audit.json"
OUTPUTS=OUT/"sap_ot_o5_real16_per_case.private.jsonl"
RECEIPTS=OUT/"sap_ot_original_receipts.private"


def main():
    if AUDIT.exists() or OUTPUTS.exists():raise FileExistsError("NO_OVERWRITE_AUDIT")
    roster={x["case_sha256"]:x for line in ALLOWED.read_text().splitlines()
            if line.strip() for x in [json.loads(line)]}
    if len(roster)!=100:raise ValueError("OWNER_SELECTION_DRIFT")
    source=SRC.read_bytes()
    if sha256(source).hexdigest()!=(
            "81c8da152f428c0d1c6273aa24d6ca4b01cbe4a2fedd17fcb1cefce41fc37be1"):
        raise ValueError("ORIGINAL_CSHARP_BYTES_NOT_PINNED")
    if not RECEIPTS.is_dir():RECEIPTS.mkdir(mode=0o700)
    items=[]
    with zipfile.ZipFile(PACK) as z:
        names=sorted(z.namelist())
        if len(names)!=16 or len(set(names))!=16:
            raise ValueError("OT_ARCHIVE_NOT_16")
        for name in names:
            sha=name[:64]
            if (name!=sha+".private.json" or sha not in roster):
                raise ValueError("ARCHIVE_CASE_PATH_NOT_OWNER_BOUND")
            raw=z.read(name)
            dest=RECEIPTS/name
            if dest.exists() and dest.read_bytes()!=raw:
                raise ValueError("ORIGINAL_RECEIPT_CHANGED")
            if not dest.exists():
                with dest.open("xb") as f:f.write(raw)
                dest.chmod(0o600)
            owner=AuthorizedSapOtReceipt(
                dest,sha256(raw).hexdigest(),sha,sha256(source).hexdigest(),
                len(source),roster[sha]["description_redacted"])
            capability,router,operation=build_sap_ot_router(owner)
            result=router.route(operation)
            if not (result.outcome==Outcome.PASS and
                    result.guardian_result.executions==1 and
                    result.guardian_result.verification.passed is True and
                    result.guardian_result.verification.independent is True and
                    result.dominance_receipt.get("capability_id")==capability.capability_id):
                raise ValueError("NATIVE_SAP_OT_O5_GUARDIAN_DOMINANCE_FAIL")
            payload=result.guardian_result.value.outputs
            if not (
                    payload["business_entity_join_certified"] is False and
                    payload["repair_certified"] is False and
                    payload["reported_ot_sha256"]==owner.reported_ot_sha256 and
                    payload["source"]=="ELSE70/dbDistribucion_D"):
                raise ValueError("FALSE_OT_BUSINESS_JOIN_CLAIM")
            items.append({
                "case_sha256":sha,
                "receipt_sha256":sha256(raw).hexdigest(),
                "source_sha256":sha256(source).hexdigest(),
                "operation_id":result.operation_id,
                "guardian_verified":True,"dominance_pass":True,
                "found_in_qa_table":payload["order_found"],
                "response_rows_up_to5":payload["response_rows_up_to5"],
                "business_entity_link_not_certified":True,
                "functional_repair":False,
            })
    if len(items)!=16 or len({x["case_sha256"] for x in items})!=16:
        raise ValueError("FINALIZED_SAP_OT_NOT_UNIQUE")
    blob=("\n".join(json.dumps(x,sort_keys=True) for x in items)+"\n").encode()
    with OUTPUTS.open("xb") as f:f.write(blob)
    summary={
        "schema":"else.itil.v1beta.sap-ot-native-o5-real16.v1",
        "original_qa_receipts":16,"native_o5_pass":16,
        "guardian_independent_pass":16,"dominance_pass":16,
        "orders_found_in_specific_qa_table":sum(x["found_in_qa_table"] for x in items),
        "orders_not_found_in_specific_qa_table":sum(
            not x["found_in_qa_table"] for x in items),
        "historical_solution_exposure":False,"new_sql_queries":0,
        "human_approvals":0,"functional_repairs":0,
        "official_itil_business_joins_certified":0,
        "source_sha256":sha256(source).hexdigest(),
        "per_case_audit_sha256":sha256(blob).hexdigest(),
    }
    with AUDIT.open("x") as f:json.dump(summary,f,indent=2,sort_keys=True)
    print(json.dumps(summary,sort_keys=True))

if __name__=="__main__":main()

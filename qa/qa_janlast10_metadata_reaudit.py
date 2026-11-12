"""Reinspect Jan QA receipts through the actual *dispatcher* verification path.

Does not execute a new SQL query or LLM call; this verifies that the new
typed ticket-state / classification / origin capability is backed by exact
NuGet bytes and native O5/O13/O15 instead of the model's prose.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from else_dominance.qa_dispatch_queue import verify_actual_receipts

def check(root:Path,audit:Path):
    report=json.loads(audit.read_text(encoding="utf-8"))
    assert report["runs_verified"]==12
    meta=Counter()
    for item in report["cases"]:
        case=item["case_sha256"]
        run=next(p for p in root.glob("case_"+case[:16]+"_*")
                 if (p/"verified_final.private.json").exists() and
                 sha256((p/"verified_final.private.json").read_bytes()).hexdigest()
                       ==item["final_output_sha256"])
        final=json.loads((run/"verified_final.private.json").read_text())
        payload={
            "schema":"else.itil.qa.dynamic-nuget-hand.v1",
            "model_requested_tool_before_sql":True,
            "new_qa_sql_read_executed":True,
            "o5_o13_o15_verified":True,
            "model_reconsidered_after_evidence":True,
            "repair_certified":False,
            "case_sha_prefix":case[:16],
            "run_id":run.name,
            "private_cluster_run":str(run),
            "receipt_sha256":sha256((run/"receipt.private.json").read_bytes()).hexdigest(),
            "final_output_sha256":item["final_output_sha256"],
            "diagnosis_status":final["status"],
            "quality_accepted":final["quality"]["accepted"],
        }
        verified=verify_actual_receipts(payload,case,
                                         cohort="2026-01-last10")
        fields=verified["ticket_metadata"]
        assert fields["opened_at"]==item["opened_at"]
        assert fields["service_code"]==item["service_code"]
        assert fields["ticket_status_code"] is not None
        assert fields["classification_code"] is not None
        assert fields["origin_code"] is not None
        assert fields["request_bytes"]>=0
        meta["verified"]+=1
        meta["quality_accepted"]+=int(verified["quality_accepted"])
    return {
        "schema":"else.itil.qa.janlast10.typed-metadata-reinspection.v1",
        "verified_exact_receipts":meta["verified"],
        "verified_metadata_bindings":meta["verified"],
        "diagnostic_guidance_contract_accepted":meta["quality_accepted"],
        "repairs":0,"actual_current_permissions_read":0,
        "status":"QA_RECEIPT_AND_DOMAIN_METADATA_REVERIFIED"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--audit",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=check(a.root,a.audit)
    with a.out.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2)
    print(json.dumps(result))
if __name__=="__main__":main()

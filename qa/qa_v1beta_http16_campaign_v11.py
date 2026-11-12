"""Drive all 16 REAL February OT/SAP eligible cases through QA HTTP Beta.

No direct DB access, no historical solutions, no human signoff. Authenticate
against loopback-only service; ledger stores plan privately, this journal
stores status/receipt digests but never ticket text.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import urllib.request,urllib.error,json

QA=Path("/home/u23u/else_itil_beta_vslice_qa_20261110")
TOKEN=Path("/home/u23u/else_itil_sup_run/support_live_private/service.token")
URL="http://127.0.0.1:18886"
JOURNAL=QA/"beta_http16_e2e_v11.private.jsonl"

def call(path,sha,token):
    request=urllib.request.Request(
        URL+path,
        data=json.dumps({"case_sha256":sha}).encode(),
        headers={"Authorization":"Bearer "+token,
                 "Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(request,timeout=180) as resp:
        return json.loads(resp.read())

def main():
    if JOURNAL.exists():raise FileExistsError("QA_BATCH_NO_OVERWRITE")
    from else_dominance.beta_vertical_slice import BetaEvidenceBundle
    bundle=BetaEvidenceBundle(
      base=Path("/home/u23u/else_itil_beta_vslice_20261110"),
      qa=Path("/home/u23u/else_itil_feb100_qa_20261110"),
      core_source=QA)
    token=TOKEN.read_text().strip()
    shas=sorted(bundle.sap_recs)
    if len(shas)!=16:raise ValueError("ORIGINAL_OT_POPULATION_DRIFT")
    with JOURNAL.open("x") as out:
        for i,sha in enumerate(shas,1):
            try:
                result=call("/v1/beta/investigate",sha,token)
                if (result["case_sha256"]!=sha or
                    result["native_itil_verified"] is not True or
                    result["native_sap_ot_verified"] is not True or
                    result["business_join_certified"] is not False or
                    result["repair_certified"] is not False or
                    result["human_review_required"] is not True):
                    raise ValueError("NOT_DUAL_NATIVE_VERIFIED_OUTPUT")
                row={
                    "case_sha256":sha,
                    "status":"E2E_VERIFIED",
                    "plan_status":result["status"],
                    "contract_accepted":result["quality"]["accepted"],
                    "model_attempts":result["model_attempts"],
                    "order_found":result["reported_order_found_in_qa"],
                    "itil_receipt":result["source_receipts"]["itil"],
                    "sap_receipt":result["source_receipts"]["sap_ot"],
                    "root_cause_certified":False,"repairs_certified":False,
                }
            except Exception as exc:
                row={
                    "case_sha256":sha,"status":"E2E_FAILED",
                    "error_type":type(exc).__name__,
                    "root_cause_certified":False,"repairs_certified":False}
            out.write(json.dumps(row,sort_keys=True)+"\n")
            out.flush()
            print(json.dumps({"case_number":i,"total":16,
                "state":row["status"],"plan":row.get("plan_status")}),
                flush=True)
    data=[json.loads(x) for x in JOURNAL.read_text().splitlines()]
    report={
        "schema":"else.itil.v1beta.real-http16-e2e.v1",
        "cases":len(data),"verified":sum(x["status"]=="E2E_VERIFIED" for x in data),
        "failed":sum(x["status"]!="E2E_VERIFIED" for x in data),
        "accepted":sum(x.get("contract_accepted") is True for x in data),
        "triage":sum(x.get("contract_accepted") is False for x in data),
        "orders_found":sum(x.get("order_found") is True for x in data),
        "new_sql_executions":0,"historical_solution_shown":False,
        "repairs":0,"reviewer_signoffs":0,
        "journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest(),
    }
    (QA/"beta_http16_e2e_v11_summary.json").write_text(
        json.dumps(report,indent=2,sort_keys=True))
    print(json.dumps(report),flush=True)

if __name__=="__main__":main()

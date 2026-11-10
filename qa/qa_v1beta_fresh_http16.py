"""Independent QA HTTP campaign: all 16 NEW Windows SAP/OT receipts.

Compares to immutable native HMAC/O5-verified per-case inputs and never reads
historical solutions or silently promotes accepted plans as resolved cases.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from collections import Counter
import json,urllib.request,urllib.error

from else_dominance.beta_fresh_api import FreshBetaEvidenceBundle

ROOT=Path("/home/u23u/else_itil_beta_fresh_qa_20261110")
SOURCE=Path("/home/u23u/else_itil_beta_fresh_20261110")
QA=Path("/home/u23u/else_itil_feb100_qa_20261110")
TOKEN=Path("/home/u23u/else_itil_sup_run/support_live_private/service.token")
URL="http://127.0.0.1:18887"
JOURNAL=ROOT/"fresh_http16_campaign.private.jsonl"
OUT=ROOT/"fresh_http16_campaign_audit.json"

def call(sha,token):
    request=urllib.request.Request(
        URL+"/v1/beta/investigate",
        data=json.dumps({"case_sha256":sha}).encode(),
        headers={"Authorization":"Bearer "+token,
                 "Content-Type":"application/json"},
        method="POST")
    with urllib.request.urlopen(request,timeout=175) as response:
        return json.loads(response.read())

def main():
    if JOURNAL.exists() or OUT.exists():
        raise FileExistsError("FRESH_CAMPAIGN_OVERWRITE_FORBIDDEN")
    bundle=FreshBetaEvidenceBundle(base=SOURCE,qa=QA,core_source=ROOT)
    if len(bundle.sap_recs)!=16:
        raise ValueError("EXPECTED_16_FRESH_RECEIPTS")
    token=TOKEN.read_text().strip()
    with JOURNAL.open("x") as f:
        for idx,sha in enumerate(sorted(bundle.sap_recs),1):
            try:
                evidence=bundle.verify(sha)
                result=call(sha,token)
                if not (
                    result["case_sha256"]==sha and
                    result["native_itil_verified"] is True and
                    result["native_sap_ot_verified"] is True and
                    result["source_receipts"]=={
                        "itil":evidence["itil_receipt_sha256"],
                        "sap_ot":evidence["sap_receipt_sha256"]} and
                    result["repair_certified"] is False and
                    result["root_cause_certified"] is False and
                    result["business_join_certified"] is False and
                    result["human_review_required"] is True):
                    raise ValueError("FRESH_DUAL_HAND_EVIDENCE_DRIFT")
                if result["quality"]["accepted"]:
                    if (
                      result["proposal"]["vinculacion_comercial_verificada"]
                         is not False or
                      result["proposal"]["rol_oficial_validado"]
                         is not False or
                      any(x["responsable"].strip().casefold() !=
                          "responsable autorizado por confirmar"
                          for x in result["proposal"]["pasos"])):
                        raise ValueError("BETA_ROLE_NOT_ABSTAINING")
                row={
                    "case_sha256":sha,
                    "state":"FRESH_HTTP_E2E_VERIFIED",
                    "native_hmac_o5_o13_o15":True,
                    "contract_accepted":result["quality"]["accepted"],
                    "investigation_status":result["status"],
                    "new_sap_receipt_sha256":
                       result["source_receipts"]["sap_ot"],
                    "read_time":evidence["sap_observation"].get("read_utc",""),
                    "order_found_in_qa":result["reported_order_found_in_qa"],
                    "model_attempts":result["model_attempts"],
                    "repair_certified":False,
                    "human_approved":False,
                }
            except Exception as ex:
                row={
                   "case_sha256":sha,"state":"FRESH_E2E_FAILED",
                   "error_type":type(ex).__name__,
                   "error_code":str(ex)[:90] if isinstance(ex,ValueError)
                                  else "FRESH_RUNTIME_ERROR",
                }
            f.write(json.dumps(row,sort_keys=True)+"\n")
            f.flush()
            print(json.dumps({
                "index":idx,"total":16,
                "state":row["state"],
                "contract_accepted":row.get("contract_accepted")}),flush=True)
    all_rows=[json.loads(x) for x in JOURNAL.read_text().splitlines()]
    audit={
        "schema":"else.itil.beta.fresh-http16-campaign-audit.v1",
        "cases":len(all_rows),
        "new_qa_sql_reads":16,
        "fresh_hmac_o5_o13_o15_e2e":sum(
            x["state"]=="FRESH_HTTP_E2E_VERIFIED" for x in all_rows),
        "e2e_errors":sum(x["state"]!="FRESH_HTTP_E2E_VERIFIED"
                        for x in all_rows),
        "contract_accepted":sum(x.get("contract_accepted") is True
                                for x in all_rows),
        "contract_human_triage":sum(x.get("contract_accepted") is False
                                    for x in all_rows),
        "orders_found_in_qa":sum(x.get("order_found_in_qa") is True
                                  for x in all_rows),
        "human_reviewer_events":0,
        "repairs_certified":0,
        "official_itil_ot_business_joins":0,
        "role_matrix_verified":False,
        "historical_solutions_exposed":False,
        "journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest(),
    }
    with OUT.open("x") as f:json.dump(audit,f,indent=2,sort_keys=True)
    print(json.dumps(audit,sort_keys=True),flush=True)

if __name__=="__main__":
    main()

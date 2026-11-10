"""Independent 16-case audit: fresh Windows SQL + HMAC + native dual O5 + ledger.

Keeps all customer evidence and source receipts on the private QA host;
writes summary counts and per-case SHA-linked metadata only.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from collections import Counter
import json,zipfile
from else_dominance.beta_fresh_api import FreshBetaEvidenceBundle
from else_dominance.beta_supervision import BetaSupervisionLedger

BASE=Path("/home/u23u/else_itil_beta_fresh_20261110")
FRESH=Path("/home/u23u/else_itil_beta_fresh_qa_20261110")
QA=Path("/home/u23u/else_itil_feb100_qa_20261110")
LEDGER=FRESH/"beta_supervision_fresh.sqlite"
JOURNAL=FRESH/"fresh_http16_campaign.private.jsonl"
OUT=FRESH/"fresh_independent_e2e16_audit.json"
PER=FRESH/"fresh_independent_e2e16_per_case.private.jsonl"

def need(x,code):
    if not x:raise ValueError(code)

def main():
    need(not OUT.exists() and not PER.exists(),"AUDIT_NO_OVERWRITE")
    bundle=FreshBetaEvidenceBundle(
        base=BASE,qa=QA,core_source=FRESH)
    need(len(bundle.sap_recs)==16,"FRESH_EXACT_COHORT_NOT_16")
    old={}
    with zipfile.ZipFile(QA/"feb100_ot_sap_receipts.private.zip") as pack:
        for name in pack.namelist():
            val=json.loads(pack.read(name))
            sha=name[:64]
            need(val["case_sha256"]==sha,"OLDER_RECEIPT_CASE_DRIFT")
            old[sha]=val
    need(set(old)==set(bundle.sap_recs),"FRESH_COHORT_SELECTION_DRIFT")
    journal=[json.loads(x) for x in JOURNAL.read_text().splitlines() if x.strip()]
    need(len(journal)==16 and
         {x["case_sha256"] for x in journal}==set(old),
         "FRESH_JOURNAL_DRIFT")
    by_sha={x["case_sha256"]:x for x in journal}
    need(len(by_sha)==16,"DUPLICATE_JOURNAL_CASE")
    report=[]
    with BetaSupervisionLedger(LEDGER) as ledger:
        for sha in sorted(old):
            observed=bundle.verify(sha)
            job=next(j for p in (FRESH/"requests").glob("*.private.json")
                     for j in [json.loads(p.read_bytes())]
                     if j["case_sha256"]==sha)
            proof=json.loads((FRESH/"verified"/job["job_id"]/
                              "verified_receipt.private.json").read_bytes())
            stored=ledger.get(sha)
            row=by_sha[sha]
            need(observed["status"]=="DUAL_NATIVE_EVIDENCE_VERIFIED" and
                 observed["itil_o5_verified"] and
                 observed["sap_o5_verified"] and
                 observed["fresh_evidence_attestation"]==
                 "WINDOWS_HMAC_PLUS_NATIVE_O5" and
                 observed["official_business_join_certified"] is False,
                 "FRESH_DUAL_O5_NOT_VERIFIED")
            need(proof["o5_o13_o15_verified"] is True and
                 proof["hmac_attested"] is True and
                 proof["sap_receipt_sha256"]==
                 observed["sap_receipt_sha256"] and
                 proof["job_sha256"]==
                 sha256((FRESH/"requests"/(
                     job["job_id"]+".private.json")).read_bytes()).hexdigest(),
                 "HMAC_PROOF_NOT_LINKED_TO_OWNER_JOB")
            need(stored is not None and
                 stored["case_sha256"]==sha and
                 stored["source_receipts"]=={
                    "itil":observed["itil_receipt_sha256"],
                    "sap_ot":observed["sap_receipt_sha256"]} and
                 stored["native_itil_verified"] is True and
                 stored["native_sap_ot_verified"] is True and
                 stored["repair_certified"] is False and
                 stored["root_cause_certified"] is False and
                 stored["business_join_certified"] is False and
                 stored["human_review_required"] is True,
                 "PUBLISHED_LEDGER_NOT_EVIDENCE_BOUND")
            need(row["state"]=="FRESH_HTTP_E2E_VERIFIED" and
                 row["contract_accepted"]==stored["quality"]["accepted"] and
                 row["new_sap_receipt_sha256"]==
                 observed["sap_receipt_sha256"],
                 "HTTP_CAMPAIGN_CONTRADICTS_LEDGER")
            need(ledger.status(sha)["reviews_count"]==0,
                 "UNAUTHORIZED_TECHNICIAN_APPROVAL")
            # Native O5 outputs deliberately omit raw SQL timing/fields.
            # Reinspect the exact receipt bytes after the native gate PASSES.
            new=json.loads((FRESH/"verified"/job["job_id"]/
                            "receipt.private.json").read_bytes())["observation"]
            previous=old[sha]["observation"]
            report.append({
                "case_sha256":sha,
                "old_sap_receipt_sha256":
                    sha256(json.dumps(old[sha],sort_keys=True,
                            separators=(",",":"),ensure_ascii=False).encode()).hexdigest(),
                "new_sap_receipt_sha256":observed["sap_receipt_sha256"],
                "hmac_o5_o13_o15_verified":True,
                "new_read_observed_utc":new["read_utc"],
                "source_read_reexecuted":True,
                "old_order_found":previous["order_found"],
                "new_order_found":new["order_found"],
                "old_response_rows":previous["response_rows_up_to5"],
                "new_response_rows":new["response_rows_up_to5"],
                "order_found_state_changed":
                    previous["order_found"]!=new["order_found"],
                "sap_state_code_changed":
                    previous["codigo_estado_envio_sap"]!=
                    new["codigo_estado_envio_sap"],
                "contract_accepted":stored["quality"]["accepted"],
                "authorized_business_join":False,
                "technician_reviewed":False,
                "repair_certified":False,
            })
        aggregate=ledger.aggregate()
    need(len(report)==16 and
         aggregate["investigations"]==16 and
         aggregate["recorded_human_review_events"]==0,
         "SUPERVISED_LEDGER_NOT_16_ZERO_REVIEWS")
    raw=("\n".join(json.dumps(x,sort_keys=True)
         for x in report)+"\n").encode()
    with PER.open("xb") as f:f.write(raw)
    audit={
        "schema":"else.itil.beta.fresh-ot-16-independent-audit.v1",
        "cohort_eligible":16,
        "fresh_windows_sql_reads_with_signed_receipts":16,
        "fresh_receipts_hmac_native_o5_o13_o15_verified":16,
        "dual_source_http_e2e_verified":16,
        "contract_accepted":sum(x["contract_accepted"] for x in report),
        "contract_rejected":sum(not x["contract_accepted"] for x in report),
        "orders_found_in_qa":sum(x["new_order_found"] for x in report),
        "order_presence_changed_vs_archive":
            sum(x["order_found_state_changed"] for x in report),
        "sap_state_code_changed_vs_archive":
            sum(x["sap_state_code_changed"] for x in report),
        "response_count_changed_vs_archive":
            sum(x["old_response_rows"]!=x["new_response_rows"] for x in report),
        "real_technician_review_events":0,
        "certified_itil_sap_entity_links":0,
        "certified_role_assignments":0,
        "certified_repairs":0,
        "historical_gold_solutions_exposed_to_qwen":False,
        "per_case_sha256":sha256(raw).hexdigest(),
        "campaign_sha256":sha256(JOURNAL.read_bytes()).hexdigest(),
    }
    with OUT.open("x") as f:json.dump(audit,f,indent=2,sort_keys=True)
    print(json.dumps(audit,sort_keys=True))

if __name__=="__main__":main()

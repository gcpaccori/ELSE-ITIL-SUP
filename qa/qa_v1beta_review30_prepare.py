"""Generate a PRIVATE 30-case technician pilot queue without false approvals.

16 have NEW HMAC+native O5 SAP/OT reads; 14 other ITIL cases are
marked as source-acquisition pending, not evaluated as business-diagnosis
successes. Historical solutions are never copied into the packet.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

ROOT=Path("/home/u23u/else_itil_beta_fresh_qa_20261110")
QA=Path("/home/u23u/else_itil_feb100_qa_20261110")
PEER=Path("/home/u23u/else_itil_feb100_grounding_qa_20261110/v21/feb100_grounded_v21_peer4b.private.jsonl")
OUT=ROOT/"human_review30_queue.private.jsonl"
SUMMARY=ROOT/"human_review30_queue_manifest.json"

def main():
    if OUT.exists() or SUMMARY.exists():
        raise FileExistsError("REVIEW_QUEUE_NO_OVERWRITE")
    allow={x["case_sha256"]:x for line in (
         QA/"feb100_allowlist.private.jsonl").read_text().splitlines()
         if line.strip() for x in [json.loads(line)]}
    peer={x["case_sha256"]:x for line in PEER.read_text().splitlines()
          if line.strip() for x in [json.loads(line)]}
    if len(allow)!=len(peer)!=100:
        raise ValueError("REVIEW_SOURCE_COHORT_INVALID")
    recent={}
    for file in (ROOT/"verified").glob(
        "*/verified_receipt.private.json"):
        body=json.loads(file.read_bytes())
        sha=body["case_sha256"]
        if sha in recent:raise ValueError("DUPLICATE_FRESH_CASE_REQUIRES_ADJUDICATION")
        recent[sha]=body
    if len(recent)!=16 or not set(recent)<=set(allow):
        raise ValueError("EXACT_NEW_SAP_SOURCE_COUNT_DRIFT")
    old=[]
    for sha,item in peer.items():
        if sha in recent:continue
        precedence={"CONFLICT":0,"NOT_DETERMINABLE":1,
                    "SUPPORTED":2}.get(item.get("relation"),3)
        old.append((precedence,sha))
    old.sort()
    chosen=[sha for _,sha in old[:14]]
    if len(chosen)!=14 or len(set(chosen)|set(recent))!=30:
        raise ValueError("REVIEW30_SELECTION_FAIL")
    rows=[]
    for sha in sorted(recent)+chosen:
        has_sap=sha in recent
        peer_label=peer[sha].get("relation","NOT_REVIEWED")
        rows.append({
            "schema":"else.itil.beta.qa.human-review-candidate.v1",
            "case_sha256":sha,
            "historical_month":"2026-02",
            "cohort_origin":"FEB100_OWNER_SELECTED",
            "category":"DUAL_FRESH_OT_QA" if has_sap
                else "ITIL_ONLY_MISSING_ADDITIONAL_SOURCE",
            "fresh_sap_o5_attested":has_sap,
            "itil_o5_source_available":True,
            "sap_receipt_sha256":
                recent[sha]["sap_receipt_sha256"] if has_sap else None,
            "historical_peer_opinion_not_ground_truth":peer_label,
            "review_questions":[
                "¿Las hipótesis se sustentan solo en evidencia observada?",
                "¿Qué prueba discriminante o acceso real falta?",
                "¿El rol o grupo responsable está aprobado formalmente?",
                "¿Existe vinculación empresarial demostrada entre ticket y OT?",
                "¿Qué comprobación funcional permitiría cerrar el incidente?",
            ],
            "required_human_action":"REVIEW_AND_REQUEST_EVIDENCE"
                     if has_sap else "OBTAIN_MISSING_DOMAIN_EVIDENCE",
            "approved_reviewer":None,
            "review_decision":None,
            "official_business_join_certified":False,
            "role_authorization_certified":False,
            "repair_certified":False,
            "causal_truth_confirmed":False,
        })
    raw=("\n".join(json.dumps(x,sort_keys=True,ensure_ascii=False)
                   for x in rows)+"\n").encode()
    with OUT.open("xb") as f:f.write(raw)
    OUT.chmod(0o600)
    report={
        "schema":"else.itil.beta.qa.review30-preparation.v1",
        "candidates":len(rows),
        "fresh_dual_hand_candidates":len(recent),
        "missing_other_domain_evidence":len(chosen),
        "human_reviews_completed":0,
        "official_role_assignments":0,
        "official_business_joins":0,
        "certified_repairs":0,
        "historical_gold_solution_exposed":False,
        "private_queue_sha256":sha256(raw).hexdigest(),
    }
    with SUMMARY.open("x") as f:json.dump(report,f,indent=2,sort_keys=True)
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":main()

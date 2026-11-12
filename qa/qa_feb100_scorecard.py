"""Finalize February 100-case E2E QA scorecard from sealed evidence.

Never conflates receipt correctness, model-format acceptance, Qwen4B peer
judgment, historical technician notes or certified functional resolution.
Avoids copying ticket text and solution text into the report.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

def load_lines(p:Path):
    return [json.loads(v) for v in p.read_text(encoding="utf-8").splitlines()
            if v.strip()]

def require(ok,code):
    if not ok:raise ValueError(code)

def unique(rows,name,expected=100):
    require(len(rows)==expected,name+"_COUNT")
    d={x["case_sha256"]:x for x in rows}
    require(len(d)==expected,name+"_UNIQUE")
    return d

def build(root:Path,allowlist:Path,report_path:Path):
    require(not report_path.exists(),"REFUSE_OVERWRITE")
    from qa.qa_feb100_windows import read_allowlist
    a=read_allowlist(allowlist)
    require(len(a)==100,"ALLOWLIST_NOT_100")
    audit=json.loads((root/"independent_audit_100.json").read_text())
    require(audit["schema"]=="else.itil.qa.feb100-independent-audit.v1" and
            audit["runs_verified"]==100 and
            audit["negative_sha_tamper_tests_rejected"]==100 and
            audit["fresh_nuget_receipts_o5_o13_o15_verified"]==100,
            "NATIVE_100_AUDIT_NOT_PASS")
    native=unique(audit["cases"],"NATIVE")
    require(set(native)==set(a),"NATIVE_COHORT_DRIFT")
    peer=unique(load_lines(root/"feb100_peer4b_historical_review.private.jsonl"),
                "PEER")
    holdout=unique(load_lines(root/"feb100_historical_holdout.private.jsonl"),
                   "HISTORY")
    require(set(peer)==set(a)==set(holdout),"PEER_OR_HOLDOUT_COHORT_DRIFT")
    augmented=load_lines(root/"ot_augmented_model_review.private.jsonl")
    ot_by_sha={r["case_sha256"]:r for r in augmented}
    require(len(augmented)==len(ot_by_sha)==16,"OT_AUGMENTED_NOT_16")
    require(set(ot_by_sha)<=set(a),"OT_CASE_OUTSIDE_COHORT")
    ot_audit=json.loads((root/"feb100_ot_independent_audit.private.json").read_text())
    require(ot_audit["verified_cases"]==16 and
            ot_audit["business_entity_links_certified"]==0,"OT_AUDIT_NOT_VALID")
    require({x["case_sha256"] for x in ot_audit["case_audit"]}==set(ot_by_sha),
            "OT_AUDIT_COHORT_DRIFT")
    flags=Counter()
    statuses=Counter()
    historical_quality=Counter()
    peer_relation=Counter()
    day_counts=Counter()
    service_counts=Counter()
    rows=[]
    final_runs={}
    for path in (root/"runs").glob("case_*/verified_final.private.json"):
        body=json.loads(path.read_bytes())
        case=body["case_sha256"]
        require(case not in final_runs,"DUPLICATE_FINAL")
        final_runs[case]=(body,path)
    require(set(final_runs)==set(a),"FINALIZED_COHORT_NOT_100")
    for sha,row in sorted(a.items()):
        verified=native[sha]
        final,artifact=final_runs[sha]
        q=final["quality"]
        accepted=q["accepted"] is True
        require(verified["quality_accepted"]==accepted,
                "NATIVE_QUALITY_DRIFT")
        require(final["o5_o13_o15_verified"] is True and
                final["repair_certified"] is False and
                final["root_cause_certified"] is False and
                final["approved_for_training"] is False,
                "FALSE_CERTIFICATION")
        require(final["source_receipt_sha256"]==sha256(
                (artifact.parent/"receipt.private.json").read_bytes()).hexdigest(),
                "RECEIPT_SHA_NOT_BOUND")
        require(peer[sha]["state"]==(
                "PEER_COMPLETED" if accepted
                else "NOT_COMPARABLE_REJECTED_PLAN"),
                "PEER_REVIEW_POLICY_DRIFT")
        for flag in q["schema_flags"]+q["safety_flags"]+q["review_flags"]:
            flags[flag]+=1
        day_counts[row["opened_at"][:10]]+=1
        service_counts[row["service_code"]]+=1
        statuses["accepted"]+=int(accepted)
        statuses["triage"]+=int(not accepted)
        if accepted:
            peer_relation[peer[sha]["relation"]]+=1
            historical_quality[peer[sha]["history_quality"]]+=1
            statuses["missing_verifiable_test"]+=int(
                peer[sha]["missing_verifiable_test"] is True)
        else:
            require(final.get("proposal",{})=={},"REJECTED_PLAN_NOT_QUARANTINED")
        require(holdout[sha]["historical_solution_present"] is True,
                "HISTORICAL_HOLDOUT_STATUS_DRIFT")
        ot=ot_by_sha.get(sha)
        rows.append({"sha":sha,
            "opened_at":row["opened_at"],
            "service_code":row["service_code"],
            "native_receipt_verified":True,
            "native_tamper_rejected":True,
            "model_quality_accepted":accepted,
            "review_flags":q["review_flags"],
            "safety_flags":q["safety_flags"],
            "schema_flags":q["schema_flags"],
            "peer_relation_not_ground_truth":(
                peer[sha]["relation"] if accepted else None),
            "peer_history_quality":(
                peer[sha]["history_quality"] if accepted else None),
            "ot_read_performed":ot is not None,
            "ot_new_quality_accepted":(
                ot["quality_accepted"] if ot else None),
            "repair_certified":False})
    require(len(day_counts)==24,"FEB_ACTIVITY_DAYS_DRIFT")
    transitions=Counter()
    for x in augmented:
        require(x["state"]=="COMPLETED" and x["sap_read_verified"] is True,
                "OT_AUGMENTED_RESULT_INCOMPLETE")
        transitions[str(int(x["before_quality_accepted"]))+"→"+
                    str(int(x["quality_accepted"]))]+=1
    summary={
      "schema":"else.itil.feb2026.100-e2e-independent-scorecard.v1",
      "population_february":1799,
      "selected_cases":100,
      "active_days_covered":len(day_counts),
      "native_o5_receipts_verified":100,
      "native_o5_tampered_receipts_rejected":100,
      "quality_contract_accepted":statuses["accepted"],
      "human_triage_required":statuses["triage"],
      "new_sql_table_refs_unbound":flags["UNBOUND_SQL_TABLE_REFERENCES"],
      "unverified_role_mapping_pending_cases":sum(
          1 for x in rows if x["review_flags"]),
      "historical_human_notes_available":100,
      "peer_qwen4b_completed":sum(peer_relation.values()),
      "peer_not_reviewed_due_to_rejected_plan":statuses["triage"],
      "peer_relation_not_ground_truth":dict(peer_relation),
      "peer_historical_note_quality":dict(historical_quality),
      "peer_missing_verifiable_test":statuses["missing_verifiable_test"],
      "sap_ot_receipts_verified":ot_audit["verified_cases"],
      "sap_ot_orders_found":ot_audit["orders_found"],
      "sap_ot_not_found_in_specific_table":ot_audit["not_found_in_these_tables"],
      "sap_ot_before_after_16_cases":dict(transitions),
      "sap_ot_accepted_before":sum(x["before_quality_accepted"] for x in augmented),
      "sap_ot_accepted_after":sum(x["quality_accepted"] for x in augmented),
      "sap_ot_native_o5_certification":False,
      "human_root_causes_certified":0,
      "functional_repairs_certified":0,
      "diagnostic_accuracy_measured":False,
      "fraudulent_evidence_promotions":0,
      "source_shas":{
        "native_audit":sha256((root/"independent_audit_100.json").read_bytes()).hexdigest(),
        "peer_journal":sha256((root/"feb100_peer4b_historical_review.private.jsonl").read_bytes()).hexdigest(),
        "holdout":sha256((root/"feb100_historical_holdout.private.jsonl").read_bytes()).hexdigest(),
        "ot_audit":sha256((root/"feb100_ot_independent_audit.private.json").read_bytes()).hexdigest(),
      },
      "per_case_digest":sha256(("\n".join(
          json.dumps(x,sort_keys=True,ensure_ascii=False) for x in rows)+"\n").encode()).hexdigest(),
      "hard_flags":dict(flags),
      "service_counts":dict(service_counts.most_common()),
      "day_counts":dict(sorted(day_counts.items())),
    }
    report_path.write_text(json.dumps(summary,sort_keys=True,indent=2),encoding="utf-8")
    private=report_path.with_name("feb100_per_case_scorecard.private.jsonl")
    require(not private.exists(),"REFUSE_PRIVATE_OVERWRITE")
    private.write_text("\n".join(json.dumps(x,sort_keys=True) for x in rows)+"\n",
                       encoding="utf-8")
    return summary

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--allowlist",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(build(a.root,a.allowlist,a.out),ensure_ascii=False))
if __name__=="__main__":main()

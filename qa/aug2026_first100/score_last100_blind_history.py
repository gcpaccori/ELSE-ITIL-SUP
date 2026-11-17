"""Score frozen last-100 August 2026 blind model plans versus historical peer opinions.

This does not claim historical causal accuracy or re-run Qwen. Historical model
outputs were generated on 2026-11-10. No ITIL texts, corporate identifiers,
per-case hashes, or solutions are written to the public report.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

SCHEMA="else.itil.qa.2026-aug-last100-blind-vs-history.v1"

def load_jsonl(path:Path)->list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()]

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def score(blind:list[dict],qwen:list[dict],peer:list[dict],manifest:dict,peer_summary:dict)->dict:
    if manifest.get("month")!="2026-08" or manifest.get("cases")!=1819:
        raise ValueError("AUG_SOURCE_WRONG_COHORT")
    if len(blind)!=len(qwen)!=len(peer):
        raise ValueError("AUG_JOURNAL_DIFFERENT_LENGTHS")
    if len(blind)!=1819:
        raise ValueError("AUG_JOURNAL_1819_REQUIRED")
    ids=[x["ticket_sha256"] for x in blind]
    if len(ids)!=len(set(ids)):
        raise ValueError("AUG_DUPLICATE_SOURCE_ID")
    for x in blind:
        if x["historical_resolution"]!="WITHHELD" or x["model_tools_enabled"] is not False:
            raise ValueError("AUG_BLIND_GOLD_LEAK_OR_TOOLS_ENABLED")
    if any(a["opened_at"]>b["opened_at"] for a,b in zip(blind,blind[1:])):
        raise ValueError("AUG_INPUT_NOT_CHRONOLOGICAL")
    by_q={x["ticket_sha256"]:x for x in qwen}
    by_p={x["case_sha256"]:x for x in peer}
    if len(by_q)!=1819 or len(by_p)!=1819 or set(by_q)!=set(ids) or set(by_p)!=set(ids):
        raise ValueError("AUG_JOURNAL_CASE_SET_MISMATCH")
    selected=blind[-100:]
    statuses=Counter()
    peer_states=Counter()
    peer_relations=Counter()
    history_quality=Counter()
    services=Counter()
    module_set=set()
    for case in selected:
        cid=case["ticket_sha256"]
        plan=by_q[cid]
        judge=by_p[cid]
        if (case["month"]!="2026-08" or plan["month"]!="2026-08"
            or plan["historical_gold_exposed"] is not False
            or plan["repairs_certified"] is not False
            or judge["repair_certified"] is not False
            or judge["human_confirmed"] is not False):
            raise ValueError("AUG_LAST100_FALSE_CAUSAL_CERTIFICATION")
        statuses[plan["status"]]+=1
        peer_states[judge["peer_state"]]+=1
        peer_relations[judge["peer_relation"]]+=1
        history_quality[judge["history_quality"]]+=1
        services[case["service_code"]]+=1
        module_set.add(case["module_code"])
    if (sum(statuses.values())!=100 or sum(peer_states.values())!=100
            or sum(peer_relations.values())!=100 or sum(history_quality.values())!=100):
        raise ValueError("AUG_LAST100_COHORT_ALIGNMENT_FAILURE")
    return {
        "schema":SCHEMA,
        "evaluation_period":"2026-08",
        "selection":"LAST_100_FechaSolicitud_CodigoIncidente_ASC",
        "source_month_incidents":1819,
        "evaluated_cases":100,
        "first_opened_at":selected[0]["opened_at"],
        "last_opened_at":selected[-1]["opened_at"],
        "distinct_modules":len(module_set),
        "blind_diagnoses_from_previous_20261110_campaign":True,
        "model_rerun_in_this_stage":False,
        "history_withheld_during_model_generation":True,
        "matched_distinct_ticket_hashes":100,
        "model_contract_outcomes":dict(sorted(statuses.items())),
        "historical_peer_states":dict(sorted(peer_states.items())),
        "peer_relation_model_opinion_not_certified_truth":dict(sorted(peer_relations.items())),
        "historical_notes_quality_peer_opinion":dict(sorted(history_quality.items())),
        "service_distribution":dict(sorted(services.items())),
        "repair_certification_count":0,
        "expert_human_review_count":0,
        "historical_accuracy_cannot_be_inferred_from_peer_relation":True,
        "business_writes":0,
        "frozen_august_manifest_sha256":manifest["blind_sha256"],
        "previous_peer_audit_schema":peer_summary["schema"],
    }

def main()->None:
    p=argparse.ArgumentParser()
    for option in ("blind","manifest","qwen","peer","peer-audit","public-output"):
        p.add_argument("--"+option,required=True,type=Path)
    args=p.parse_args()
    manifest=json.loads(args.manifest.read_text())
    audit=json.loads(args.peer_audit.read_text())
    if sha(args.blind)!=manifest["blind_sha256"]:
        raise ValueError("AUG_BLIND_HASH_MISMATCH")
    if sha(args.qwen)!=audit["source_journal_sha256"]:
        raise ValueError("AUG_QWEN_JOURNAL_HASH_MISMATCH")
    if sha(args.peer)!=audit["per_case_audit_sha256"]:
        raise ValueError("AUG_PEER_JOURNAL_HASH_MISMATCH")
    report=score(load_jsonl(args.blind),load_jsonl(args.qwen),
                 load_jsonl(args.peer),manifest,audit)
    report["blind_journal_sha256"]=sha(args.blind)
    report["qwen_journal_sha256"]=sha(args.qwen)
    report["peer_journal_sha256"]=sha(args.peer)
    args.public_output.parent.mkdir(parents=True,exist_ok=True)
    args.public_output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("AUG_LAST100_BLIND_HISTORICAL_AUDIT=PASS",report["model_contract_outcomes"],
          report["peer_relation_model_opinion_not_certified_truth"])

if __name__=="__main__":main()

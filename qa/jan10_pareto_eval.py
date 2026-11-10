"""Full-population retrospective QA evaluation: January 1-10, 2026.

Inputs are original Windows QA export + historical Qwen9B/peer receipts.
No new model inference, no SQL, no mutation. 638/638 cases, no sampling.
Human historical answers are NEVER input to the Pareto lane/contract gate.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from else_dominance.pareto_evidence import (
    route_case, evidence_gate, SCHEMA as ROUTER_SCHEMA)

SCHEMA="else.itil.jan10.pareto-audit.v1"
START="2026-01-01"
END="2026-01-11"
EXPECTED_MONTH=1987
EXPECTED_PERIOD=638
FILES={
    "requests":"jan2026_requests.private.jsonl",
    "gold":"jan2026_historical_solutions.private.jsonl",
    "model0":"qwen9b_jan2026_full_shard_0.private.jsonl",
    "model1":"qwen9b_jan2026_full_shard_1.private.jsonl",
    "judge0":"jan2026_independent_4b_full_shard_0.private.jsonl",
    "judge1":"jan2026_independent_4b_full_shard_1.private.jsonl",
}
TABLE_RE=re.compile(r"\b(?:ITIL|SEC|ADM|COM|DIS|DIST|DBO)\."
                    r"[A-Za-z][A-Za-z0-9_]*\b",re.I)


def require(ok,why):
    if not ok:raise ValueError(why)


def sha(data):
    return sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf-8")


def read_rows(path:Path) -> list[dict]:
    require(path.is_file() and not path.is_symlink(),
            "INPUT_FILE_MISSING")
    rows=[]
    for line in path.read_bytes().splitlines():
        if not line.strip():continue
        record=json.loads(line)
        require(type(record) is dict,"INPUT_NOT_OBJECT")
        rows.append(record)
    return rows


def keyed(rows:list[dict],expected:int,label:str)->dict[str,dict]:
    require(len(rows)==expected,"COUNT_MISMATCH_"+label)
    keys=[x.get("case_sha256") for x in rows]
    require(all(type(k) is str and re.fullmatch(r"[0-9a-f]{64}",k)
                for k in keys),"CASE_SHA_NOT_CANONICAL_"+label)
    require(len(set(keys))==len(keys),"DUPLICATE_CASE_SHA_"+label)
    return {k:r for k,r in zip(keys,rows)}


def evaluate(directory:Path,out:Path)->dict:
    require(not out.exists(),"OUTPUT_ALREADY_EXISTS")
    sources={k:directory/v for k,v in FILES.items()}
    rows={k:read_rows(p) for k,p in sources.items()}
    requests=keyed(rows["requests"],EXPECTED_MONTH,"REQUESTS")
    gold=keyed(rows["gold"],EXPECTED_MONTH,"GOLD")
    models=keyed(rows["model0"]+rows["model1"],
                 EXPECTED_MONTH,"QWEN9B")
    judge=keyed(rows["judge0"]+rows["judge1"],
                EXPECTED_MONTH,"QWEN4B_PEER")
    require(set(requests)==set(models)==set(judge)==set(gold),
            "MODEL_HISTORICAL_COHORT_MISMATCH")
    eligible=[r for r in requests.values()
              if START<=r.get("opened_at","")[:10]<END]
    require(len(eligible)==EXPECTED_PERIOD,"JAN10_SCOPE_NOT_638")
    eligible.sort(key=lambda r:(r["opened_at"],r["case_sha256"]))
    require(all(r["month"]=="2026-01" for r in eligible),
            "JAN10_MONTH_MISMATCH")
    require(not any("historical_solution" in r for r in rows["requests"]),
            "GOLD_LEAKED_IN_INPUT_EXPORT")
    stats={
        "days":Counter(),"services":Counter(),"classifications":Counter(),
        "lanes":Counter(),"pareto_lane_by_service":defaultdict(Counter),
        "baseline":Counter(),"gate":Counter(),"peer_relation":Counter(),
        "peer_action_relation":Counter(),"peer_history_quality":Counter(),
        "claims":Counter(),"evidence_gap_categories":Counter(),
        "historical_quality":Counter(),"source_unbound_table_mentions":Counter(),
    }
    cases=[]
    for row in eligible:
        case_sha=row["case_sha256"]
        plan=models[case_sha]
        prior=judge[case_sha]
        # Required fresh evidence is absent for January. Evaluating a
        # historical text model output is not a NuGet/O5 read.
        route=route_case(
            case_sha256=case_sha,
            service_code=row["service_code"],
            description=row["incident_text"],
            verified_receipt_categories=frozenset())
        result=evidence_gate(
            route=route,
            model_completed=plan.get("model_completed") is True,
            original_contract_pass=plan.get("source_bound_gate_accepted") is True)
        # Inspect *claimed* SQL tables only as a provenance hint. An
        # unbound mention is NOT proof the underlying table is nonexistent.
        answer=(plan.get("normalized_plan") or
                plan.get("technical_plan") or {})
        if type(answer) is not dict:answer={}
        declared={str(x).upper() for x in (answer.get("fuentes") or [])
                  if type(x) is str}
        referenced={x.upper() for x in TABLE_RE.findall(
            json.dumps(answer,ensure_ascii=False))}
        undocumented=sorted(x for x in referenced if x not in declared)
        # Gold is opened only after the model/route gate is computed.
        historical=gold[case_sha].get("historical_solution") or ""
        require(row["has_historical_solution"] is bool(historical.strip()),
                "GOLD_EXISTENCE_BINDING_MISMATCH")
        history_quality=("EMPTY" if not historical.strip() else
                         "SHORT_LT80" if len(historical.strip())<80 else
                         "LONGER_NOT_NECESSARILY_CORRECT")
        peer=prior.get("judge_result") or {}
        if type(peer) is not dict:peer={}
        day=row["opened_at"][:10]
        stats["days"][day]+=1
        stats["services"][row["service_code"]]+=1
        stats["classifications"][row["classification_code"]]+=1
        stats["lanes"][route.lane]+=1
        stats["pareto_lane_by_service"][row["service_code"]][route.lane]+=1
        stats["baseline"]["model_completed"]+=int(plan.get("model_completed") is True)
        stats["baseline"]["raw_gate_pass"]+=int(plan.get("raw_gate_accepted") is True)
        stats["baseline"]["source_bound_gate_pass"]+=int(
            plan.get("source_bound_gate_accepted") is True)
        added=plan.get("source_binding_added")
        require(type(added) is list and all(type(x) is str for x in added),
                "POSTHOC_SOURCE_BINDING_RECEIPT_INVALID")
        stats["baseline"]["posthoc_source_binding_added_cases"]+=int(bool(added))
        stats["baseline"]["posthoc_binding_added_and_gate_pass"]+=int(
            bool(added) and plan.get("source_bound_gate_accepted") is True)
        stats["baseline"]["historical_gold_shown"]+=int(
            plan.get("historical_solution_shown") is True)
        stats["baseline"]["peer_completed"]+=int(prior.get("judge_completed") is True)
        stats["gate"][result["status"]]+=1
        for missing in route.missing_receipts:
            stats["evidence_gap_categories"][missing]+=1
        stats["historical_quality"][history_quality]+=1
        stats["claims"]["reported_ot_pattern_not_verified"]+=int(
            route.ot_identifier_reported)
        stats["claims"]["pareto_top3_service_codes"]+=int(
            route.case_in_pareto_services)
        stats["claims"]["unbound_sql_table_mentions"]+=int(bool(undocumented))
        for name in undocumented:stats["source_unbound_table_mentions"][name]+=1
        if prior.get("judge_completed") is True:
            stats["peer_relation"][str(peer.get("diagnosis_relation","UNKNOWN"))]+=1
            stats["peer_action_relation"][str(peer.get("action_relation","UNKNOWN"))]+=1
            stats["peer_history_quality"][str(peer.get("history_quality","UNKNOWN"))]+=1
            stats["claims"]["peer_possible_unjustified_mutation"]+=int(
                peer.get("unjustified_mutation") is True)
            stats["claims"]["peer_domain_mismatch"]+=int(
                peer.get("domain_mismatch") is True)
        cases.append({
            "case_sha256":case_sha,
            "opened_at":row["opened_at"],
            "service_code":row["service_code"],
            "classification_code":row["classification_code"],
            "lane":route.lane,
            "ot_identifier_reported_not_verified":route.ot_identifier_reported,
            "missing_verified_receipts":list(route.missing_receipts),
            "qwen_model_completed":plan.get("model_completed") is True,
            "qwen_source_bound_contract_pass":
                plan.get("source_bound_gate_accepted") is True,
            "posthoc_source_binding_added":bool(added),
            "pareto_gate":result["status"],
            "unbound_sql_table_mentions":undocumented,
            "history_quality_stratum":history_quality,
            "peer_relation_heuristic":str(peer.get("diagnosis_relation","NOT_JUDGED"))
                    if prior.get("judge_completed") is True else "NOT_JUDGED",
            "repair_certified":False,
            "human_accepted":False,
        })
    n=len(cases)
    summary={
        "schema":SCHEMA,
        "source":"ELSE70/dbITIL_D/dbo.taIncidente snapshot on ELSE62",
        "window_start_inclusive":START,
        "window_end_exclusive":END,
        "snapshot_month_cases":EXPECTED_MONTH,
        "evaluated_cases":n,
        "cases_unique":len({x["case_sha256"] for x in cases}),
        "full_population_not_sample":True,
        "historical_solutions_hidden_from_prior_inference":True,
        "historical_solutions_used_for_routing":False,
        "daily_counts":dict(sorted(stats["days"].items())),
        "service_counts":dict(stats["services"].most_common()),
        "classification_counts":dict(stats["classifications"].most_common()),
        "pareto_top3_service_codes":["1","3","2"],
        "pareto_top3_cases":stats["claims"]["pareto_top3_service_codes"],
        "pareto_top3_pct":round(100*stats["claims"]["pareto_top3_service_codes"]/n,2),
        "lane_counts":dict(stats["lanes"].most_common()),
        "lane_by_service":{
            s:dict(c.most_common()) for s,c in sorted(
                stats["pareto_lane_by_service"].items())},
        "historical_quality_strata":dict(stats["historical_quality"]),
        "qwen9b_prior_baseline":dict(stats["baseline"]),
        "qwen4b_peer_semantic_labels_not_accuracy":{
            "diagnosis":dict(stats["peer_relation"]),
            "actions":dict(stats["peer_action_relation"]),
            "historical_quality":dict(stats["peer_history_quality"])},
        "new_evidence_gate_decisions":dict(stats["gate"]),
        "missing_evidence_categories":dict(stats["evidence_gap_categories"]),
        "risk_screeners_not_causal_proof":{
            "unbound_source_table_mention_cases":
                stats["claims"]["unbound_sql_table_mentions"],
            "reported_ot_pattern_not_verified":
                stats["claims"]["reported_ot_pattern_not_verified"],
            "peer_possible_unjustified_mutation":
                stats["claims"]["peer_possible_unjustified_mutation"],
            "peer_domain_mismatch":
                stats["claims"]["peer_domain_mismatch"]},
        "top_unbound_table_mention_terms":
            stats["source_unbound_table_mentions"].most_common(12),
        "result_not_root_cause_or_resolution_accuracy":True,
        "real_jan10_nuget_receipts_executed":0,
        "functional_repair_certified":0,
        "human_validations":0,
        "automatic_training_promotions":0,
        "inputs_sha256":{k:sha(p.read_bytes()) for k,p in sources.items()},
        "per_case_result_sha256":sha(b"".join(
            canonical(x)+b"\n" for x in cases)),
        "generated_utc":datetime.now(timezone.utc).isoformat(),
    }
    out.mkdir(parents=True,exist_ok=False)
    with (out/"jan10_pareto_cases.private.jsonl").open("xb") as f:
        for record in cases:f.write(canonical(record)+b"\n")
    (out/"jan10_pareto_summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    require(sha((out/"jan10_pareto_cases.private.jsonl").read_bytes())==
            summary["per_case_result_sha256"],"OUTPUT_DIGEST_DRIFT")
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    report=evaluate(args.source,args.out)
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=="__main__":main()

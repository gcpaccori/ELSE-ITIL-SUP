"""Full-population Jan22–31 capability evaluation, strictly held out from gold.

Reads historical prior Qwen/peer receipts + separately completed new NuGet
O5/O13/O15 audit; computes actual coverage and contract acceptance, never
asserts diagnosis/repair accuracy or leaks historical solutions to model.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
from collections import Counter
from datetime import datetime,timezone
import argparse,json,re

PERIOD_START="2026-01-22"
PERIOD_END="2026-02-01"
EXPECTED_MONTH=1987
EXPECTED_WINDOW=574
EXPECTED_FRESH=12
FILES={
 "requests":"jan2026_requests.private.jsonl",
 "historical":"jan2026_historical_solutions.private.jsonl",
 "qwen0":"qwen9b_jan2026_full_shard_0.private.jsonl",
 "qwen1":"qwen9b_jan2026_full_shard_1.private.jsonl",
 "peer0":"jan2026_independent_4b_full_shard_0.private.jsonl",
 "peer1":"jan2026_independent_4b_full_shard_1.private.jsonl",
}
HEX=re.compile(r"[0-9a-f]{64}\Z")

def require(ok,code):
    if not ok:raise ValueError(code)

def load(path):
    require(path.is_file() and not path.is_symlink(),"INPUT_MISSING")
    return [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines()
            if x.strip()]

def by_id(rows, expected, name):
    require(len(rows)==expected,"COUNT_MISMATCH_"+name)
    ids=[r["case_sha256"] for r in rows]
    require(all(type(x) is str and HEX.fullmatch(x) for x in ids),
            "INVALID_SHA_"+name)
    require(len(set(ids))==len(ids),"DUPLICATE_SHA_"+name)
    return {r["case_sha256"]:r for r in rows}

def evaluate(source, audit_path, output):
    require(not output.exists(),"OUTPUT_EXISTS")
    req=by_id(load(source/FILES["requests"]),EXPECTED_MONTH,"REQUESTS")
    hist=by_id(load(source/FILES["historical"]),EXPECTED_MONTH,"HISTORY")
    model=by_id(load(source/FILES["qwen0"])+load(source/FILES["qwen1"]),
                EXPECTED_MONTH,"MODEL")
    peer=by_id(load(source/FILES["peer0"])+load(source/FILES["peer1"]),
                EXPECTED_MONTH,"PEER")
    require(set(req)==set(hist)==set(model)==set(peer),
            "JOIN_COHORT_MISMATCH")
    cohort={sha:row for sha,row in req.items()
            if PERIOD_START<=row["opened_at"][:10]<PERIOD_END}
    require(len(cohort)==EXPECTED_WINDOW,"COHORT_COUNT_NOT_574")
    require(all("historical_solution" not in v for v in req.values()),
            "HISTORICAL_SOLUTION_LEAK")
    audit=json.loads(audit_path.read_text(encoding="utf-8"))
    require(audit["schema"]=="else.itil.qa.janlast10-independent-audit.v1",
            "FRESH_AUDIT_NOT_INDEPENDENT")
    fresh=audit["cases"]
    require(len(fresh)==audit["runs_verified"]==EXPECTED_FRESH,
            "FRESH_AUDIT_CASE_COUNT_NOT_12")
    verified={}
    for entry in fresh:
        sha=entry["case_sha256"]
        require(sha in cohort and sha not in verified,
                "FRESH_CASE_NOT_UNIQUE_IN_LAST10")
        require(entry["o5_o13_o15_pass"] is True and
                entry["tampered_receipt_rejected"] is True,
                "FRESH_PROOF_NOT_VERIFIED")
        require(entry["opened_at"]==cohort[sha]["opened_at"],
                "FRESH_CASE_DATE_DRIFT")
        verified[sha]=entry
    require(len({v["opened_at"][:10] for v in fresh})==10,
            "FRESH_NOT_ALL_TEN_DAYS")
    days=Counter()
    services=Counter()
    baseline=Counter()
    judge_labels=Counter()
    history=Counter()
    new_status=Counter()
    outcomes=[]
    for sha,row in sorted(cohort.items(),key=lambda x:(x[1]["opened_at"],x[0])):
        m=model[sha]
        j=peer[sha]
        gold=hist[sha].get("historical_solution") or ""
        require(bool(gold.strip())==row["has_historical_solution"],
                "HISTORY_EXTRINSIC_STATUS_DRIFT")
        days[row["opened_at"][:10]]+=1
        services[row["service_code"]]+=1
        flags={
          "prior_completed":m.get("model_completed") is True,
          "prior_raw_contract_pass":m.get("raw_gate_accepted") is True,
          "prior_source_bound_contract_pass":m.get("source_bound_gate_accepted") is True,
          "posthoc_source_names_added":bool(m.get("source_binding_added")),
          "prior_history_shown":m.get("historical_solution_shown") is True,
          "prior_peer_completed":j.get("judge_completed") is True,
        }
        for name,value in flags.items():baseline[name]+=int(value)
        if flags["posthoc_source_names_added"] and flags["prior_source_bound_contract_pass"]:
            baseline["posthoc_source_names_and_bound_contract_pass"]+=1
        judge=(j.get("judge_result") or {})
        if flags["prior_peer_completed"]:
            judge_labels[str(judge.get("diagnosis_relation","UNKNOWN"))]+=1
        history["nonempty"]+=int(bool(gold.strip()))
        if gold.strip():
            history["lt80"]+=int(len(gold.strip())<80)
            history["gte80"]+=int(len(gold.strip())>=80)
        extra=verified.get(sha)
        if extra:new_status["fresh_o5_verified"]+=1
        if extra and extra["quality_accepted"]:
            new_status["fresh_contract_accepted"]+=1
        if extra and not extra["quality_accepted"]:
            new_status["fresh_human_triage"]+=1
        outcomes.append({
            "case_sha256":sha,"opened_at":row["opened_at"],
            "service_code":row["service_code"],
            **flags,
            "fresh_nuget_o5_verified":bool(extra),
            "fresh_contract_accepted":(
                extra["quality_accepted"] if extra else None),
            "new_case_reviewed_by_human":False,
            "causal_resolution_certified":False,
        })
    raw=b"".join((json.dumps(x,sort_keys=True,ensure_ascii=False,
                separators=(",",":"))+"\n").encode() for x in outcomes)
    report={
        "schema":"else.itil.jan22-31.real-capability-eval.v1",
        "period_start":PERIOD_START,
        "period_end_inclusive":"2026-01-31",
        "historical_population":EXPECTED_WINDOW,
        "distinct_cases":len(outcomes),
        "fresh_execution_coverage":len(verified),
        "fresh_execution_coverage_pct":round(len(verified)/len(outcomes)*100,2),
        "fresh_unique_days":len({entry["opened_at"][:10] for entry in fresh}),
        "fresh_receipts_verified":new_status["fresh_o5_verified"],
        "fresh_contract_accepted":new_status["fresh_contract_accepted"],
        "fresh_needs_human_triage":new_status["fresh_human_triage"],
        "day_counts":dict(sorted(days.items())),
        "service_counts":dict(services.most_common()),
        "prior_model_baseline":dict(baseline),
        "peer_semantic_labels_not_ground_truth":dict(judge_labels),
        "historical_solution_strata":dict(history),
        "new_model_inferences":len(verified),
        "new_per_ticket_sql_reads":len(verified),
        "historical_model_inferences_rerun":0,
        "human_root_cause_confirmations":0,
        "certified_repairs":0,
        "classification_accuracy_not_measured":True,
        "new_diagnosis_accuracy_not_measured":True,
        "no_training_promotion":True,
        "input_sha256":{k:sha256((source/v).read_bytes()).hexdigest()
                        for k,v in FILES.items()},
        "audit_sha256":sha256(audit_path.read_bytes()).hexdigest(),
        "per_case_audit_sha256":sha256(raw).hexdigest(),
        "generated_utc":datetime.now(timezone.utc).isoformat(),
    }
    output.mkdir(parents=True,exist_ok=False)
    with (output/"janlast10_cases.private.jsonl").open("xb") as file:
        file.write(raw)
    (output/"janlast10_summary.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    return report

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source",type=Path,required=True)
    a.add_argument("--audit",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    x=a.parse_args()
    print(json.dumps(evaluate(x.source,x.audit,x.out),
                     ensure_ascii=False,sort_keys=True))
if __name__=="__main__":main()

"""February 100 peer comparison baseline vs grounded-v2, no gold text output.

A model judge is not truth; report disagreement and lack of decisive
historical closure separately from structural grounding success.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
ROOT=Path("/home/u23u/else_itil_feb100_qa_20261110")
NEW=Path("/home/u23u/else_itil_feb100_grounding_qa_20261110")
BASE=ROOT/"feb100_peer4b_historical_review.private.jsonl"
CURRENT=NEW/"feb100_grounded_v2_peer4b.private.jsonl"
OUT=NEW/"peer4b_grounded_v2_comparison.json"

def load(p):
    a=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    if len(a)!=100 or len({x["case_sha256"] for x in a})!=100:
        raise ValueError("PEER_COHORT_NOT_100")
    return {x["case_sha256"]:x for x in a}

def make():
    if OUT.exists():raise FileExistsError("PEER_COMPARISON_EXISTS")
    prior=load(BASE);updated=load(CURRENT)
    if set(prior)!=set(updated):
        raise ValueError("PRIOR_PEER_IDENTITY_DRIFT")
    states=Counter();basis=Counter();present=Counter();overlap=Counter()
    transition=Counter();specificity=Counter();closure=Counter()
    for sha in sorted(prior):
        a,b=prior[sha],updated[sha]
        states[b["state"]]+=1
        if b["state"]=="PEER_COMPLETED":
            present[b["relation"]]+=1
            specificity[b["plan_specificity"]]+=1
            closure["missing_test"]+=int(b["missing_verifiable_test"] is True)
            basis[b["history_quality"]]+=1
        if a["state"]=="PEER_COMPLETED" and b["state"]=="PEER_COMPLETED":
            overlap["both_peer_evaluated"]+=1
            transition[(a["relation"],b["relation"])]+=1
            if a["relation"]!=b["relation"]:
                overlap["judge_label_changed"]+=1
        elif a["state"]=="NOT_COMPARABLE_REJECTED_PLAN" and b["state"]=="PEER_COMPLETED":
            overlap["newly_reviewable"]+=1
        elif a["state"]=="PEER_COMPLETED" and b["state"]=="NOT_COMPARABLE_REJECTED_PLAN":
            overlap["regressed_to_unreviewable"]+=1
    return {
        "schema":"else.itil.feb100.grounded-v2-peer-comparison.v1",
        "cases":100,
        "peer_v2_states":dict(states),
        "peer_v2_relations_not_ground_truth":dict(present),
        "peer_v2_historical_note_quality":dict(basis),
        "peer_v2_plan_specificity":dict(specificity),
        "peer_v2_missing_verifiable_test":closure["missing_test"],
        "comparably_evaluated_cases":overlap["both_peer_evaluated"],
        "newly_reviewable_cases":overlap["newly_reviewable"],
        "regressed_to_unreviewable_cases":overlap["regressed_to_unreviewable"],
        "judge_relation_label_changed_on_shared_cases":overlap["judge_label_changed"],
        "judge_transition_counts_not_ground_truth":{
            f"{x[0]}→{x[1]}":n for x,n in transition.items()},
        "peer_is_model_not_human":True,
        "historical_notes_are_not_causal_truth":True,
        "certified_root_causes":0,
        "certified_repairs":0,
        "old_peer_sha256":sha256(BASE.read_bytes()).hexdigest(),
        "new_peer_sha256":sha256(CURRENT.read_bytes()).hexdigest(),
    }

if __name__=="__main__":
    report=make()
    OUT.write_text(json.dumps(report,sort_keys=True,indent=2))
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))

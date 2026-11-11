"""Unseen 30-case August 2026 holdout: no gold, no previous scores.

Deterministic service-proportional sample from 1,769 cases not in the
50-case development review. Source seal is checked before any inference.
No mutation to original model outputs, no SQL, no repair.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,random,math,os,argparse

from else_dominance.functional_investigator_v2 import run_case,canon

BASE=Path("/home/u23u/else_itil_aug2026_qa_20261110")
DEV=Path("/home/u23u/else_itil_aug2026_review_private_20261110/human50_audit_20261110")
ROOT=Path("/home/u23u/else_itil_functional_v2_qa_20261110")
SOURCE=BASE/"aug2026_blind_redacted.private.jsonl"
MANIFEST=BASE/"aug2026_manifest.json"
SELECTION=ROOT/"unseen30_selection.private.jsonl"
JOURNAL=ROOT/"unseen30_v2_2.private.jsonl"
PROGRESS=ROOT/"unseen30_v2_2_progress.json"
RNG=20261111

def check(ok,why):
    if not ok:raise ValueError(why)

def rows():
    m=json.loads(MANIFEST.read_bytes())
    raw=SOURCE.read_bytes()
    check(m["blind_sha256"]==sha256(raw).hexdigest() and
          m["cases"]==1819 and m["gold_shown_to_model"] is False,
          "AUGUST_SEAL_CHANGED")
    cases=[json.loads(x) for x in raw.splitlines() if x]
    check(len(cases)==len({x["ticket_sha256"] for x in cases})==1819,
          "AUG1819_NOT_UNIQUE")
    old=json.loads((DEV/"sample50.private.json").read_bytes())
    prior={x["sha256"] for x in old}
    check(len(prior)==50,"DEVELOPMENT_COHORT_CHANGED")
    remain=[x for x in cases if x["ticket_sha256"] not in prior]
    check(len(remain)==1769,"UNSEEN_POPULATION_INVALID")
    groups=defaultdict(list)
    for x in remain:groups[x["service_code"]].append(x)
    quotas={s:30*len(v)/1769 for s,v in groups.items()}
    n={s:int(math.floor(q)) for s,q in quotas.items()}
    for s in sorted(groups,key=lambda k:(-(quotas[k]-n[k]),k))[:30-sum(n.values())]:
        n[s]+=1
    rng=random.Random(RNG)
    sample=[]
    for s in sorted(n):
        sample.extend(rng.sample(sorted(groups[s],key=lambda x:x["ticket_sha256"]),n[s]))
    check(len(sample)==len({x["ticket_sha256"] for x in sample})==30 and
          {x["ticket_sha256"] for x in sample}.isdisjoint(prior),
          "UNSEEN_SAMPLE_IS_NOT_INDEPENDENT")
    if not SELECTION.exists():
        with SELECTION.open("xb") as f:
            f.write(b"\n".join(canon({
                "case_sha256":x["ticket_sha256"],
                "service_code":x["service_code"],
                "redacted_request_sha256":sha256(canon(x)).hexdigest(),
            }) for x in sample)+b"\n")
    else:
        previous=[json.loads(x) for x in SELECTION.read_bytes().splitlines()]
        check([x["case_sha256"] for x in previous]==
              [x["ticket_sha256"] for x in sample],
              "UNSEEN_SELECTION_CHANGED")
    return [{
        "ticket_sha256":x["ticket_sha256"],
        "incident_text_redacted":x["incident_text_redacted"],
    } for x in sample]

def load_done(source):
    allowed={x["ticket_sha256"]:x for x in source}
    done={}
    if not JOURNAL.exists():return done
    for line in JOURNAL.read_bytes().splitlines():
        if not line:continue
        r=json.loads(line)
        k=r["case_sha256"]
        check(k in allowed and k not in done and
              r["source_row_sha256"]==sha256(canon(allowed[k])).hexdigest() and
              r["historical_resolution_exposed"] is False and
              r["repair_certified"] is False,
              "UNSEEN_REPLAY_NOT_IMMUTABLY_BOUND")
        done[k]=r
    return done

def progress(done):
    counted=Counter(x["status"] for x in done.values())
    val={
        "schema":"else.itil.functional-v2.unseen30-progress.v1",
        "selected":30,"processed":len(done),"remaining":30-len(done),
        "functional_contract_pass":counted["FUNCTIONAL_DRAFT_CONTRACT_PASS"],
        "needs_clarification":counted["CLARIFICATION_REQUIRED"],
        "rejected":counted["FUNCTIONAL_DRAFT_REJECTED"],
        "unseen":"STRICT_DISJOINT_FROM_DEVELOPMENT_50",
        "historical_gold_exposed":False,
        "real_business_joins_verified":0,
        "certified_repairs":0,
        "source_selection_sha256":sha256(SELECTION.read_bytes()).hexdigest(),
        "finished_utc":datetime.now(timezone.utc).isoformat() if len(done)==30 else None,
    }
    temp=PROGRESS.with_suffix(".tmp")
    temp.write_text(json.dumps(val,indent=2,sort_keys=True))
    os.replace(temp,PROGRESS)
    return val

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--workers",type=int,default=5)
    a=p.parse_args()
    check(1<=a.workers<=8,"UNSEEN_MODEL_BUDGET_EXCEEDED")
    source=rows()
    done=load_done(source)
    remaining=[x for x in source if x["ticket_sha256"] not in done]
    print(json.dumps({"state":"STARTED","done":len(done),
                      "remaining":len(remaining)}),flush=True)
    with JOURNAL.open("ab") as f,ThreadPoolExecutor(
        max_workers=a.workers) as pool:
        tasks={pool.submit(run_case,x):x["ticket_sha256"] for x in remaining}
        for task in as_completed(tasks):
            v=task.result()
            k=v["case_sha256"]
            check(k not in done,"DUPLICATE_WRITE")
            f.write(canon(v)+b"\n");f.flush()
            done[k]=v
            if len(done)%5==0 or len(done)==30:
                print(json.dumps(progress(done),sort_keys=True),flush=True)
    print(json.dumps(progress(done),sort_keys=True),flush=True)

if __name__=="__main__":main()

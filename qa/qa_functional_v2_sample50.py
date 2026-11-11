"""Reproducible 50-case functional regression, frozen independent baseline.

The V2 model sees ONLY the redacted request + deterministic domain and
NO history, peer classification, original Qwen9B answer or GPT-6 score.
A separate reviewer may compare outputs AFTER inference.
Checkpointed append-only by exact case SHA and input digest.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from hashlib import sha256
from collections import Counter
from datetime import datetime,timezone
import json,os,argparse

from else_dominance.functional_investigator_v2 import run_case,canon
from else_dominance.functional_contract_v2 import check_plan

ROOT=Path("/home/u23u/else_itil_functional_v2_qa_20261110")
REFERENCE=Path("/home/u23u/else_itil_aug2026_review_private_20261110/human50_audit_20261110")
INPUT=REFERENCE/"sample50.private.json"
MANIFEST=REFERENCE/"sample50_manifest.json"
JOURNAL=ROOT/"v2_sample50.private.jsonl"
PROGRESS=ROOT/"v2_sample50_progress.json"

def need(ok,why):
    if not ok:raise ValueError(why)

def canonical(x):return canon(x)

def load():
    entries=json.loads(INPUT.read_bytes())
    manifest=json.loads(MANIFEST.read_bytes())
    need(manifest["sample"]==50 and len(entries)==50 and
         manifest["sample_ids_sha256"]==
         sha256(("\n".join(x["sha256"] for x in entries)+"\n").encode()).hexdigest() and
         len({x["sha256"] for x in entries})==50,"SAMPLE50_SHA_DRIFT")
    requests=[]
    for item in entries:
        # Important: intentionally do NOT copy baseline plan, history,
        # peer label or prior human qualitative rating into model input.
        row={
            "ticket_sha256":item["sha256"],
            "incident_text_redacted":item["description"],
        }
        requests.append(row)
    return requests,manifest

def done_load(rows):
    identities={x["ticket_sha256"]:x for x in rows}
    done={}
    if not JOURNAL.exists():return done
    for line in JOURNAL.read_bytes().splitlines():
        if not line:continue
        row=json.loads(line)
        sha=row["case_sha256"]
        need(sha in identities and sha not in done,"V2_DUPLICATE_OR_FOREIGN_SHA")
        need(row["source_row_sha256"]==
             sha256(canonical(identities[sha])).hexdigest() and
             row["historical_resolution_exposed"] is False and
             row["repair_certified"] is False,
             "V2_REPLAY_UNBOUND_SOURCE")
        done[sha]=row
    return done

def save_progress(done):
    by=Counter(x["status"] for x in done.values())
    r={
        "schema":"else.itil.functional-v2.sample50-progress.v1",
        "selected":50,"processed":len(done),"remaining":50-len(done),
        "functional_contract_pass":by["FUNCTIONAL_DRAFT_CONTRACT_PASS"],
        "needs_clarification":by["CLARIFICATION_REQUIRED"],
        "rejected":by["FUNCTIONAL_DRAFT_REJECTED"],
        "by_status":dict(by),
        "root_cause_certified":0,"repairs_certified":0,
        "historical_gold_exposed":False,
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    }
    tmp=PROGRESS.with_suffix(".tmp")
    tmp.write_text(json.dumps(r,sort_keys=True,indent=2))
    os.replace(tmp,PROGRESS)
    return r

def main():
    args=argparse.ArgumentParser()
    args.add_argument("--workers",type=int,default=6)
    args=args.parse_args()
    need(1<=args.workers<=8,"V2_MODEL_CONCURRENCY_LIMIT")
    cases,manifest=load()
    done=done_load(cases)
    todo=[x for x in cases if x["ticket_sha256"] not in done]
    print(json.dumps({"state":"STARTED","done":len(done),
          "todo":len(todo),"max_workers":args.workers}),flush=True)
    with JOURNAL.open("ab") as f,ThreadPoolExecutor(
            max_workers=args.workers) as pool:
        futures={pool.submit(run_case,row):row["ticket_sha256"] for row in todo}
        for task in as_completed(futures):
            result=task.result()
            sha=result["case_sha256"]
            need(sha not in done,"V2_DUPLICATE_WRITE")
            f.write(canonical(result)+b"\n")
            f.flush()
            done[sha]=result
            if len(done)%5==0 or len(done)==50:
                p=save_progress(done)
                print(json.dumps({k:p[k] for k in (
                    "processed","functional_contract_pass",
                    "needs_clarification","rejected","remaining")}),flush=True)
    print(json.dumps(save_progress(done),sort_keys=True),flush=True)

if __name__=="__main__":main()

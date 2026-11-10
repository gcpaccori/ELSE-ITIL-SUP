"""V2.1 replay ONLY for newly detected bare/bracketed SQL object references.

The original 100 baseline and V2 results are immutable. All unaffected
cases are rechecked by the stricter gate without another model call; affected
cases receive at most two *new* Qwen responses on original pinned O5 receipt.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
from pathlib import Path
import json

from else_dominance.qa_evidence_grounding import evidence_provenance_gate
from qa import qa_feb100_grounding_replay as replay

QA=Path("/home/u23u/else_itil_feb100_grounding_qa_20261110")
V21=QA/"v21"
OUT=V21/"outputs"
JOURNAL=V21/"v21_targeted_replay.private.jsonl"
BASE=QA/"outputs"

def main():
    if V21.exists():raise FileExistsError("V21_NO_OVERWRITE")
    files=sorted(BASE.glob("*.private.json"))
    if len(files)!=100:raise ValueError("V2_NOT_100")
    affected=[]
    for p in files:
        d=json.loads(p.read_bytes())
        r=d["new_result"]
        if not r["quality"]["accepted"]:continue
        gate=evidence_provenance_gate(
            r["proposal"],native_o5_verified=True,
            source_receipt_sha256=r["source_receipt_sha256"])
        if not gate["accepted"]:
            affected.append(d)
    if not 1<=len(affected)<=20:
        raise ValueError("UNEXPECTED_V21_CORRECTION_COUNT")
    V21.mkdir(mode=0o700)
    OUT.mkdir(mode=0o700)
    replay.OUTPUTS=OUT
    print(json.dumps({"affected":len(affected),
                      "original":len(files),
                      "sql_reexecution":False}),flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool,JOURNAL.open("x") as out:
        tasks={pool.submit(replay.run_one,
            (d["case_sha256"],replay.INPUT_RUNS/d["parent_run_id"])):d
            for d in affected}
        for f in as_completed(tasks):
            result=f.result()
            out.write(json.dumps(result,sort_keys=True)+"\n")
            out.flush()
            print(json.dumps({
                "case_prefix":result["case_sha256"][:16],
                "state":result["state"],
                "accepted":result.get("accepted"),
                "attempts":result.get("attempts"),
                "grounding_policy":"v2.1"}),flush=True)
    records=[json.loads(x) for x in JOURNAL.read_text().splitlines()]
    print(json.dumps({
        "affected":len(affected),
        "completed":sum(x["state"]=="COMPLETED" for x in records),
        "accepted":sum(x.get("accepted") is True for x in records),
        "sql_reexecutions":0,
        "history_shown_to_model":False,
        "journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest(),
    }),flush=True)

if __name__=="__main__":main()

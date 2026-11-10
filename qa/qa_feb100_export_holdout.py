"""Create a 100-case sealed solution holdout AFTER model generation.

Model inference never opens this file. Only the independent retrospective
reviewer may compare redacted human resolution text to final Qwen output.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,sys
ROOT=Path(r"C:\Temp\ELSE_ITIL_FEB100_QA_20261110")
OUT=ROOT/"feb100_historical_holdout.private.jsonl"
def main():
    if OUT.exists():raise FileExistsError("HOLDOUT_ALREADY_EXISTS")
    sys.path.insert(0,r"C:\Temp\ELSE_ITIL_SUP_RUN")
    from else_dominance.resolution_batch import redact
    source=ROOT/"feb2026_requests.private.jsonl"
    gold=ROOT/"feb2026_historical_solutions.private.jsonl"
    selection=ROOT/"feb100_allowlist.private.jsonl"
    req=[json.loads(x) for x in source.read_text(encoding="utf-8").splitlines()]
    hist=[json.loads(x) for x in gold.read_text(encoding="utf-8").splitlines()]
    sel=[json.loads(x) for x in selection.read_text(encoding="utf-8").splitlines()]
    if len(req)!=1799 or len(hist)!=1799 or len(sel)!=100:
        raise ValueError("FEB_SNAPSHOT_CARDINALITY_DRIFT")
    reqs={r["case_sha256"]:r for r in req}
    golds={r["case_sha256"]:r for r in hist}
    if set(reqs)!=set(golds) or len(reqs)!=1799:
        raise ValueError("GOLD_REQUEST_JOIN_MISMATCH")
    ids=[r["case_sha256"] for r in sel]
    if len(set(ids))!=100 or not set(ids)<=set(reqs):
        raise ValueError("HOLDOUT_100_SCOPE_INVALID")
    rows=[]
    for sha in sorted(ids):
        solution=golds[sha].get("historical_solution") or ""
        if reqs[sha]["has_historical_solution"] != bool(solution.strip()):
            raise ValueError("HISTORY_EXISTENCE_CONFLICT")
        rows.append({
            "case_sha256":sha,
            "historical_solution_redacted":redact(solution)[:2600],
            "historical_solution_present":bool(solution.strip()),
            "historical_solution_bytes":len(solution.encode("utf-8")),
            "original_solution_sha256":sha256(solution.encode()).hexdigest(),
            "human_solution_not_certified":True,
        })
    with OUT.open("xb") as f:
        for r in rows:
            f.write((json.dumps(r,sort_keys=True,ensure_ascii=False)+"\n").encode())
    print(json.dumps({
        "selected":100,
        "human_solution_nonempty":sum(r["historical_solution_present"] for r in rows),
        "empty":sum(not r["historical_solution_present"] for r in rows),
        "holdout_sha256":sha256(OUT.read_bytes()).hexdigest(),
        "note":"HISTORICAL_SOLUTIONS_NOT_CERTIFIED_AS_CAUSAL_TRUTH",
    }))
if __name__=="__main__":main()

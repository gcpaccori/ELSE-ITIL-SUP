"""Recover already-transferred immutable FEB QA receipts locally on Linux.

No SQL re-execution and no new model tool request; these run dirs have
preexisting exact Qwen-requested tool, case metadata and real Windows NuGet
receipt. Native O5/O13/O15 still verifies before the second model turn.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from collections import Counter
import os,subprocess,json
from datetime import datetime,timezone

ROOT=Path("/home/u23u/else_itil_feb100_qa_20261110/runs")
REPO=Path("/home/u23u/else_itil_feb100_20261110")
PYTHON="/home/u23u/miniconda/envs/orquesta_py311/bin/python"
CORE="/home/u23u/elsecore_itil_janlast10_20261110/src"
SOURCE=str(REPO/"qa/Feb100ExactRead.cs")
OUT=Path("/home/u23u/else_itil_feb100_qa_20261110/recovery_41_journal.private.jsonl")

def run_one(path:Path):
    require={"case.private.json","tool_request.private.json","receipt.private.json"}
    if {x.name for x in path.iterdir()}<require or (path/"verified_final.private.json").exists():
        return {"run_id":path.name,"state":"NOT_ELIGIBLE"}
    command=[PYTHON,"-m","else_dominance.qa_feb100_cluster",
             "--root",str(path),"--source",SOURCE]
    env=dict(os.environ,PYTHONPATH=str(REPO)+":"+CORE)
    try:
        p=subprocess.run(command,cwd=str(REPO),env=env,
                         capture_output=True,timeout=300)
        if p.returncode!=0:
            return {"run_id":path.name,"state":"RECOVERY_FAILED",
                    "error_type":"QA_O5_OR_MODEL_REJECTED"}
        result=json.loads(p.stdout.splitlines()[-1])
        if result.get("o5_o13_o15_verified") is not True:
            return {"run_id":path.name,"state":"RECEIPT_NOT_VERIFIED"}
        return {"run_id":path.name,"state":"COMPLETED",
                "quality_accepted":result.get("quality_accepted"),
                "diagnosis_status":result.get("status"),
                "output_sha256":result.get("output_sha256"),
                "qa_real_evidence":True,
                "repair_certified":False}
    except Exception as e:
        return {"run_id":path.name,"state":"RECOVERY_EXCEPTION",
                "error_type":type(e).__name__}

def main():
    if OUT.exists():raise FileExistsError("NO_OVERWRITE_RECOVERY_LOG")
    cases=sorted(p for p in ROOT.glob("case_*")
        if {x.name for x in p.iterdir()}>=
        {"case.private.json","tool_request.private.json","receipt.private.json"}
        and not (p/"verified_final.private.json").exists())
    if not 1<=len(cases)<=100:raise ValueError("RECOVERY_COHORT_INVALID")
    print(json.dumps({"recovery_candidates":len(cases)}),flush=True)
    with OUT.open("x") as f,ThreadPoolExecutor(max_workers=4) as pool:
        for i,future in enumerate(as_completed(
                [pool.submit(run_one,path) for path in cases]),start=1):
            row=future.result()
            f.write(json.dumps(row,sort_keys=True)+"\n")
            f.flush()
            print(json.dumps({"completed":i,"total":len(cases),
                    "status":row["state"],
                    "case_prefix":row["run_id"][5:21]}),flush=True)
    rows=[json.loads(x) for x in OUT.read_text().splitlines()]
    print(json.dumps({"recovered":sum(x["state"]=="COMPLETED" for x in rows),
                      "failures":sum(x["state"]!="COMPLETED" for x in rows)},
                     sort_keys=True),flush=True)
if __name__=="__main__":main()

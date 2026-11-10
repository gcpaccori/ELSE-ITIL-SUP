"""Finish the 54 batch-transferred Feb receipts through native O5 then Qwen9B."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from collections import Counter
import json
from qa_feb100_recover_cluster import ROOT,run_one
OUT=Path("/home/u23u/else_itil_feb100_qa_20261110/finalize_batch_54_journal.private.jsonl")
def main():
    if OUT.exists():raise FileExistsError("NO_OVERWRITE_FINALIZE")
    candidates=sorted(p for p in ROOT.glob("case_*")
        if {'case.private.json','tool_request.private.json','receipt.private.json'}
           <= {x.name for x in p.iterdir()}
        and not (p/"verified_final.private.json").exists())
    if len(candidates)!=54:
        raise ValueError("EXPECTED_54_NOT_"+str(len(candidates)))
    print(json.dumps({"finalize_candidate_count":len(candidates)}),flush=True)
    with OUT.open("x",encoding="utf-8") as f,ThreadPoolExecutor(max_workers=4) as pool:
        for i,future in enumerate(as_completed(
                 [pool.submit(run_one,p) for p in candidates]),start=1):
            row=future.result()
            f.write(json.dumps(row,sort_keys=True)+"\n")
            f.flush()
            print(json.dumps({"completed":i,"total":len(candidates),
                              "state":row["state"]}),flush=True)
    rows=[json.loads(x) for x in OUT.read_text().splitlines()]
    print(json.dumps({"finalized":sum(x["state"]=="COMPLETED" for x in rows),
                      "exceptions":sum(x["state"]!="COMPLETED" for x in rows)},
                     sort_keys=True),flush=True)
if __name__=="__main__":main()

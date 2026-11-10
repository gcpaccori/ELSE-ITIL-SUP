"""Launch only the 16 exact archived-eligible February QA cases as NEW reads.

The Qwen model independently asks for the whitelisted tool by case SHA;
only then a durable fixed SQL job is written. No historical gold solution
or arbitrary SQL reaches the model or Windows.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,zipfile
from else_dominance.agent import OpenAICompatibleModel
from else_dominance.beta_fresh_ot import (
    queue_job,SOURCE_SHA,canonical)
from qa.qa_feb100_windows import read_allowlist

QA=Path("/home/u23u/else_itil_feb100_qa_20261110")
BASE=Path("/home/u23u/else_itil_beta_fresh_20261110")
OUT=Path("/home/u23u/else_itil_beta_fresh_qa_20261110")
JOURNAL=OUT/"fresh_16_model_request_journal.private.jsonl"

def invoke(row):
    model=OpenAICompatibleModel(
       "http://127.0.0.1:18782/v1",
       "else-itil-riv-qwen9b-gpu6",timeout=125)
    for attempt in range(2):
        try:
            path,request=queue_job(row=row,model=model,
                requests_dir=OUT/"requests",
                source_file=BASE/"qa/Feb100SapOtRead.cs")
            return {
                "case_sha256":row["case_sha256"],
                "job_id":request["job_id"],
                "job_sha256":sha256(path.read_bytes()).hexdigest(),
                "model_requested_exact_tool":True,
                "request_validated":True,"read_only":True,
                "historical_solution_not_read":True,
                "state":"QUEUED_FOR_NEW_WINDOWS_SQL",
            }
        except Exception as ex:
            error=type(ex).__name__
    return {"case_sha256":row["case_sha256"],
            "state":"MODEL_EXACT_TOOL_REQUEST_FAILED",
            "error_type":error}

def main():
    if JOURNAL.exists():
        raise FileExistsError("NO_OVERWRITE_MODEL_REQUESTS")
    roster=read_allowlist(QA/"feb100_allowlist.private.jsonl")
    with zipfile.ZipFile(QA/"feb100_ot_sap_receipts.private.zip") as z:
        names=z.namelist()
    ids={name[:64] for name in names}
    if len(ids)!=16 or len(names)!=16 or not ids<=set(roster):
        raise ValueError("SAMPLE_16_DRIFT")
    rows=[roster[sha] for sha in sorted(ids)]
    with JOURNAL.open("x") as f,ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(invoke,rows))
        for r in results:
            f.write(json.dumps(r,sort_keys=True)+"\n")
    print(json.dumps({
        "cases":len(results),
        "new_model_tool_requests_validated":sum(
            x["state"]=="QUEUED_FOR_NEW_WINDOWS_SQL" for x in results),
        "errors":[{"case_prefix":x["case_sha256"][:12],
                   "error":x.get("error_type")} for x in results
                  if x["state"]!="QUEUED_FOR_NEW_WINDOWS_SQL"],
        "request_journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest(),
    }),flush=True)
if __name__=="__main__":main()

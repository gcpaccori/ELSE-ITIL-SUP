"""Windows: run fresh precompiled NuGet SELECT for batch of real Qwen tool asks.

The approved model tool requests were generated on the cluster and their
hashes are re-bound here before SQL. 54 new records, one archive transfer.
No business solutions, no SQL from the model, no mutations.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
from pathlib import Path
import json,subprocess,re,zipfile,os
from qa_feb100_windows import read_allowlist,validate_model_tool,canonical
ROOT=Path(r"C:\Temp\ELSE_ITIL_FEB100_QA_20261110")
SOURCE=ROOT/"qa"/"Feb100ExactRead.cs"
PROJECT=ROOT/"qa"/"Feb100ExactRead.csproj"
DLL=ROOT/"qa"/"bin"/"Release"/"net8.0"/"Feb100ExactRead.dll"
ALLOW=ROOT/"feb100_allowlist.private.jsonl"
MANIFEST=ROOT/"missing_model_requests.private.jsonl"
RUNS=ROOT/"runs"
JOURNAL=ROOT/"batch_sql_receipts.private.jsonl"
ZIP=ROOT/"batch_sql_receipts.private.zip"
SENTINEL="FEB100-BATCH-20261110"
RUN_RE=re.compile(r"case_[0-9a-f]{16}_[0-9a-f]{10}\Z")

def single(record):
    sha=record["case_sha256"]
    run_id=record["run_id"]
    expect="case_"+sha[:16]+"_"+sha256((SENTINEL+sha).encode()).hexdigest()[:10]
    if run_id!=expect or RUN_RE.fullmatch(run_id) is None:
        raise ValueError("BATCH_RUN_ID_SCOPE_INVALID")
    request={"type":"tool","name":"qa_exact_read",
             "query_id":"ITIL_2026_02_FEB100_CASE_EXACT_READ",
             "parameters":{"case_sha256":sha}}
    validate_model_tool(request,sha)
    if sha256(canonical(request)).hexdigest()!=record["model_tool_request_sha256"]:
        raise ValueError("MODEL_REQUEST_HASH_MISMATCH")
    if record.get("genuine_model_request_before_sql") is not True:
        raise ValueError("MODEL_REQUEST_NOT_VERIFIED")
    run=RUNS/run_id
    if run.exists():raise FileExistsError("RECEIPT_RUN_ALREADY_EXISTS")
    run.mkdir(mode=0o700)
    receipt=run/"receipt.private.json"
    command=["dotnet",str(DLL),
       "--allowlist",str(ALLOW),"--case-sha",sha,
       "--out",str(receipt),"--source",str(SOURCE)]
    try:
        cp=subprocess.run(command,capture_output=True,timeout=100)
        if cp.returncode!=0:
            raise RuntimeError("WINDOWS_NUGET_READ_FAILED")
        data=json.loads(cp.stdout.splitlines()[-1])
        if data.get("status")!="NEW_QA_NUGET_RECEIPT_CREATED":
            raise ValueError("NEW_SQL_RECEIPT_MISSING")
        raw=receipt.read_bytes()
        if data["receipt_sha256"]!=sha256(raw).hexdigest() or data["case_sha256"]!=sha:
            raise ValueError("SQL_CASE_RECEIPT_BINDING_FAILED")
        body=json.loads(raw)
        if body.get("hand_source_sha256")!=sha256(SOURCE.read_bytes()).hexdigest():
            raise ValueError("WRONG_EXECUTED_SOURCE")
        if body.get("query_id")!="ITIL_2026_02_FEB100_CASE_EXACT_READ":
            raise ValueError("WRONG_QUERY_ID")
        if body.get("read_only") is not True or body.get("historical_solution_not_read") is not True:
            raise ValueError("UNSAFE_RECEIPT_CLAIM")
        return {"case_sha256":sha,"run_id":run_id,
            "state":"RECEIPT_READY",
            "receipt_sha256":sha256(raw).hexdigest(),
            "source_sha256":body["hand_source_sha256"],
            "read_only":True}
    except Exception as e:
        return {"case_sha256":sha,"run_id":run_id,
                "state":"RECEIPT_FAILED","error_type":type(e).__name__}

def main():
    rows=read_allowlist(ALLOW)
    if JOURNAL.exists() or ZIP.exists():raise FileExistsError("NO_OVERWRITE_BATCH")
    manifest=[json.loads(x) for x in MANIFEST.read_text().splitlines() if x.strip()]
    if not 1<=len(manifest)<=100 or len({r["case_sha256"] for r in manifest})!=len(manifest):
        raise ValueError("MANIFEST_CARDINALITY_INVALID")
    if not all(r["case_sha256"] in rows for r in manifest):
        raise ValueError("MODEL_CASE_NOT_IN_OWNER_ALLOWLIST")
    print(json.dumps({"sql_receipts_requested":len(manifest)}),flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future={pool.submit(single,row):row["case_sha256"] for row in manifest}
        with JOURNAL.open("x",encoding="utf-8") as out:
            for i,f in enumerate(as_completed(future),start=1):
                value=f.result()
                out.write(json.dumps(value,sort_keys=True)+"\n")
                out.flush()
                if i%10==0:os.fsync(out.fileno())
                print(json.dumps({"completed":i,"total":len(manifest),
                                  "status":value["state"]}),flush=True)
    result=[json.loads(x) for x in JOURNAL.read_text().splitlines()]
    good=[x for x in result if x["state"]=="RECEIPT_READY"]
    with zipfile.ZipFile(ZIP,mode="x",compression=zipfile.ZIP_STORED) as archive:
        for row in sorted(good,key=lambda x:x["run_id"]):
            file=RUNS/row["run_id"]/"receipt.private.json"
            archive.write(file,arcname=row["run_id"]+"/receipt.private.json")
    print(json.dumps({"receipts_ready":len(good),
          "receipts_failed":len(result)-len(good),
          "zip_sha256":sha256(ZIP.read_bytes()).hexdigest(),
          "journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest()}),flush=True)
if __name__=="__main__":main()

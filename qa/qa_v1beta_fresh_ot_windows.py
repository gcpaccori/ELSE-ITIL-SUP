"""Windows ELSE62 outbound-only fresh SAP/OT NuGet QA worker.

Pulls model-requested job IDs from the private cluster through SSH,
authorizes case SHA against February's fixed 100-case allowlist, verifies
the exact pinned C# source bytes, runs ONLY the prebuilt read-only DLL with
a uniquely reported OT taken from the allowlist (never model inputs), and
HMAC-authenticates the receipt before transferring it back privately.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import argparse,hmac,json,os,re,secrets,subprocess,sys
from qa_feb100_windows import read_allowlist,strict_json,canonical
REMOTE="u23u@elsecluster5"
REMOTE_ROOT="/home/u23u/else_itil_beta_fresh_qa_20261110"
LOCAL=Path(r"C:\Temp\ELSE_ITIL_BETA_FRESH_QA_20261110")
QA=Path(r"C:\Temp\ELSE_ITIL_FEB100_QA_20261110")
SOURCE=QA/"qa/Feb100SapOtRead.cs"
DLL=QA/"qa/bin/Release/net8.0/Feb100SapOtRead.dll"
ALLOW=QA/"feb100_allowlist.private.jsonl"
KEY=LOCAL/"worker_hmac.private"
JOBS=LOCAL/"jobs"
OUT=LOCAL/"outbox"
SOURCE_SHA="81c8da152f428c0d1c6273aa24d6ca4b01cbe4a2fedd17fcb1cefce41fc37be1"
QUERY="QA_DISTRIB_SAP_OT_EXACT_READ_V1"
HEX=re.compile(r"[0-9a-f]{64}\Z")
JOB=re.compile(r"[0-9a-f]{32}\Z")
OT=re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)"
              r"\s*[:#=-]?\s*(\d{4,19})\b",re.I)
SCHEMA="else.itil.beta.fresh-ot-job.v1"
DELIVERY="else.itil.beta.windows-fresh-sap-ot-delivery.v1"

def demand(ok,reason):
    if not ok:raise ValueError(reason)

def unique_ot(text):
    nums=set(OT.findall(text))
    demand(len(nums)==1,"OT_REPORTED_VALUE_NOT_UNIQUE")
    return next(iter(nums))

def ssh(command):
    cp=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=9",
                       REMOTE,command],capture_output=True,timeout=35)
    demand(cp.returncode==0,"PRIVATE_QA_REMOTE_LIST_FAILED")
    return cp.stdout

def scp(src,dst):
    cp=subprocess.run(["scp","-q","-o","BatchMode=yes",
                       "-o","ConnectTimeout=9",str(src),str(dst)],
                      capture_output=True,timeout=50)
    demand(cp.returncode==0,"PRIVATE_QA_COPY_FAILED")

def pull_names():
    # Fixed remote command; no shell content from model, case or operator.
    listing=ssh("find "+REMOTE_ROOT+
                "/requests -maxdepth 1 -type f -name '*.private.json' -printf '%f\\n'")
    entries=listing.decode("utf-8").splitlines()
    demand(len(entries)<=100,"REQUEST_BURST_LIMIT")
    result=[]
    for name in entries:
        demand(re.fullmatch(r"[0-9a-f]{32}\.private\.json",name) is not None,
               "UNKNOWN_REMOTE_REQUEST_FILE")
        result.append(name)
    return sorted(result)

def pull_remote_deliveries():
    listing=ssh("find "+REMOTE_ROOT+
                "/outbox -maxdepth 1 -type f -name '*.private.json' "
                "-printf '%f\\n'")
    entries=listing.decode("utf-8").splitlines()
    demand(len(entries)<=100,"DELIVERED_FILE_BURST_LIMIT")
    for name in entries:
        demand(re.fullmatch(r"[0-9a-f]{32}\.private\.json",name)
               is not None,"UNKNOWN_REMOTE_DELIVERY_FILE")
    return set(entries)


def validate_job(job,rows):
    demand(type(job) is dict and set(job)=={
        "schema","job_id","case_sha256","allowlist_row_sha256",
        "reported_ot_sha256","source_sha256","source_bytes",
        "tool_request_sha256","tool_request","query_id",
        "requested_utc","historical_solution_not_read","read_only",
        "business_join_certified","repair_certified"},
        "WINDOWS_JOB_UNEXPECTED_FIELDS")
    sha=job["case_sha256"]
    demand(job["schema"]==SCHEMA and
           type(sha) is str and HEX.fullmatch(sha) and sha in rows and
           type(job["job_id"]) is str and JOB.fullmatch(job["job_id"]),
           "WINDOWS_JOB_CASE_SCOPE_INVALID")
    row=rows[sha]
    ot=unique_ot(row["description_redacted"])
    demand(job["allowlist_row_sha256"]==sha256(canonical(row)).hexdigest() and
           job["reported_ot_sha256"]==sha256(ot.encode()).hexdigest(),
           "WINDOWS_JOB_ALLOWLIST_OT_HASH_MISMATCH")
    demand(job["source_sha256"]==SOURCE_SHA and
           job["source_bytes"]==len(SOURCE.read_bytes()) and
           sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA and
           DLL.is_file(),"WINDOWS_PREBUILT_PINNED_SOURCE_MISSING")
    tool=job["tool_request"]
    demand(type(tool) is dict and
           set(tool)=={"type","name","query_id","parameters"} and
           tool["type"]=="tool" and tool["name"]=="qa_sap_ot_exact_read" and
           tool["query_id"]==QUERY and
           type(tool["parameters"]) is dict and
           tool["parameters"]=={"case_sha256":sha} and
           sha256(canonical(tool)).hexdigest()==job["tool_request_sha256"] and
           job["query_id"]==QUERY,
           "WINDOWS_JOB_MODEL_TOOL_NOT_ALLOWED")
    demand(job["historical_solution_not_read"] is True and
           job["read_only"] is True and
           job["business_join_certified"] is False and
           job["repair_certified"] is False,
           "WINDOWS_JOB_FALSE_BUSINESS_CLAIM")
    return ot

def execute(job_path,rows,key):
    raw_job=job_path.read_bytes()
    job=strict_json(raw_job)
    job_id=job["job_id"]
    demand(job_path.name==job_id+".private.json",
           "WINDOWS_JOB_PATH_SCOPE_MISMATCH")
    ot=validate_job(job,rows)
    delivery_path=OUT/(job_id+".private.json")
    demand(not delivery_path.exists(),"NO_REISSUE_OF_FINISHED_JOB")
    cp=subprocess.run(["dotnet",str(DLL),ot],capture_output=True,timeout=80)
    demand(cp.returncode==0,"FIXED_NUGET_SAP_OT_QA_READ_FAILED")
    observation=strict_json(cp.stdout.splitlines()[-1])
    demand(observation.get("schema")==
           "else.itil.qa.feb100.sap-ot-readonly.v1" and
           observation.get("query_ids")==[
               "QA_DISTRIB_SAP_ORDER_BY_OT",
               "QA_DISTRIB_SAP_RESPONSE_BY_OT"] and
           observation.get("qa_target")=="ELSE70/dbDistribucion_D" and
           observation.get("sources")==[
               "dbo.taOrdenTrabajoSAP",
               "dbo.taOrdenTrabajoSAPEnvioRespuesta"] and
           observation.get("order_sha256")==sha256(ot.encode()).hexdigest() and
           observation.get("read_only") is True and
           observation.get("changes_executed") is False,
           "WINDOWS_NUGET_OBSERVATION_NOT_FIXED_QUERY")
    receipt={
        "schema":"else.itil.feb100.ot-sap-case-evidence.v1",
        "case_sha256":job["case_sha256"],
        "binding_provenance":"REPORTED_OT_FROM_REDACTED_CASE_TEXT_ONLY",
        "reported_ot_sha256":job["reported_ot_sha256"],
        "reader_source_sha256":SOURCE_SHA,
        "observation":observation,
        "read_only":True,"mutations":False,
        "functional_repair_certified":False,
        "root_cause_certified":False,
        "requires_technician_review":True,
    }
    raw_receipt=canonical(receipt)
    proof={
        "schema":DELIVERY,
        "job_id":job_id,"case_sha256":job["case_sha256"],
        "job_sha256":sha256(raw_job).hexdigest(),
        "receipt_sha256":sha256(raw_receipt).hexdigest(),
        "source_sha256":SOURCE_SHA,
        "completed_utc":datetime.now(timezone.utc).isoformat(),
        "receipt":receipt,
        "sql_executed_on_windows":True,
        "read_only":True,"repair_certified":False,
        "business_join_certified":False,
    }
    sig_msg=(DELIVERY+":"+job_id+":"+
             proof["job_sha256"]+":"+proof["receipt_sha256"]).encode()
    proof["hmac_sha256"]=hmac.new(key,sig_msg,"sha256").hexdigest()
    with delivery_path.open("xb") as f:f.write(canonical(proof))
    scp(delivery_path,REMOTE+":"+REMOTE_ROOT+"/outbox/"+delivery_path.name)
    return {"job_prefix":job_id[:12],"state":"NEW_WINDOWS_QA_SQL_READ_CREATED",
            "case_prefix":job["case_sha256"][:12],
            "order_found":observation["order_found"],
            "response_rows":observation["response_rows_up_to5"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--once",action="store_true",required=True)
    p.add_argument("--limit",type=int,default=100)
    args=p.parse_args()
    demand(1<=args.limit<=100,"WORKER_JOB_LIMIT_INVALID")
    LOCAL.mkdir(parents=True,exist_ok=True)
    JOBS.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    demand(KEY.is_file() and len(KEY.read_bytes())==32,
           "PRIVATE_WORKER_HMAC_KEY_MISSING")
    rows=read_allowlist(ALLOW)
    names=pull_names()
    delivered=pull_remote_deliveries()
    results=[]
    for name in names[:args.limit]:
        remote=REMOTE+":"+REMOTE_ROOT+"/requests/"+name
        dest=JOBS/name
        if not dest.exists():scp(remote,dest)
        elif not (OUT/name).exists():
            # A repeated request must be byte-identical; fetch to a temp
            # file to avoid trusting stale local copies.
            temp=JOBS/(name+".new")
            scp(remote,temp)
            demand(temp.read_bytes()==dest.read_bytes(),
                   "REMOTE_JOB_BYTES_CHANGED")
            temp.unlink()
        if (OUT/name).exists():
            # Only retransmit after a missing transfer, never overwrite
            # an already delivered receipt while QA is reading it.
            if name not in delivered:
                scp(OUT/name,REMOTE+":"+REMOTE_ROOT+"/outbox/"+name)
            continue
        try:
            report=execute(dest,rows,KEY.read_bytes())
        except Exception as exc:
            report={"job_prefix":name[:12],"state":"WINDOWS_JOB_REJECTED",
                    "error_type":type(exc).__name__,
                    "error_code":str(exc) if isinstance(exc,ValueError) else
                                 "WINDOWS_EXECUTION_FAILURE"}
        results.append(report)
        print(json.dumps(report,sort_keys=True),flush=True)
    new_count=sum(x["state"]=="NEW_WINDOWS_QA_SQL_READ_CREATED"
                  for x in results)
    # Ingest on the cluster immediately, from one fixed command. No job,
    # model or user text can affect the shell string.
    if names:
        ssh("cd /home/u23u/else_itil_beta_fresh_20261110 && "
            "PYTHONPATH=.:/home/u23u/elsecore_itil_janlast10_20261110/src "
            "/home/u23u/miniconda/envs/orquesta_py311/bin/python -m "
            "else_dominance.beta_fresh_ingest")
    print(json.dumps({"requests_seen":len(names),
                      "processed":len(results),
                      "reads_created":new_count,
                      "rejected":sum(x["state"]=="WINDOWS_JOB_REJECTED"
                      for x in results),
                      "cluster_ingest_invoked":bool(names)},
                      sort_keys=True),flush=True)

if __name__=="__main__":main()

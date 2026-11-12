"""ELSE62 QA operational OT read, SHA-bounded to the SAME five August jobs.

Fixed, new C# SELECT of dbo.taOrdenTrabajo by unique OT in the AUG
redacted request; never accepts SQL, OT, server, credentials from a model.
HMAC signed using private existing August read-worker secret, separate
delivery schema and separate verified source.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,hmac,os,re,subprocess

ROOT=Path(r"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110")
SOURCE=ROOT/"probe/AugOperationalOtRead.cs"
DLL=ROOT/"probe/bin/Release/net8.0/AugOperationalOtRead.dll"
REQUESTS=ROOT/"requests"
OUTBOX=ROOT/"operational_outbox"
KEY=ROOT/"worker_hmac.private"
REMOTE="u23u@elsecluster5"
TARGET="/home/u23u/else_itil_aug_domain_hand_qa_20261110/operational_outbox"
SOURCE_SHA="b6453fee7d6fa8bc4b953b3167074dc6fa6b15cccefd74ae93c740e37288eb00"
QUERY_ID="QA_DISTRIB_OPERATIONAL_OT_BY_CODE_V1"
SCHEMA="else.itil.aug2026.windows-operational-ot-delivery.v1"
OT_RE=re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)"
                 r"\s*[:#=-]?\s*(\d{4,19})\b",re.I)

def demand(cond,why):
    if not cond:raise ValueError(why)

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()

def parse(raw):
    def unique(items):
        obj={}
        for k,v in items:
            if k in obj:raise ValueError("DUPLICATE_JSON_PROPERTY")
            obj[k]=v
        return obj
    return json.loads(raw,object_pairs_hook=unique)

def main():
    OUTBOX.mkdir(exist_ok=True)
    demand(KEY.is_file() and len(KEY.read_bytes())==32,
           "NO_PRIVATE_WORKER_ATTESTATION_KEY")
    key=KEY.read_bytes()
    demand(SOURCE.is_file() and DLL.is_file() and
           sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA,
           "PINNED_OPERATIONAL_READER_MISSING")
    files=sorted(REQUESTS.glob("*.private.json"))
    demand(len(files)==5,"EXACT_FIVE_JOBS_REQUIRED")
    cohort=Path(r"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110\aug2026_blind_redacted.private.jsonl")
    manifest=Path(r"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110\aug2026_manifest.json")
    a=parse(manifest.read_bytes())
    raw=cohort.read_bytes()
    demand(a["blind_sha256"]==sha256(raw).hexdigest() and a["cases"]==1819,
           "WINDOWS_AUG_COHORT_CHANGED")
    cases={}
    for line in raw.splitlines():
        if line:
            item=parse(line);cases[item["ticket_sha256"]]=item
    summary=[]
    for file in files:
        job=parse(file.read_bytes())
        sha=job["case_sha256"]
        demand(sha in cases and job["cohort_sha256"]==a["blind_sha256"],
               "OP_CASE_NOT_IN_AUTHORIZED_COHORT")
        row=cases[sha]
        demand(job["case_row_sha256"]==sha256(canonical(row)).hexdigest()
               and job["redacted_ticket_sha256"]==
                   sha256(row["incident_text_redacted"].encode()).hexdigest(),
               "OP_CASE_SOURCE_DRIFT")
        candidates=set(OT_RE.findall(row["incident_text_redacted"]))
        demand(len(candidates)==1,"OP_OT_NOT_UNIQUE_IN_TEXT")
        ot=next(iter(candidates))
        demand(job["reported_ot_sha256"]==sha256(ot.encode()).hexdigest(),
               "OP_OT_NOT_BOUND_TO_TICKET")
        path=OUTBOX/file.name
        if not path.exists():
            exe=subprocess.run(["dotnet",str(DLL),ot],capture_output=True,timeout=90)
            demand(exe.returncode==0,"OP_QA_FIXED_NUGET_EXECUTION_FAILED")
            obs=parse(exe.stdout.splitlines()[-1])
            demand(obs["schema"]=="else.itil.aug2026.qa.operational-ot-readonly.v1"
               and obs["qa_target"]=="ELSE70/dbDistribucion_D"
               and obs["source"]=="dbo.taOrdenTrabajo"
               and obs["query_id"]==QUERY_ID
               and obs["order_sha256"]==sha256(ot.encode()).hexdigest()
               and obs["read_only"] is True and obs["changes_executed"] is False,
               "OP_RESULT_NOT_QA_SOURCE_BOUND")
            receipt={
                "schema":"else.itil.aug2026.operational-ot-receipt.v1",
                "case_sha256":sha,
                "reported_ot_sha256":job["reported_ot_sha256"],
                "reader_source_sha256":SOURCE_SHA,
                "observation":obs,
                "business_join_certified":False,
                "root_cause_certified":False,
                "repair_certified":False,
                "read_only":True,
            }
            envelope={
                "schema":SCHEMA,"job_id":job["job_id"],
                "case_sha256":sha,
                "job_sha256":sha256(file.read_bytes()).hexdigest(),
                "receipt_sha256":sha256(canonical(receipt)).hexdigest(),
                "source_sha256":SOURCE_SHA,
                "completed_utc":datetime.now(timezone.utc).isoformat(),
                "receipt":receipt,
                "read_only":True,"sql_executed_on_windows":True,
                "business_join_certified":False,"repair_certified":False,
            }
            message=(SCHEMA+":"+job["job_id"]+":"+
                envelope["job_sha256"]+":"+envelope["receipt_sha256"]).encode()
            envelope["hmac_sha256"]=hmac.new(key,message,"sha256").hexdigest()
            with path.open("xb") as f:f.write(canonical(envelope))
            state="OP_NEW_SQL_READ"
        else:state="OP_PREVIOUS_SQL_READ"
        r=subprocess.run(["scp","-q","-o","BatchMode=yes",
                          str(path),REMOTE+":"+TARGET+"/"+file.name],
                         capture_output=True,timeout=50)
        demand(r.returncode==0,"OP_PRIVATE_UPLOAD_FAILED")
        summary.append({"case_prefix":sha[:12],"state":state})
    print(json.dumps({"jobs":len(summary),
       "new_sql_reads":sum(x["state"]=="OP_NEW_SQL_READ" for x in summary),
       "read_only":True,"model_sql":False,"results":summary},sort_keys=True))
if __name__=="__main__":main()

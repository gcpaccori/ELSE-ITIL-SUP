"""ELSE62 exact read-only August SAP/OT QA worker (five scoped cases).

Uses prebuilt, byte-pinned .NET NuGet SELECT from original Feb QA reader.
Source August blind cohort must match original 1819-case Windows export SHA.
No arbitrary SQL/OT from model, no DML, no production mutation.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import hmac,json,os,re,secrets,subprocess,sys

ROOT=Path(r"C:\Temp\ELSE_ITIL_AUG_SAP_OT_HAND_QA_20261110")
AUG=Path(r"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110")
OLD=Path(r"C:\Temp\ELSE_ITIL_FEB100_QA_20261110")
SOURCE=OLD/"qa/Feb100SapOtRead.cs"
DLL=OLD/"qa/bin/Release/net8.0/Feb100SapOtRead.dll"
ORIGINAL=AUG/"aug2026_blind_redacted.private.jsonl"
MANIFEST=AUG/"aug2026_manifest.json"
KEY=ROOT/"worker_hmac.private"
REQUESTS=ROOT/"requests"
OUTBOX=ROOT/"outbox"
REMOTE="u23u@elsecluster5"
REMOTE_ROOT="/home/u23u/else_itil_aug_domain_hand_qa_20261110"
SCHEMA="else.itil.aug2026.fixed-sap-ot-request.v1"
DELIVERY="else.itil.aug2026.windows-sap-ot-delivery.v1"
SOURCE_SHA="81c8da152f428c0d1c6273aa24d6ca4b01cbe4a2fedd17fcb1cefce41fc37be1"
QUERY=["QA_DISTRIB_SAP_ORDER_BY_OT","QA_DISTRIB_SAP_RESPONSE_BY_OT"]
TABLES=["dbo.taOrdenTrabajoSAP","dbo.taOrdenTrabajoSAPEnvioRespuesta"]
HEX=re.compile(r"[a-f0-9]{64}\Z")
JOBID=re.compile(r"[a-f0-9]{32}\Z")
OT=re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)"
              r"\s*[:#=-]?\s*(\d{4,19})\b",re.I)

def demand(ok,reason):
    if not ok:raise ValueError(reason)

def canonical(d):
    return json.dumps(d,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()

def parse(raw):
    def keys(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError("DUPLICATE_JSON_KEY")
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=keys)

def ssh(command):
    r=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",
                      REMOTE,command],capture_output=True,timeout=35)
    demand(r.returncode==0,"PRIVATE_QA_SSH_UNAVAILABLE")
    return r.stdout

def scp(src,dst):
    r=subprocess.run(["scp","-q","-o","BatchMode=yes",
                      "-o","ConnectTimeout=10",str(src),str(dst)],
                     capture_output=True,timeout=45)
    demand(r.returncode==0,"PRIVATE_QA_SCP_UNAVAILABLE")

def get_cohort():
    manifest=parse(MANIFEST.read_bytes())
    raw=ORIGINAL.read_bytes()
    demand(manifest["blind_sha256"]==sha256(raw).hexdigest()
           and manifest["cases"]==1819
           and manifest["gold_shown_to_model"] is False,
           "AUG_WINDOWS_AUTHORITATIVE_SOURCE_CHANGED")
    items={}
    for line in raw.splitlines():
        if not line.strip():continue
        item=parse(line)
        ident=item["ticket_sha256"]
        demand(HEX.fullmatch(ident) is not None
               and ident not in items
               and item["month"]=="2026-08"
               and item["historical_resolution"]=="WITHHELD",
               "AUG_ALLOWLIST_ROW_INVALID")
        items[ident]=item
    demand(len(items)==1819,"AUG1819_NOT_EXACT")
    return items,manifest

def check_job(job,cohort,manifest):
    demand(type(job) is dict and set(job)=={
        "schema","job_id","case_sha256","case_row_sha256",
        "redacted_ticket_sha256","reported_ot_sha256",
        "source_sha256","source_bytes","cohort_sha256",
        "query_ids","sources","target","read_only",
        "sql_from_model","official_business_join_certified",
        "repair_certified"},"AUG_JOB_SCHEMA_REJECTED")
    sha=job["case_sha256"]
    demand(type(sha) is str and HEX.fullmatch(sha) is not None
           and sha in cohort
           and job["schema"]==SCHEMA
           and type(job["job_id"]) is str
           and JOBID.fullmatch(job["job_id"]) is not None,
           "AUG_CASE_NOT_EXACT_OWNER")
    row=cohort[sha]
    matches=set(OT.findall(row["incident_text_redacted"]))
    demand(len(matches)==1,"NO_SINGLE_EXPLICIT_OT")
    ot=next(iter(matches))
    expected_ident=sha256(("else.itil.aug2026.sap-ot-fixed:"+sha+
             ":"+manifest["blind_sha256"]).encode()).hexdigest()[:32]
    demand(job["job_id"]==expected_ident
           and job["case_row_sha256"]==sha256(canonical(row)).hexdigest()
           and job["redacted_ticket_sha256"]==
               sha256(row["incident_text_redacted"].encode()).hexdigest()
           and job["reported_ot_sha256"]==sha256(ot.encode()).hexdigest()
           and job["cohort_sha256"]==manifest["blind_sha256"],
           "AUG_TICKET_OT_PROVENANCE_FAILED")
    source=SOURCE.read_bytes()
    demand(job["source_sha256"]==SOURCE_SHA
           and sha256(source).hexdigest()==SOURCE_SHA
           and job["source_bytes"]==len(source)
           and DLL.is_file()
           and job["query_ids"]==QUERY
           and job["sources"]==TABLES
           and job["target"]=="ELSE70/dbDistribucion_D"
           and job["read_only"] is True
           and job["sql_from_model"] is False
           and job["official_business_join_certified"] is False
           and job["repair_certified"] is False,
           "FIXED_NUGET_QA_SCOPE_FAILED")
    return ot

def key_setup():
    if not KEY.exists():
        with KEY.open("xb") as f:f.write(secrets.token_bytes(32))
    demand(len(KEY.read_bytes())==32,"WORKER_HMAC_KEY_INVALID")
    # Lock down NTFS key ACL; no BUILTIN Users or inherited permissions.
    username=os.environ.get("USERDOMAIN","")+"\\"+os.environ.get("USERNAME","")
    r=subprocess.run(["icacls",str(KEY),"/inheritance:r","/grant:r",
                      username+":(F)","NT AUTHORITY\\SYSTEM:(F)",
                      "BUILTIN\\Administrators:(F)"],
                     capture_output=True,timeout=15)
    demand(r.returncode==0,"WORKER_HMAC_ACL_NOT_RESTRICTED")
    scp(KEY,REMOTE+":"+REMOTE_ROOT+"/worker_hmac.private")
    ssh("chmod 600 "+REMOTE_ROOT+"/worker_hmac.private")
    return KEY.read_bytes()

def execute(job_file,cohort,manifest,key):
    raw_job=job_file.read_bytes()
    job=parse(raw_job)
    ident=job["job_id"]
    demand(job_file.name==ident+".private.json","JOB_FILE_ID_DRIFT")
    ot=check_job(job,cohort,manifest)
    result_file=OUTBOX/job_file.name
    if result_file.exists():return "ALREADY_EXECUTED"
    r=subprocess.run(["dotnet",str(DLL),ot],capture_output=True,timeout=90)
    demand(r.returncode==0,"FIXED_NUGET_SQL_QA_EXECUTION_FAILED")
    obs=parse(r.stdout.splitlines()[-1])
    demand(obs["schema"]=="else.itil.qa.feb100.sap-ot-readonly.v1"
           and obs["query_ids"]==QUERY
           and obs["sources"]==TABLES
           and obs["qa_target"]=="ELSE70/dbDistribucion_D"
           and obs["order_sha256"]==sha256(ot.encode()).hexdigest()
           and obs["read_only"] is True
           and obs["changes_executed"] is False,
           "NUGET_OBSERVATION_DID_NOT_USE_FIXED_SOURCE")
    receipt={
        "schema":"else.itil.feb100.ot-sap-case-evidence.v1",
        "case_sha256":job["case_sha256"],
        "binding_provenance":"REPORTED_OT_FROM_REDACTED_CASE_TEXT_ONLY",
        "reported_ot_sha256":job["reported_ot_sha256"],
        "reader_source_sha256":SOURCE_SHA,
        "observation":obs,"read_only":True,"mutations":False,
        "functional_repair_certified":False,
        "root_cause_certified":False,
        "requires_technician_review":True,
    }
    raw_receipt=canonical(receipt)
    envelope={
        "schema":DELIVERY,"job_id":ident,
        "case_sha256":job["case_sha256"],
        "job_sha256":sha256(raw_job).hexdigest(),
        "receipt_sha256":sha256(raw_receipt).hexdigest(),
        "source_sha256":SOURCE_SHA,
        "completed_utc":datetime.now(timezone.utc).isoformat(),
        "receipt":receipt,
        "read_only":True,"sql_executed_on_windows":True,
        "business_join_certified":False,"repair_certified":False,
    }
    message=(DELIVERY+":"+ident+":"+envelope["job_sha256"]+":"+
             envelope["receipt_sha256"]).encode()
    envelope["hmac_sha256"]=hmac.new(key,message,"sha256").hexdigest()
    with result_file.open("xb") as f:f.write(canonical(envelope))
    return "WINDOWS_NEW_SQL_READ"

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    REQUESTS.mkdir(exist_ok=True)
    OUTBOX.mkdir(exist_ok=True)
    roster,manifest=get_cohort()
    key=key_setup()
    remote=ssh("find "+REMOTE_ROOT+
        "/requests -maxdepth 1 -type f -name '*.private.json' -printf '%f\\n'")
    names=remote.decode().splitlines()
    demand(len(names)==5,"REMOTE_AUG_JOB_COUNT_CHANGED")
    summary=[]
    for name in sorted(names):
        demand(re.fullmatch(r"[0-9a-f]{32}\.private\.json",name) is not None,
               "UNAUTHORIZED_REMOTE_JOB_NAME")
        path=REQUESTS/name
        remote_path=REMOTE+":"+REMOTE_ROOT+"/requests/"+name
        if not path.exists():scp(remote_path,path)
        # Immutable case job must not change between scheduled reads.
        cached=REQUESTS/(name+".temp")
        scp(remote_path,cached)
        demand(cached.read_bytes()==path.read_bytes(),"JOB_CHANGED_AFTER_FIRST_PULL")
        cached.unlink()
        job=parse(path.read_bytes())
        check_job(job,roster,manifest)
        state=execute(path,roster,manifest,key)
        dest=OUTBOX/name
        scp(dest,REMOTE+":"+REMOTE_ROOT+"/outbox/"+name)
        summary.append({"case_prefix":job["case_sha256"][:12],"state":state})
    print(json.dumps({"jobs":len(summary),"new_sql_reads":sum(
        x["state"]=="WINDOWS_NEW_SQL_READ" for x in summary),
        "no_sql_from_model":True,"read_only":True,
        "results":summary},sort_keys=True))

if __name__=="__main__":main()

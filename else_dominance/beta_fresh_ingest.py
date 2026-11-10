"""Ingest newly executed Windows SAP/OT QA receipts, with HMAC + native O5.

No blind trust in operator-supplied source fields. Exact case SHA,
tool request, OT hash, source SHA and Windows attestation must match.
Native O5/O13/O15 re-verifies the plain receipt before any model use.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
import hmac,json,re,os,shutil,tempfile
from .beta_fresh_ot import (
    validate_job,canonical,SOURCE_SHA,HEX,JOB)
from .qa_feb100_cluster import parse_strict
from qa.qa_feb100_windows import read_allowlist
from else_core.itil_feb100_sap_ot_o5_hand import (
    AuthorizedSapOtReceipt,build_sap_ot_router)
from else_core.hand_kernel import Outcome

DELIVERY="else.itil.beta.windows-fresh-sap-ot-delivery.v1"
PROOF="else.itil.beta.fresh-ot-o5-hmac-verified.v1"
ROOT=Path("/home/u23u/else_itil_beta_fresh_qa_20261110")
QA=Path("/home/u23u/else_itil_feb100_qa_20261110")
SOURCE=Path("/home/u23u/else_itil_beta_fresh_20261110/qa/Feb100SapOtRead.cs")

def demand(ok,reason):
    if not ok:raise ValueError(reason)

def utc(dt):
    return datetime.fromisoformat(dt.replace("Z","+00:00")).astimezone(timezone.utc)

def ingest_one(delivery_file:Path,*,key:bytes,roster:dict,
               verified_dir:Path=ROOT/"verified"):
    demand(delivery_file.is_file() and not delivery_file.is_symlink(),
           "DELIVERY_FILE_NOT_REGULAR")
    envelope=parse_strict(delivery_file.read_bytes())
    demand(type(envelope) is dict and set(envelope)=={
        "schema","job_id","case_sha256","job_sha256",
        "receipt_sha256","source_sha256","completed_utc",
        "receipt","sql_executed_on_windows","read_only",
        "repair_certified","business_join_certified","hmac_sha256"},
        "DELIVERY_FIELDS_UNEXPECTED")
    ident=envelope["job_id"]
    demand(type(ident) is str and JOB.fullmatch(ident) is not None and
           delivery_file.name==ident+".private.json",
           "DELIVERY_IDENTITY_NOT_BOUND")
    job_path=ROOT/"requests"/delivery_file.name
    demand(job_path.is_file() and not job_path.is_symlink(),
           "AUTHORITATIVE_REQUEST_MISSING")
    raw_job=job_path.read_bytes()
    job=parse_strict(raw_job)
    demand(envelope["schema"]==DELIVERY and
           envelope["source_sha256"]==SOURCE_SHA and
           envelope["case_sha256"]==job["case_sha256"] and
           envelope["job_sha256"]==sha256(raw_job).hexdigest() and
           envelope["sql_executed_on_windows"] is True and
           envelope["read_only"] is True and
           envelope["repair_certified"] is False and
           envelope["business_join_certified"] is False,
           "DELIVERY_OWNER_OR_SOURCE_DRIFT")
    demand(envelope["receipt_sha256"]==
           sha256(canonical(envelope["receipt"])).hexdigest(),
           "FRESH_RECEIPT_SHA_NOT_BOUND")
    signature=(DELIVERY+":"+ident+":"+
               envelope["job_sha256"]+":"+envelope["receipt_sha256"]).encode()
    expected=hmac.new(key,signature,"sha256").hexdigest()
    demand(type(envelope["hmac_sha256"]) is str and
           hmac.compare_digest(expected,envelope["hmac_sha256"]),
           "WINDOWS_HMAC_ATTESTATION_INVALID")
    validate_job(job,roster,SOURCE.read_bytes())
    obs=envelope["receipt"]["observation"]
    start=utc(job["requested_utc"])
    read_time=utc(obs["read_utc"])
    finish=utc(envelope["completed_utc"])
    demand(start-timedelta(seconds=45)<=read_time<=finish+
           timedelta(seconds=45),"FRESH_WINDOWS_SQL_TIME_BEFORE_REQUEST")
    demand(envelope["receipt"]["case_sha256"]==job["case_sha256"] and
           envelope["receipt"]["reported_ot_sha256"]==
           job["reported_ot_sha256"],"FRESH_CASE_OT_HASH_NOT_BOUND")
    verified_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    final=verified_dir/ident
    demand(not final.exists(),"FRESH_RECEIPT_JOB_ALREADY_INGESTED")
    # Never publish a partially verified receipt. Guardian and Dominance
    # operate on a private staging directory; rename only after PASS.
    stage_parent=verified_dir.parent/"staging"
    stage_parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    stage=Path(tempfile.mkdtemp(prefix=ident+"-",dir=stage_parent))
    try:
        path=stage/"receipt.private.json"
        with path.open("xb") as f:
            f.write(canonical(envelope["receipt"]))
        path.chmod(0o600)
        owner=AuthorizedSapOtReceipt(
            path,envelope["receipt_sha256"],job["case_sha256"],
            SOURCE_SHA,len(SOURCE.read_bytes()),
            roster[job["case_sha256"]]["description_redacted"])
        _,router,operation=build_sap_ot_router(owner)
        result=router.route(operation)
        demand(result.outcome==Outcome.PASS and
               result.guardian_result.verification.passed is True and
               result.guardian_result.verification.independent is True and
               result.guardian_result.executions==1,
               "NATIVE_O5_O13_O15_FRESH_RECEIPT_REJECTED")
        values=result.guardian_result.value.outputs
        demand(values["business_entity_join_certified"] is False and
               values["repair_certified"] is False,
               "FRESH_EVIDENCE_FALSE_BUSINESS_CLAIM")
        proof={
        "schema":PROOF,"job_id":ident,
        "case_sha256":job["case_sha256"],
        "job_sha256":envelope["job_sha256"],
        "windows_delivery_sha256":sha256(delivery_file.read_bytes()).hexdigest(),
        "hmac_attested":True,
        "fresh_read_started_utc":obs["read_utc"],
        "sap_receipt_sha256":envelope["receipt_sha256"],
        "source_sha256":SOURCE_SHA,
        "read_only":True,
        "o5_o13_o15_verified":True,
        "order_found":values["order_found"],
        "official_itil_ot_join_verified":False,
        "role_authorized":False,
        "repairs_certified":False,
    }
        audit=stage/"verified_receipt.private.json"
        with audit.open("xb") as f:f.write(canonical(proof))
        audit.chmod(0o600)
        demand(not final.exists(),"FRESH_RACE_DUPLICATE_JOB_ID")
        os.rename(stage,final)
        return proof
    except BaseException:
        if stage.exists():shutil.rmtree(stage)
        raise

def main():
    from collections import Counter
    keyfile=ROOT/"worker_hmac.private"
    demand(keyfile.is_file() and not keyfile.is_symlink() and
           keyfile.stat().st_mode&0o077==0,"QA_HMAC_KEY_PERMISSIONS_INVALID")
    key=keyfile.read_bytes()
    demand(len(key)==32,"QA_HMAC_KEY_INVALID")
    roster=read_allowlist(QA/"feb100_allowlist.private.jsonl")
    processed=[]
    for file in sorted((ROOT/"outbox").glob("*.private.json")):
        if (ROOT/"verified"/file.name[:-13]).exists():
            continue
        try:
            result=ingest_one(file,key=key,roster=roster)
            processed.append({"job_prefix":result["job_id"][:12],
                "state":"NATIVE_O5_HMAC_VERIFIED","order_found":result["order_found"]})
        except Exception as exc:
            processed.append({"job_prefix":file.name[:12],
                "state":"INGEST_REJECTED","error_type":type(exc).__name__,
                "error_code":str(exc) if isinstance(exc,ValueError) else
                             "NATIVE_VERIFICATION_FAILED"})
    print(json.dumps({
        "processed":len(processed),
        "native_verified":sum(x["state"]=="NATIVE_O5_HMAC_VERIFIED" for x in processed),
        "errors":[x for x in processed if x["state"]!="NATIVE_O5_HMAC_VERIFIED"],
    },sort_keys=True))

if __name__=="__main__":main()

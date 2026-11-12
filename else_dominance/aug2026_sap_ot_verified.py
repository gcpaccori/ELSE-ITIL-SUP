"""August 2026 QA: exact, operator-bounded SAP/OT read with native CORE proof.

**Important:** Reuses the February fixed reader & legacy CORE receipt schema
because the SQL query is byte-identical. The workflow itself is August
cohort-bound; we never claim the legacy Hand was originally designed for
August. No business-key ITIL↔OT join or repair is certified.

- 1819 immutable August redacted cases, but only unique explicit OT eligible.
- Windows ELSE62 alone executes .NET NuGet fixed SELECT to ELSE70.
- Windows HMAC attests delivery; independently replay native O5/O13/O15.
- Receipt published atomically after PASS. No model-defined query or OT.
"""
from __future__ import annotations

from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import hmac,json,os,re,shutil,tempfile

from .functional_domain_v2 import route
from .qa_feb100_ot_evidence import extract_unique_reported_ot
from .qa_feb100_cluster import parse_strict
from .beta_fresh_ot import SOURCE_SHA

ROOT=Path("/home/u23u/else_itil_aug_domain_hand_qa_20261110")
QA=Path("/home/u23u/else_itil_aug2026_qa_20261110")
SOURCE=Path("/home/u23u/else_itil_aug_domain_hand_20261110/qa/Feb100SapOtRead.cs")
SCHEMA="else.itil.aug2026.fixed-sap-ot-request.v1"
DELIVERY="else.itil.aug2026.windows-sap-ot-delivery.v1"
PROOF="else.itil.aug2026.sap-ot-o5-verified.v1"
HEX=re.compile(r"[0-9a-f]{64}\Z")
JOB=re.compile(r"[0-9a-f]{32}\Z")
QUERIES=["QA_DISTRIB_SAP_ORDER_BY_OT","QA_DISTRIB_SAP_RESPONSE_BY_OT"]
TABLES=["dbo.taOrdenTrabajoSAP","dbo.taOrdenTrabajoSAPEnvioRespuesta"]
MAX_JOBS=5

def demand(c,why):
    if not c:raise ValueError(why)

def canonical(v):
    return json.dumps(v,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode()

def data():
    manifest=parse_strict((QA/"aug2026_manifest.json").read_bytes())
    raw=(QA/"aug2026_blind_redacted.private.jsonl").read_bytes()
    demand(manifest["cases"]==1819 and
           manifest["blind_sha256"]==sha256(raw).hexdigest() and
           manifest["gold_shown_to_model"] is False,
           "AUGUST_SOURCE_DIGEST_NOT_AUTHORITATIVE")
    cohort={}
    for line in raw.splitlines():
        if not line.strip():continue
        item=parse_strict(line)
        sha=item["ticket_sha256"]
        demand(type(sha) is str and HEX.fullmatch(sha) is not None
               and sha not in cohort and item["month"]=="2026-08" and
               item["historical_resolution"]=="WITHHELD",
               "AUG_ROW_SCHEMA_OR_MONTH_INVALID")
        cohort[sha]=item
    demand(len(cohort)==1819,"AUG1819_NOT_EXACT")
    return cohort,manifest

def eligible(cohort):
    found={}
    for sha,row in cohort.items():
        ot=extract_unique_reported_ot(row["incident_text_redacted"])
        if ot is not None and route(row["incident_text_redacted"])["domain"]=="COMMERCIAL_OT":
            found[sha]=ot
    demand(len(found)==MAX_JOBS,"AUG_EXACT_OT_ELIGIBLE_SET_DRIFT")
    return found

def job_for(sha,row,manifest,ot):
    raw=SOURCE.read_bytes()
    demand(sha256(raw).hexdigest()==SOURCE_SHA,"FIXED_CSHARP_SOURCE_CHANGED")
    digest=sha256(("else.itil.aug2026.sap-ot-fixed:"+sha+":"+
                   manifest["blind_sha256"]).encode()).hexdigest()
    return {
        "schema":SCHEMA,"job_id":digest[:32],"case_sha256":sha,
        "case_row_sha256":sha256(canonical(row)).hexdigest(),
        "redacted_ticket_sha256":sha256(row["incident_text_redacted"].encode()).hexdigest(),
        "reported_ot_sha256":sha256(ot.encode()).hexdigest(),
        "source_sha256":SOURCE_SHA,"source_bytes":len(raw),
        "cohort_sha256":manifest["blind_sha256"],
        "query_ids":QUERIES,"sources":TABLES,
        "target":"ELSE70/dbDistribucion_D",
        "read_only":True,"sql_from_model":False,
        "official_business_join_certified":False,
        "repair_certified":False,
    }

def validate_job(job,cohort,manifest):
    demand(type(job) is dict and set(job)==set(job_for(
        next(iter(eligible(cohort))),cohort[next(iter(eligible(cohort)))],
        manifest,eligible(cohort)[next(iter(eligible(cohort)))])),
        "AUG_JOB_SCHEMA_INVALID")
    sha=job["case_sha256"]
    valid=eligible(cohort)
    demand(sha in valid,"AUG_SHA_NOT_ELIGIBLE")
    expect=job_for(sha,cohort[sha],manifest,valid[sha])
    demand(job==expect and JOB.fullmatch(job["job_id"]) is not None,
           "AUG_JOB_SOURCE_CASE_OR_TOOL_BINDING_DRIFT")
    return valid[sha]

def prepare():
    cohort,manifest=data()
    found=eligible(cohort)
    requests=ROOT/"requests"
    requests.mkdir(mode=0o700,parents=True,exist_ok=True)
    pending=[]
    for sha,ot in sorted(found.items()):
        job=job_for(sha,cohort[sha],manifest,ot)
        file=requests/(job["job_id"]+".private.json")
        raw=canonical(job)
        if file.exists():
            demand(file.read_bytes()==raw and not file.is_symlink(),
                   "EXISTING_JOB_BYTES_DIFFER")
        else:
            with file.open("xb") as f:f.write(raw)
            file.chmod(0o600)
        pending.append({"case_sha_prefix":sha[:12],"job_prefix":job["job_id"][:12],
                        "domain":"COMMERCIAL_OT"})
    return {"scheduled":len(pending),"source":"ELSE70/dbDistribucion_D",
            "model_defined_sql":False,"read_only":True,
            "cases":pending}

def ingest_one(file:Path,*,key:bytes,cohort,manifest):
    from else_core.itil_feb100_sap_ot_o5_hand import (
        AuthorizedSapOtReceipt,build_sap_ot_router)
    from else_core.hand_kernel import Outcome
    demand(file.is_file() and not file.is_symlink(),"DELIVERY_NOT_FILE")
    envelope=parse_strict(file.read_bytes())
    demand(type(envelope) is dict and set(envelope)=={
        "schema","job_id","case_sha256","job_sha256","receipt_sha256",
        "source_sha256","completed_utc","receipt",
        "read_only","sql_executed_on_windows","business_join_certified",
        "repair_certified","hmac_sha256"},
        "ENVELOPE_FIELDS_UNEXPECTED")
    ident=envelope["job_id"]
    demand(type(ident) is str and JOB.fullmatch(ident) is not None
           and file.name==ident+".private.json",
           "DELIVERY_JOB_NAME_MISMATCH")
    job_file=ROOT/"requests"/file.name
    demand(job_file.is_file() and not job_file.is_symlink(),"OWNER_JOB_NOT_FOUND")
    raw_job=job_file.read_bytes()
    job=parse_strict(raw_job)
    ot=validate_job(job,cohort,manifest)
    demand(job["job_id"]==ident and envelope["schema"]==DELIVERY
           and envelope["case_sha256"]==job["case_sha256"] and
           envelope["job_sha256"]==sha256(raw_job).hexdigest()
           and envelope["source_sha256"]==SOURCE_SHA
           and envelope["read_only"] is True
           and envelope["sql_executed_on_windows"] is True
           and envelope["business_join_certified"] is False
           and envelope["repair_certified"] is False,
           "DELIVERY_SCOPE_OR_EXECUTION_MISMATCH")
    receipt=envelope["receipt"]
    raw_receipt=canonical(receipt)
    demand(envelope["receipt_sha256"]==sha256(raw_receipt).hexdigest(),
           "RECEIPT_BYTES_NOT_PINNED")
    message=(DELIVERY+":"+ident+":"+
             envelope["job_sha256"]+":"+envelope["receipt_sha256"]).encode()
    demand(type(envelope["hmac_sha256"]) is str and
           hmac.compare_digest(hmac.new(key,message,"sha256").hexdigest(),
                               envelope["hmac_sha256"]),
           "WINDOWS_HMAC_ATTESTATION_FAILED")
    from .beta_fresh_ingest import utc
    obs=receipt["observation"]
    demand(utc(obs["read_utc"])<=utc(envelope["completed_utc"])+timedelta(minutes=1),
           "WINDOWS_SQL_READ_AFTER_ATTESTED_DELIVERY")
    # Linux server-side timestamp limits replay to delivery not older than
    # fixed campaign start; time skew Windows↔Linux never grants trust.
    demand(file.stat().st_mtime>=1730000000,"STAGING_FILE_TIMESTAMP_INVALID")
    demand(receipt["case_sha256"]==job["case_sha256"] and
           receipt["reported_ot_sha256"]==job["reported_ot_sha256"] and
           receipt["reader_source_sha256"]==SOURCE_SHA,
           "OWNER_OT_READER_MISMATCH")
    demand(len(key)==32,"ATTESTATION_SECRET_INVALID")
    folder=ROOT/"verified"/ident
    demand(not folder.exists(),"NO_DUPLICATE_NATIVE_RECEIPT")
    stage_root=ROOT/"staging"
    stage_root.mkdir(mode=0o700,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix=ident+"-",dir=stage_root))
    try:
        p=stage/"receipt.private.json"
        with p.open("xb") as f:f.write(raw_receipt)
        p.chmod(0o600)
        owner=AuthorizedSapOtReceipt(
            p,envelope["receipt_sha256"],job["case_sha256"],
            SOURCE_SHA,len(SOURCE.read_bytes()),
            cohort[job["case_sha256"]]["incident_text_redacted"])
        _,router,operation=build_sap_ot_router(owner)
        result=router.route(operation)
        demand(result.outcome==Outcome.PASS and
               result.guardian_result.verification.passed is True
               and result.guardian_result.verification.independent is True
               and result.guardian_result.executions==1,
               "CORE_O5_O13_O15_REJECTED")
        values=result.guardian_result.value.outputs
        demand(values["business_entity_join_certified"] is False
               and values["repair_certified"] is False,
               "UNAUTHORIZED_BUSINESS_JOIN_OR_REPAIR_CLAIM")
        proof={
            "schema":PROOF,"job_id":ident,"case_sha256":job["case_sha256"],
            "source_ticket_row_sha256":job["case_row_sha256"],
            "job_sha256":envelope["job_sha256"],
            "source_sha256":SOURCE_SHA,
            "delivery_sha256":sha256(file.read_bytes()).hexdigest(),
            "sap_receipt_sha256":envelope["receipt_sha256"],
            "o5_o13_o15_verified":True,
            "windows_hmac_attested":True,
            "order_found_in_specific_table":values["order_found"],
            "order_state_code":values["order_state_code"],
            "response_rows_up_to5":values["response_rows_up_to5"],
            "sql_executed_on_windows":True,
            "read_only":True,"official_itil_ot_business_join_certified":False,
            "repair_certified":False,"current_business_root_cause_certified":False,
        }
        proof_file=stage/"verified_receipt.private.json"
        with proof_file.open("xb") as f:f.write(canonical(proof))
        proof_file.chmod(0o600)
        os.rename(stage,folder)
        return proof
    except BaseException:
        if stage.exists():shutil.rmtree(stage)
        raise

def ingest():
    cohort,manifest=data()
    keyfile=ROOT/"worker_hmac.private"
    demand(keyfile.is_file() and not keyfile.is_symlink()
           and keyfile.stat().st_mode&0o077==0,"SECRET_PERMISSIONS_INVALID")
    key=keyfile.read_bytes()
    demand(len(key)==32,"BAD_HMAC_SECRET")
    good=[];failed=[]
    for file in sorted((ROOT/"outbox").glob("*.private.json")):
        ident=file.name[:32]
        if (ROOT/"verified"/ident/"verified_receipt.private.json").exists():
            continue
        try:
            proof=ingest_one(file,key=key,cohort=cohort,manifest=manifest)
            good.append({"case_prefix":proof["case_sha256"][:12],
                         "order_found":proof["order_found_in_specific_table"]})
        except Exception as exc:
            failed.append({"job_prefix":ident[:12],"error":str(exc)[:100]})
    return {"new_verified":len(good),"new_rejected":len(failed),
            "verified":good,"failures":failed}

def verify_case(sha:str):
    cohort,manifest=data()
    demand(sha in eligible(cohort),"CASE_NOT_ELIGIBLE_FOR_EXACT_OT")
    candidate=job_for(sha,cohort[sha],manifest,eligible(cohort)[sha])
    ident=candidate["job_id"]
    job_file=ROOT/"requests"/(ident+".private.json")
    delivery=ROOT/"outbox"/(ident+".private.json")
    proof_file=ROOT/"verified"/ident/"verified_receipt.private.json"
    for file in (job_file,delivery,proof_file,
                 ROOT/"verified"/ident/"receipt.private.json"):
        demand(file.is_file() and not file.is_symlink(),
               "NATIVE_PROOF_OR_OWNER_REQUIRED")
    demand(parse_strict(job_file.read_bytes())==candidate,"OWNER_JOB_CHANGED")
    key=(ROOT/"worker_hmac.private").read_bytes()
    envelope=parse_strict(delivery.read_bytes())
    signature=(DELIVERY+":"+ident+":"+envelope["job_sha256"]+":"+
               envelope["receipt_sha256"]).encode()
    demand(hmac.compare_digest(
          hmac.new(key,signature,"sha256").hexdigest(),
          envelope["hmac_sha256"]),"HMAC_CHANGED")
    proof=parse_strict(proof_file.read_bytes())
    demand(proof["schema"]==PROOF
           and proof["job_id"]==ident and proof["case_sha256"]==sha
           and proof["source_ticket_row_sha256"]==candidate["case_row_sha256"]
           and proof["job_sha256"]==sha256(job_file.read_bytes()).hexdigest()
           and proof["delivery_sha256"]==sha256(delivery.read_bytes()).hexdigest()
           and proof["sap_receipt_sha256"]==envelope["receipt_sha256"]
           and proof["windows_hmac_attested"] is True
           and proof["o5_o13_o15_verified"] is True
           and proof["read_only"] is True
           and proof["official_itil_ot_business_join_certified"] is False
           and proof["repair_certified"] is False,
           "NATIVE_PROOF_DATA_DRIFT")
    # Replay exact independent O5 for the read itself, not just a bool.
    from else_core.itil_feb100_sap_ot_o5_hand import (
        AuthorizedSapOtReceipt,build_sap_ot_router)
    from else_core.hand_kernel import Outcome
    receipt_file=ROOT/"verified"/ident/"receipt.private.json"
    demand(sha256(receipt_file.read_bytes()).hexdigest()==
           envelope["receipt_sha256"] and
           canonical(envelope["receipt"])==receipt_file.read_bytes(),
           "ORIGINAL_RECEIPT_CHANGED")
    owner=AuthorizedSapOtReceipt(receipt_file,proof["sap_receipt_sha256"],sha,
             SOURCE_SHA,len(SOURCE.read_bytes()),
             cohort[sha]["incident_text_redacted"])
    _,router,operation=build_sap_ot_router(owner)
    result=router.route(operation)
    demand(result.outcome==Outcome.PASS
           and result.guardian_result.verification.passed is True
           and result.guardian_result.verification.independent is True,
           "REPLAY_NATIVE_O5_NOT_VERIFIED")
    values=result.guardian_result.value.outputs
    demand(values["order_found"]==proof["order_found_in_specific_table"]
           and values["order_state_code"]==proof["order_state_code"]
           and values["response_rows_up_to5"]==proof["response_rows_up_to5"],
           "HAND_OUTPUT_DRIFT")
    return {
       "schema":"else.itil.aug2026.domain-evidence-context.v1",
       "case_sha256":sha,"domain":"COMMERCIAL_OT",
       "target_system":"ELSE70/dbDistribucion_D SAP/OT",
       "reported_ot_sha256":candidate["reported_ot_sha256"],
       "observed_ticket_source":"ITIL.taIncidente",
       "verified_domain_sources":TABLES,
       "observation":{"order_found_in_specific_table":values["order_found"],
                      "order_state_code":values["order_state_code"],
                      "response_rows_up_to5":values["response_rows_up_to5"],
                      "sap_number_present":values["sap_number_present"]},
       "sap_o5_receipt_sha256":proof["sap_receipt_sha256"],
       "source_ticket_row_sha256":proof["source_ticket_row_sha256"],
       "o5_o13_o15_verified":True,
       "sql_fresh_read_on_windows":True,
       "official_itil_ot_business_join_verified":False,
       "repair_certified":False,
    }

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["prepare","ingest","check"])
    p.add_argument("--case-sha")
    a=p.parse_args()
    if a.command=="prepare":print(json.dumps(prepare()))
    elif a.command=="ingest":print(json.dumps(ingest()))
    else:print(json.dumps(verify_case(a.case_sha)))

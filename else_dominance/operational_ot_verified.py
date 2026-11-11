"""Independently verify Windows QA operational OT read receipts (five August).

Separate from SAP O5 Hand: different source dbo.taOrdenTrabajo and
independently pinned C# NuGet SELECT. A HMAC-bound receipt does not
mean the ITIL↔OT corporate relationship was established.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
import hmac,json,re,os,shutil,tempfile

from .aug2026_sap_ot_verified import (
    ROOT,data,eligible,job_for,validate_job,canonical,demand,verify_case)
from .qa_feb100_cluster import parse_strict

SOURCE=Path("/home/u23u/else_itil_aug_domain_hand_20261110/qa/AugOperationalOtRead.cs")
SOURCE_SHA="b6453fee7d6fa8bc4b953b3167074dc6fa6b15cccefd74ae93c740e37288eb00"
DELIVERY="else.itil.aug2026.windows-operational-ot-delivery.v1"
RECEIPT="else.itil.aug2026.operational-ot-receipt.v1"
OBS="else.itil.aug2026.qa.operational-ot-readonly.v1"
PROOF="else.itil.aug2026.operational-ot-hmac-verified.v1"
QUERY="QA_DISTRIB_OPERATIONAL_OT_BY_CODE_V1"
FIELDS={
    "schema","qa_target","source","query_id","order_sha256",
    "order_rows","order_found",
    "codigo_estado_orden_trabajo","codigo_clase_orden_trabajo",
    "codigo_tipo_orden_trabajo","codigo_subtipo_orden_trabajo",
    "fecha_elaboracion_present","fecha_inicio_present",
    "fecha_fin_present","read_only","changes_executed","read_utc"}
HEX32=re.compile(r"[0-9a-f]{32}\Z")
HEX64=re.compile(r"[0-9a-f]{64}\Z")

def utc(value):
    return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+",r"\1",value.replace("Z","+00:00"))).astimezone(timezone.utc)

def validate_one(path:Path,*,key:bytes,cohort,manifest):
    demand(path.is_file() and not path.is_symlink(),"OP_DELIVERY_FILE_INVALID")
    envelope=parse_strict(path.read_bytes())
    demand(type(envelope) is dict and set(envelope)=={
        "schema","job_id","case_sha256","job_sha256","receipt_sha256",
        "source_sha256","completed_utc","receipt","read_only",
        "sql_executed_on_windows","business_join_certified",
        "repair_certified","hmac_sha256"},
        "OP_DELIVERY_SCHEMA_INVALID")
    jobid=envelope["job_id"]
    demand(type(jobid) is str and HEX32.fullmatch(jobid) is not None
           and path.name==jobid+".private.json",
           "OP_DELIVERY_NOT_EXACT_JOB")
    req=ROOT/"requests"/path.name
    demand(req.is_file() and not req.is_symlink(),"OP_OWNER_JOB_MISSING")
    job=parse_strict(req.read_bytes())
    validate_job(job,cohort,manifest)
    demand(job["job_id"]==jobid and
           envelope["schema"]==DELIVERY
           and envelope["case_sha256"]==job["case_sha256"]
           and envelope["job_sha256"]==sha256(req.read_bytes()).hexdigest()
           and envelope["source_sha256"]==SOURCE_SHA
           and envelope["read_only"] is True
           and envelope["sql_executed_on_windows"] is True
           and envelope["repair_certified"] is False
           and envelope["business_join_certified"] is False,
           "OP_DELIVERY_OWNER_OR_SOURCE_DRIFT")
    demand(sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
           and len(key)==32,"OP_READER_CODE_OR_HMAC_KEY_CHANGED")
    raw_receipt=canonical(envelope["receipt"])
    demand(envelope["receipt_sha256"]==sha256(raw_receipt).hexdigest(),
           "OP_RECEIPT_NOT_BOUND_TO_SIGNATURE")
    msg=(DELIVERY+":"+jobid+":"+envelope["job_sha256"]+":"+
         envelope["receipt_sha256"]).encode()
    demand(type(envelope["hmac_sha256"]) is str
           and hmac.compare_digest(hmac.new(key,msg,"sha256").hexdigest(),
                                   envelope["hmac_sha256"]),
           "OP_WINDOWS_HMAC_REJECTED")
    receipt=envelope["receipt"]
    demand(type(receipt) is dict and set(receipt)=={
        "schema","case_sha256","reported_ot_sha256",
        "reader_source_sha256","observation","business_join_certified",
        "root_cause_certified","repair_certified","read_only"},
        "OP_RECEIPT_FIELDS_INVALID")
    demand(receipt["schema"]==RECEIPT
           and receipt["case_sha256"]==job["case_sha256"]
           and receipt["reported_ot_sha256"]==job["reported_ot_sha256"]
           and receipt["reader_source_sha256"]==SOURCE_SHA
           and receipt["business_join_certified"] is False
           and receipt["root_cause_certified"] is False
           and receipt["repair_certified"] is False
           and receipt["read_only"] is True,
           "OP_RECEIPT_FALSE_BUSINESS_CLAIM")
    obs=receipt["observation"]
    demand(type(obs) is dict and set(obs)==FIELDS
           and obs["schema"]==OBS
           and obs["qa_target"]=="ELSE70/dbDistribucion_D"
           and obs["source"]=="dbo.taOrdenTrabajo"
           and obs["query_id"]==QUERY
           and obs["order_sha256"]==job["reported_ot_sha256"]
           and type(obs["order_rows"]) is int
           and obs["order_rows"] in (0,1)
           and type(obs["order_found"]) is bool
           and obs["order_found"]==(obs["order_rows"]==1)
           and obs["read_only"] is True
           and obs["changes_executed"] is False,
           "OP_OBSERVATION_SOURCE_OR_ROW_INVALID")
    for field in ("fecha_elaboracion_present","fecha_inicio_present",
                  "fecha_fin_present"):
        demand(type(obs[field]) is bool and
               (obs["order_found"] or obs[field] is False),
               "OP_TIMESTAMP_BOOL_MISMATCH")
    for field in ("codigo_estado_orden_trabajo",
                  "codigo_clase_orden_trabajo",
                  "codigo_tipo_orden_trabajo",
                  "codigo_subtipo_orden_trabajo"):
        demand(type(obs[field]) is str and len(obs[field])<=100
               and (obs["order_found"] or obs[field]==""),
               "OP_STATE_CODE_NOT_FROM_ROW")
    demand(utc(obs["read_utc"])<=utc(envelope["completed_utc"])+timedelta(minutes=1),
           "OP_WINDOWS_READ_AFTER_SIGNED_DELIVERY")
    return {"job":job,"envelope":envelope,
            "receipt_bytes":raw_receipt,"observation":obs}

def ingest():
    cohort,manifest=data()
    keyfile=ROOT/"worker_hmac.private"
    demand(keyfile.is_file() and not keyfile.is_symlink()
           and keyfile.stat().st_mode&0o077==0,
           "OP_SECRET_ACL_UNSAFE")
    key=keyfile.read_bytes()
    demand(len(key)==32,"OP_SECRET_MISSING")
    out=[]
    for file in sorted((ROOT/"operational_outbox").glob("*.private.json")):
        ident=file.name[:32]
        final=ROOT/"operational_verified"/ident
        if final.exists():continue
        item=validate_one(file,key=key,cohort=cohort,manifest=manifest)
        parent=ROOT/"operational_staging"
        parent.mkdir(mode=0o700,exist_ok=True)
        tmp=Path(tempfile.mkdtemp(prefix=ident+"-",dir=parent))
        try:
            receipt=tmp/"receipt.private.json"
            with receipt.open("xb") as f:f.write(item["receipt_bytes"])
            receipt.chmod(0o600)
            proof={
              "schema":PROOF,
              "job_id":ident,
              "case_sha256":item["job"]["case_sha256"],
              "case_row_sha256":item["job"]["case_row_sha256"],
              "source_sha256":SOURCE_SHA,
              "job_sha256":item["envelope"]["job_sha256"],
              "delivery_sha256":sha256(file.read_bytes()).hexdigest(),
              "receipt_sha256":item["envelope"]["receipt_sha256"],
              "hmac_verified":True,
              "independent_receipt_fields_verified":True,
              "source":"ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo",
              "order_found":item["observation"]["order_found"],
              "operational_state_code":
                  item["observation"]["codigo_estado_orden_trabajo"],
              "read_only":True,
              "business_join_certified":False,"repair_certified":False,
            }
            with (tmp/"verified_receipt.private.json").open("xb") as f:
                f.write(canonical(proof))
            (tmp/"verified_receipt.private.json").chmod(0o600)
            os.rename(tmp,final)
            out.append({"case_prefix":proof["case_sha256"][:12],
                        "operational_order_found":proof["order_found"]})
        except BaseException:
            if tmp.exists():shutil.rmtree(tmp)
            raise
    return {"new_verified_hmac":len(out),"records":out}

def verify_case_operational(sha):
    cohort,manifest=data()
    found=eligible(cohort)
    demand(sha in found,"OP_CASE_NOT_5_CASE_ALLOWLIST")
    job=job_for(sha,cohort[sha],manifest,found[sha])
    name=job["job_id"]+".private.json"
    delivery=ROOT/"operational_outbox"/name
    keyfile=ROOT/"worker_hmac.private"
    demand(keyfile.is_file() and not keyfile.is_symlink()
           and keyfile.stat().st_mode&0o077==0,"OP_PRIVATE_KEY_NOT_SAFE")
    item=validate_one(delivery,key=keyfile.read_bytes(),
                      cohort=cohort,manifest=manifest)
    file=ROOT/"operational_verified"/job["job_id"]/"verified_receipt.private.json"
    pinned=ROOT/"operational_verified"/job["job_id"]/"receipt.private.json"
    demand(file.is_file() and not file.is_symlink()
           and pinned.is_file() and not pinned.is_symlink(),
           "OP_VERIFIED_FILE_NOT_PRESENT")
    proof=parse_strict(file.read_bytes())
    demand(proof["schema"]==PROOF
           and proof["case_sha256"]==sha
           and proof["job_id"]==job["job_id"]
           and proof["source_sha256"]==SOURCE_SHA
           and proof["job_sha256"]==item["envelope"]["job_sha256"]
           and proof["case_row_sha256"]==job["case_row_sha256"]
           and proof["receipt_sha256"]==item["envelope"]["receipt_sha256"]
           and proof["delivery_sha256"]==sha256(delivery.read_bytes()).hexdigest()
           and proof["hmac_verified"] is True
           and proof["independent_receipt_fields_verified"] is True
           and proof["business_join_certified"] is False
           and proof["repair_certified"] is False
           and pinned.read_bytes()==item["receipt_bytes"],
           "OP_PUBLISHED_PROOF_NOT_INDEPENDENTLY_REPLAYABLE")
    # Native independent CORE kernel: trust is not derived merely
    # from the HMAC or a Boolean stored in an earlier receipt.
    from .operational_ot_o5_hand import (
        AuthorizedOperationalOtReceipt,build_operational_ot_router)
    from else_core.hand_kernel import Outcome
    owner=AuthorizedOperationalOtReceipt(
        pinned,sha256(pinned.read_bytes()).hexdigest(),sha,
        SOURCE_SHA,len(SOURCE.read_bytes()),
        cohort[sha]["incident_text_redacted"])
    _,router,operation=build_operational_ot_router(owner)
    result=router.route(operation)
    demand(result.outcome==Outcome.PASS
           and result.guardian_result.verification.passed is True
           and result.guardian_result.verification.independent is True
           and result.guardian_result.executions==1,
           "NATIVE_OPERATIONAL_O5_O13_O15_NOT_VERIFIED")
    values=result.guardian_result.value.outputs
    demand(values["order_found"]==item["observation"]["order_found"]
           and values["order_state_code"]==
              item["observation"]["codigo_estado_orden_trabajo"]
           and values["receipt_sha256"]==proof["receipt_sha256"]
           and values["business_entity_join_certified"] is False,
           "OP_HAND_VALUES_NOT_MATCHING_INDEPENDENT_PROOF")
    return {
      "schema":"else.itil.aug2026.verified-operational-ot-context.v1",
      "case_sha256":sha,
      "source":"ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo",
      "source_receipt_sha256":proof["receipt_sha256"],
      "order_found":item["observation"]["order_found"],
      "state_code":item["observation"]["codigo_estado_orden_trabajo"],
      "type_code":item["observation"]["codigo_tipo_orden_trabajo"],
      "creation_date_present":item["observation"]["fecha_elaboracion_present"],
      "start_date_present":item["observation"]["fecha_inicio_present"],
      "end_date_present":item["observation"]["fecha_fin_present"],
      "hmac_verified":True,
      "independent_receipt_fields_verified":True,
      "native_o5_o13_o15_verified":True,
      "business_join_certified":False,
      "repair_certified":False,
    }

if __name__=="__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="ingest":
        print(json.dumps(ingest(),sort_keys=True))
    else:
        cohort,_=data()
        rows=[verify_case_operational(sha) for sha in sorted(eligible(cohort))]
        print(json.dumps({"verified":len(rows),"order_found":sum(x["order_found"] for x in rows),
                          "statuses":[{"case_prefix":x["case_sha256"][:10],
                            "op_found":x["order_found"],
                            "state_present":bool(x["state_code"])} for x in rows]},
                          sort_keys=True))

"""Independent replay of a *previously executed* Windows QA domain probe.

This verifies source-code SHA-256, a Windows worker HMAC, strict profile identity,
two typed SQL lookups (positive vs negative) for each of 11 approved sources,
and an explicit freshness limit. It DOES NOT execute SQL, re-query Windows,
certify ticket-specific rows, or authorize O5 mutations.

A signed QA snapshot is NOT a live SELECT for a particular support request.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
import hmac
import json
import re

from .qa_feb100_cluster import parse_strict

ROOT=Path("/home/u23u/else_itil_db_knowledge_20261111/raw")
SOURCE=ROOT/"SielseQaDomainConnectivity.cs"
SOURCE_SHA="251160343a05b9ae3b21cc0bbf6cefa96438aaa282c6614fe8aa6091e141c5f9"
SIGNER=Path("/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private")
RECEIPT_NAME="qa_domain_connectivity.private.json"
SCHEMA="else.itil.qa.verified-domain-connectivity.v1"
PROOF="else.itil.qa.verified-domain-connectivity-hmac.v1"
ID_RE=re.compile(r"[0-9a-f]{64}\Z")
PROFILE_KEYS={
 "profile","system","company","qa_target","source","primary_key_column",
 "status","identity_hmac","selected_rows","typed_exact_rows",
 "negative_control_rows","read_only","modifications","error"}
BODY_KEYS={
 "schema","worker","qa_server","source_sha256","profile_count",
 "profiles_positive","profiles_empty","profiles_blocked",
 "observations","sql_executed_on_qa","read_only","changes_executed",
 "no_business_row_payload","raw_entity_keys_disclosed","read_utc"}
PROOF_KEYS={
 "schema","worker","source_sha256","receipt_sha256","hmac_sha256",
 "read_only","changes_executed","signed_utc"}
# Explicit approved, immutable mapping: no company or database inferred from names.
PROFILES=(
 ("ITIL_INCIDENT","ITIL",1,"dbITIL_D","taIncidente","CodigoIncidente"),
 ("SECURITY_MODULE","Seguridad",1,"dbSeguridad_D","taModulo","CodigoModulo"),
 ("DISTRIBUTION_ORDER","Distribucion",1,"dbDistribucion_D","taOrdenTrabajo","CodigoOrdenTrabajo"),
 ("COMPANY1_ORDER","Comercial",1,"dbComercial001_D","taOrdenTrabajo","CodigoOrdenTrabajo"),
 ("COMPANY1_SUPPLY","Comercial",1,"dbComercial001_D","taSuministro","CodigoSuministro"),
 ("COMPANY1_BUDGET","Comercial",1,"dbComercial001_D","taPresupuesto","CodigoOrdenTrabajo"),
 ("COMPANY1_INVOICE","Comercial",1,"dbComercial001_D","taComprobante","CodigoComprobante"),
 ("COMPANY3_ORDER","Comercial",3,"dbComercial003_D","taOrdenTrabajo","CodigoOrdenTrabajo"),
 ("COMPANY3_SUPPLY","Comercial",3,"dbComercial003_D","taSuministro","CodigoSuministro"),
 ("COMPANY3_BUDGET","Comercial",3,"dbComercial003_D","taPresupuesto","CodigoOrdenTrabajo"),
 ("COMPANY3_INVOICE","Comercial",3,"dbComercial003_D","taComprobante","CodigoComprobante"),
)
EXPECTED={p[0]:p for p in PROFILES}
class QaConnectionRejected(ValueError):pass

def require(flag,code):
    if not flag:raise QaConnectionRejected(code)

def _read_small(p,size_limit):
    p=Path(p)
    require(p.is_file() and not p.is_symlink(),"QA_PROOF_FILE_NOT_REGULAR")
    require(0<p.stat().st_size<=size_limit,"QA_PROOF_FILE_SIZE_INVALID")
    return p.read_bytes()

def _utc(value):
    require(type(value) is str and 10<len(value)<65,"QA_TIME_FORMAT_INVALID")
    try:
        parsed=datetime.fromisoformat(re.sub(
           r"(\.\d{6})\d+",r"\1",value.replace("Z","+00:00")))
        require(parsed.tzinfo is not None,"QA_TIME_MISSING_OFFSET")
        return parsed.astimezone(timezone.utc)
    except (ValueError,OverflowError) as exc:
        raise QaConnectionRejected("QA_TIME_NOT_PARSEABLE") from exc

def _hash(raw):return sha256(raw).hexdigest()

def verify_qa_probe(*,root=ROOT,signer=SIGNER,source=None,
                    expected_source_sha=None,now=None,max_age_hours=12):
    """Validate worker receipt independently, fail closed on any discrepancy."""
    require(type(max_age_hours) in (int,float) and 0<max_age_hours<=24,
            "QA_READ_MAX_AGE_NOT_BOUNDED")
    root=Path(root)
    expected_source_sha=SOURCE_SHA if expected_source_sha is None else expected_source_sha
    source=Path(source) if source is not None else SOURCE
    keypath=Path(signer)
    receipt_file=root/RECEIPT_NAME
    proof_file=root/(RECEIPT_NAME+".proof.json")
    require(root.is_dir() and not root.is_symlink(),"QA_RECEIPTS_PRIVATE_ROOT_MISSING")
    require(_hash(_read_small(source,60000))==expected_source_sha
           and expected_source_sha==SOURCE_SHA,
           "QA_WINDOWS_READER_CODE_BYTES_CHANGED")
    require(keypath.is_file() and not keypath.is_symlink()
            and not keypath.stat().st_mode&0o077,
            "QA_SIGNING_KEY_ACL_UNSAFE")
    key=_read_small(keypath,32)
    require(len(key)==32,"QA_SIGNING_KEY_32_BYTES_REQUIRED")
    raw=_read_small(receipt_file,12000)
    proof=parse_strict(_read_small(proof_file,2000))
    body=parse_strict(raw)
    require(type(proof) is dict and set(proof)==PROOF_KEYS,
            "QA_HMAC_PROOF_SCHEMA_INVALID")
    require(type(body) is dict and set(body)==BODY_KEYS,
            "QA_DOMAIN_RECEIPT_SCHEMA_INVALID")
    receipt_sha=_hash(raw)
    require(proof["schema"]==PROOF
        and proof["worker"]=="ELSE62"
        and proof["source_sha256"]==SOURCE_SHA
        and proof["receipt_sha256"]==receipt_sha
        and proof["read_only"] is True
        and proof["changes_executed"] is False
        and type(proof["hmac_sha256"]) is str
        and ID_RE.fullmatch(proof["hmac_sha256"]) is not None,
        "QA_HMAC_PROOF_SCOPE_MISMATCH")
    msg=(SCHEMA+":"+SOURCE_SHA+":"+receipt_sha).encode()
    require(hmac.compare_digest(
        hmac.new(key,msg,"sha256").hexdigest(),proof["hmac_sha256"]),
        "QA_WORKER_HMAC_INVALID")
    read=_utc(body["read_utc"])
    signed=_utc(proof["signed_utc"])
    if now is None:now=datetime.now(timezone.utc)
    require(isinstance(now,datetime) and now.tzinfo is not None,
            "QA_NOW_MUST_HAVE_TZ")
    require(read<=signed+timedelta(minutes=2)
           and signed<=now.astimezone(timezone.utc)+timedelta(minutes=15)
           and read>=now.astimezone(timezone.utc)-timedelta(hours=max_age_hours),
           "QA_WINDOWS_RECEIPT_STALE_OR_FUTURE")
    require(body["schema"]==SCHEMA
        and body["worker"]=="ELSE62"
        and body["qa_server"]=="ELSE70"
        and body["source_sha256"]==SOURCE_SHA
        and type(body["profile_count"]) is int
        and body["profile_count"]==11
        and type(body["profiles_positive"]) is int
        and body["profiles_positive"]==11
        and type(body["profiles_empty"]) is int
        and body["profiles_empty"]==0
        and type(body["profiles_blocked"]) is int
        and body["profiles_blocked"]==0
        and body["sql_executed_on_qa"] is True
        and body["read_only"] is True
        and body["changes_executed"] is False
        and body["no_business_row_payload"] is True
        and body["raw_entity_keys_disclosed"] is False
        and type(body["observations"]) is list
        and len(body["observations"])==11,
        "QA_SCOPE_OR_POSITIVE_COUNT_MISMATCH")
    clock_skew_seconds=max(0,int((signed-now.astimezone(timezone.utc)).total_seconds()))
    for observed,expected in zip(body["observations"],PROFILES):
        require(type(observed) is dict and set(observed)==PROFILE_KEYS,
                "QA_PROFILE_FIELDS_NOT_EXACT")
        name,system,company,db,table,column=expected
        require(
           observed["profile"]==name
           and observed["system"]==system
           and type(observed["company"]) is int
           and observed["company"]==company
           and observed["qa_target"]=="ELSE70/"+db
           and observed["source"]=="dbo."+table
           and observed["primary_key_column"]==column
           and observed["status"]=="POSITIVE_TYPED_READ_VERIFIED"
           and type(observed["identity_hmac"]) is str
           and ID_RE.fullmatch(observed["identity_hmac"]) is not None
           and type(observed["selected_rows"]) is int
           and observed["selected_rows"]==1
           and type(observed["typed_exact_rows"]) is int
           and observed["typed_exact_rows"]==1
           and type(observed["negative_control_rows"]) is int
           and observed["negative_control_rows"]==0
           and observed["read_only"] is True
           and type(observed["modifications"]) is int
           and observed["modifications"]==0
           and observed["error"]=="",
           "QA_PROFILE_POSITIVE_TYPED_LOOKUP_NOT_VERIFIED")
    return {
        "schema":"else.itil.qa.independent-domain-connectivity-proof.v1",
        "status":("SIGNED_QA_SNAPSHOT_VERIFIED_CLOCK_SKEW"
                  if clock_skew_seconds>120 else "SIGNED_QA_SNAPSHOT_VERIFIED"),
        "qa_server":"ELSE70",
        "profiles_verified":len(PROFILES),
        "profiles_positive_typed_lookups":11,
        "negative_controls_confirmed":11,
        "qa_worker_hmac_validated":True,
        "windows_reader_sha256":SOURCE_SHA,
        "worker_receipt_sha256":receipt_sha,
        "read_utc":body["read_utc"],
        "qa_windows_clock_ahead_seconds":clock_skew_seconds,
        "clock_skew_bound_seconds":900,
        "read_only":True,
        "business_row_values_disclosed":False,
        "incident_row_or_relationship_certified":False,
        "fresh_requery_at_call_time":False,
        "o5_o13_o15_execution_certified":False,
        "repair_certified":False
    }

class QaSignedConnectionCatalog:
    """Source discovery API over proof, not a ticket-scoped live query tool."""
    def __init__(self,*,root=ROOT,signer=SIGNER,source=None):
        self.root=Path(root)
        self.signer=Path(signer)
        self.source=Path(source) if source is not None else SOURCE
    def report(self,profile_id):
        if type(profile_id) is not str or profile_id not in EXPECTED:
            return {"status":"BLOCKED","error":"QA_PROFILE_NOT_REGISTERED"}
        proof=verify_qa_probe(root=self.root,signer=self.signer,source=self.source)
        name,system,company,db,table,column=EXPECTED[profile_id]
        return {
          "status":"QA_SNAPSHOT_SOURCE_CONFIRMED_NOT_CASE_READ",
          "query_id":"QA_SIGNED_CONNECTIVITY_SNAPSHOT_V1",
          "profile_id":name,
          "system":system,"company":company,
          "qa_target":"ELSE70/"+db,
          "source":"dbo."+table,"key_column":column,
          "qa_receipt_sha256":proof["worker_receipt_sha256"],
          "windows_reader_sha256":proof["windows_reader_sha256"],
          "windows_hmac_verified":True,
          "qa_windows_clock_ahead_seconds":proof["qa_windows_clock_ahead_seconds"],
          "typed_key_positive":True,
          "typed_key_negative_control_zero":True,
          "fresh_requery_at_call_time":False,
          "business_case_evidence":False,
          "repair_certified":False,
        }

if __name__=="__main__":
    print(json.dumps(verify_qa_probe(),sort_keys=True,ensure_ascii=False))

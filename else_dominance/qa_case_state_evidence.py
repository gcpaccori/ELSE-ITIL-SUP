"""HMAC-verified read-only case-bound ITIL field snapshot and hypothesis gate.

A dated snapshot is evidence only of the **specified fields** of this EXACT
ITIL incident at the read time. It does NOT establish present-time state,
domain business-object linkage, an incident cause or execution of any fix.
No arbitrary SQL, raw incident IDs, passwords, people, or corporate writes.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import hmac,json,re

SCHEMA="else.itil.qa.2026-case-bound-current-itil-state.v1"
PROOF="else.itil.qa.2026-case-bound-current-state-hmac.v1"
MONTH_SCHEMA="else.itil.qa.2026-monthend100-source.v1"
MONTH_PROOF="else.itil.qa.2026-monthend100-source-hmac.v1"
SHA=re.compile(r'[0-9a-f]{64}\Z')
HEX_MONTH=re.compile(r'2026-0[1-9]\Z')
CASE_FIELDS=frozenset({
    "CodigoEstadoIncidente","CodigoModulo","CodigoEmpresa",
    "CodigoCalificacion","CodigoOrigenIncidente","CodigoServicio",
    "FechaCierre.present","FechaRespuestaSolucion.present"
})
BOOLEANS=frozenset({"FechaCierre.present","FechaRespuestaSolucion.present"})
SOURCE="ELSE70/dbITIL_D/dbo.taIncidente"

def strict_json(raw:bytes):
    def unique(pairs):
        out={}
        for key,val in pairs:
            if key in out:raise ValueError("RECEIPT_DUPLICATE_JSON_KEY")
            out[key]=val
        return out
    return json.loads(raw,object_pairs_hook=unique,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError("INVALID_JSON_CONSTANT")))

def digest(raw:bytes)->str:
    return sha256(raw).hexdigest()

def verify_signed(path:Path,key:bytes,code_sha:str,schema:str,proof_schema:str)->tuple[dict,str]:
    if (path.is_symlink() or not path.is_file() or
        path.with_name(path.name+'.proof.json').is_symlink()):
        raise ValueError("SIGNED_RECEIPT_FILE_NOT_REGULAR")
    raw=path.read_bytes()
    if len(raw)>750_000:raise ValueError("SIGNED_RECEIPT_TOO_LARGE")
    meta=path.with_name(path.name+".proof.json")
    proof=strict_json(meta.read_bytes())
    data=strict_json(raw)
    if (type(data) is not dict or type(proof) is not dict or len(key)!=32
        or data.get("schema")!=schema or proof.get("schema")!=proof_schema
        or data.get("source_sha256")!=code_sha
        or proof.get("source_sha256")!=code_sha
        or proof.get("receipt_sha256")!=digest(raw)
        or data.get("read_only") is not True
        or proof.get("read_only") is not True):
        raise ValueError("SIGNED_RECEIPT_BINDING_MISMATCH")
    msg=f"{schema}:{code_sha}:{digest(raw)}".encode()
    mac=hmac.new(key,msg,sha256).hexdigest()
    if not hmac.compare_digest(mac,str(proof.get('hmac_sha256',''))):
        raise ValueError("SIGNED_RECEIPT_HMAC_MISMATCH")
    return data,digest(raw)

def parse_time(timestamp:str)->datetime:
    if type(timestamp) is not str:
        raise ValueError("QA_READ_TIMESTAMP_BAD")
    try:
        # .NET DateTime "O" emits seven fractional digits, Python accepts six.
        normalized=re.sub(r'(\.\d{6})\d+(?=[Z+\-]|$)',r'\1',timestamp)
        d=datetime.fromisoformat(normalized.replace('Z','+00:00'))
        if d.tzinfo is None:raise ValueError("NAIVE")
        return d.astimezone(timezone.utc)
    except (ValueError,OverflowError) as ex:
        raise ValueError("QA_READ_TIMESTAMP_BAD") from ex

class VerifiedCaseStateIndex:
    def __init__(self,*,private_root:Path|str,source_file:Path|str,
                 month_private:Path|str,month_source:Path|str,key_file:Path|str):
        root=Path(private_root)
        source=Path(source_file)
        month_src=Path(month_source)
        self.reader_source_sha256=digest(source.read_bytes())
        monthly_sha=digest(month_src.read_bytes())
        key_path=Path(key_file)
        if key_path.is_symlink():
            raise ValueError("SIGNING_KEY_SYMLINK")
        key=key_path.read_bytes()
        if len(key)!=32:raise ValueError("SIGNING_KEY_INVALID")
        current,receipt_sha=verify_signed(
            root/"case_state_90.private.json",key,self.reader_source_sha256,
            SCHEMA,PROOF)
        if (current.get("selected")!=90 or current.get("months")!=9
            or current.get("qa_server")!="ELSE70"
            or current.get("read_scope")!="EXACT_CASE_STATE_ONLY_NOT_DOMAIN_ENTITY"
            or current.get("query_id")!="QA_ITIL_EXACT_INCIDENT_STATE_READ"
            or current.get("business_modifications")!=0
            or current.get("verified_business_domain_links")!=0):
            raise ValueError("CASESTATE_RECEIPT_SCOPE_INVALID")
        source_index={}
        month_dir=Path(month_private)
        for n in range(1,10):
            ym=f"2026-{n:02d}"
            month_file=month_dir/f"monthend_2026{n:02d}.private.json"
            original,month_sha=verify_signed(
                month_file,key,monthly_sha,MONTH_SCHEMA,MONTH_PROOF)
            if (original.get("period")!=ym
                or original.get("selected")!=100
                or original.get("business_modifications")!=0
                or original.get("history_or_resolution_read") is not False
                or len(original.get("results",[]))!=100):
                raise ValueError("CASESTATE_SOURCE_MONTH_INVALID")
            source_index[ym]={"month":ym,"receipt_sha":month_sha,"rows":original["results"]}
        declared_months=current.get("first_phase_monthly_receipts",[])
        if type(declared_months) is not list or len(declared_months)!=9:
            raise ValueError("CASESTATE_DECLARED_COHORTS_INVALID")
        for month,source_row in zip(source_index.values(),declared_months):
            if (month.get("month")!=source_row.get("month") or
                source_row.get("receipt_sha256")!=month["receipt_sha"] or
                source_row["selected_rechecked"]!=10 or
                source_row["original_source_sha256"]!=monthly_sha):
                raise ValueError("CASESTATE_MONTH_RECEIPT_REBOUND")
        self.rows={}
        self.receipt_sha256=receipt_sha
        self.read_utc=parse_time(current["read_utc"])
        count=0
        for row in current.get("results",[]):
            ym=row.get("month")
            rank=row.get("rank")
            case=row.get("case_sha256")
            if (ym not in source_index or type(rank) is not int
                or rank not in (1,12,23,34,45,56,67,78,89,100)
                or type(case) is not str or not SHA.fullmatch(case)
                or case in self.rows
                or row.get("source_month_receipt_sha256")!=source_index[ym]["receipt_sha"]):
                raise ValueError("CASESTATE_CASE_SOURCE_INVALID")
            expected=source_index[ym]["rows"][rank-1]
            obs=row.get("observed_fields")
            if (case!=expected["case_sha256"]
                or row.get("source")!=SOURCE
                or row.get("query_id")!="QA_ITIL_EXACT_INCIDENT_STATE_READ"
                or row.get("row_count")!=1
                or row.get("case_provenance_verified_by_worker") is not True
                or row.get("domain_business_relation_verified") is not False
                or row.get("root_cause_certified") is not False
                or row.get("repair_certified") is not False
                or row.get("read_only") is not True
                or type(obs) is not dict or set(obs)!=CASE_FIELDS
                or obs["CodigoModulo"]!=expected["module_code"]
                or obs["CodigoEmpresa"]!=expected["company"]
                or row.get("snapshot_status_same") is not (
                     obs["CodigoEstadoIncidente"]==expected["status_code"])):
                raise ValueError("CASESTATE_ROW_SOURCE_BINDING_INVALID")
            if (any(type(obs[k]) is not bool for k in BOOLEANS)
                or any(type(obs[k]) is not str or len(obs[k])>64
                       for k in CASE_FIELDS-BOOLEANS)):
                raise ValueError("CASESTATE_OBSERVED_FIELD_TYPE_INVALID")
            moment=parse_time(row["read_utc"])
            if abs((moment-self.read_utc).total_seconds())>900:
                raise ValueError("CASESTATE_ROW_TIMESTAMP_DRIFT")
            self.rows[case]=row
            count+=1
        if count!=90 or len(self.rows)!=90:
            raise ValueError("CASESTATE_NINETY_ROWS_MISSING")
        self.status_drift=sum(not r["snapshot_status_same"] for r in self.rows.values())
        if (self.status_drift!=current["status_drift_since_source"]
            or current["close_date_present"]!=sum(
                bool(r["observed_fields"]["FechaCierre.present"]) for r in self.rows.values())):
            raise ValueError("CASESTATE_AGGREGATE_DRIFT")

    def summary(self)->dict:
        return {
          "schema":"else.itil.qa.2026-case-state-verification-summary.v1",
          "status":"SIGNED_CASE_BOUNDED_QA_READ_VERIFIED",
          "source":SOURCE,"case_count":len(self.rows),
          "months":9,"evidence_receipt_sha256":self.receipt_sha256,
          "observed_field_names":sorted(CASE_FIELDS),
          "closed_date_present_count":sum(
             bool(r["observed_fields"]["FechaCierre.present"]) for r in self.rows.values()),
          "status_drift_count":self.status_drift,
          "observed_at_utc":self.read_utc.isoformat(),
          "does_not_certify_current_business_domain_state":True,
          "does_not_certify_causal_fix":True,
          "verified_business_domain_links":0,
          "business_modifications":0,
        }

    def inspect(self,*,case_sha256:str,module_code:str,as_of:str,field:str)->dict:
        if (type(case_sha256) is not str or not SHA.fullmatch(case_sha256)
            or type(module_code) is not str or not module_code
            or type(as_of) is not str or type(field) is not str
            or field not in CASE_FIELDS):
            return {"status":"BLOCKED","error":"CASESTATE_SCOPE_OR_FIELD_INVALID"}
        case=self.rows.get(case_sha256)
        if case is None:
            return {"status":"BLOCKED","error":"CASE_NOT_IN_SIGNED_QA_SAMPLE"}
        if (case["observed_fields"]["CodigoModulo"]!=module_code
            or case["month"]!=as_of[:7]):
            return {"status":"BLOCKED","error":"CASESTATE_MODULE_OR_TIME_SCOPE_VIOLATION"}
        return {
          "status":"READ_VERIFIED_QA_SNAPSHOT",
          "query_id":"QA_ITIL_EXACT_INCIDENT_STATE_READ",
          "source":SOURCE,"field":field,
          "observed_value":case["observed_fields"][field],
          "observed_at_utc":case["read_utc"],
          "receipt_sha256":self.receipt_sha256,
          "original_month_receipt_sha256":case["source_month_receipt_sha256"],
          "case_sha256":case_sha256,
          "row_count":1,
          "read_only":True,"provenance_verified":True,
          "business_object_relation_verified":False,
          "root_cause_certified":False,
          "repair_certified":False,
          "snapshot_not_guaranteed_live":True,
        }

def verify_claim(index:VerifiedCaseStateIndex,claim:dict)->dict:
    """Field+value+source+case+receipt must bind EXACTLY; no fuzzy correction."""
    if type(claim) is not dict or set(claim)!={
      "case_sha256","module_code","as_of","source","field",
      "observed_value","receipt_sha256"}:
        return {"status":"BLOCKED","error":"CLAIM_CONTRACT_MISMATCH"}
    obs=index.inspect(case_sha256=claim["case_sha256"],
          module_code=claim["module_code"],as_of=claim["as_of"],
          field=claim["field"])
    if obs["status"]!="READ_VERIFIED_QA_SNAPSHOT":
        return {"status":"BLOCKED","error":"CLAIM_NOT_IN_CASE_SCOPE"}
    if (claim["source"]!=obs["source"]
        or claim["receipt_sha256"]!=obs["receipt_sha256"]
        or type(claim["observed_value"]) is not type(obs["observed_value"])
        or claim["observed_value"]!=obs["observed_value"]):
        return {"status":"BLOCKED","error":"CLAIM_VALUE_OR_RECEIPT_NOT_OBSERVED"}
    return {
        **obs,"status":"FIELD_VALUE_EXACTLY_VERIFIED_IN_QA_SNAPSHOT",
        "verified_current_domain_cause":False,
        "historical_repair_executed":False,
    }

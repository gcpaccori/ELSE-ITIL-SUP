"""Signed exact reported-order QA observation from authorized Windows worker.

The OT identifier came from a ONE-and-ONLY explicit code in a signed ticket's
original description; it is not an official ITIL foreign key. A zero-row
lookup is NOT proof the order doesn't exist anywhere, and a matching record
does not establish ticket cause or modification outcome.
"""
from __future__ import annotations
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import re

from .qa_case_state_evidence import (
    SOURCE,verify_signed,parse_time,strict_json,SHA)

SCHEMA="else.itil.qa.2026-reported-ot-domain-field-probe.v1"
PROOF="else.itil.qa.2026-reported-ot-domain-hmac.v1"
DOMAIN="ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo"
QUERY="QA_DISTR_OPERATIONAL_OT_BY_REPORTED_CODE"
CODE_FIELDS=frozenset({
    "CodigoEstadoOrdenTrabajo","CodigoClaseOrdenTrabajo",
    "CodigoTipoOrdenTrabajo","CodigoSubTipoOrdenTrabajo",
    "FechaElaboracion_present","FechaInicio_present","FechaFin_present"
})
BOOLEAN_FIELDS=frozenset({
    "FechaElaboracion_present","FechaInicio_present","FechaFin_present"
})
CODE_PATTERN=re.compile(r"[0-9A-Za-z._-]{0,50}\Z")

class VerifiedReportedOtIndex:
    def __init__(self,*,private_root:Path|str,source_file:Path|str,
                 month_private:Path|str,month_source:Path|str,
                 key_file:Path|str):
        private=Path(private_root)
        key=Path(key_file)
        if key.is_symlink():raise ValueError("REPORTED_OT_HMAC_KEY_SYMLINK")
        kb=key.read_bytes()
        source=sha256(Path(source_file).read_bytes()).hexdigest()
        original_source=sha256(Path(month_source).read_bytes()).hexdigest()
        data,sha=verify_signed(
            private/"reported_ot_domain.private.json",kb,source,SCHEMA,PROOF)
        if (data.get("qa_server")!="ELSE70"
            or data.get("source")!=DOMAIN
            or data.get("scanned_itil_cases")!=900
            or data.get("official_ticket_to_ot_fk_verified") is not False
            or data.get("modifications")!=0):
            raise ValueError("REPORTED_OT_DOMAIN_SCOPE_INVALID")
        rows=data.get("domain_read_results",[])
        counts=data.get("candidates_reported_ot_unique")
        if (type(rows) is not list or type(counts) is not int
            or len(rows)!=counts
            or counts>900
            or counts!=data.get("exact_domain_record_found",0)+
                       data.get("exact_domain_record_empty",0)
            or counts+data.get("candidates_ambiguous",0)+
               data.get("candidates_other_company",0)+
               data.get("no_explicit_unique_ot",0)!=900):
            raise ValueError("REPORTED_OT_COUNTS_INVALID")
        sources={}
        for n in range(1,10):
            ym=f"2026-{n:02d}"
            path=Path(month_private)/f"monthend_2026{n:02d}.private.json"
            baseline,digest=verify_signed(
               path,kb,original_source,
               "else.itil.qa.2026-monthend100-source.v1",
               "else.itil.qa.2026-monthend100-source-hmac.v1")
            if (baseline.get("period")!=ym
                or baseline.get("selected")!=100
                or len(baseline.get("results",[]))!=100
                or baseline.get("history_or_resolution_read") is not False):
                raise ValueError("REPORTED_OT_SOURCE_CORRUPTED")
            sources[ym]=(digest,baseline["results"])
        declared=data.get("month_receipts",[])
        if (type(declared) is not list or len(declared)!=9
            or {v.get("month"):v.get("month_receipt_sha256") for v in declared}
               !={m:x[0] for m,x in sources.items()}):
            raise ValueError("REPORTED_OT_MONTH_RECEIPTS_UNBOUND")
        self.receipt_sha256=sha
        self.read_utc=parse_time(data["read_utc"])
        self.rows={}
        matched=0
        for r in rows:
            case=r.get("case_sha256")
            period=r.get("month")
            rank=r.get("rank")
            ot=r.get("reported_ot_sha256")
            if (period not in sources or type(rank) is not int
                or not 1<=rank<=100
                or type(case) is not str or not SHA.fullmatch(case)
                or type(ot) is not str or not SHA.fullmatch(ot)
                or case in self.rows
                or r.get("original_month_receipt_sha256")!=sources[period][0]):
                raise ValueError("REPORTED_OT_CASE_SCOPE_INVALID")
            src=sources[period][1][rank-1]
            if (src["case_sha256"]!=case or src["company"]!="1"
                or r.get("candidate_source")!="EXPLICIT_REPORTER_OT_IDENTIFIER_NOT_OFFICIAL_ITIL_FK"
                or r.get("source")!=DOMAIN or r.get("query_id")!=QUERY
                or r.get("official_itil_ot_join_verified") is not False
                or r.get("causal_correction_certified") is not False
                or r.get("modifications")!=0
                or r.get("read_only") is not True
                or type(r.get("row_count")) is not int
                or r["row_count"] not in (0,1)):
                raise ValueError("REPORTED_OT_ROW_CONTRACT_INVALID")
            obs=r.get("observed_fields")
            if r["row_count"]==1:
                if (type(obs) is not dict or set(obs)!=CODE_FIELDS
                    or any(type(obs[k]) is not bool for k in BOOLEAN_FIELDS)
                    or any(type(obs[k]) is not str or len(obs[k])>50
                           for k in CODE_FIELDS-BOOLEAN_FIELDS)):
                    raise ValueError("REPORTED_OT_FIELDS_NOT_VERIFIABLE")
                matched+=1
            elif obs is not None:
                raise ValueError("EMPTY_OT_ROW_HAS_FABRICATED_FIELDS")
            if abs((parse_time(r["read_utc"])-self.read_utc).total_seconds())>900:
                raise ValueError("REPORTED_OT_TIMESTAMP_DRIFT")
            self.rows[case]={**r,"case_module_code":src["module_code"]}
        if len(self.rows)!=counts or matched!=data["exact_domain_record_found"]:
            raise ValueError("REPORTED_OT_DOMAIN_ROW_TOTAL_MISMATCH")
        self.found=matched
        self.empty=counts-matched
        self.reported=counts
        self.ambiguous=data["candidates_ambiguous"]
        self.other_company=data["candidates_other_company"]
        self.no_code=data["no_explicit_unique_ot"]

    def summary(self)->dict:
        return {
           "status":"QA_REPORTED_OT_READ_VERIFIED",
           "schema":"else.itil.qa.2026-reported-ot-evidence-summary.v1",
           "source":DOMAIN,"receipt_sha256":self.receipt_sha256,
           "itil_cases_scanned":900,
           "unique_reported_ot_codes_read":self.reported,
           "ambiguous_ticket_ot_codes":self.ambiguous,
           "different_company_not_queried":self.other_company,
           "without_unique_explicit_ot_code":self.no_code,
           "domain_rows_found":self.found,
           "domain_queries_returned_zero_rows":self.empty,
           "domain_fields_per_found_row":len(CODE_FIELDS),
           "formal_itil_ot_link_verified":False,
           "root_cause_certified":False,
           "business_modifications":0,
           "snapshot_not_guaranteed_live":True,
        }

    def inspect(self,*,case_sha256:str,module_code:str,as_of:str,field:str)->dict:
        if (type(case_sha256) is not str or not SHA.fullmatch(case_sha256)
            or type(module_code) is not str or type(as_of) is not str
            or type(field) is not str or field not in CODE_FIELDS):
            return {"status":"BLOCKED","error":"REPORTED_OT_INVALID_CASE_OR_FIELD"}
        row=self.rows.get(case_sha256)
        if row is None:
            return {"status":"ABSTAIN_NO_UNIQUE_EXPLICIT_REPORTED_OT"}
        if (row["case_module_code"]!=module_code
            or row["month"]!=as_of[:7]):
            return {"status":"BLOCKED","error":"REPORTED_OT_CROSS_CASE_SCOPE"}
        base={
          "source":DOMAIN,"field":field,
          "receipt_sha256":self.receipt_sha256,
          "original_case_sha256":case_sha256,
          "reported_ot_sha256":row["reported_ot_sha256"],
          "observed_at_utc":row["read_utc"],
          "row_count":row["row_count"],
          "provenance_verified":True,
          "reported_identifier_not_official_foreign_key":True,
          "formal_itil_ot_link_verified":False,
          "root_cause_certified":False,
          "repair_certified":False,"read_only":True,
          "snapshot_not_guaranteed_live":True
        }
        if row["row_count"]==0:
            return {**base,"status":"ZERO_ROWS_ONLY_IN_PROBED_DISTRIBUTION_QA_TABLE",
               "observed_value":None,
               "global_order_absence_proven":False}
        return {**base,"status":"READ_VERIFIED_REPORTED_OT_QA_FIELD",
                "observed_value":row["observed_fields"][field]}

def verify_reported_ot_claim(index:VerifiedReportedOtIndex,claim:dict)->dict:
    if type(claim) is not dict or set(claim)!={
      "case_sha256","module_code","as_of","source","field",
      "observed_value","receipt_sha256","reported_ot_sha256"}:
        return {"status":"BLOCKED","error":"OT_FACT_CONTRACT_BAD"}
    actual=index.inspect(case_sha256=claim["case_sha256"],
        module_code=claim["module_code"],as_of=claim["as_of"],field=claim["field"])
    if actual["status"]!="READ_VERIFIED_REPORTED_OT_QA_FIELD":
        return {"status":"BLOCKED","error":"OT_FACT_NOT_OBSERVED"}
    if (claim["source"]!=actual["source"]
        or claim["reported_ot_sha256"]!=actual["reported_ot_sha256"]
        or claim["receipt_sha256"]!=actual["receipt_sha256"]
        or type(claim["observed_value"]) is not type(actual["observed_value"])
        or claim["observed_value"]!=actual["observed_value"]):
        return {"status":"BLOCKED","error":"OT_FACT_VALUE_OR_SOURCE_MISMATCH"}
    return {**actual,"status":"REPORTED_OT_FIELD_EXACT_QA_VALUE_VERIFIED",
        "official_ticket_business_relation_verified":False,
        "causal_diagnosis_confirmed":False}

"""Verified ITIL native-key lifecycle evidence from signed ELSE62 QA SELECTs.

An observed matching CodigoIncidente is not automatically a SQL FOREIGN KEY,
nor proof of an applied fix. This module never executes SQL. It verifies
source-code SHA, worker HMAC and all row/case/month bindings, returning
bounded details from the owner's exact authorised incident only.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import re
from .qa_case_state_evidence import (
    SOURCE, SHA,verify_signed,parse_time)

SCHEMA="else.itil.qa.2026-case-lifecycle-native-keys.v1"
PROOF="else.itil.qa.2026-case-lifecycle-hmac.v1"
EVENT_SCHEMA="else.itil.qa.2026-native-derivation-events.v1"
EVENT_PROOF="else.itil.qa.2026-native-derivation-events-hmac.v1"
MONTH_SCHEMA="else.itil.qa.2026-monthend100-source.v1"
MONTH_PROOF="else.itil.qa.2026-monthend100-source-hmac.v1"
PK_REQUIRED={
    "taIncidente":("CodigoIncidente",),
    "taIncidenteAtencion":("CodigoIncidente","Atencion"),
    "taIncidenteDerivacion":("CodigoIncidente","NumeroDerivacion"),
    "taIncidenteEncuesta":("CodigoIncidente",),
    "taModulo":("CodigoModulo",),
    "gnEstadoIncidente":("CodigoEstadoIncidente",),
}
OBSERVED_FIELDS=frozenset({
    "exact_key_equality_atencion","exact_key_equality_derivacion",
    "exact_key_equality_encuesta","atencion_solved_flag_count",
    "atencion_finish_date_count","modulo_key_row_match",
    "estado_key_row_match","codigo_estado_incidente",
    "state_dictionary_atendido"
})
COUNT_FIELDS=frozenset({
    "exact_key_equality_atencion","exact_key_equality_derivacion",
    "exact_key_equality_encuesta","atencion_solved_flag_count",
    "atencion_finish_date_count",
})
BOOL_FIELDS=frozenset({"modulo_key_row_match","estado_key_row_match"})
SCOPE_FIELD="module_code"
MONTH_PATTERN=re.compile(r'2026-(0[1-9]|1[0-2])')
UTC_TIMESTAMP_PATTERN=re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}')

def _must(test,code):
    if not test:raise ValueError(code)

class VerifiedItILNativeLifecycle:
    def __init__(self,*,private_root:Path|str,reader_file:Path|str,
                 events_reader_file:Path|str,monthly_root:Path|str,
                 month_source_file:Path|str,key_file:Path|str):
        root=Path(private_root)
        month_root=Path(monthly_root)
        key_path=Path(key_file)
        _must(key_path.is_file() and not key_path.is_symlink(),"ITIL_QA_SIGNER_UNTRUSTED")
        key=key_path.read_bytes()
        _must(len(key)==32,"ITIL_QA_SIGNER_BAD")
        source_sha=sha256(Path(reader_file).read_bytes()).hexdigest()
        event_source_sha=sha256(Path(events_reader_file).read_bytes()).hexdigest()
        monthly_sha=sha256(Path(month_source_file).read_bytes()).hexdigest()
        data,receipt_hash=verify_signed(
            root/"itil_native_lifecycle_900.private.json",key,source_sha,
            SCHEMA,PROOF)
        deriv,deriv_hash=verify_signed(
            root/"itil_derivation_events_900.private.json",key,event_source_sha,
            EVENT_SCHEMA,EVENT_PROOF)
        _must(
            data.get("qa_server")=="ELSE70"
            and data.get("qa_database")=="dbITIL_D"
            and data.get("source")=="dbo.taIncidente"
            and data.get("selected")==900
            and data.get("months")==9
            and data.get("business_modifications")==0
            and data.get("causal_fixes_certified")==0
            and data.get("observed_key_equality_not_declaration_of_fk") is True
            and data.get("read_only") is True
            and type(data.get("declared_fk_edges_observed")) is list
            and data.get("declared_fk_edges_observed")==[],
            "LIFECYCLE_UNVERIFIED_BUSINESS_RELATION_OR_SCOPE")
        keys=data.get("pk_constraints")
        _must(type(keys) is list and len(keys)==len(PK_REQUIRED),"LIFECYCLE_PK_SET_INVALID")
        actual={k.get("table"):tuple(k.get("columns",())) for k in keys}
        _must(actual==PK_REQUIRED,"LIFECYCLE_PK_METADATA_MISMATCH")
        _must(deriv.get("source_lifecycle_receipt_sha256")==receipt_hash
              and deriv.get("source") is None  # a separate typed origin field, not SQL input
              and deriv.get("origin")=="dbo.taIncidenteDerivacion"
              and deriv.get("parent_source")=="dbo.taIncidente"
              and deriv.get("qa_server")=="ELSE70"
              and deriv.get("qa_database")=="dbITIL_D"
              and deriv.get("selected_tickets")==900
              and deriv.get("formal_itil_to_derivacion_foreign_key_verified") is False
              and deriv.get("relationship")=="OBSERVED_EXACT_CODIGO_INCIDENTE_KEY_EQUALITY_NOT_FOREIGN_KEY"
              and deriv.get("modifications")==0
              and deriv.get("causal_fixes_certified")==0
              and deriv.get("read_only") is True,
              "LIFECYCLE_DERIVATION_SOURCE_NOT_BOUND")
        # A newly captured life-cycle snapshot must not be confused with an
        # arbitrary later refresh. It is historical QA evidence, not live truth.
        self.read_utc=parse_time(data["read_utc"])
        self.derivation_read_utc=parse_time(deriv["read_utc"])
        _must(abs((self.derivation_read_utc-self.read_utc).total_seconds())<900,
              "LIFECYCLE_READ_RECEIPT_TIME_DRIFT")
        month_sources={}
        for n in range(1,10):
            ym=f"2026-{n:02d}"
            doc,digest=verify_signed(
                month_root/f"monthend_2026{n:02d}.private.json",
                key,monthly_sha,MONTH_SCHEMA,MONTH_PROOF)
            _must(
                doc.get("period")==ym and doc.get("selected")==100
                and len(doc.get("results",[]))==100
                and doc.get("history_or_resolution_read") is False
                and doc.get("business_modifications")==0,
                "LIFECYCLE_FROZEN_MONTH_OR_GOLD_INVALID")
            month_sources[ym]=(digest,doc["results"])
        expected_declared=[
          {"month":ym,"receipt_sha256":month_sources[ym][0]}
          for ym in month_sources
        ]
        _must(data.get("source_receipts")==expected_declared,
              "LIFECYCLE_SOURCE_RECEIPTS_NOT_EXACT")
        self.rows={}
        monthly=Counter()
        for row in data.get("results",[]):
            case=row.get("case_sha256")
            month=row.get("month")
            rank=row.get("rank")
            _must(
              type(case) is str and SHA.fullmatch(case) is not None
              and case not in self.rows and month in month_sources
              and type(rank) is int and 1<=rank<=100,
              "LIFECYCLE_CASE_OR_DUPLICATE_INVALID")
            old=month_sources[month][1][rank-1]
            _must(
               case==old["case_sha256"]
               and row.get("monthly_receipt_sha256")==month_sources[month][0]
               and row.get("source")==SOURCE
               and row.get("query_id")=="QA_ITIL_CASE_NATIVE_LIFECYCLE_BY_CODIGO_INCIDENTE"
               and row.get("parent_rows")==1
               and row.get("codigo_estado_incidente")==old["status_code"]
               and row.get("business_resolution_certified") is False
               and row.get("db_declared_itil_to_ot_fk") is False
               and row.get("read_only") is True,
               "LIFECYCLE_CASE_NOT_BOUND_TO_MONTH")
            _must(set(row)==(
                {'month','rank','case_sha256','monthly_receipt_sha256',
                 'source','query_id','parent_rows','db_declared_itil_to_ot_fk',
                 'business_resolution_certified','read_only'}|OBSERVED_FIELDS),
                 "LIFECYCLE_ROW_UNKNOWN_FIELDS")
            for field in OBSERVED_FIELDS:
                value=row[field]
                if field in COUNT_FIELDS:
                    _must(type(value) is int and 0<=value<=100,
                          "LIFECYCLE_ROW_COUNT_VALUE_BAD")
                elif field in BOOL_FIELDS:
                    _must(type(value) is bool,"LIFECYCLE_ROW_BOOLEAN_BAD")
                elif field=="codigo_estado_incidente":
                    _must(type(value) is str and len(value)<=12,"LIFECYCLE_ROW_STATUS_BAD")
                else:
                    _must(value is None or (type(value) is int and 0<=value<=255),
                          "LIFECYCLE_DICTIONARY_FLAG_BAD")
            _must(
                row["atencion_solved_flag_count"]<=row["exact_key_equality_atencion"]
                and row["atencion_finish_date_count"]<=row["exact_key_equality_atencion"],
                "LIFECYCLE_CHILD_STATUS_COUNT_INVALID")
            self.rows[case]={**row,"module_code":old["module_code"],
                             "opened_at":old["opened_at"]}
            monthly[month]+=1
        _must(len(self.rows)==900 and
              dict(monthly)=={ym:100 for ym in month_sources},
              "LIFECYCLE_EXPECTED_NINE_HUNDRED")
        for k,field in [
          ("cases_with_attention","exact_key_equality_atencion"),
          ("cases_with_derivation","exact_key_equality_derivacion"),
          ("cases_with_survey","exact_key_equality_encuesta"),
          ("cases_module_code_matched","modulo_key_row_match"),
          ("cases_state_code_matched","estado_key_row_match")
        ]:
            _must(data[k]==sum(bool(r[field]) for r in self.rows.values()),
                  "LIFECYCLE_AGGREGATE_MISMATCH_"+k)
        for k,field in [
          ("attention_rows","exact_key_equality_atencion"),
          ("derivation_rows","exact_key_equality_derivacion"),
          ("survey_rows","exact_key_equality_encuesta")
        ]:
            _must(data[k]==sum(r[field] for r in self.rows.values()),
                  "LIFECYCLE_CHILD_COUNT_MISMATCH_"+k)
        self.events=defaultdict(list)
        seen=set()
        deriv_months=Counter()
        for e in deriv.get("results",[]):
            case=e.get("case_sha256")
            n=e.get("numero_derivacion")
            month=e.get("month")
            rank=e.get("rank")
            _must(
                case in self.rows and type(n) is int and 0<=n<=32767
                and (case,n) not in seen
                and month==self.rows[case]["month"]
                and rank==self.rows[case]["rank"]
                and e.get("exact_same_codigo_incidente_as_ticket") is True
                and e.get("official_sql_fk_declared") is False
                and e.get("historical_business_fix_executed_certified") is False
                and type(e.get("codigo_tipo_derivacion")) is str
                and len(e["codigo_tipo_derivacion"])<=20
                and type(e.get("fecha_modificacion_present")) is bool,
                "DERIVATION_EVENT_CASE_PK_NOT_BOUND")
            stamp=e.get("fecha_creacion_utc_unspecified_local")
            _must(type(stamp) is str
                 and (stamp=="" or UTC_TIMESTAMP_PATTERN.fullmatch(stamp) is not None),
                 "DERIVATION_EVENT_DATE_INVALID")
            seen.add((case,n))
            self.events[case].append({
               "sequence_number":n,
               "type_code":e["codigo_tipo_derivacion"],
               "created_date_time_without_timezone":stamp,
               "modified_date_present":e["fecha_modificacion_present"]
            })
            deriv_months[month]+=1
        _must(len(seen)==deriv.get("events_count")
              and len(seen)==data["derivation_rows"]
              and deriv["events_with_creation_date"]==sum(
                  bool(ev["created_date_time_without_timezone"])
                  for group in self.events.values() for ev in group),
              "DERIVATION_EVENTS_AGGREGATE_DRIFT")
        declared_monthly=deriv.get("months",[])
        _must(declared_monthly==[
            {"month":m,"events_returned":deriv_months[m]}
            for m in month_sources],
            "DERIVATION_EVENTS_MONTH_DRIFT")
        for case,row in self.rows.items():
            _must(len(self.events[case])==row["exact_key_equality_derivacion"],
                  "DERIVATION_EVENTS_CROSS_CASE_COUNT_DRIFT")
            self.events[case].sort(key=lambda v:v["sequence_number"])
        self.receipt_sha256=receipt_hash
        self.events_receipt_sha256=deriv_hash
        self.month_sources=month_sources

    def summary(self)->dict:
        histogram=Counter(len(v) for v in self.events.values())
        types=Counter(e["type_code"] for group in self.events.values() for e in group)
        return {
            "status":"SIGNED_ITIL_LIFECYCLE_QA_VERIFIED",
            "schema":"else.itil.qa.2026-native-lifecycle-verified-summary.v1",
            "cases":len(self.rows),"months":9,
            "source":SOURCE,
            "lifecycle_receipt_sha256":self.receipt_sha256,
            "derivation_events_receipt_sha256":self.events_receipt_sha256,
            "cases_with_one_derivation":histogram[1],
            "cases_with_multiple_derivations":sum(
                count for n,count in histogram.items() if n>=2),
            "cases_with_no_derivations":histogram[0],
            "derivation_events":sum(types.values()),
            "derivation_type_code_counts":dict(sorted(types.items())),
            "verified_module_rows":sum(
                r["modulo_key_row_match"] for r in self.rows.values()),
            "verified_incident_state_lookup_rows":sum(
                r["estado_key_row_match"] for r in self.rows.values()),
            "sql_declared_fk_from_incident_tables":0,
            "observed_key_equality_not_declared_fk":True,
            "human_intervention_meaning_not_inferred":True,
            "business_causes_certified":0,
            "business_repairs_certified":0,
        }

    def inspect(self,*,case_sha256:str,module_code:str,as_of:str,view:str)->dict:
        if (type(case_sha256) is not str or SHA.fullmatch(case_sha256) is None
            or type(module_code) is not str or not module_code
            or type(as_of) is not str or MONTH_PATTERN.fullmatch(as_of[:7]) is None
            or view not in ("summary","derivation_events")):
            return {"status":"BLOCKED","error":"LIFECYCLE_CASE_MODULE_DATE_OR_VIEW_INVALID"}
        row=self.rows.get(case_sha256)
        if row is None:
            return {"status":"BLOCKED","error":"CASE_NOT_IN_SIGNED_ITIL_COHORT"}
        if row["module_code"]!=module_code or row["month"]!=as_of[:7]:
            return {"status":"BLOCKED","error":"LIFECYCLE_CROSS_CASE_OR_MODULE"}
        base={
            "status":"READ_VERIFIED_ITIL_NATIVE_KEY_QA",
            "case_sha256":case_sha256,
            "source":"ELSE70/dbITIL_D/dbo.taIncidente",
            "related_source":"ELSE70/dbITIL_D/dbo.taIncidenteDerivacion",
            "lifecycle_receipt_sha256":self.receipt_sha256,
            "derivation_receipt_sha256":self.events_receipt_sha256,
            "snapshot_at_utc":self.derivation_read_utc.isoformat(),
            "record_company_and_module_matched":True,
            "related_child_match_method":"EXACT_CODIGO_INCIDENTE_KEY_EQUALITY",
            "declared_sql_foreign_key_verified":False,
            "history_narrative_or_solution_was_read":False,
            "business_root_cause_verified":False,
            "repair_certified":False,
            "read_only":True,
            "provenance_verified":True,
        }
        if view=="summary":
            return {**base,"view":"summary","observed_fields":{
               key:row[key] for key in sorted(OBSERVED_FIELDS)}}
        events=self.events[case_sha256]
        return {**base,"view":"derivation_events",
            "derivation_event_count":len(events),
            "events":events[:8],"more_events_not_returned":max(0,len(events)-8),
            "type_codes_not_interpreted_as_business_actions":True}

def verify_lifecycle_field_claim(index:VerifiedItILNativeLifecycle,claim:dict)->dict:
    exact={"case_sha256","module_code","as_of","source","field",
           "observed_value","lifecycle_receipt_sha256"}
    if type(claim) is not dict or set(claim)!=exact:
        return {"status":"BLOCKED","error":"LIFECYCLE_FIELD_CLAIM_SCHEMA_BAD"}
    if claim.get("field") not in OBSERVED_FIELDS:
        return {"status":"BLOCKED","error":"LIFECYCLE_FIELD_NOT_REGISTERED"}
    observed=index.inspect(
       case_sha256=claim["case_sha256"],module_code=claim["module_code"],
       as_of=claim["as_of"],view="summary")
    if observed.get("status")!="READ_VERIFIED_ITIL_NATIVE_KEY_QA":
        return {"status":"BLOCKED","error":"LIFECYCLE_CLAIM_NOT_IN_CASE"}
    actual=observed["observed_fields"][claim["field"]]
    if (claim["source"]!=SOURCE
        or claim["lifecycle_receipt_sha256"]!=index.receipt_sha256
        or type(claim["observed_value"]) is not type(actual)
        or claim["observed_value"]!=actual):
        return {"status":"BLOCKED","error":"LIFECYCLE_CLAIM_VALUE_OR_SOURCE_CHANGED"}
    return {
        "status":"EXACT_ITIL_LIFECYCLE_FIELD_VALUE_VERIFIED",
        "source":SOURCE,"field":claim["field"],
        "observed_value":actual,
        "lifecycle_receipt_sha256":index.receipt_sha256,
        "observed_key_relation_not_fk":True,
        "business_cause_certified":False,
        "repair_certified":False,
    }

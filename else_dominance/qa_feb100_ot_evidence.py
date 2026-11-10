"""Independent evidence contract for Feb 100 read-only SAP/OT Hand.

Source: exact fixed C# SQL on ELSE70/dbDistribucion_D. The reported OT
identifier is bound to the incident text by SHA but is NOT a confirmed
business join between ITIL and Distribución. No model-defined SQL.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,re,zipfile
from typing import Any

SCHEMA="else.itil.feb100.ot-sap-case-evidence.v1"
OBS_SCHEMA="else.itil.qa.feb100.sap-ot-readonly.v1"
QUERIES=["QA_DISTRIB_SAP_ORDER_BY_OT",
         "QA_DISTRIB_SAP_RESPONSE_BY_OT"]
SOURCES=["dbo.taOrdenTrabajoSAP",
         "dbo.taOrdenTrabajoSAPEnvioRespuesta"]
OT_RE=re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)"
                 r"\s*[:#=-]?\s*(\d{4,19})\b",re.I)
HEX64=re.compile(r"[0-9a-f]{64}\Z")

def require(condition,code):
    if not condition:raise ValueError(code)

def extract_unique_reported_ot(text:str):
    require(type(text) is str,"DESCRIPTION_INVALID")
    nums=set(OT_RE.findall(text))
    if len(nums)!=1:return None
    return next(iter(nums))

def verify_ot_receipt(*,row:dict,receipt:dict,source_bytes:bytes)->dict:
    sha=row["case_sha256"]
    require(type(sha) is str and HEX64.fullmatch(sha) is not None,
            "CASE_SHA_INVALID")
    ot=extract_unique_reported_ot(row["description_redacted"])
    require(ot is not None,"OT_REPORT_NOT_UNIQUE")
    require(type(receipt) is dict and set(receipt)=={
        "schema","case_sha256","binding_provenance","reported_ot_sha256",
        "reader_source_sha256","observation","read_only","mutations",
        "functional_repair_certified","root_cause_certified",
        "requires_technician_review"},"OT_RECEIPT_FIELDS_INVALID")
    require(receipt["schema"]==SCHEMA and receipt["case_sha256"]==sha,
            "OT_CASE_DRIFT")
    require(receipt["binding_provenance"]==
            "REPORTED_OT_FROM_REDACTED_CASE_TEXT_ONLY",
            "UNVERIFIED_OT_LINK_CLAIM")
    expect=sha256(ot.encode()).hexdigest()
    require(receipt["reported_ot_sha256"]==expect,
            "OT_IDENTITY_NOT_BOUND_TO_TICKET_TEXT")
    require(receipt["reader_source_sha256"]==sha256(source_bytes).hexdigest(),
            "OT_SOURCE_SHA_MISMATCH")
    require(receipt["read_only"] is True and
            receipt["mutations"] is False and
            receipt["functional_repair_certified"] is False and
            receipt["root_cause_certified"] is False and
            receipt["requires_technician_review"] is True,
            "OT_UNSUPPORTED_EXECUTION_CLAIM")
    obs=receipt["observation"]
    require(type(obs) is dict and set(obs)=={
        "schema","query_ids","qa_target","sources","order_sha256",
        "order_rows","order_found","codigo_estado_envio_sap",
        "codigo_clase_orden_sap","numero_co_sap_present",
        "response_rows_up_to5","response_message_present",
        "response_orden_co_present","response_sample_limited",
        "read_only","changes_executed","read_utc"},
        "OT_OBSERVATION_FIELDS_INVALID")
    require(obs["schema"]==OBS_SCHEMA and
            obs["qa_target"]=="ELSE70/dbDistribucion_D" and
            obs["query_ids"]==QUERIES and obs["sources"]==SOURCES and
            obs["order_sha256"]==expect,"OT_QA_SCOPE_INVALID")
    require(type(obs["order_rows"]) is int and obs["order_rows"] in (0,1) and
            type(obs["order_found"]) is bool and
            obs["order_found"]==(obs["order_rows"]==1),
            "OT_CARDINALITY_INVALID")
    require(type(obs["response_rows_up_to5"]) is int and
            0<=obs["response_rows_up_to5"]<=5 and
            type(obs["read_utc"]) is str and len(obs["read_utc"])>=20 and
            obs["read_only"] is True and obs["changes_executed"] is False,
            "OT_RESPONSE_SCOPE_INVALID")
    for flag in ("numero_co_sap_present","response_message_present",
                 "response_orden_co_present","response_sample_limited"):
        require(type(obs[flag]) is bool,"OT_FLAG_INVALID_"+flag)
    for field in ("codigo_estado_envio_sap","codigo_clase_orden_sap"):
        require(type(obs[field]) is str and len(obs[field])<=100,
                "OT_STATE_CODE_INVALID")
    return {
        "schema":"else.itil.feb100.ot-sap-evidence-verification.v1",
        "case_sha256":sha,
        "read_only_source_verified":True,
        "data_source":"ELSE70/dbDistribucion_D",
        "order_found_in_this_specific_table":obs["order_found"],
        "order_state_code":obs["codigo_estado_envio_sap"] if
            obs["order_found"] else None,
        "response_rows_up_to5":obs["response_rows_up_to5"],
        "response_message_present":obs["response_message_present"],
        "sap_number_present":obs["numero_co_sap_present"],
        "entity_link_to_itil_not_certified":True,
        "current_business_root_cause_not_certified":True,
        "source_receipt_sha256":sha256(json.dumps(
             receipt,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
        "repair_certified":False,
        "human_review_required":True,
    }

def audit_ot_zip(*,zip_path:Path,allowlist:Path,source_file:Path)->dict:
    from collections import Counter
    from qa.qa_feb100_windows import read_allowlist
    rows=read_allowlist(allowlist)
    source=source_file.read_bytes()
    results=[]
    with zipfile.ZipFile(zip_path) as pack:
        files=pack.namelist()
        require(len(files)==len(set(files)),"DUPLICATE_ZIP_ENTRY")
        for entry in sorted(files):
            require(re.fullmatch(r"[0-9a-f]{64}\.private\.json",entry)
                    is not None,"ARCHIVE_ENTRY_NOT_OWNER_BOUNDED")
            sha=entry[:64]
            require(sha in rows,"CASE_NOT_IN_FEB100_ALLOWLIST")
            raw=pack.read(entry)
            require(len(raw)<15000,"OT_RECEIPT_TOO_LARGE")
            value=json.loads(raw)
            answer=verify_ot_receipt(row=rows[sha],receipt=value,
                                     source_bytes=source)
            results.append(answer)
    require(len({r["case_sha256"] for r in results})==len(results),
            "OT_DUPLICATE_CASE_IN_ARCHIVE")
    return {"schema":"else.itil.feb100.ot-sap-independent-audit.v1",
            "verified_cases":len(results),
            "orders_found":sum(x["order_found_in_this_specific_table"] for x in results),
            "not_found_in_these_tables":sum(not x["order_found_in_this_specific_table"]
                                            for x in results),
            "source_sha256":sha256(source).hexdigest(),
            "zip_sha256":sha256(zip_path.read_bytes()).hexdigest(),
            "case_audit":results,"business_entity_links_certified":0,
            "functional_repairs_certified":0}

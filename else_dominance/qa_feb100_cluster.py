"""Finish a model-triggered, fresh NuGet QA investigation via real CORE O5.

This module is intentionally separate from the existing requester-submitted
HTTP listener. It NEVER executes SQL itself and never accepts a model path,
query or database. It verifies Windows receipt bytes + exact source code
through CORE O5/O13/O15 before any model final diagnosis is produced.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any

from .agent import OpenAICompatibleModel
from .qa_feb100_native import (
    QA_SOURCE, QaNativeDenied, require, require_private_local_model_url,
    validate_qa_ticket, verify_native_o5)
from .qa_feb100_o5_tool_runtime import O5QaToolAdapter, QUERY_ID, TOOL_NAME
from .resolution_batch import KNOWN_SOURCES
from .support_desk import SYSTEM, _quality

SCHEMA = "else.itil.qa.model-triggered-nuget-investigation.v1"
HEX = re.compile(r"[0-9a-f]{64}\Z")
TABLE = re.compile(r"\b(?:ITIL|SEC|ADM|COM|DIS|DIST|DBO)\.[A-Za-z][A-Za-z0-9_]*",
                   re.IGNORECASE)


def parse_strict(content: bytes) -> dict:
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:
                raise QaNativeDenied("DUPLICATE_JSON_KEY")
            out[k]=v
        return out
    try:
        obj=json.loads(content,object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(
                           QaNativeDenied("NONFINITE_JSON")))
    except (UnicodeDecodeError,ValueError) as exc:
        raise QaNativeDenied("JSON_NOT_VALID") from exc
    require(type(obj) is dict,"JSON_OBJECT_REQUIRED")
    return obj


def source_context(proof: dict,case: dict) -> dict:
    """Seal additional read-only SQL columns to O5's exact receipt bytes.

    CORE O5 verifies the source, source manifest, receipt SHA and primary
    identity. This function independently checks optional QA metadata and
    does not claim it establishes a current repair or root cause.
    """
    require(proof.get("opened_at")==case["opened_at"],"READ_DATE_DRIFT")
    require(proof.get("service_code")==case["service_code"] and
            proof.get("module_code")==case["module_code"],
            "READ_SERVICE_MODULE_DRIFT")
    for k in ("classification_code","origin_code","status_code"):
        require(type(proof.get(k)) is str and len(proof[k])<=80,
                "INVALID_QA_METADATA_"+k.upper())
    byte_text=proof.get("request_bytes")
    require(type(byte_text) is str and
            re.fullmatch(r"\d{1,12}",byte_text) is not None,
            "REQUEST_BYTES_INVALID")
    size=int(byte_text)
    require(size>=0 and size<=200_000_000,"QA_REQUEST_SIZE_INVALID")
    require(type(proof.get("issued_at_utc")) is str and
            len(proof["issued_at_utc"])>=20,"ISSUED_TIME_NOT_PRESENT")
    return {
        "source":"ELSE70/dbITIL_D/dbo.taIncidente",
        "opened_at":proof["opened_at"],
        "service_code":proof["service_code"],
        "module_code":proof["module_code"],
        "classification_code":proof["classification_code"],
        "origin_code":proof["origin_code"],
        "ticket_status_code":proof["status_code"],
        "request_bytes":size,
        "observation_kind":"HISTORICAL_QA_INCIDENT_METADATA",
        "current_endpoint_state_observed":False,
        "repair_verified":False}


def table_mentions_in_proposal(plan:dict) -> list[str]:
    content=json.dumps(plan,ensure_ascii=False,sort_keys=True)
    known={x.upper() for x in KNOWN_SOURCES}
    declared={x.upper() for x in plan.get("fuentes",[])
              if type(x) is str} if type(plan.get("fuentes")) is list else set()
    names={m.group(0).upper() for m in TABLE.finditer(content)}
    return sorted(x for x in names if x not in known or x not in declared)


def finish_fresh_qa_case(*, owner, case:dict, model,
                         tool_request:dict) -> dict:
    """One tool requested by the model, fresh Windows SQL receipt, O5 + final inference."""
    clean=validate_qa_ticket(case,case_sha256=owner.case_sha256,
                             service_code=case.get("service_code"),
                             module_code=case.get("module_code"))
    require(tool_request.get("parameters",{}).get("case_sha256")==
            clean["case_sha256"],"REQUEST_NOT_FOR_THIS_CASE")
    verified,tool_observation=O5QaToolAdapter(owner).run(tool_request,clean)
    require(verified.get("guardian_o13_pass") is True and
            verified.get("dominance_o15_pass") is True,
            "O5_O13_O15_REQUIRED")
    raw,proof=owner.read_verified()
    context=source_context(proof,clean)
    # Two distinct evidence layers: E1 primary immutable case receipt; E2
    # exact metadata bound to that sealed source, not proof of functional repair.
    evidence=[
        {"ref":"E1","observation":
         "La solicitud y los códigos servicio/módulo se observaron en "
         "ELSE70/dbITIL_D QA mediante NuGet; recibo sellado y verificado "
         "por O5/O13/O15. NO se leyó una solución histórica."},
        {"ref":"E2","observation":
         "Metadatos SQL QA verificados: clasificación "+
         context["classification_code"]+
         "; estado de incidencia "+context["ticket_status_code"]+
         "; origen "+context["origin_code"]+
         ". No es el estado actual del equipo ni confirma la causa."}
    ]
    sys=SYSTEM+(
        "\nSe obtuvo un resultado nuevo del lector Windows NuGet tras tu "
        "petición exacta de herramienta. O5/O13/O15 verificaron la procedencia "
        "del recibo. Usa E1 y E2 para ajustar tus hipótesis cuando aporten "
        "datos, pero un estado administrativo ITIL no prueba la causa raíz. "
        "Pide evidencia adicional necesaria; no inventes tablas, perfiles, "
        "responsables oficiales ni reparaciones."
    )
    payload={
        "case_sha256_prefix":owner.case_sha256[:16],
        "incident_text_redacted_unverified":clean["description"],
        "tool_request_accepted":tool_request,
        "tool_observation":tool_observation,
        "verified_sql_metadata":context,
        "evidence":evidence,
        "historical_solution":"WITHHELD",
        "allowed_source_names":sorted(KNOWN_SOURCES),
        "required":"Diagnóstico diferencial actualizado y plan condicional "
                   "en JSON. Tres pasos como máximo, sin afirmar cierre."}
    try:
        response=model.complete([
            {"role":"system","content":sys},
            {"role":"user","content":json.dumps(payload,ensure_ascii=False)}])
        plan=parse_strict(response.encode("utf-8"))
        quality=_quality(plan,evidence)
        missing_tables=table_mentions_in_proposal(plan)
        if missing_tables:
            quality={**quality,"accepted":False,
                     "status":"REJECT",
                     "safety_flags":list(quality["safety_flags"])+[
                        "UNBOUND_SQL_TABLE_REFERENCES"],
                     "unbound_table_mentions":missing_tables}
        accepted=(quality.get("accepted") is True and
                  plan.get("ejecutado") is False and
                  plan.get("confirmado") is False)
    except (ValueError,TypeError,KeyError,AttributeError):
        plan={}
        quality={"accepted":False,"status":"REJECT",
                 "schema_flags":["MODEL_RESPONSE_NOT_ACCEPTED"],
                 "safety_flags":[],"review_flags":[]}
        accepted=False

    return {
        "schema":SCHEMA,
        "case_sha256":owner.case_sha256,
        "model_requested_tool":True,
        "tool_name":TOOL_NAME,"query_id":QUERY_ID,
        "new_nuget_qa_receipt_consumed":True,
        "source_receipt_sha256":owner.pinned_sha256,
        "hand_source_sha256":owner.source_sha256,
        "o5_operation_id":verified["o5_operation_id"],
        "o15_receipt_sha256":verified["o15_receipt_sha256"],
        "o5_o13_o15_verified":True,
        "independently_reinspected_metadata":context,
        "qa_sql_read_only":True,
        "model_had_verified_metadata_before_final":True,
        "quality":quality,
        "status":quality.get("status","NEEDS_HUMAN_TRIAGE")
                 if accepted else "NEEDS_HUMAN_TRIAGE",
        "proposal":plan if accepted else {},
        "repair_certified":False,"root_cause_certified":False,
        "approved_for_training":False,"executed_mutations":False,
        "requires_human_verification":True}


def run_cli(*, root:Path, source:Path,
            model_url:str="http://127.0.0.1:18782/v1",
            model_name:str="else-itil-riv-qwen9b-gpu6"):
    from else_core.itil_feb100_o5_hand import AuthorizedNugetReceipt
    require(root.is_absolute() and root.is_dir() and not root.is_symlink(),
            "PRIVATE_BUNDLE_ROOT_INVALID")
    require(source.is_absolute() and source.is_file() and
            not source.is_symlink() and source.name=="Feb100ExactRead.cs",
            "HAND_SOURCE_NOT_APPROVED")
    require_private_local_model_url(model_url)
    receipt=root/"receipt.private.json"
    case_path=root/"case.private.json"
    tool_path=root/"tool_request.private.json"
    for p in (receipt,case_path,tool_path):
        require(p.is_file() and not p.is_symlink(),"REQUIRED_PRIVATE_INPUT_MISSING")
    req=parse_strict(tool_path.read_bytes())
    case=parse_strict(case_path.read_bytes())
    proof=parse_strict(receipt.read_bytes())
    source_raw=source.read_bytes()
    source_sha=sha256(source_raw).hexdigest()
    receipt_sha=sha256(receipt.read_bytes()).hexdigest()
    require(proof.get("hand_source_sha256")==source_sha,
            "WINDOWS_HAND_SOURCE_NOT_EQUAL_REPO_SOURCE")
    require(proof.get("case_sha256")==case.get("case_sha256"),
            "CASE_RECEIPT_SHA_DRIFT")
    owner=AuthorizedNugetReceipt(receipt,receipt_sha,case["case_sha256"],
                                 source_sha,len(source_raw))
    expected_manifest=owner.source_receipt()["source_manifest_sha256"]
    require(proof.get("hand_manifest_sha256")==expected_manifest,
            "HAND_SOURCE_MANIFEST_DRIFT")
    model=OpenAICompatibleModel(model_url,model_name,timeout=155)
    result=finish_fresh_qa_case(owner=owner,case=case,
                                tool_request=req,model=model)
    out=root/"verified_final.private.json"
    raw=json.dumps(result,ensure_ascii=False,indent=2).encode()
    fd=os.open(out,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    return {
        "schema":SCHEMA,
        "case_sha_prefix":owner.case_sha256[:16],
        "o5_o13_o15_verified":result["o5_o13_o15_verified"],
        "status":result["status"],
        "quality_accepted":result["quality"].get("accepted"),
        "model_received_fresh_qa_evidence":True,
        "functional_repair_certified":False,
        "output_sha256":sha256(raw).hexdigest()}


def main():
    p=argparse.ArgumentParser(description="ELSE ITIL native O5 fresh QA pass")
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--source",required=True,type=Path)
    args=p.parse_args()
    print(json.dumps(run_cli(root=args.root,source=args.source),
                     ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()

"""Adversarial evidence grounding tests: no catalog→SQL evidence laundering."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path

import pytest
pytest.importorskip("else_core.itil_feb100_o5_hand",
                  reason="Feb native O5 requires ELSE CORE PR #363")

from else_dominance.qa_evidence_grounding import (
    evidence_provenance_gate,evaluate_grounded_plan,grounded_system_policy,
    missing_source_repair_instruction)
from else_dominance.qa_feb100_cluster import finish_fresh_qa_case
from else_core.itil_feb100_o5_hand import AuthorizedNugetReceipt,TRANSFER_SCHEMA,QA_SCOPE,QUERY_ID
from test_qa_native_runtime import good_plan

CASE=sha256(b"feb-grounding-synthetic-case").hexdigest()
SOURCE=sha256(b"feb-grounding-source-bytes").hexdigest()
RECEIPT="a"*64

def grounded_plan():
    p=good_plan()
    p["fuentes"]=["ITIL.taIncidente"]
    p["evidence_refs"]=["E1","E2"]
    p["diagnostico"]="La incidencia existe, pero la causa es una hipótesis."
    p["pasos"][0]["accion"]="Probar acceso con una cuenta autorizada, sin modificar permisos."
    return p

def provenance(plan,**kwargs):
    return evidence_provenance_gate(plan,native_o5_verified=True,
                                    source_receipt_sha256=RECEIPT,**kwargs)

def test_good_plan_is_grounded_in_one_executed_table():
    q=provenance(grounded_plan())
    assert q["accepted"]
    assert q["observed_sources"]==["ITIL.taIncidente"]
    assert q["unobserved_mentions"]==[]

@pytest.mark.parametrize("override",[
    lambda p:p.update(fuentes=["SEC.taUsuario"]),
    lambda p:p.update(fuentes=["ITIL.taIncidente","SEC.taUsuario"]),
    lambda p:p.update(fuentes=[]),
    lambda p:p.update(fuentes=["ITIL.taIncidente","ITIL.taIncidente"]),
    lambda p:p.update(fuentes=[["ITIL.taIncidente"]]),
    lambda p:p.update(evidence_refs=["E99"]),
    lambda p:p.update(evidence_refs=[]),
    lambda p:p.update(evidence_refs=["E1","E1"]),
    lambda p:p["pasos"][0].update(accion=
        "Consultar SEC.taUsuarioBitacora, perfil del empleado."),
    lambda p:p["faltantes"].append("Verificar ADM.taActivoTrabajador"),
    lambda p:p["cierre"].append("Leer dbo.taIncidente"),
    lambda p:p.update(ejecutado=True),
])
def test_cannot_promote_catalog_unknown_table_or_false_execution(override):
    p=grounded_plan();override(p)
    assert provenance(p)["accepted"] is False

def test_do_not_accept_invalid_receipt_even_with_valid_plan():
    p=grounded_plan()
    assert not evidence_provenance_gate(p,native_o5_verified=False,
                                        source_receipt_sha256=RECEIPT)["accepted"]
    assert not evidence_provenance_gate(p,native_o5_verified=True,
                                        source_receipt_sha256=123)["accepted"]

def test_full_contract_includes_role_review_not_authorized_to_repair():
    p=grounded_plan()
    quality=evaluate_grounded_plan(p,evidence=[
        {"ref":"E1","observation":"Caso observado en ITIL QA; no reparado."},
        {"ref":"E2","observation":"Clasificación histórica de incidencia."}],
        source_receipt_sha256=RECEIPT)
    assert quality["accepted"] is True
    assert quality["status"] in ("DIAGNOSTIC_GUIDANCE",
                                 "ACTION_PLAN_AUTHORIZATION_PENDING",
                                 "ACTION_PLAN_REVIEWABLE")
    assert any("ROLE_MAPPING_PENDING" in f
               for f in quality.get("review_flags",[]))
    assert quality["grounded_acceptance_not_causal_truth"]

class Responses:
    def __init__(self,*plans):
        self.responses=list(plans);self.messages=[]
    def complete(self,messages):
        self.messages.append(messages)
        if not self.responses:raise RuntimeError("NO_UNEXPECTED_MODEL_RETRY")
        return json.dumps(self.responses.pop(0))

def setup(tmp_path):
    opened="2026-02-18T10:11:00"
    case={
      "schema":"else.itil.qa.sanitized-case.operator-submitted.v1",
      "case_sha256":CASE,"service_code":"1","module_code":"0109100100000",
      "opened_at":opened,
      "description":"Solicitud de prueba sobre acceso a un módulo, aún no resuelta.",
      "historical_solution":"WITHHELD",
      "content_provenance":"PRIVATE_HISTORICAL_EXPORT_NOT_BYTE_EQUAL_QA_SQL",
      "model_may_execute_sql":False}
    receipt={
      "schema":TRANSFER_SCHEMA,"scope":QA_SCOPE,"query_id":QUERY_ID,
      "case_sha256":CASE,"hand_source_sha256":SOURCE,
      "hand_manifest_sha256":"9"*64,"opened_at":opened,
      "service_code":"1","module_code":"0109100100000",
      "classification_code":"101","origin_code":"01","status_code":"03",
      "request_bytes":"350","issued_at_utc":"2026-11-10T10:00:00.000000Z",
      "row_count":1,"read_only":True,"provenance_verified":True,
      "historical_solution_not_read":True,
      "deterministic_source_binding_passed":True,
      "negative_sha_tamper_rejected":True,
      "functional_repair_certified":False,
      "core_o5_native_registration":False}
    p=tmp_path/"receipt.json";b=json.dumps(receipt,sort_keys=True).encode()
    p.write_bytes(b)
    owner=AuthorizedNugetReceipt(
        p,sha256(b).hexdigest(),CASE,SOURCE,2000)
    tool={"type":"tool","name":"qa_exact_read","query_id":QUERY_ID,
          "parameters":{"case_sha256":CASE}}
    return owner,case,tool

def test_real_native_o5_first_plan_grounded_no_second_model_call(tmp_path):
    owner,case,tool=setup(tmp_path);model=Responses(grounded_plan())
    result=finish_fresh_qa_case(owner=owner,case=case,tool_request=tool,model=model)
    assert result["o5_o13_o15_verified"] is True
    assert result["quality"]["accepted"] is True
    assert result["model_attempts"]==1
    assert result["observed_sources"]==["ITIL.taIncidente"]
    assert result["repair_certified"] is False
    assert "historical_solution" not in model.messages[0][0]["content"]
    assert "ITIL.taIncidente" in model.messages[0][0]["content"]

def test_real_native_o5_one_model_regeneration_no_posthoc_source_patch(tmp_path):
    owner,case,tool=setup(tmp_path)
    bad=grounded_plan()
    bad["fuentes"]=["ITIL.taIncidente","SEC.taUsuario"]
    bad["pasos"][0]["accion"]="Consultar SEC.taUsuario sin autorización."
    model=Responses(bad,grounded_plan())
    result=finish_fresh_qa_case(owner=owner,case=case,tool_request=tool,model=model)
    assert result["model_attempts"]==2
    assert result["quality"]["accepted"] is True
    assert result["proposal"]["fuentes"]==["ITIL.taIncidente"]
    assert any("UNOBSERVED_SQL_TABLE_MENTION" in flag for flag in
               result["first_attempt_flags"])
    assert model.messages[1][-1]["role"]=="user"
    assert result["approved_for_training"] is False

def test_two_unsupported_model_outputs_stay_quarantined(tmp_path):
    owner,case,tool=setup(tmp_path)
    bad=grounded_plan()
    bad["fuentes"]=["SEC.taUsuario"]
    model=Responses(bad,bad)
    result=finish_fresh_qa_case(owner=owner,case=case,tool_request=tool,model=model)
    assert result["quality"]["accepted"] is False
    assert result["proposal"]=={}
    assert result["status"]=="NEEDS_HUMAN_TRIAGE"
    assert result["model_attempts"]==2

def test_no_repair_attempt_after_two_invalid_outputs(tmp_path):
    owner,case,tool=setup(tmp_path)
    bad=grounded_plan()
    bad["ejecutado"]=True;bad["confirmado"]=True
    model=Responses(bad,bad)
    result=finish_fresh_qa_case(owner=owner,case=case,tool_request=tool,model=model)
    assert result["proposal"]=={}
    assert result["repair_certified"] is False
    assert result["o5_o13_o15_verified"] is True

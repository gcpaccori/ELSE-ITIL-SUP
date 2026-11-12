"""Synthetic exact-source anchor and model separation tests."""
from hashlib import sha256
from unittest.mock import patch
import json,pytest

from else_dominance.functional_investigator_v2 import (
    run_case,frozen_fact_quotes)
from else_dominance.functional_domain_v2 import route
from else_dominance.functional_contract_v2 import SCHEMA

TEXT="El buzón de correo del usuario está lleno y no recibe mensajes."
SHA=sha256(b"synthetic-v2-engine-anchor").hexdigest()
ROW={"ticket_sha256":SHA,"incident_text_redacted":TEXT}

def valid_raw():
    r=route(TEXT)
    assert r["domain"]=="EMAIL"
    return {
        "schema":SCHEMA,"domain":r["domain"],
        "target_system":r["target_system"],
        "intent":"Determinar si la cuota de correo impide la recepción de mensajes",
        "ticket_fact_quotes":["Buzón lleno por error del hardware inventado"],
        "hypotheses":["El buzón podría haber alcanzado el límite de almacenamiento."],
        "checks":[{
            "target_system":r["target_system"],
            "business_object":"Cuota del buzón afectado",
            "input_identifier":"Buzón del usuario pendiente de identificar",
            "observable":"Cantidad de almacenamiento ocupada y cuota máxima del buzón",
            "expected":"Uso del almacenamiento inferior al límite configurado para el buzón",
            "if_expected":"Comprobar reglas de transporte o problemas de recepción distintos de cuota",
            "if_different":"Solicitar liberar espacio autorizado y repetir prueba de recepción",
            "execution":"NOT_EXECUTED","observation_status":"NOT_READ",
        }],
        "missing_evidence":["Cuenta de correo autorizada y medida real de cuota"],
        "observed_sources":["ITIL.taIncidente"],"evidence_refs":["E1"],
        "domain_evidence_status":"NOT_READ",
        "executed":False,"repair_certified":False,
        "root_cause_certified":False,
    }

def test_deterministic_source_quote_replaces_untrusted_llm_text_transparently():
    generated=valid_raw()
    with patch("else_dominance.functional_investigator_v2.call_model",
               return_value=generated):
        result=run_case(ROW,max_attempts=1)
    assert result["status"]=="FUNCTIONAL_DRAFT_CONTRACT_PASS"
    assert result["source_fact_binding"]["substitution_declared"] is True
    assert result["source_fact_binding"]["model_quotes_exact"] is False
    assert result["proposal"]["ticket_fact_quotes"]==frozen_fact_quotes(TEXT)
    assert result["historical_resolution_exposed"] is False
    assert result["live_domain_evidence_verified"] is False
    assert result["repair_certified"] is False

def test_unverified_sql_table_in_model_is_not_fixed_by_engine_anchor():
    p=valid_raw()
    p["checks"][0]["observable"]+=" desde COM.taInventada"
    with patch("else_dominance.functional_investigator_v2.call_model",
               return_value=p):
        result=run_case(ROW,max_attempts=1)
    assert result["status"]=="FUNCTIONAL_DRAFT_REJECTED"
    assert not result["quality"]["accepted"]
    assert "UNOBSERVED_SQL_OBJECT_CITED" in result["quality"]["flags"]
    assert result["proposal"]=={}

def test_false_execution_claim_never_promoted_even_with_exact_quote():
    p=valid_raw()
    p["executed"]=True
    with patch("else_dominance.functional_investigator_v2.call_model",
               return_value=p):
        result=run_case(ROW,max_attempts=1)
    assert result["status"]=="FUNCTIONAL_DRAFT_REJECTED"
    assert "FALSE_OBSERVATION_EXECUTION_OR_REPAIR" in result["quality"]["flags"]

def test_unknown_domain_never_calls_qwen():
    short={"ticket_sha256":SHA,"incident_text_redacted":
           "Por favor apoyo, ver archivo adjunto para más detalle"}
    with patch("else_dominance.functional_investigator_v2.call_model",
               side_effect=AssertionError("UNKNOWN_MODEL_CALLED")):
        result=run_case(short,max_attempts=1)
    assert result["status"]=="CLARIFICATION_REQUIRED"
    assert result["attempts"]==0
    assert result["repair_certified"] is False

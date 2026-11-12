"""Adversarial Beta functional route and diagnostic contract tests.

No service, SQL or LLM needed. Domains are hints, never evidence receipts.
"""
from __future__ import annotations
from hashlib import sha256
import json,pytest

from else_dominance.functional_domain_v2 import route,DOMAINS
from else_dominance.functional_contract_v2 import (
    check_plan,sql_mentions,SCHEMA)

CASES=[
 ("Corrección de códigos de liquidación de materiales",
  "COMMERCIAL_MATERIALS"),
 ("La orden de trabajo OT 177444 no abre al cambiar razón social",
  "COMMERCIAL_OT"),
 ("Por favor verificar la OT de reconexión y su estado",
  "COMMERCIAL_OT"),
 ("Tras facturación el consumo debe reflejar 14 unidades",
  "COMMERCIAL_BILLING"),
 ("Error en módulo 188 FISE, registrar teléfono del beneficiario",
  "COMMERCIAL_FISE"),
 ("MGD no permite derivar documento, coordinadora FISE",
  "MGD"),
 ("SAP VL75 exporta PDF blanco",
  "SAP"),
 ("En Outlook llegó rechazo SMTP 554 5.4.12 de else10.else.com.pe",
  "EMAIL"),
 ("El buzón de correo se encuentra lleno",
  "EMAIL"),
 ("Contraseñas de GOS no se pueden restablecer",
  "IAM"),
 ("Reinstalar SIELSE en equipo formateado",
  "ENDPOINT_SOFTWARE"),
 ("No se imprime reporte de valorización",
  "ENDPOINT_PRINT"),
 ("Horas extras no se pueden registrar con fecha pasada",
  "HR"),
 ("cambio en SIRE para notas de crédito RVIE",
  "TAX_REPORTING"),
 ("Transferir material de dos liquidaciones",
  "COMMERCIAL_MATERIALS"),
 ("Se perdió el celular, recuperar chip",
  "TELECOM"),
 ("Solicito control de cámaras PTZ",
  "SECURITY_VIDEO"),
 ("Consulto en qué jornadas comerciales están los técnicos",
  "COMMERCIAL_SCHEDULE"),
 ("Error sin descripción, adjunto imagen",
  "UNKNOWN"),
]

@pytest.mark.parametrize("text,expected",CASES)
def test_router_recognizes_functional_domain_without_fake_reads(text,expected):
    result=route(text)
    assert result["domain"]==expected
    assert result["current_domain_state_verified"] is False
    assert result["domain_evidence_status"]=="NOT_READ"
    assert not result["read_hand_registered"]
    assert result["read_hand_id"] is None

def plan(domain="EMAIL",text="Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe"):
    routed=route(text)
    assert routed["domain"]==domain
    return {
        "schema":SCHEMA,
        "domain":domain,
        "target_system":routed["target_system"],
        "intent":"Localizar la razón del rechazo SMTP y comprobar el reenvío",
        "ticket_fact_quotes":["Rebote de correo SMTP 554 5.4.12"],
        "hypotheses":["Podría existir un reenvío circular en la ruta de correo."],
        "checks":[{
            "target_system":routed["target_system"],
            "business_object":"Ruta de transporte SMTP del mensaje rechazado",
            "input_identifier":"Identificador del mensaje pendiente de obtener",
            "observable":"Saltos de transporte y repetición de servidores en cabeceras",
            "expected":"No aparecen saltos repetidos ni rebotes cíclicos",
            "if_expected":"Revisar si la entrega al destino completa la operación",
            "if_different":"Examinar las reglas de reenvío de correo con el operador",
            "execution":"NOT_EXECUTED","observation_status":"NOT_READ"
        }],
        "missing_evidence":["Cabeceras completas del mensaje rechazado"],
        "observed_sources":["ITIL.taIncidente"],
        "evidence_refs":["E1"],
        "domain_evidence_status":"NOT_READ",
        "executed":False,"repair_certified":False,
        "root_cause_certified":False,
    },routed

def test_valid_smtp_domain_with_com_pe_does_not_count_as_sql_table():
    p,r=plan()
    assert sql_mentions(p)==(["ITIL.TAINCIDENTE"],[])
    v=check_plan(p,"Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe",r)
    assert v["accepted"] and v["functionally_actionable"]
    assert not v["business_source_accessed"]

@pytest.mark.parametrize("bad",[
    "ITIL.taUsuario","dbo.taCobranza","COM.taOrdenTrabajo",
    "taUsuario", "taOrdenTrabajo",
])
def test_actual_foreign_sql_objects_denied(bad):
    t="Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe"
    p,r=plan(text=t)
    p["checks"][0]["observable"]+=" "+bad
    v=check_plan(p,t,r)
    assert "UNOBSERVED_SQL_OBJECT_CITED" in v["flags"]

def test_itil_ticket_state_cannot_substitute_current_sap_state():
    t="Error SMTP 554 5.4.12 else10.else.com.pe"
    p,r=plan(text=t)
    p["ticket_fact_quotes"]=["Error SMTP 554 5.4.12"]
    p["checks"][0]["observable"]="Estado del ticket ITIL.taIncidente después del error"
    v=check_plan(p,t,r)
    assert "ITIL_ENVELOPE_USED_AS_DOMAIN_EVIDENCE" in v["flags"]

@pytest.mark.parametrize("value",[
 "El valor es WITHHELD, por tanto ticket está cerrado",
 "Se verificó que el servidor funciona",
 "Hemos modificado la configuración de destino",
])
def test_no_laundered_sentinel_or_unverified_status(value):
    t="Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe"
    p,r=plan(text=t)
    p["intent"]=value
    v=check_plan(p,t,r)
    assert not v["accepted"]

def test_registered_hand_is_not_a_queried_source():
    t="Error SMTP 554 5.4.12 en correo"
    r=route(t,verified_hands={"EMAIL":"itil.qa.mail.exact.read.v1"})
    assert r["read_hand_registered"]
    assert not r["current_domain_state_verified"]
    p,_=plan()
    p["domain_evidence_status"]="READ"
    v=check_plan(p,t,r)
    assert "FALSE_OBSERVATION_EXECUTION_OR_REPAIR" in v["flags"]

def test_wrong_target_system_rejected():
    t="Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe"
    p,r=plan(text=t)
    p["checks"][0]["target_system"]="ITIL.taIncidente"
    assert "CHECK_NOT_IN_ROUTED_SYSTEM" in check_plan(p,t,r)["flags"]

def test_fact_must_be_exactly_present_in_original_ticket():
    t="Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe"
    p,r=plan(text=t)
    p["ticket_fact_quotes"]=["El servidor bloquea por permisos no probados"]
    assert "FACT_NOT_SUBSTRING_OF_REQUEST" in check_plan(p,t,r)["flags"]

def test_identical_if_and_else_not_discriminating():
    t="Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe"
    p,r=plan(text=t)
    p["checks"][0]["if_expected"]=p["checks"][0]["if_different"]
    assert "CHECK_BOTH_BRANCHES_IDENTICAL" in check_plan(p,t,r)["flags"]

def test_sql_modification_rejected_without_any_execution():
    t="Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe"
    p,r=plan(text=t)
    p["checks"][0]["if_different"]="UPDATE dbo.taUsuario SET Estado=0"
    v=check_plan(p,t,r)
    assert "EXECUTABLE_SQL_MUTATION_NOT_ALLOWED" in v["flags"]
    assert "UNOBSERVED_SQL_OBJECT_CITED" in v["flags"]

def test_claims_of_real_repair_not_allowed():
    t="Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe"
    p,r=plan(text=t)
    p["repair_certified"]=True
    assert "FALSE_OBSERVATION_EXECUTION_OR_REPAIR" in check_plan(p,t,r)["flags"]

def test_zero_value_direction_inversion_rejected():
    t="El precio aparece 0.00 y se solicita actualizarlo"
    r=route(t)
    p,_=plan()
    p["domain"]=r["domain"]
    p["target_system"]=r["target_system"]
    p["ticket_fact_quotes"]=["El precio aparece 0.00"]
    p["intent"]="Actualizar el precio a 0.00 para cerrar la solicitud"
    p["checks"][0]["target_system"]=r["target_system"]
    v=check_plan(p,t,r)
    assert "REQUEST_INTENT_REVERSED_ZERO_VALUE" in v["flags"]

def test_unknown_clarification_does_not_attempt_other_domain():
    r=route("Por favor ayudar, adjunto documento")
    assert r["domain"]=="UNKNOWN"
    assert r["needs_clarification"]


def test_unverified_smtp_hop_threshold_is_rejected():
    text="Rebote de correo SMTP 554 5.4.12 en else10.else.com.pe"
    p,r=plan(text=text)
    p["checks"][0]["expected"]="El servidor debe permitir un máximo exacto de 50 saltos."
    q=check_plan(p,text,r)
    assert "NUMERIC_EXPECTATION_NOT_GROUNDED" in q["flags"]

def test_specific_password_collection_is_not_appropriate_for_iam():
    text="No puedo restablecer contraseña de mi usuario"
    r=route(text)
    p,_=plan()
    p["domain"]=r["domain"]
    p["target_system"]=r["target_system"]
    p["checks"][0]["target_system"]=r["target_system"]
    p["ticket_fact_quotes"]=["restablecer contraseña de mi usuario"]
    p["missing_evidence"]=["Nueva contraseña específica deseada por el usuario"]
    assert "CREDENTIAL_DISCLOSURE_REQUEST" in check_plan(p,text,r)["flags"]

def test_unverified_named_role_must_not_be_required_as_expected():
    text="No puedo restablecer contraseña de mi usuario"
    r=route(text)
    p,_=plan()
    p["domain"]=r["domain"]
    p["target_system"]=r["target_system"]
    p["checks"][0]["target_system"]=r["target_system"]
    p["ticket_fact_quotes"]=["restablecer contraseña de mi usuario"]
    p["checks"][0]["expected"]="El usuario debe tener rol 'Administrador' en el sistema."
    assert "ROLE_NAME_NOT_IN_VERIFIED_EVIDENCE" in check_plan(p,text,r)["flags"]

def test_generic_target_without_named_field_fails():
    text="El módulo 188 muestra un error no especificado"
    r=route(text)
    p,_=plan()
    p["domain"]=r["domain"]
    p["target_system"]=r["target_system"]
    p["checks"][0]["target_system"]=r["target_system"]
    p["ticket_fact_quotes"]=["El módulo 188 muestra"]
    p["checks"][0]["observable"]="Valor actual del campo objetivo"
    assert "GENERIC_TARGET_NOT_MEASURABLE" in check_plan(p,text,r)["flags"]

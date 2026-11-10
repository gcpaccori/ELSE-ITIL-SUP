"""Pareto QA lane and evidence-gate tests. Synthetic inputs only."""
from __future__ import annotations
from hashlib import sha256

import pytest

from else_dominance.pareto_evidence import (
    decide_lane,route_case,evidence_gate,LANE_REQUIRED)

CASE=sha256(b"synthetic-jan10-case").hexdigest()


@pytest.mark.parametrize("service,description,expected",[
    ("1","Descuadre del suministro y medidor comercial","COMMERCIAL_OT"),
    ("1","Orden de trabajo sin materiales asociados","COMMERCIAL_OT"),
    ("3","Pedido de almacen sin confirmacion SAP","SAP_INTEGRATION"),
    ("3","Fallo al comunicar por BAPI desde sistema","SAP_INTEGRATION"),
    ("70","No aparece permiso efectivo del usuario","ACCESS_PERMISSIONS"),
    ("2","Falla intermitente al abrir la pantalla principal","APPLICATION"),
    ("1","Incidencia recibida por mesa de ayuda, pendiente.","ITIL_TRIAGE"),
    ("1","Equipo reporta error de facturación","COMMERCIAL_OT"),
    ("70","Solicitud de acceso a módulo SAP","SAP_INTEGRATION"),
])
def test_lanes(service,description,expected):
    assert decide_lane(service_code=service,description=description)==expected


def test_model_contract_does_not_count_as_evidence():
    route=route_case(case_sha256=CASE,service_code="1",
                     description="Suministro con saldo no concordante")
    result=evidence_gate(route=route,model_completed=True,
                         original_contract_pass=True)
    assert result["status"]=="MISSING_VERIFIED_EVIDENCE"
    assert result["contract_passed"] is True
    assert result["domain_evidence_complete"] is False
    assert result["repair_certified"] is False
    assert result["automatic_training"] is False


def test_verified_itil_metadata_is_not_commercial_qa():
    route=route_case(case_sha256=CASE,service_code="1",
                     description="Lectura de medidor con anomalía",
                     verified_receipt_categories=frozenset({"ITIL_CASE_EXACT"}))
    assert route.missing_receipts==("COMMERCIAL_OT_EXACT",)
    assert route.public()["root_cause_certified"] is False


def test_sap_cannot_use_ot_number_text_as_bind_receipt():
    route=route_case(case_sha256=CASE,service_code="3",
                     description="SAP: OT: 123456789 sin número de confirmación",
                     verified_receipt_categories=frozenset({"ITIL_CASE_EXACT"}))
    assert route.ot_identifier_reported is True
    assert "SAP_OT_BINDING" in route.missing_receipts
    assert "SAP_ORDER_AND_RESPONSE" in route.missing_receipts
    assert "123456789" not in str(route.public())


def test_generic_itil_only_after_native_receipt_reviewable_not_certified():
    route=route_case(case_sha256=CASE,service_code="2",
                     description="Incidencia sin clasificación técnica",
                     verified_receipt_categories=frozenset({"ITIL_CASE_EXACT"}))
    result=evidence_gate(route=route,model_completed=True,
                         original_contract_pass=True)
    assert result["status"]=="REVIEWABLE_NOT_CERTIFIED"
    assert result["repair_certified"] is False


def test_no_model_completion_claims_validity():
    route=route_case(case_sha256=CASE,service_code="1",
                     description="Suministro con problema comercial")
    result=evidence_gate(route=route,model_completed=False,
                         original_contract_pass=True)
    assert result["status"]=="MODEL_INCOMPLETE"


def test_technical_contract_failure_wins_over_evidence():
    route=route_case(case_sha256=CASE,service_code="1",
                     description="Incidencia genérica ITIL de prueba")
    result=evidence_gate(route=route,model_completed=True,
                         original_contract_pass=False)
    assert result["status"]=="MODEL_CONTRACT_REJECTED"


def test_invalid_or_unbound_receipt_category_rejected():
    with pytest.raises(ValueError,match="RECEIPT_CATEGORY_INVALID"):
        route_case(case_sha256=CASE,service_code="1",
                   description="Suministro afectado",
                   verified_receipt_categories={"SQL_FROM_MODEL"})


def test_invalid_case_hash_rejected():
    with pytest.raises(ValueError,match="CASE_SHA_INVALID"):
        route_case(case_sha256="0"*63,service_code="1",
                   description="Caso sintético sin detalle")


def test_no_substitution_of_corporate_service_definitions():
    route=route_case(case_sha256=CASE,service_code="1",
                     description="Un incidente de acceso al equipo")
    assert route.service_code=="1"
    assert route.lane=="ACCESS_PERMISSIONS"
    assert route.case_in_pareto_services is True
    assert "SEC_EFFECTIVE_PERMISSION" in route.missing_receipts

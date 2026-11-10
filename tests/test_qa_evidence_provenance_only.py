"""Standalone provenance contract tests without private ELSE CORE dependency."""
from __future__ import annotations
import pytest
from else_dominance.qa_evidence_grounding import (
    evidence_provenance_gate, normalized_mentions)

SHA="a"*64

def plan(action="Probar acceso al módulo desde cuenta autorizada"):
    return {
        "fuentes":["ITIL.taIncidente"],
        "evidence_refs":["E1","E2"],
        "pasos":[{"condicion":"Si se reproduce el síntoma",
                  "accion":action,
                  "responsable":"Técnico autorizado pendiente de validar",
                  "verificacion":"Reproducir la operación con registro de resultado"}],
        "faltantes":["Confirmar el estado funcional exacto"],
        "cierre":["Verificar operación original sin síntomas posteriores"],
        "ejecutado":False,
        "confirmado":False,
    }

def audit(value):
    return evidence_provenance_gate(
        value,native_o5_verified=True,source_receipt_sha256=SHA)

def test_only_real_observed_source_is_accepted_without_false_approval():
    p=plan()
    r=audit(p)
    assert r["accepted"] is True
    assert r["receipt_bound"] is True
    assert r["observed_sources"]==["ITIL.taIncidente"]

@pytest.mark.parametrize("sql",[
    "SEC.taUsuario","SEC.[taUsuario]","[SEC].[taUsuario]",
    '"SEC"."taUsuario"',"dbo.taIncidente","ADM.taActivoTrabajador",
    "taArqueoGuardar","taUsuarioBitacora",
])
def test_sql_object_in_any_model_field_must_not_be_laundered(sql):
    for field in ("accion","faltantes","cierre"):
        p=plan()
        if field=="accion":
            p["pasos"][0]["accion"]="Consultar "+sql+" sin fuente."
        else:
            p[field]=["Solicitar comprobación de "+sql+" pendiente"]
        r=audit(p)
        assert r["accepted"] is False
        assert ("UNOBSERVED_SQL_OBJECT_MENTION" in r["flags"] or
                "UNOBSERVED_SQL_TABLE_MENTION" in r["flags"])

def test_itil_sentence_period_is_not_sql_table():
    p=plan()
    p["pasos"][0]["accion"]="ITIL. El procedimiento requiere validar la cuenta."
    assert audit(p)["accepted"]

@pytest.mark.parametrize("bad_source",[
    ["SEC.taUsuario"],["ITIL.taIncidente","SEC.taUsuario"],
    ["ITIL.taIncidente","ITIL.taIncidente"],[],
])
def test_source_catalog_is_not_a_query(bad_source):
    p=plan()
    p["fuentes"]=bad_source
    assert audit(p)["accepted"] is False

@pytest.mark.parametrize("bad_refs",[
    [],["E3"],["E1","E1"],
])
def test_evidence_refs_only_registered_real_receipts(bad_refs):
    p=plan()
    p["evidence_refs"]=bad_refs
    assert audit(p)["accepted"] is False

@pytest.mark.parametrize("field",["faltantes","cierre"])
def test_closure_and_missing_evidence_must_be_explicit(field):
    p=plan()
    p[field]=[]
    assert audit(p)["accepted"] is False

def test_fake_receipt_or_execution_claim_rejected():
    p=plan()
    assert not evidence_provenance_gate(
        p,native_o5_verified=False,source_receipt_sha256=SHA)["accepted"]
    assert not evidence_provenance_gate(
        p,native_o5_verified=True,source_receipt_sha256="0")["accepted"]
    p["ejecutado"]=True
    assert not audit(p)["accepted"]

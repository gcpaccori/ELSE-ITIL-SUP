"""Synthetic invariants for August 1819-case blinded QA (no network/SQL)."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,pytest

from qa import qa_aug2026_full as aug

SHA=sha256(b"synthetic-Aug2026-case").hexdigest()
ROW={
    "schema":"else.itil.aug2026.blind-case.v1",
    "ticket_sha256":SHA,"month":"2026-08",
    "opened_at":"2026-08-13T13:45:00",
    "service_code":"1","module_code":"0101100100000",
    "classification_code":"101",
    "incident_text_redacted":
        "La operación de consulta registra una incidencia de prueba "
        "y requiere comprobar el módulo con el técnico de QA.",
    "historical_resolution":"WITHHELD",
    "live_state":"NOT_OBSERVED",
    "model_tools_enabled":False,
    "privacy_transform":"WINDOWS_REDACTED_QA",
}

def valid_plan():
    return {
        "estado":"INVESTIGACION_ESPECIFICA",
        "diagnostico":"La solicitud describe una falla pero no demuestra su causa.",
        "hipotesis":["La operación puede requerir verificar un estado previo."],
        "fuentes":["ITIL.taIncidente"],
        "evidence_refs":["E1"],
        "pasos":[{
            "condicion":"Si el solicitante puede reproducir el error en QA",
            "accion":"Registrar el resultado de la operación y contrastar los pasos",
            "responsable":"Responsable autorizado por confirmar",
            "verificacion":"Repetir la operación y comparar el resultado esperado",
        }],
        "faltantes":["Resultado de una reproducción autorizada del incidente"],
        "cierre":["Comprobar la operación funcional sin el síntoma reportado"],
        "ejecutado":False,"confirmado":False,
    }

def test_only_redacted_case_and_withheld_gold_reach_model():
    payload=aug.model_input(ROW)
    assert payload["historical_solution"]=="WITHHELD"
    assert "historical_solution_withheld" not in payload
    assert "incident_text" not in payload
    assert payload["request_redacted_untrusted"]==ROW["incident_text_redacted"]
    assert payload["current_sql_or_iam_queries_executed"] is False
    assert payload["source_catalog"]==["ITIL.taIncidente"]
    assert payload["evidence"][0]["ref"]=="E1"

def test_one_exact_verified_source_is_structurally_accepted():
    result=aug.gate(valid_plan())
    assert result["accepted"] is True
    assert result["live_source_queried"] is False
    assert result["repair_certified"] is False

@pytest.mark.parametrize("mutate",[
    lambda p:p.update(fuentes=["ITIL.taIncidente","SEC.taUsuario"]),
    lambda p:p.update(fuentes=[]),
    lambda p:p.update(evidence_refs=["E9"]),
    lambda p:p.update(ejecutado=True),
    lambda p:p.update(confirmado=True),
    lambda p:p["pasos"][0].update(responsable="Administrador SQL"),
    lambda p:p["pasos"][0].update(accion="Consultar SEC.taUsuario"),
    lambda p:p.update(cierre=[]),
    lambda p:p.update(rol_oficial_validado=True),
])
def test_false_source_role_or_completion_is_rejected(mutate):
    p=valid_plan()
    mutate(p)
    result=aug.gate(p)
    assert result["accepted"] is False

def test_replay_requires_exact_same_input_sha_and_model(tmp_path,monkeypatch):
    path=tmp_path/"journal.private.jsonl"
    monkeypatch.setattr(aug,"JOURNAL",path)
    rec={
        "ticket_sha256":SHA,
        "blind_sha256":"a"*64,
        "case_input_sha256":sha256(aug.canonical(ROW)).hexdigest(),
        "model":aug.MODEL,"month":"2026-08",
        "historical_gold_exposed":False,"repairs_certified":False,
    }
    path.write_bytes(aug.canonical(rec)+b"\n")
    assert list(aug.read_done([ROW],"a"*64))==[SHA]
    with pytest.raises(ValueError,match="REPLAY_SOURCE_OR_VERSION_MISMATCH"):
        aug.read_done([ROW],"b"*64)
    path.write_bytes(aug.canonical(rec)+b"\n"+aug.canonical(rec)+b"\n")
    with pytest.raises(ValueError,match="REPLAY_ID_NOT_UNIQUE"):
        aug.read_done([ROW],"a"*64)

def test_short_request_is_processed_without_model(monkeypatch):
    def fail(_):
        raise RuntimeError("MODEL_MUST_NOT_BE_CALLED")
    monkeypatch.setattr(aug,"complete",fail)
    row={**ROW,"incident_text_redacted":"No funciona."}
    out=aug.analyze(row,"a"*64)
    assert out["status"]=="INSUFFICIENT_REQUEST_TEXT"
    assert not out["model_completed"]
    assert not out["structural_accepted"]
    assert not out["repairs_certified"]

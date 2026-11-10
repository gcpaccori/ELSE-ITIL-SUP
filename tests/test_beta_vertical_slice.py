"""Contract tests for V1 Beta two-Hand supervised flow (synthetic only)."""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json
import pytest

pytest.importorskip("else_core.itil_feb100_sap_ot_o5_hand",
                  reason="New native CORE SAP/OT Hand requires stacked PR")
from else_dominance.beta_vertical_slice import beta_plan_gate,SOURCES
from else_dominance.beta_supervision import BetaSupervisionLedger
from test_qa_native_runtime import good_plan

CASE=sha256(b"qa-beta-synthetic").hexdigest()
ITIL="a"*64
SAP="b"*64

def plan():
    p=good_plan()
    p["fuentes"]=sorted(SOURCES)
    p["evidence_refs"]=["E1","E2","E3"]
    p["faltantes"]=["Confirmar relación de negocio entre la OT y el expediente."]
    p["cierre"]=["Verificar resultado funcional con técnico responsable."]
    p["vinculacion_comercial_verificada"]=False
    p["rol_oficial_validado"]=False
    for step in p["pasos"]:
        step["responsable"]="Responsable autorizado por confirmar"
    return p

def evidence():
    return [{"ref":"E1","observation":"Recibo ITIL O5 autenticado"},
            {"ref":"E2","observation":"Recibo OT SAP O5 autenticado"},
            {"ref":"E3","observation":"Respuesta SAP QA con salida acotada"}]

def test_plan_requires_both_actual_read_sources_and_review():
    g=beta_plan_gate(plan(),evidence())
    assert g["accepted"] is True
    assert g["business_entity_link_verified"] is False
    assert g["repair_certified"] is False
    assert g["human_approval_required"] is True
    assert g["review_flags"]

@pytest.mark.parametrize("modify",[
    lambda p:p.update(fuentes=["ITIL.taIncidente"]),
    lambda p:p.update(fuentes=["dbo.taOrdenTrabajoSAP"]),
    lambda p:p.update(evidence_refs=["E1"]),
    lambda p:p.update(ejecutado=True),
    lambda p:p.update(confirmado=True),
    lambda p:p["pasos"][0].update(accion="Consultar SEC.taUsuario como hecho."),
    lambda p:p.update(faltantes=[]),
    lambda p:p.update(cierre=[]),
])
def test_invalid_plan_stays_in_human_triage(modify):
    p=plan()
    modify(p)
    assert beta_plan_gate(p,evidence())["accepted"] is False

def report():
    return {
      "schema":"else.itil.v1beta.dual-hand.supervised-investigation.v1",
      "case_sha256":CASE,"status":"PENDING_TECHNICIAN_REVIEW",
      "native_itil_verified":True,"native_sap_ot_verified":True,
      "business_join_certified":False,
      "source_receipts":{"itil":ITIL,"sap_ot":SAP},
      "quality":{"accepted":True},"proposal":plan(),
      "repair_certified":False,"root_cause_certified":False,
      "human_review_required":True}

def test_review_ledger_fails_closed_without_real_reviewer_credentials(tmp_path):
    db=(tmp_path/"ledger.sqlite").absolute()
    with BetaSupervisionLedger(db) as ledger:
        r=ledger.record(report())
        assert r["status"]=="PENDING_TECHNICIAN_REVIEW"
        assert ledger.record(report())==r
        assert ledger.aggregate()["recorded_human_review_events"]==0
        with pytest.raises(ValueError,match="REVIEWER_ROSTER_NOT_CONFIGURED"):
            ledger.review(case_sha256=CASE,reviewer_id="QAReviewer",
                          reviewer_secret="synthetic-credential-1234567890-abcdef",
                          decision="USEFUL_FOR_TECHNICIAN",
                          note="La prueba fue un ensayo sintético sin revisor real")
        assert ledger.status(CASE)["reviews_count"]==0

def test_two_part_technician_review_in_synthetic_environment(tmp_path):
    secret="synthetic-only-reviewer-secret-9876543210"
    registry=tmp_path/"reviewers.private.json"
    registry.write_text(json.dumps({"ReviewerQA":sha256(secret.encode()).hexdigest()}))
    registry.chmod(0o600)
    with BetaSupervisionLedger((tmp_path/"ledger.sqlite").absolute(),registry) as ledger:
        ledger.record(report())
        with pytest.raises(ValueError):
            ledger.review(case_sha256=CASE,reviewer_id="ReviewerQA",
                          reviewer_secret="incorrect-but-long-synthetic-secret",
                          decision="USEFUL_FOR_TECHNICIAN",
                          note="Prueba sintética registrada sin autorización")
        accepted=ledger.review(case_sha256=CASE,reviewer_id="ReviewerQA",
                               reviewer_secret=secret,
                               decision="NEEDS_MORE_EVIDENCE",
                               note="Revisar el vínculo comercial antes de intervenir.")
        assert accepted["human_review_recorded"] is True
        assert accepted["repair_certified"] is False
        assert ledger.status(CASE)["reviews_count"]==1
        with pytest.raises(ValueError):
            ledger.review(case_sha256=CASE,reviewer_id="ReviewerQA",
                          reviewer_secret=secret,decision="USEFUL_FOR_TECHNICIAN",
                          note="Cambio de criterio sin dejar nueva evidencia")



def test_nonapproved_responsible_team_is_blocked():
    p=plan()
    p["pasos"][0]["responsable"]="Administrador de aplicación"
    assert beta_plan_gate(p,evidence())["accepted"] is False


def test_false_business_join_and_role_approval_are_blocked():
    for field in ("vinculacion_comercial_verificada","rol_oficial_validado"):
        p=plan()
        p[field]=True
        assert beta_plan_gate(p,evidence())["accepted"] is False

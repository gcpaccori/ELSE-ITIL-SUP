import copy
import hashlib
import json
import pytest

from else_dominance.apprenticeship_v1 import (
    learning_messages, select_2025_curriculum, draft_2025_case, validated_input,
)


def sample(month, seq=0):
    digest=hashlib.sha256(f"{month}:{seq}".encode()).hexdigest()
    return {
        "case_sha256": digest, "year": 2025, "month": month,
        "label_status": "UNVERIFIED_HISTORIC_2025",
        "user": "Servicio TIC; incidencia ficticia de impresión sin respuesta en la oficina.",
        "assistant_target": "Antecedente no verificado: revisar la cola de impresión y solicitar prueba.",
    }


class FakeModel:
    def __init__(self):
        self.calls = []
    def complete(self, messages):
        self.calls.append(messages)
        return json.dumps({
            "estado": "INVESTIGACION_ESPECIFICA",
            "diagnostico": "Hipótesis: cola de impresión detenida, no comprobada.",
            "hipotesis": ["Cola de impresión con errores"],
            "fuentes": ["ITIL.taIncidente"],
            "pasos": [{"condicion": "Si la cola está detenida tras diagnóstico autorizado",
                       "accion": "Revisar el servicio de impresión en lectura",
                       "responsable": "Técnico autorizado de Soporte TIC",
                       "verificacion": "Comprobar envío de documento de prueba"}],
            "faltantes": ["Estado real de cola de impresión"],
            "cierre": ["Verificar que el documento de prueba salga impreso"],
            "ejecutado": False, "confirmado": False,
        })


def test_only_2025_and_weak_label():
    r=sample("2025-04")
    assert validated_input(r)["training_approved"] is False
    for changes in [
        {"year": 2026},
        {"month": "2026-04"},
        {"label_status": "VERIFIED"},
        {"assistant_target": ""},
        {"user": "Contraseña: ABCDEFG987"},
        {"case_sha256": "12345"}
    ]:
        bad={**r,**changes}
        with pytest.raises(ValueError):
            validated_input(bad)


def test_2025_balance_and_determinism():
    rows=[sample(f"2025-{m:02d}",n) for m in range(1,13) for n in range(3)]
    out=select_2025_curriculum(rows,per_month=2)
    assert len(out)==24
    assert [x["month"] for x in out]==[f"2025-{m:02d}" for m in range(1,13) for _ in range(2)]
    assert out==select_2025_curriculum(list(reversed(rows)),per_month=2)
    with pytest.raises(ValueError,match="INCOMPLETE"):
        select_2025_curriculum(rows[:-3],per_month=2)


def test_training_draft_never_sees_historic_answer():
    row=sample("2025-06")
    model=FakeModel()
    draft=draft_2025_case(row,model)
    rendered=json.dumps(model.calls,ensure_ascii=False)
    assert row["assistant_target"] not in rendered
    assert "2026" not in rendered
    assert draft["state"]=="DRAFT_NEEDS_REVIEW"
    assert draft["schema_ok"] is True
    assert draft["training_approved"] is False
    assert draft["repair_certified"] is False
    assert draft["historical_answer_shown_to_student"] is False


def test_invalid_model_draft_never_approved():
    row=sample("2025-01")
    class BadModel:
        def complete(self,messages):
            return json.dumps({"ejecutado":True,"confirmado":True,"estado":"RESUELTO"})
    result=draft_2025_case(row,BadModel())
    assert result["state"]=="REJECTED_DRAFT"
    assert not result["training_approved"]

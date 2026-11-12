"""Adversarial CORE O5/O13/O15 independent operational OT contract.

Synthetic-only receipt; real QA observations are private and not used in CI.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json
import pytest

pytest.importorskip("else_core.hand_kernel",reason="Native CORE dependency")
from else_core.hand_kernel import Outcome
from else_dominance.operational_ot_o5_hand import (
    AuthorizedOperationalOtReceipt,build_operational_ot_router)
from else_dominance.operational_ot_verified import SOURCE,SOURCE_SHA

SHA=sha256(b"aug-qa-operational-synthetic").hexdigest()
TEXT="Solicitamos verificar la OT 123456 para revisar los datos operativos de QA."

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False).encode()

def make_receipt(tmp_path):
    obs={
      "schema":"else.itil.aug2026.qa.operational-ot-readonly.v1",
      "qa_target":"ELSE70/dbDistribucion_D",
      "source":"dbo.taOrdenTrabajo",
      "query_id":"QA_DISTRIB_OPERATIONAL_OT_BY_CODE_V1",
      "order_sha256":sha256(b"123456").hexdigest(),
      "order_rows":0,"order_found":False,
      "codigo_estado_orden_trabajo":"",
      "codigo_clase_orden_trabajo":"",
      "codigo_tipo_orden_trabajo":"",
      "codigo_subtipo_orden_trabajo":"",
      "fecha_elaboracion_present":False,
      "fecha_inicio_present":False,"fecha_fin_present":False,
      "read_only":True,"changes_executed":False,
      "read_utc":datetime.now(timezone.utc).isoformat(),
    }
    receipt={
      "schema":"else.itil.aug2026.operational-ot-receipt.v1",
      "case_sha256":SHA,
      "reported_ot_sha256":sha256(b"123456").hexdigest(),
      "reader_source_sha256":SOURCE_SHA,
      "observation":obs,
      "business_join_certified":False,
      "root_cause_certified":False,
      "repair_certified":False,"read_only":True,
    }
    raw=canonical(receipt)
    file=tmp_path/"receipt.private.json"
    file.write_bytes(raw)
    return file,receipt

def owner(path,text=TEXT):
    raw=path.read_bytes()
    return AuthorizedOperationalOtReceipt(
        path,sha256(raw).hexdigest(),SHA,
        SOURCE_SHA,len(SOURCE.read_bytes()),text)

def test_real_core_hand_uses_independent_guardian_verifier(tmp_path):
    file,_=make_receipt(tmp_path)
    _,router,op=build_operational_ot_router(owner(file))
    result=router.route(op)
    assert result.outcome==Outcome.PASS
    assert result.guardian_result.verification.passed is True
    assert result.guardian_result.verification.independent is True
    assert result.guardian_result.executions==1
    assert result.guardian_result.value.outputs["order_found"] is False
    assert not result.guardian_result.value.outputs["repair_certified"]

@pytest.mark.parametrize("mutation",[
    lambda r:r.update(business_join_certified=True),
    lambda r:r.update(root_cause_certified=True),
    lambda r:r.update(repair_certified=True),
    lambda r:r["observation"].update(order_rows=1),
    lambda r:r["observation"].update(order_found=True),
    lambda r:r["observation"].update(qa_target="PRODUCTION"),
    lambda r:r["observation"].update(source="dbo.taInventada"),
    lambda r:r["observation"].update(changes_executed=True),
    lambda r:r["observation"].update(order_sha256="f"*64),
    lambda r:r.update(reader_source_sha256="f"*64),
])
def test_invalid_receipt_is_denied_preexecution(tmp_path,mutation):
    file,receipt=make_receipt(tmp_path)
    mutation(receipt)
    file.write_bytes(canonical(receipt))
    _,router,op=build_operational_ot_router(owner(file))
    result=router.route(op)
    assert result.outcome!=Outcome.PASS

def test_other_ot_text_cannot_rebind_same_receipt(tmp_path):
    file,_=make_receipt(tmp_path)
    _,router,op=build_operational_ot_router(
        owner(file,"Solicitamos revisar OT 123457 para evaluación QA."))
    result=router.route(op)
    assert result.outcome!=Outcome.PASS

def test_receipt_tampering_after_pin_denied(tmp_path):
    file,receipt=make_receipt(tmp_path)
    obj=owner(file)
    receipt["observation"]["read_only"]=False
    file.write_bytes(canonical(receipt))
    _,router,op=build_operational_ot_router(obj)
    result=router.route(op)
    assert result.outcome!=Outcome.PASS

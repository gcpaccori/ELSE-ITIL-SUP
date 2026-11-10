"""Synthetic negative tests for February's exact read and SAP/OT evidence.

No live SQL, no Qwen requests, no copied corporate incidents.
"""
from __future__ import annotations
import json
from hashlib import sha256
from pathlib import Path

import pytest

from qa.qa_feb100_windows import read_allowlist,validate_model_tool
from else_dominance.qa_feb100_ot_evidence import verify_ot_receipt,extract_unique_reported_ot
from else_dominance.qa_feb100_native import validate_qa_ticket,QaNativeDenied

SHA=sha256(b"synthetic-february-qa-incident").hexdigest()
OT="12345678"
SOURCE=b"synthetic-csharp-source-for-local-test"
def ticket():
    return {"case_sha256":SHA,"opened_at":"2026-02-18T11:15:00",
            "service_code":"1","module_code":"MOD-01","classification_code":"100",
            "description_redacted":("Solicitud QA: la OT "+OT+
                " no aparece en la pantalla; validar estado antes de intervenir.")}

def receipt():
    return {
      "schema":"else.itil.feb100.ot-sap-case-evidence.v1",
      "case_sha256":SHA,
      "binding_provenance":"REPORTED_OT_FROM_REDACTED_CASE_TEXT_ONLY",
      "reported_ot_sha256":sha256(OT.encode()).hexdigest(),
      "reader_source_sha256":sha256(SOURCE).hexdigest(),
      "observation":{
         "schema":"else.itil.qa.feb100.sap-ot-readonly.v1",
         "query_ids":["QA_DISTRIB_SAP_ORDER_BY_OT",
                      "QA_DISTRIB_SAP_RESPONSE_BY_OT"],
         "qa_target":"ELSE70/dbDistribucion_D",
         "sources":["dbo.taOrdenTrabajoSAP",
                    "dbo.taOrdenTrabajoSAPEnvioRespuesta"],
         "order_sha256":sha256(OT.encode()).hexdigest(),
         "order_rows":1,"order_found":True,
         "codigo_estado_envio_sap":"02",
         "codigo_clase_orden_sap":"10",
         "numero_co_sap_present":False,
         "response_rows_up_to5":0,
         "response_message_present":False,
         "response_orden_co_present":False,
         "response_sample_limited":False,
         "read_only":True,"changes_executed":False,
         "read_utc":"2026-11-10T16:00:00Z",
      },
      "read_only":True,"mutations":False,
      "functional_repair_certified":False,
      "root_cause_certified":False,
      "requires_technician_review":True,
    }

def test_verified_sap_observation_does_not_certify_business_entity_relation():
    result=verify_ot_receipt(row=ticket(),receipt=receipt(),
                             source_bytes=SOURCE)
    assert result["order_found_in_this_specific_table"] is True
    assert result["entity_link_to_itil_not_certified"] is True
    assert result["repair_certified"] is False
    assert result["human_review_required"] is True

@pytest.mark.parametrize("change",[
  lambda r: r.update(reported_ot_sha256="0"*64),
  lambda r: r.update(reader_source_sha256="0"*64),
  lambda r: r.update(functional_repair_certified=True),
  lambda r: r.update(binding_provenance="DATABASE_JOIN_CERTIFIED"),
  lambda r: r.update(case_sha256="f"*64),
  lambda r: r["observation"].update(qa_target="ELSE70/dbComercial_D"),
  lambda r: r["observation"].update(changes_executed=True),
  lambda r: r["observation"].update(order_rows=2),
  lambda r: r["observation"].update(order_sha256="f"*64),
])
def test_sap_receipt_tamper_rejected(change):
    r=receipt()
    change(r)
    with pytest.raises(ValueError):
        verify_ot_receipt(row=ticket(),receipt=r,source_bytes=SOURCE)

def test_reported_ot_not_trusted_if_ambiguous():
    assert extract_unique_reported_ot("OT 12345678 y OT 99999999") is None
    assert extract_unique_reported_ot("No se conoce la orden") is None
    assert extract_unique_reported_ot(ticket()["description_redacted"])==OT

def test_feb100_model_tool_query_cannot_use_january_identity():
    good={"type":"tool","name":"qa_exact_read",
          "query_id":"ITIL_2026_02_FEB100_CASE_EXACT_READ",
          "parameters":{"case_sha256":SHA}}
    validate_model_tool(good,SHA)
    wrong=dict(good,query_id="ITIL_2026_01_LAST10_CASE_EXACT_READ")
    with pytest.raises(ValueError):
        validate_model_tool(wrong,SHA)
    wrong=dict(good,parameters={"case_sha256":SHA,"sql":"SELECT *"})
    with pytest.raises(ValueError):
        validate_model_tool(wrong,SHA)

def test_feb100_allowlist_has_strict_count_and_window(tmp_path):
    rows=[]
    for n in range(100):
        item=ticket()
        item["case_sha256"]=sha256(f"synthetic-{n}".encode()).hexdigest()
        rows.append(item)
    file=tmp_path/"allowed.jsonl"
    file.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
    assert len(read_allowlist(file))==100
    rows[0]["opened_at"]="2026-03-01T00:00:00"
    file.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
    with pytest.raises(ValueError):
        read_allowlist(file)
    file.write_text("\n".join(json.dumps(x) for x in rows[1:])+"\n")
    with pytest.raises(ValueError):
        read_allowlist(file)

def test_feb_case_native_window_rejects_march():
    data={
      "schema":"else.itil.qa.sanitized-case.operator-submitted.v1",
      "case_sha256":SHA,"service_code":"1","module_code":"MOD-01",
      "description":ticket()["description_redacted"],
      "opened_at":"2026-03-01T00:00:00",
      "historical_solution":"WITHHELD",
      "content_provenance":"PRIVATE_HISTORICAL_EXPORT_NOT_BYTE_EQUAL_QA_SQL",
      "model_may_execute_sql":False}
    with pytest.raises(QaNativeDenied):
        validate_qa_ticket(data,case_sha256=SHA,service_code="1",
                           module_code="MOD-01")

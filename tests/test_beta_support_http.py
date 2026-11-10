"""HTTP integration tests with synthetic case/receipt and fake Qwen model."""
from __future__ import annotations

from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json

import pytest
pytest.importorskip("else_core.itil_feb100_sap_ot_o5_hand")

from else_dominance.beta_support_http import make_handler
from else_dominance.beta_vertical_slice import SOURCES
from test_qa_native_runtime import good_plan

CASE=sha256(b"beta-http-synthetic").hexdigest()
TOKEN="synthetic-api-token-1234567890-abcdef1234567890"

class FakeBundle:
    def __init__(self):
        self.sap_recs={CASE:None}
    def verify(self,sha):
        if sha!=CASE:raise ValueError("CASE_NOT_QA_ALLOWED")
        return {
           "status":"DUAL_NATIVE_EVIDENCE_VERIFIED",
           "case_sha256":CASE,
           "itil_receipt_sha256":"a"*64,
           "sap_receipt_sha256":"b"*64,
           "itil_metadata":{"observation_kind":"HISTORICAL_QA_INCIDENT_METADATA"},
           "sap_observation":{"order_found":False,
                              "response_rows_up_to5":0},
           "evidence":[
             {"ref":"E1","observation":"Valid native ITIL receipt"},
             {"ref":"E2","observation":"Valid native OT receipt"},
             {"ref":"E3","observation":"Valid response receipt"},
           ],
           "incident_text_redacted":"Consulta QA sobre la OT 12345678 sin reparación.",
           "official_business_join_certified":False,
           "repair_certified":False,
        }

class FakeModel:
    def __init__(self):self.calls=0
    def complete(self,_):
        self.calls+=1
        p=good_plan()
        p["fuentes"]=sorted(SOURCES)
        p["evidence_refs"]=["E1","E2","E3"]
        p["vinculacion_comercial_verificada"]=False
        p["rol_oficial_validado"]=False
        p["faltantes"]=["Requiere validar relación comercial con datos oficiales."]
        p["cierre"]=["Validar la operación original con prueba funcional."]
        for step in p["pasos"]:
            step["responsable"]="Responsable autorizado por confirmar"
        return json.dumps(p,ensure_ascii=False)

def request(base,path,*,method="GET",payload=None,bearer=True):
    headers={"Content-Type":"application/json"}
    if bearer:headers["Authorization"]="Bearer "+TOKEN
    data=None if payload is None else json.dumps(payload).encode()
    with urlopen(Request(base+path,headers=headers,
                         data=data,method=method),timeout=8) as resp:
        return resp.status,json.loads(resp.read())

@pytest.fixture()
def beta_api(tmp_path):
    model=FakeModel()
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(
        token=TOKEN,bundle=FakeBundle(),model=model,
        ledger_path=(tmp_path/"beta.sqlite").absolute()))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:"+str(server.server_port),model
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)

def test_http_beta_has_no_auto_repair_or_business_join(beta_api):
    base,model=beta_api
    status,health=request(base,"/health",bearer=False)
    assert status==200 and health["repairs_enabled"] is False
    assert health["reviewer_roster_configured"] is False
    status,body=request(base,"/v1/beta/investigate",method="POST",
                        payload={"case_sha256":CASE})
    assert status==200 and body["status"]=="PENDING_TECHNICIAN_REVIEW"
    assert body["native_itil_verified"] and body["native_sap_ot_verified"]
    assert body["business_join_certified"] is False
    assert body["repair_certified"] is False
    assert model.calls==1
    # Exact retry is idempotent; no second LLM invocation.
    status,again=request(base,"/v1/beta/investigate",method="POST",
                         payload={"case_sha256":CASE})
    assert status==200 and again==body and model.calls==1
    _,summary=request(base,"/v1/beta/summary")
    assert summary["investigations"]==1
    assert summary["recorded_human_review_events"]==0

def test_http_token_and_case_scope_are_not_bypassed(beta_api):
    base,_=beta_api
    with pytest.raises(HTTPError) as err:
        request(base,"/v1/beta/summary",bearer=False)
    assert err.value.code==401
    with pytest.raises(HTTPError) as err:
        request(base,"/v1/beta/investigate",method="POST",
                payload={"case_sha256":"0"*64})
    assert err.value.code==422

def test_http_cannot_fake_human_signoff_without_roster(beta_api):
    base,_=beta_api
    request(base,"/v1/beta/investigate",method="POST",
            payload={"case_sha256":CASE})
    with pytest.raises(HTTPError) as err:
        request(base,"/v1/beta/review",method="POST",payload={
            "case_sha256":CASE,
            "reviewer_id":"SyntheticReviewer",
            "reviewer_secret":"synthetic-token-longer-than-32characters",
            "decision":"USEFUL_FOR_TECHNICIAN",
            "note":"Registro de prueba sintética sin un revisor autorizado"})
    assert err.value.code==422
    _,status=request(base,"/v1/beta/status/"+CASE)
    assert status["reviews_count"]==0

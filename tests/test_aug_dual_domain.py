"""Functional two-native-Hand QA gate and private HTTP adversarial tests."""
from __future__ import annotations
from hashlib import sha256
from http.server import ThreadingHTTPServer
from threading import Thread,BoundedSemaphore
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json,pytest
from else_dominance.functional_live_sap_v2 import SCHEMA,check_addendum
from else_dominance import functional_verified_http_v2 as http
from else_dominance.functional_api_v2 import Store

SHA=sha256(b"synthetic-dual-o5-ticket").hexdigest()
TOKEN="synthetic-private-qa-token-1234567890123456789012345"

def sap():
    return {
       "case_sha256":SHA,"o5_o13_o15_verified":True,
       "sql_fresh_read_on_windows":True,
       "official_itil_ot_business_join_verified":False,
       "repair_certified":False,"domain":"COMMERCIAL_OT",
       "observation":{"order_found_in_specific_table":False},
    }

def operational():
    return {
      "case_sha256":SHA,
      "native_o5_o13_o15_verified":True,
      "hmac_verified":True,
      "independent_receipt_fields_verified":True,
      "source":"ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo",
      "order_found":False,"business_join_certified":False,
      "repair_certified":False,
    }

def addendum():
    return {
      "schema":SCHEMA,
      "hypotheses":["El código mencionado podría pertenecer a otra instancia de órdenes."],
      "what_this_sap_read_can_prove":
         "La consulta exacta a las dos tablas SAP QA no devolvió coincidencia.",
      "what_operational_read_can_prove":
         "La consulta exacta a dbo.taOrdenTrabajo QA tampoco devolvió coincidencia.",
      "what_it_cannot_prove":
         "No demuestra inexistencia global ni relación ITIL y OT empresarial.",
      "next_domain_check":{
          "target":"SIELSE/órdenes de trabajo",
          "business_object":"Orden referida en la solicitud ITIL",
          "observable":"Identificador de orden que corresponde al proceso de negocio real",
          "expected":"Código registrado en el módulo de trabajo correspondiente a la operación",
          "if_expected":"Solicitar una lectura de esa fuente autorizada para contrastar la orden",
          "if_different":"Comprobar en qué módulo y con qué clave se registró la solicitud",
          "execution":"NOT_EXECUTED",
      },
      "official_itil_ot_join_verified":False,
      "root_cause_certified":False,"repair_certified":False,
    }

def test_dual_verified_evidence_gate_accepts_explicit_limits():
    a=check_addendum(addendum(),sap(),operational())
    assert a["accepted"] is True
    assert a["cause_certified"] is False

@pytest.mark.parametrize("kind",[
 "SAP_O5_MISSING","OP_O5_MISSING","CASE_SWAP","OP_FOUND",
 "UNAUTHORIZED_JOIN","GLOBAL_NONEXISTENCE","FALSE_REPAIR",
])
def test_forged_read_or_false_claim_is_fail_closed(kind):
    s=sap();o=operational();v=addendum()
    if kind=="SAP_O5_MISSING":s["o5_o13_o15_verified"]=False
    elif kind=="OP_O5_MISSING":o["native_o5_o13_o15_verified"]=False
    elif kind=="CASE_SWAP":o["case_sha256"]="f"*64
    elif kind=="OP_FOUND":o["order_found"]=True
    elif kind=="UNAUTHORIZED_JOIN":v["official_itil_ot_join_verified"]=True
    elif kind=="GLOBAL_NONEXISTENCE":
        v["hypotheses"]=["La orden no existe en ningún sistema de la empresa."]
    elif kind=="FALSE_REPAIR":v["repair_certified"]=True
    assert not check_addendum(v,s,o)["accepted"]

@pytest.fixture
def server(tmp_path,monkeypatch):
    invoked=[]
    def verified1(sha):
        assert sha==SHA
        return sap()
    def verified2(sha):
        assert sha==SHA
        return operational()
    def generate(sha):
        invoked.append(sha)
        return {"schema":"qa.mock.dual-o5","case_sha256":sha,
                "status":"DUAL_NATIVE_OT_SAP_OBSERVATIONS_WITH_CONDITIONAL_NEXT_CHECK",
                "quality":{"accepted":True},
                "repair_certified":False}
    monkeypatch.setattr(http,"verify_case",verified1)
    monkeypatch.setattr(http,"verify_case_operational",verified2)
    monkeypatch.setattr(http,"diagnose_case",generate)
    store=Store(tmp_path/"dual.sqlite")
    handler=http.make_handler(token=TOKEN,allowed={SHA},
                               store=store,limit=BoundedSemaphore(1))
    app=ThreadingHTTPServer(("127.0.0.1",0),handler)
    task=Thread(target=app.serve_forever,daemon=True);task.start()
    try:yield "http://127.0.0.1:"+str(app.server_port),invoked
    finally:app.shutdown();app.server_close();task.join(timeout=3)

def call(base,path,body=None,token=True):
    headers={"Content-Type":"application/json"}
    if token:headers["Authorization"]="Bearer "+TOKEN
    raw=None if body is None else json.dumps(body).encode()
    with urlopen(Request(base+path,headers=headers,
        method="POST" if raw is not None else "GET",
        data=raw),timeout=7) as r:
        return r.status,json.loads(r.read())

def test_http_refuses_unauthorized_and_arbitrary_source(server):
    base,calls=server
    with pytest.raises(HTTPError) as err:
        call(base,"/v1/domain/investigate",{"case_sha256":SHA},False)
    assert err.value.code==401
    for body in ({"case_sha256":SHA,"sql":"DELETE FROM..."},
                 {"case_sha256":"f"*64},
                 {"case_sha256":SHA,"ot":"123456"}):
        with pytest.raises(HTTPError) as err:
            call(base,"/v1/domain/investigate",body)
        assert err.value.code==422
    assert not calls

def test_private_http_get_replays_both_hands_and_is_idempotent(server):
    base,calls=server
    n,d=call(base,"/v1/domain/evidence/"+SHA)
    assert n==200 and d["sap_ot"]["o5_o13_o15_verified"]
    assert d["operational_ot"]["native_o5_o13_o15_verified"]
    for i in range(2):
        n,d=call(base,"/v1/domain/investigate",{"case_sha256":SHA})
        assert n==200 and d["idempotent"]==(i==1)
        assert d["repair_certified"] is False
    assert calls==[SHA]

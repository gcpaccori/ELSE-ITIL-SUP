"""Synthetic QA HTTP checks for the new model-triggered OT refresh queue."""
from __future__ import annotations
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json,pytest

pytest.importorskip("else_core.itil_feb100_sap_ot_o5_hand",
   reason="Native O5 SAP/OT Hand installed only with ELSE CORE PR #364")
from else_dominance.beta_fresh_api import make_fresh_handler

CASE=sha256(b"synthetic-QA-refresh-case").hexdigest()
TOKEN="qa-synthetic-http-token-12345678901234567890"
SOURCE=Path(__file__).resolve().parents[1]/"qa/Feb100SapOtRead.cs"
ROW={
 "case_sha256":CASE,"opened_at":"2026-02-02T08:00:00",
 "service_code":"1","module_code":"10","classification_code":"09",
 "description_redacted":"La incidencia relacionada con OT 12345678 debe verificarse en QA.",
}

class FakeBundle:
 def __init__(self,root):
  self.roster={CASE:ROW}
  self.sap_recs={}
  self.fresh_root=root
  self.source_file=SOURCE
 def _refresh(self):pass
 def verify(self,sha):
  if sha!=CASE:raise ValueError("CASE_NOT_ALLOWED")
  return {"status":"REQUIRES_OT_CORPORATE_EVIDENCE",
          "case_sha256":sha,"repair_certified":False}

class ExactModel:
 def __init__(self):self.calls=0
 def complete(self,messages):
  self.calls+=1
  return json.dumps({
      "type":"tool","name":"qa_sap_ot_exact_read",
      "query_id":"QA_DISTRIB_SAP_OT_EXACT_READ_V1",
      "parameters":{"case_sha256":CASE}})

@pytest.fixture
def http(tmp_path):
 root=tmp_path/"evidence"
 (root/"requests").mkdir(parents=True)
 bundle=FakeBundle(root)
 model=ExactModel()
 handler=make_fresh_handler(
     token=TOKEN,bundle=bundle,model=model,
     ledger_path=(tmp_path/"ledger.sqlite").absolute())
 server=ThreadingHTTPServer(("127.0.0.1",0),handler)
 t=Thread(target=server.serve_forever,daemon=True);t.start()
 try:yield "http://127.0.0.1:"+str(server.server_port),model,root
 finally:server.shutdown();server.server_close();t.join(timeout=3)

def call(url,path,data=None,token=True):
 headers={"Content-Type":"application/json"}
 if token:headers["Authorization"]="Bearer "+TOKEN
 payload=None if data is None else json.dumps(data).encode()
 with urlopen(Request(url+path,data=payload,headers=headers,
                      method="POST" if data is not None else "GET"),
              timeout=7) as r:
  return r.status,json.loads(r.read())

def test_fresh_api_requests_exact_tool_once_and_is_idempotent(http):
 url,model,root=http
 status,out=call(url,"/v1/beta/refresh-ot",{"case_sha256":CASE})
 assert status==202 and out["model_requested_exact_tool"]
 assert out["read_only"] and not out["repair_certified"]
 assert model.calls==1
 assert len(list((root/"requests").glob("*.private.json")))==1
 status,duplicate=call(url,"/v1/beta/refresh-ot",{"case_sha256":CASE})
 assert status==200 and duplicate["job_id"]==out["job_id"]
 assert model.calls==1
 _,result=call(url,"/v1/beta/refresh-status/"+out["job_id"])
 assert result["state"]=="QUEUED_FOR_WINDOWS_QA"
 assert not result["business_join_certified"]

def test_unauthorized_refresh_denied_without_side_effects(http):
 url,model,root=http
 with pytest.raises(HTTPError) as exc:
  call(url,"/v1/beta/refresh-ot",{"case_sha256":CASE},token=False)
 assert exc.value.code==401
 assert model.calls==0
 assert not list((root/"requests").glob("*.private.json"))

def test_out_of_scope_or_arbitrary_parameters_denied(http):
 url,model,root=http
 for invalid in (
   {"case_sha256":"f"*64},
   {"case_sha256":CASE,"sql":"SELECT *"},
   {"case_sha256":CASE,"ot":"12345678"},
 ):
  with pytest.raises(HTTPError) as exc:
   call(url,"/v1/beta/refresh-ot",invalid)
  assert exc.value.code==422
 assert model.calls==0

def test_incident_without_fresh_proof_cannot_be_investigated(http):
 url,model,root=http
 with pytest.raises(HTTPError) as exc:
  call(url,"/v1/beta/investigate",{"case_sha256":CASE})
 assert exc.value.code==422
 assert model.calls==0

"""Authenticated and idempotent private functional QA HTTP gateway tests."""
from hashlib import sha256
from http.server import ThreadingHTTPServer
from threading import BoundedSemaphore,Thread
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pathlib import Path
import json,pytest
import else_dominance.functional_api_v2 as api

SHA=sha256(b"synthetic-v2-functional-sample").hexdigest()
TOKEN="a-synthetic-qa-bearer-at-least-twenty-chars-long"
REQUEST={"ticket_sha256":SHA,
         "incident_text_redacted":"Correo SMTP 554 5.4.12 al enviar a dominio ejemplo.com.pe"}

@pytest.fixture
def server(tmp_path,monkeypatch):
    calls=[]
    def fake_run(row):
        calls.append(row)
        return {"schema":"synthetic-functional-result",
                "case_sha256":row["ticket_sha256"],
                "status":"FUNCTIONAL_DRAFT_CONTRACT_PASS",
                "repair_certified":False}
    monkeypatch.setattr(api,"run_case",fake_run)
    store=api.Store(tmp_path/"qa-ledger.sqlite")
    handler=api.make_handler(token=TOKEN,cohort={SHA:REQUEST},
         store=store,limit=BoundedSemaphore(2))
    s=ThreadingHTTPServer(("127.0.0.1",0),handler)
    t=Thread(target=s.serve_forever,daemon=True);t.start()
    try:yield "http://127.0.0.1:"+str(s.server_port),calls,store
    finally:s.shutdown();s.server_close();t.join(timeout=3)

def http(url,path,body=None,authorized=True):
    headers={"Content-Type":"application/json"}
    if authorized:headers["Authorization"]="Bearer "+TOKEN
    data=None if body is None else json.dumps(body).encode()
    req=Request(url+path,data=data,method="POST" if body is not None else "GET",
                headers=headers)
    with urlopen(req,timeout=5) as resp:
        return resp.status,json.loads(resp.read())

def test_source_qa_gateway_requires_authentication_before_running(server):
    url,calls,store=server
    with pytest.raises(HTTPError) as exc:
        http(url,"/v1/functional/investigate",{"case_sha256":SHA},False)
    assert exc.value.code==401
    assert not calls and store.get(SHA) is None

def test_rejects_arbitrary_sql_and_unapproved_cases(server):
    url,calls,store=server
    for body in [
        {"case_sha256":SHA,"sql":"SELECT * FROM sensitive"},
        {"case_sha256":"f"*64},
        {"case_sha256":SHA,"host":"other-server"},
        {"case_sha256":SHA,"domain":"IAM"}]:
        with pytest.raises(HTTPError) as ex:
            http(url,"/v1/functional/investigate",body)
        assert ex.value.code==422
    assert not calls

def test_same_case_returns_stored_result_without_reinvoking_model(server):
    url,calls,store=server
    status,r=http(url,"/v1/functional/investigate",{"case_sha256":SHA})
    assert status==200 and r["state"]=="FINISHED"
    assert not r["idempotent"] and not r["repair_certified"]
    status,s=http(url,"/v1/functional/investigate",{"case_sha256":SHA})
    assert status==200 and s["idempotent"] and len(calls)==1
    status,s=http(url,"/v1/functional/status/"+SHA)
    assert s["state"]=="FINISHED" and s["result"]["case_sha256"]==SHA

def test_stale_case_hash_cannot_replace_owner_in_ledger(tmp_path):
    store=api.Store(tmp_path/"qa-ledger.sqlite")
    assert store.claim(SHA,"a"*64)
    with pytest.raises(ValueError,match="CASE_SHA_SNAPSHOT_CHANGED"):
        store.claim(SHA,"b"*64)
    store.finish(SHA,"a"*64,{"schema":"test","repair_certified":False})
    assert not store.claim(SHA,"a"*64)
    assert store.get(SHA)["state"]=="FINISHED"

def test_cannot_upgrade_running_job_with_other_snapshot(tmp_path):
    store=api.Store(tmp_path/"qa-ledger.sqlite")
    assert store.claim(SHA,"a"*64)
    with pytest.raises(ValueError,match="RESULT_NOT_BOUND"):
        store.finish(SHA,"f"*64,{"bad":True})

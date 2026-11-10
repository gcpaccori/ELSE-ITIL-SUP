"""Synthetic-only QA dispatcher tests. No real customer records or SQL."""
from __future__ import annotations

import json
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from else_dominance.qa_dispatch_queue import (
    QaDispatchQueue, load_allowed, obj, SCHEMA)
from else_dominance.support_http import make_handler


def prepare_allowed(root:Path):
    values=sorted(sha256(f"fake-itil-case-{i}".encode()).hexdigest()
                  for i in range(545))
    p=root/"allowed_sha256.txt"
    p.write_text("\n".join(values)+"\n",encoding="utf-8")
    return p,values


def fake_callback(result, expected_sha):
    if result.get("case_sha_prefix") != expected_sha[:16]:
        raise ValueError("RESULT_WRONG_CASE")
    if result.get("repair_certified") is not False:
        raise ValueError("FALSE_REPAIR")
    return {"schema":SCHEMA,"diagnosis_status":"DIAGNOSTIC_GUIDANCE",
            "o5_o13_o15_verified":True,"human_review_required":True,
            "repair_certified":False}


def fake_result(sha):
    return {"schema":"else.itil.qa.dynamic-nuget-hand.v1",
            "case_sha_prefix":sha[:16],"repair_certified":False}


def submit_and_claim(root):
    allow,values=prepare_allowed(root)
    q=QaDispatchQueue(root/"jobs.sqlite",load_allowed(allow))
    a=q.submit(values[0])
    job=q.claim()
    assert job["job_id"]==a["job_id"]
    assert job["state"]=="CLAIMED"
    return q,a,job,values


def test_545_sorted_allowlist_and_strict_identity(tmp_path):
    file,values=prepare_allowed(tmp_path)
    assert load_allowed(file)==frozenset(values)
    file.write_text("\n".join(reversed(values))+"\n")
    with pytest.raises(ValueError,match="NOT_CANONICAL"):
        load_allowed(file)


def test_submit_dedup_claim_finish_and_readback(tmp_path):
    q,a,job,values=submit_and_claim(tmp_path)
    try:
        second=q.submit(values[0])
        assert second["deduplicated"] is True
        assert second["job_id"]==a["job_id"]
        status=q.status(a["job_id"])
        assert status["state"]=="RUNNING"
        assert "claim_token" not in status
        completed=q.finish({
            "job_id":job["job_id"],
            "case_sha256":job["case_sha256"],
            "claim_token":job["claim_token"],
            "outcome":"COMPLETED",
            "result":fake_result(job["case_sha256"])
        },verifier=fake_callback)
        assert completed["state"]=="COMPLETED"
        final=q.status(a["job_id"])
        assert final["investigation"]["o5_o13_o15_verified"] is True
        assert final["functional_repair_certified"] is False
        assert "claim_token" not in json.dumps(final)
        newer=q.submit(values[0])
        assert newer["job_id"]!=a["job_id"]
    finally:
        q.close()


def test_no_unauthorized_case_and_no_unknown_job(tmp_path):
    p,values=prepare_allowed(tmp_path)
    with QaDispatchQueue(tmp_path/"jobs.sqlite",load_allowed(p)) as q:
        with pytest.raises(ValueError,match="CASE_NOT_IN_QA_ALLOWLIST"):
            q.submit("f"*64)
        with pytest.raises(ValueError,match="JOB_NOT_FOUND"):
            q.status("a"*32)
        with pytest.raises(ValueError,match="CASE_SHA256_INVALID"):
            q.submit("invalid")


def test_worker_token_wrong_job_lease_and_replay_denied(tmp_path):
    q,a,job,values=submit_and_claim(tmp_path)
    try:
        envelope={"job_id":job["job_id"],"case_sha256":job["case_sha256"],
                  "claim_token":"x"*40,"outcome":"COMPLETED",
                  "result":fake_result(job["case_sha256"])}
        with pytest.raises(ValueError,match="CLAIM_TOKEN_MISMATCH"):
            q.finish(envelope,verifier=fake_callback)
        envelope["claim_token"]=job["claim_token"]
        envelope["case_sha256"]=values[1]
        with pytest.raises(ValueError,match="JOB_SCOPE_OR_STATE_DRIFT"):
            q.finish(envelope,verifier=fake_callback)
        envelope["case_sha256"]=job["case_sha256"]
        q.finish(envelope,verifier=fake_callback)
        with pytest.raises(ValueError,match="JOB_SCOPE_OR_STATE_DRIFT"):
            q.finish(envelope,verifier=fake_callback)
    finally:q.close()


def test_default_real_verifier_cannot_be_bypassed_with_fake_claim(tmp_path):
    q,a,job,_=submit_and_claim(tmp_path)
    try:
        with pytest.raises(Exception):
            q.finish({
                "job_id":job["job_id"],
                "case_sha256":job["case_sha256"],
                "claim_token":job["claim_token"],
                "outcome":"COMPLETED",
                "result":fake_result(job["case_sha256"])
            })
        assert q.status(job["job_id"])["state"]=="RUNNING"
    finally:q.close()


def test_failure_result_is_coded_no_corporate_text(tmp_path):
    q,a,job,_=submit_and_claim(tmp_path)
    try:
        result=q.finish({
            "job_id":job["job_id"],
            "case_sha256":job["case_sha256"],
            "claim_token":job["claim_token"],
            "outcome":"FAILED","result":{"error_code":"QA_READ_PIPELINE_FAILED"}})
        assert result["state"]=="FAILED"
        assert q.status(a["job_id"])["error_code"]=="QA_READ_PIPELINE_FAILED"
    finally:q.close()


def test_worker_claim_lease_expiration_fails_closed(tmp_path):
    q,a,job,_=submit_and_claim(tmp_path)
    try:
        with q.conn:
            q.conn.execute(
                "UPDATE qa_jobs SET claimed_until_utc=? WHERE job_id=?",
                ("2020-01-01T00:00:00+00:00",job["job_id"]))
        empty=q.claim()
        assert empty["state"]=="EMPTY"
        assert q.status(a["job_id"])["state"]=="EXPIRED"
    finally:q.close()


def test_json_duplicate_keys_denied():
    with pytest.raises(ValueError,match="DUPLICATE_JSON_KEY"):
        obj(b'{"case_sha256":"a","case_sha256":"b"}')


class DummyModel:
    def complete(self,_):
        return json.dumps({
            "estado":"INVESTIGACION_ESPECIFICA",
            "diagnostico":"Revisar la evidencia aportada.",
            "hipotesis":["Se requiere comprobar configuración."],
            "fuentes":[],"evidence_refs":[],
            "pasos":[{"condicion":"Si la verificación de prueba confirma el caso",
                      "accion":"Consultar evidencia adicional del servicio",
                      "responsable":"Analista autorizado según matriz vigente",
                      "verificacion":"Comparar datos con los resultados esperados"}],
            "faltantes":["Evidencia de estado actual"],
            "cierre":["Verificar con el solicitante el estado actual"],
            "ejecutado":False,"confirmado":False})


def test_http_qa_submit_status_auth_no_ui_change(tmp_path):
    allow,values=prepare_allowed(tmp_path)
    db=tmp_path/"queue.sqlite"
    token="synthetic-"+("X"*48)
    server=ThreadingHTTPServer(
        ("127.0.0.1",0),
        make_handler(token=token,state_db=tmp_path/"attentions.sqlite",
                     primary=DummyModel(),fallback=None,
                     qa_queue_db=db,qa_allowlist=allow))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    url="http://127.0.0.1:"+str(server.server_port)
    try:
        with urlopen(url+"/health",timeout=5) as r:
            health=json.load(r)
        assert health["qa_dispatch"]=="QA_HISTORICAL_READY"
        assert health["source_access"]=="USER_SUBMITTED_ONLY"
        request={"case_sha256":values[0]}
        def post(body,auth=True):
            headers={"Content-Type":"application/json"}
            if auth:headers["Authorization"]="Bearer "+token
            return Request(url+"/v1/qa/investigate",
                           data=json.dumps(body).encode(),
                           method="POST",headers=headers)
        with pytest.raises(HTTPError) as err:
            urlopen(post(request,auth=False),timeout=5)
        assert err.value.code==401
        with urlopen(post(request),timeout=5) as res:
            result=json.load(res)
            assert res.status==202
        assert result["state"]=="QUEUED"
        assert "claim_token" not in result
        with pytest.raises(HTTPError) as err:
            urlopen(Request(url+"/v1/qa/jobs/"+result["job_id"]),timeout=5)
        assert err.value.code==401
        with urlopen(Request(url+"/v1/qa/jobs/"+result["job_id"],
                headers={"Authorization":"Bearer "+token}),timeout=5) as res:
            status=json.load(res)
        assert status["state"]=="QUEUED"
        with pytest.raises(HTTPError) as err:
            urlopen(post({"case_sha256":"f"*64}),timeout=5)
        assert err.value.code==422
        with pytest.raises(HTTPError) as err:
            urlopen(post({"case_sha256":values[0],"sql":"SELECT *"}),timeout=5)
        assert err.value.code==422
        # Original listener remains compatible.
        with urlopen(url+"/health",timeout=5) as res:
            assert json.load(res)["repairs_enabled"] is False
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)



def test_fresh_receipts_must_postdate_worker_claim_and_not_future():
    from datetime import datetime,timedelta,timezone
    from else_dominance.qa_dispatch_queue import validate_freshness
    stamp=datetime.now(timezone.utc)
    validate_freshness(stamp.isoformat(),stamp-timedelta(seconds=2))
    with pytest.raises(ValueError,match="STALE_RECEIPT_BEFORE_JOB_CLAIM"):
        validate_freshness(
            (stamp-timedelta(hours=3)).isoformat(),stamp)
    with pytest.raises(ValueError,match="RECEIPT_TIMESTAMP_IN_FUTURE"):
        validate_freshness(
            (stamp+timedelta(hours=2)).isoformat(),stamp)
    with pytest.raises(ValueError,match="RECEIPT_TIMEZONE_REQUIRED"):
        validate_freshness(stamp.replace(tzinfo=None).isoformat(),stamp)


def test_windows_callback_preserves_native_core_dependency_and_stdin(monkeypatch):
    import base64
    import sys
    p=Path(__file__).resolve().parents[1]/"qa"
    sys.path.insert(0,str(p))
    import qa_outbound_worker_windows as worker
    job={"job_id":"a"*32,
         "case_sha256":"b"*64,
         "claim_token":"synthetic-not-secret-"+("x"*38)}
    result={"schema":"else.itil.qa.dynamic-nuget-hand.v1",
            "o5_o13_o15_verified":True,
            "case_sha_prefix":"b"*16}
    seen={}
    def fake_remote(command,data=None,timeout=0):
        seen["command"]=command
        seen["envelope"]=json.loads(base64.b64decode(data))
        return {"job_id":job["job_id"],"state":"COMPLETED"}
    monkeypatch.setattr(worker,"remote",fake_remote)
    answer=worker.deliver(job,result=result)
    assert answer["state"]=="COMPLETED"
    assert "PYTHONPATH="+worker.REPO+":"+worker.CORE in seen["command"]
    assert "base64 -di | env" in seen["command"]
    assert seen["envelope"]["claim_token"]==job["claim_token"]
    assert seen["envelope"]["result"]==result


def test_outbound_worker_does_not_issue_nuget_without_queued_case(monkeypatch):
    import sys
    p=Path(__file__).resolve().parents[1]/"qa"
    sys.path.insert(0,str(p))
    import qa_outbound_worker_windows as worker
    monkeypatch.setattr(worker,"claim",lambda:{"state":"EMPTY"})
    monkeypatch.setattr(worker,"run_exact_nuget",lambda **kw:
                        (_ for _ in ()).throw(AssertionError("SQL_SHOULD_NOT_RUN")))
    assert worker.once()=={"state":"EMPTY","processed":False}

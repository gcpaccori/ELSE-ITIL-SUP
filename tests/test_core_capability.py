"""Actual executable Pareto core: synthetic contracts, no fake O5 passes."""
from __future__ import annotations

from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json

import pytest

from else_dominance.core_capability import (
    ExecutableHand, ParetoInvestigationCore, minimal_registered_hands)
from else_dominance.qa_dispatch_queue import QaDispatchQueue,load_allowed
from else_dominance.support_http import make_handler


def allowed(root):
    rows=sorted(sha256(f"synthetic-case-{i}".encode()).hexdigest()
                for i in range(545))
    p=root/"allowed.txt"
    p.write_text("\n".join(rows)+"\n")
    return load_allowed(p),rows,p


def fake_hand(name,observations,cost):
    return ExecutableHand(name,frozenset(observations),cost,
                          submit=lambda sha:{"job_id":"a"*32,
                                             "state":"QUEUED"})


def test_minimum_real_registered_set_cover_not_keyword_routing():
    real=(fake_hand("single-itil",{"ITIL_CASE_EXISTS"},1),
          fake_hand("multi-domain",{"ITIL_CASE_EXISTS","ITIL_SERVICE",
                                    "ITIL_MODULE"},2),
          fake_hand("service-only",{"ITIL_SERVICE"},1))
    decision=minimal_registered_hands(
        ["ITIL_CASE_EXISTS","ITIL_SERVICE","ITIL_MODULE"],real,max_hands=2)
    assert decision["selected_capability_ids"]==["multi-domain"]
    assert decision["covered_goals"]==[
        "ITIL_CASE_EXISTS","ITIL_SERVICE","ITIL_MODULE"]
    assert decision["unavailable_goals"]==[]
    assert decision["selected_cost_units"]==2


def test_missing_hand_cannot_be_counted_as_executed(tmp_path):
    items,rows,_=allowed(tmp_path)
    with QaDispatchQueue(tmp_path/"queue.sqlite",items) as q:
        result=ParetoInvestigationCore(q).start(
            rows[0],["SAP_ORDER_RESPONSE","EFFECTIVE_PERMISSIONS"])
        assert result["status"]=="NO_EXECUTABLE_HAND"
        assert result["real_hands_started"]==0
        assert result["unavailable_goals"]==[
            "SAP_ORDER_RESPONSE","EFFECTIVE_PERMISSIONS"]
        assert q.conn.execute("SELECT count(*) FROM qa_jobs").fetchone()[0]==0


def test_one_real_registered_hand_starts_one_real_job(tmp_path):
    items,rows,_=allowed(tmp_path)
    with QaDispatchQueue(tmp_path/"queue.sqlite",items) as q:
        core=ParetoInvestigationCore(q)
        result=core.start(rows[0],["ITIL_CASE_EXISTS","ITIL_SERVICE",
                                  "COMMERCIAL_STATE"])
        assert result["real_hands_started"]==1
        assert result["unavailable_goals"]==["COMMERCIAL_STATE"]
        job=result["executions_started"][0]
        assert job["capability_id"]=="itil.qa.nuget.exact.read.v1"
        assert job["state"]=="QUEUED"
        follow=core.inspect(job["job_id"])
        assert follow["state"]=="QUEUED"
        assert follow["root_cause_certified"] is False


def test_default_uses_only_one_hand_and_deduplicates(tmp_path):
    items,rows,_=allowed(tmp_path)
    with QaDispatchQueue(tmp_path/"queue.sqlite",items) as q:
        engine=ParetoInvestigationCore(q)
        first=engine.start(rows[0])
        repeat=engine.start(rows[0])
        assert first["real_hands_started"]==repeat["real_hands_started"]==1
        assert first["executions_started"][0]["job_id"]==(
            repeat["executions_started"][0]["job_id"])
        assert q.conn.execute("SELECT count(*) FROM qa_jobs").fetchone()[0]==1


@pytest.mark.parametrize("goals",[
    [],["SQL_ARBITRARY"],["ITIL_CASE_EXISTS","ITIL_CASE_EXISTS"],
    ["ITIL_CASE_EXISTS",18],["SAP_ORDER_RESPONSE","DML_WRITE"]])
def test_unregistered_model_tool_or_invalid_goal_rejected(tmp_path,goals):
    items,rows,_=allowed(tmp_path)
    with QaDispatchQueue(tmp_path/"queue.sqlite",items) as q:
        with pytest.raises(ValueError):
            ParetoInvestigationCore(q).start(rows[0],goals)
        assert q.conn.execute("SELECT count(*) FROM qa_jobs").fetchone()[0]==0


def test_bad_case_sha_does_not_start_tool(tmp_path):
    items,rows,_=allowed(tmp_path)
    with QaDispatchQueue(tmp_path/"queue.sqlite",items) as q:
        with pytest.raises(ValueError,match="CASE_NOT_AUTHORIZED_FOR_REAL_HAND"):
            ParetoInvestigationCore(q).start("f"*64)
        assert q.conn.execute("SELECT count(*) FROM qa_jobs").fetchone()[0]==0


def test_real_completion_cannot_be_impersonated_in_synthetic_queue(tmp_path):
    items,rows,_=allowed(tmp_path)
    with QaDispatchQueue(tmp_path/"queue.sqlite",items) as q:
        core=ParetoInvestigationCore(q)
        result=core.start(rows[0])
        job=result["executions_started"][0]["job_id"]
        # Disallow fake COMPLETED row even if it has the expected fields.
        q.conn.execute(
            "UPDATE qa_jobs SET state='COMPLETED',result_json=? WHERE job_id=?",
            (json.dumps({"o5_o13_o15_verified":False}),job))
        with pytest.raises(ValueError,match="NONVERIFIED_QUEUE_RESULT"):
            core.inspect(job)


def test_http_core_routes_actually_submit_and_report_missing(tmp_path):
    items,rows,allow=allowed(tmp_path)
    key="synthetic-"+("T"*48)
    class Dummy:
        def complete(self,_):
            raise RuntimeError("MODEL_NOT_CALLED_FROM_CORE_PLANNING")
    srv=ThreadingHTTPServer(("127.0.0.1",0),
         make_handler(token=key,state_db=tmp_path/"attention.sqlite",
                      primary=Dummy(),fallback=None,
                      qa_queue_db=tmp_path/"queue.sqlite",
                      qa_allowlist=allow))
    thread=Thread(target=srv.serve_forever,daemon=True)
    thread.start()
    base="http://127.0.0.1:"+str(srv.server_port)
    try:
        def post(body,auth=True):
            headers={"Content-Type":"application/json"}
            if auth:headers["Authorization"]="Bearer "+key
            return Request(base+"/v1/qa/core/investigate",
                       data=json.dumps(body).encode(),headers=headers,
                       method="POST")
        with pytest.raises(HTTPError) as err:
            urlopen(post({"case_sha256":rows[0]},False),timeout=5)
        assert err.value.code==401
        with urlopen(post({"case_sha256":rows[0],"goals":[
            "ITIL_CASE_EXISTS","SAP_ORDER_RESPONSE"]}),timeout=5) as res:
            assert res.status==202
            started=json.load(res)
        assert started["real_hands_started"]==1
        assert started["unavailable_goals"]==["SAP_ORDER_RESPONSE"]
        jid=started["executions_started"][0]["job_id"]
        get=Request(base+"/v1/qa/core/jobs/"+jid,
                    headers={"Authorization":"Bearer "+key})
        with urlopen(get,timeout=5) as res:
            assert json.load(res)["state"]=="QUEUED"
        with urlopen(post({"case_sha256":rows[1],
                           "goals":["SAP_ORDER_RESPONSE"]}),timeout=5) as res:
            assert res.status==200
            no_tools=json.load(res)
        assert no_tools["real_hands_started"]==0
        assert no_tools["status"]=="NO_EXECUTABLE_HAND"
        with pytest.raises(HTTPError) as err:
            urlopen(post({"case_sha256":rows[1],
                          "goals":["SQL_UPDATE"]}),timeout=5)
        assert err.value.code==422
        assert srv is not None
    finally:
        srv.shutdown();srv.server_close();thread.join(timeout=5)

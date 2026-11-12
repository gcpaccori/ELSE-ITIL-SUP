"""Jan22–31: executable new Hand, 574-case allowlist, no Sep masquerading.

Synthetic fixtures only; actual O5/O13/O15 receipts are independently
reinspected by the private audit in the QA cluster.
"""
from __future__ import annotations
import json
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import Request,urlopen
from urllib.error import HTTPError

import pytest

from else_dominance.qa_dispatch_queue import (
    COHORTS,QaDispatchQueue,load_allowed,verify_actual_receipts)
from else_dominance.core_capability import ParetoInvestigationCore
from else_dominance.qa_live_adapter import QaDispatchLiveAdapter
from else_dominance.support_http import make_handler
from qa.qa_janlast10_windows import read_allowlist,validate_model_tool

JAN="2026-01-last10"
QUERY="ITIL_2026_01_LAST10_CASE_EXACT_READ"
SEP="ITIL_2026_09_CASE_EXACT_READ"


def sample(tmp_path):
    rows=[]
    for i in range(574):
        digest=sha256(("jan22-31-synthetic-"+str(i)).encode()).hexdigest()
        rows.append({
            "case_sha256":digest,
            "opened_at":"2026-01-22T08:00:00",
            "service_code":"1","module_code":"0109100100000",
            "classification_code":"101",
            "description_redacted":"Synthetic diagnostic incident, never a real ticket."})
    path=tmp_path/"jan_allowlist.jsonl"
    path.write_text("\n".join(json.dumps(x) for x in rows)+"\n",
                    encoding="utf-8")
    digests=sorted(x["case_sha256"] for x in rows)
    id_file=tmp_path/"sha_only.txt"
    id_file.write_text("\n".join(digests)+"\n")
    return rows,path,id_file,digests


def test_jan574_real_backend_and_live_query_not_september(tmp_path):
    rows,raw,ids,digests=sample(tmp_path)
    assert len(read_allowlist(raw))==574
    allowed=load_allowed(ids,expected_count=574)
    with QaDispatchQueue(tmp_path/"jan.sqlite",allowed,cohort=JAN) as q:
        p=ParetoInvestigationCore(q).start(
            digests[0],["ITIL_CASE_EXISTS","ITIL_MODULE",
                        "SAP_ORDER_RESPONSE"])
        assert p["real_hands_started"]==1
        assert p["executions_started"][0]["capability_id"]==(
            "itil.qa.nuget.jan22-31.receipt.readonly.v1")
        assert p["unavailable_goals"]==["SAP_ORDER_RESPONSE"]
        a=QaDispatchLiveAdapter(q)
        assert a.allowed_queries==frozenset({QUERY})
        assert a.run(SEP,{"case_sha256":digests[0]},
                     scope={"case_sha256":digests[0]})["status"]=="BLOCKED"
        j=a.run(QUERY,{"case_sha256":digests[0]},
                scope={"case_sha256":digests[0]})
        assert j["status"]=="PENDING"
        assert j["provenance_verified"] is False
        assert q.conn.execute("SELECT count(*) FROM qa_jobs").fetchone()[0]==1


def test_cannot_mix_january_and_september_o5_receipts(tmp_path):
    rows,raw,ids,digests=sample(tmp_path)
    request={"type":"tool","name":"qa_exact_read",
             "query_id":QUERY,
             "parameters":{"case_sha256":digests[0]}}
    validate_model_tool(request,digests[0])
    wrong={**request,"query_id":SEP}
    with pytest.raises(ValueError,match="MODEL_TOOL_NOT_WHITELISTED"):
        validate_model_tool(wrong,digests[0])
    bad={**request,"parameters":{"case_sha256":digests[1]}}
    with pytest.raises(ValueError,match="MODEL_TOOL_SCOPE_VIOLATION"):
        validate_model_tool(bad,digests[0])
    with pytest.raises(Exception):
        verify_actual_receipts({
            "model_requested_tool_before_sql":True,
            "new_qa_sql_read_executed":True,
            "o5_o13_o15_verified":True,
            "model_reconsidered_after_evidence":True,
            "repair_certified":False,
            "case_sha_prefix":digests[0][:16],
            "run_id":"case_"+digests[0][:16]+"_1234567890",
            "private_cluster_run":str(COHORTS["2026-09"]["root"]/
                         ("case_"+digests[0][:16]+"_1234567890")),
        },digests[0],cohort=JAN)


def test_no_cross_month_or_truncated_whitelist(tmp_path):
    rows,raw,ids,digests=sample(tmp_path)
    rows[0]["opened_at"]="2026-01-21T09:00:00"
    raw.write_text("\n".join(json.dumps(x) for x in rows)+"\n",
                   encoding="utf-8")
    with pytest.raises(ValueError,match="ALLOWLIST_DATE"):
        read_allowlist(raw)
    ids.write_text("\n".join(digests[:-1])+"\n")
    with pytest.raises(ValueError,match="QA_ALLOWLIST_COUNT_DRIFT"):
        load_allowed(ids,expected_count=574)


def test_jan_http_core_and_legacy_health_route(tmp_path):
    _,_,ids,digests=sample(tmp_path)
    token="synthetic-"+("W"*48)
    class Unused:
        def complete(self,*_):
            raise RuntimeError("LLM_SHOULD_NOT_BE_CALLED_FOR_PLANNING")
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(
        token=token,state_db=tmp_path/"attention.sqlite",
        primary=Unused(),fallback=None,qa_queue_db=tmp_path/"jan.sqlite",
        qa_allowlist=ids,qa_cohort=JAN))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    base="http://127.0.0.1:"+str(server.server_port)
    try:
        with urlopen(base+"/health",timeout=5) as res:
            assert json.load(res)["repairs_enabled"] is False
        req=Request(base+"/v1/qa/core/investigate",
                    data=json.dumps({"case_sha256":digests[0]}).encode(),
                    headers={"Authorization":"Bearer "+token,
                             "Content-Type":"application/json"},
                    method="POST")
        with urlopen(req,timeout=5) as res:
            payload=json.load(res)
            assert res.status==202
        jid=payload["executions_started"][0]["job_id"]
        assert payload["executions_started"][0]["capability_id"]==(
            "itil.qa.nuget.jan22-31.receipt.readonly.v1")
        result=Request(base+"/v1/qa/core/jobs/"+jid,
                       headers={"Authorization":"Bearer "+token})
        with urlopen(result,timeout=5) as res:
            assert json.load(res)["status"]=="IN_PROGRESS"
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)



def test_january_hand_covers_six_verified_itil_metadata_goals(tmp_path):
    _,_,ids,digests=sample(tmp_path)
    allowed=load_allowed(ids,expected_count=574)
    with QaDispatchQueue(tmp_path/"jan_meta.sqlite",allowed,cohort=JAN) as q:
        plan=ParetoInvestigationCore(q).start(
            digests[0],["ITIL_CLASSIFICATION","ITIL_ORIGIN",
                        "ITIL_TICKET_STATUS"])
        assert plan["all_goals_covered"] is True
        assert plan["real_hands_started"]==1
        assert plan["unavailable_goals"]==[]
        assert plan["repair_certified"] is False

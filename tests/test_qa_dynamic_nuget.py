"""No private corporate records used; exact fake receipts and adversarial tests."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from else_dominance.qa_dynamic_nuget_cluster import (
    finish_fresh_qa_case, parse_strict, source_context,
    table_mentions_in_proposal)
from else_dominance.qa_native_runtime import QaNativeDenied
from else_dominance.qa_o5_tool_runtime import QUERY_ID
from test_qa_native_runtime import case as sample_case, good_plan


class OneResponseModel:
    def __init__(self, data):
        self.data=data
        self.calls=0
    def complete(self, messages):
        self.calls+=1
        return json.dumps(self.data,ensure_ascii=False)


def tool(sha):
    return {"type":"tool","name":"qa_exact_read","query_id":QUERY_ID,
            "parameters":{"case_sha256":sha}}


def fixture_owner(tmp_path, **changes):
    from else_core.itil_nuget_o5_hand import (
        AuthorizedNugetReceipt,QA_SCOPE,TRANSFER_SCHEMA)
    c=sample_case()
    source_sha=sha256(b"known QA source bytes").hexdigest()
    r={
        "schema":TRANSFER_SCHEMA,"scope":QA_SCOPE,"query_id":QUERY_ID,
        "case_sha256":c["case_sha256"],"hand_source_sha256":source_sha,
        "hand_manifest_sha256":"8"*64,
        "opened_at":c["opened_at"],
        "service_code":c["service_code"],
        "module_code":c["module_code"],
        "classification_code":"02",
        "origin_code":"01",
        "status_code":"03",
        "request_bytes":"320",
        "issued_at_utc":"2026-11-09T20:00:00.000000Z",
        "row_count":1,"read_only":True,"provenance_verified":True,
        "historical_solution_not_read":True,
        "deterministic_source_binding_passed":True,
        "negative_sha_tamper_rejected":True,
        "functional_repair_certified":False,
        "core_o5_native_registration":False
    }
    r.update(changes)
    b=json.dumps(r,sort_keys=True).encode()
    f=tmp_path/"receipt.json"
    f.write_bytes(b)
    return AuthorizedNugetReceipt(f,sha256(b).hexdigest(),
                                  c["case_sha256"],source_sha,1234),c


def test_live_receipt_core_guardian_and_second_turn(tmp_path):
    owner,c=fixture_owner(tmp_path)
    plan=good_plan()
    # Need no invented SQL table names for a positive case.
    model=OneResponseModel(plan)
    result=finish_fresh_qa_case(
        owner=owner,case=c,model=model,tool_request=tool(owner.case_sha256))
    assert result["o5_o13_o15_verified"] is True
    assert result["model_had_verified_metadata_before_final"] is True
    assert result["independently_reinspected_metadata"]["ticket_status_code"]=="03"
    assert result["quality"]["accepted"] is True
    assert result["repair_certified"] is False
    assert model.calls==1


@pytest.mark.parametrize("bad",[
    {"query_id":"MODEL_SQL"},
    {"parameters":{"case_sha256":"0"*64}},
    {"parameters":{"case_sha256":"NOT_VALID","sql":"SELECT * FROM Users"}},
    {"name":"arbitrary_sql"},
    {"type":"final"},
])
def test_wrong_tool_request_fails_before_o5_and_model(tmp_path,bad):
    owner,c=fixture_owner(tmp_path)
    t=tool(owner.case_sha256)
    t.update(bad)
    model=OneResponseModel(good_plan())
    with pytest.raises(QaNativeDenied):
        finish_fresh_qa_case(owner=owner,case=c,model=model,tool_request=t)
    assert model.calls==0


def test_preexisting_source_bytes_tamper_fails_o13_o15(tmp_path):
    owner,c=fixture_owner(tmp_path)
    owner.path.write_bytes(owner.path.read_bytes()+b" ")
    m=OneResponseModel(good_plan())
    with pytest.raises(Exception):
        finish_fresh_qa_case(owner=owner,case=c,model=m,
                             tool_request=tool(owner.case_sha256))
    assert m.calls==0


@pytest.mark.parametrize("bad",[
    {"opened_at":"2026-09-06T11:11:11"},
    {"request_bytes":"-1"},
    {"classification_code":None},
    {"status_code":3},
    {"issued_at_utc":""},
])
def test_bad_optional_metadata_denied_after_core_before_final(tmp_path,bad):
    owner,c=fixture_owner(tmp_path,**bad)
    m=OneResponseModel(good_plan())
    with pytest.raises(QaNativeDenied):
        finish_fresh_qa_case(owner=owner,case=c,model=m,
                             tool_request=tool(owner.case_sha256))
    assert m.calls==0


def test_unbound_table_mentions_rejected(tmp_path):
    owner,c=fixture_owner(tmp_path)
    plan=good_plan()
    plan["pasos"][0]["accion"]="Consultar SEC.taUsuarioBitacora sin fuente declarada."
    plan["fuentes"]=[]
    m=OneResponseModel(plan)
    result=finish_fresh_qa_case(owner=owner,case=c,model=m,
                                tool_request=tool(owner.case_sha256))
    assert result["status"]=="NEEDS_HUMAN_TRIAGE"
    assert result["quality"]["accepted"] is False
    assert "UNBOUND_SQL_TABLE_REFERENCES" in result["quality"]["safety_flags"]
    assert result["proposal"]=={}


def test_strict_json_rejects_duplicate_keys():
    with pytest.raises(QaNativeDenied):
        parse_strict(b'{"case_sha256":"a","case_sha256":"b"}')


def test_windows_tool_shape_rejects_sql_and_host():
    p=Path(__file__).resolve().parents[1]/"qa"
    sys.path.insert(0,str(p))
    from qa_dynamic_nuget_windows import validate_model_tool
    expected="a"*64
    validate_model_tool(tool(expected),expected)
    for bad in (
        {**tool(expected),"host":"ELSE70"},
        {**tool(expected),"query_id":"ARBITRARY"},
        {**tool(expected),"parameters":{"case_sha256":expected,"sql":"UPDATE"}},
        {**tool(expected),"parameters":{"case_sha256":"b"*64}},
    ):
        with pytest.raises(ValueError):
            validate_model_tool(bad,expected)

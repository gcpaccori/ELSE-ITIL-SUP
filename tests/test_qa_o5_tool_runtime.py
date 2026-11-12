"""Ensure model can request only the exact, already pinned NuGet QA receipt."""
from __future__ import annotations
import json
import pytest
from else_dominance import qa_o5_tool_runtime as r
from else_dominance.qa_native_runtime import QaNativeDenied
from test_qa_native_runtime import Owner, case, good_plan, observation


class SequencedModel:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0
    def complete(self, messages):
        res=self.responses[self.calls]
        self.calls += 1
        return json.dumps(res)


def exact_tool():
    return {"type": "tool", "name": "qa_exact_read",
            "query_id": r.QUERY_ID,
            "parameters": {"case_sha256": Owner.case_sha256}}


def test_model_requests_registered_o5_tool(monkeypatch):
    called=[]
    def verified(owner):
        called.append(True)
        return observation()
    monkeypatch.setattr(r,"verify_native_o5",verified)
    m=SequencedModel([exact_tool(),good_plan()])
    got=r.diagnose_with_tool_request(Owner(),case(),m)
    assert got["model_requested_tool"] is True
    assert got["tool_result"]["status"]=="READ_VERIFIED"
    assert got["tool_result"]["source_access"]=="ALREADY_EXISTING_PINNED_QA_RECEIPT_ONLY"
    assert got["status"]!="NEEDS_HUMAN_TRIAGE"
    assert m.calls==2 and len(called)==1
    assert got["repair_certified"] is False
    assert got["sql_executed_in_this_request"] is False


@pytest.mark.parametrize("tool",[
  {"type":"tool","name":"arbitrary_sql","query_id":r.QUERY_ID,"parameters":{"case_sha256":Owner.case_sha256}},
  {"type":"tool","name":"qa_exact_read","query_id":"DROP_USERS","parameters":{"case_sha256":Owner.case_sha256}},
  {"type":"tool","name":"qa_exact_read","query_id":r.QUERY_ID,"parameters":{"case_sha256":"0"*64}},
  {"type":"tool","name":"qa_exact_read","query_id":r.QUERY_ID,"parameters":{"case_sha256":Owner.case_sha256,"sql":"SELECT *"}},
  {"type":"final","name":"qa_exact_read","query_id":r.QUERY_ID,"parameters":{"case_sha256":Owner.case_sha256}},
  {"type":"tool","name":"qa_exact_read","query_id":r.QUERY_ID,"parameters":{"case_sha256":Owner.case_sha256},"server":"ELSE70"},
])
def test_bad_model_tool_request_denied_before_o5(monkeypatch,tool):
    called=[]
    monkeypatch.setattr(r,"verify_native_o5",lambda owner:called.append(1))
    m=SequencedModel([tool])
    with pytest.raises(QaNativeDenied):
        r.diagnose_with_tool_request(Owner(),case(),m)
    assert m.calls==1 and called==[]


def test_wrong_case_blocked_without_model_or_o5(monkeypatch):
    called=[]
    monkeypatch.setattr(r,"verify_native_o5",lambda owner:called.append(1))
    c=case();c["case_sha256"]="0"*64
    m=SequencedModel([])
    with pytest.raises(QaNativeDenied):
        r.diagnose_with_tool_request(Owner(),c,m)
    assert m.calls==0 and called==[]


def test_model_false_claim_cannot_certify(monkeypatch):
    monkeypatch.setattr(r,"verify_native_o5",lambda owner:observation())
    bad=good_plan();bad["ejecutado"]=True
    m=SequencedModel([exact_tool(),bad])
    got=r.diagnose_with_tool_request(Owner(),case(),m)
    assert got["status"]=="NEEDS_HUMAN_TRIAGE"
    assert got["repair_certified"] is False
    assert got["proposal"]=={}

"""Jan22–31 exact O5 model tool + independently verified receipt negatives."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest
pytest.importorskip("else_core.itil_janlast10_o5_hand",
                  reason="Native Jan O5 integration needs ELSE CORE PR #362")
from else_core.itil_janlast10_o5_hand import (
    AuthorizedNugetReceipt, build_nuget_qa_router,QA_SCOPE,TRANSFER_SCHEMA,QUERY_ID)
from else_core.contracts import Outcome
from else_dominance.qa_janlast10_cluster import finish_fresh_qa_case
from else_dominance.qa_janlast10_native import QaNativeDenied
from test_qa_native_runtime import good_plan

CASE=sha256(b"synthetic-jan26-qa").hexdigest()
SOURCE=sha256(b"authorized-jan-reader-source").hexdigest()


def setup(tmp_path,*,date="2026-01-26T10:00:00",overrides=None):
    case={"schema":"else.itil.qa.sanitized-case.operator-submitted.v1",
          "case_sha256":CASE,"service_code":"1",
          "module_code":"0109100100000",
          "opened_at":date,
          "description":"Synthetic application incident, no repair evidence.",
          "historical_solution":"WITHHELD",
          "content_provenance":"PRIVATE_HISTORICAL_EXPORT_NOT_BYTE_EQUAL_QA_SQL",
          "model_may_execute_sql":False}
    receipt={
          "schema":TRANSFER_SCHEMA,"scope":QA_SCOPE,
          "query_id":QUERY_ID,"case_sha256":CASE,
          "hand_source_sha256":SOURCE,"hand_manifest_sha256":"9"*64,
          "opened_at":date,
          "service_code":"1","module_code":"0109100100000",
          "classification_code":"101","origin_code":"01",
          "status_code":"03","request_bytes":"250",
          "issued_at_utc":"2026-11-10T10:00:00.000000Z",
          "row_count":1,"read_only":True,"provenance_verified":True,
          "historical_solution_not_read":True,
          "deterministic_source_binding_passed":True,
          "negative_sha_tamper_rejected":True,
          "functional_repair_certified":False,
          "core_o5_native_registration":False}
    receipt.update(overrides or {})
    blob=json.dumps(receipt,sort_keys=True).encode()
    file=tmp_path/"receipt.json"
    file.write_bytes(blob)
    owner=AuthorizedNugetReceipt(file,sha256(blob).hexdigest(),
                                 CASE,SOURCE,2000)
    call={"type":"tool","name":"qa_exact_read",
          "query_id":QUERY_ID,"parameters":{"case_sha256":CASE}}
    return owner,case,call


class Model:
    def __init__(self,plan=None):
        self.calls=0
        self.plan=plan or good_plan()
    def complete(self,_):
        self.calls+=1
        return json.dumps(self.plan)


def test_jan_exact_new_hand_can_revise_model_with_verified_metadata(tmp_path):
    owner,case,call=setup(tmp_path)
    model=Model()
    result=finish_fresh_qa_case(owner=owner,case=case,
                                tool_request=call,model=model)
    assert result["o5_o13_o15_verified"] is True
    assert result["query_id"]==QUERY_ID
    assert result["model_had_verified_metadata_before_final"] is True
    assert result["independently_reinspected_metadata"]["opened_at"]==(
        "2026-01-26T10:00:00")
    assert result["repair_certified"] is False
    assert model.calls==1


@pytest.mark.parametrize("date",[
    "2026-01-21T23:59:59",
    "2026-02-01T00:00:00",
    "2026-09-27T10:00:00",
])
def test_wrong_cohort_denied_prior_to_guardian_execution(tmp_path,date):
    owner,case,call=setup(tmp_path,date=date)
    _,router,operation=build_nuget_qa_router(owner)
    result=router.route(operation)
    assert result.outcome!=Outcome.PASS
    assert result.guardian_result.executions==0


def test_jan_case_request_wrong_sha_or_sql_never_reaches_model(tmp_path):
    owner,case,call=setup(tmp_path)
    for bad in (
        {**call,"query_id":"ITIL_2026_09_CASE_EXACT_READ"},
        {**call,"parameters":{"case_sha256":"0"*64}},
        {**call,"parameters":{"case_sha256":CASE,"sql":"UPDATE dbo.X"}},
    ):
        model=Model()
        with pytest.raises(QaNativeDenied):
            finish_fresh_qa_case(owner=owner,case=case,
                                 tool_request=bad,model=model)
        assert model.calls==0


def test_jan_receipt_bytes_change_denied_before_execution(tmp_path):
    owner,case,call=setup(tmp_path)
    owner.path.write_bytes(owner.path.read_bytes()+b" ")
    _,router,operation=build_nuget_qa_router(owner)
    result=router.route(operation)
    assert result.guardian_result.executions==0
    assert result.outcome!=Outcome.PASS


def test_non_declared_sql_table_in_model_plan_rejected(tmp_path):
    owner,case,call=setup(tmp_path)
    plan=good_plan()
    plan["pasos"][0]["accion"]="Consultar SEC.taUsuarioBitacora sin fuente."
    plan["fuentes"]=[]
    result=finish_fresh_qa_case(owner=owner,case=case,
                                tool_request=call,model=Model(plan))
    assert result["status"]=="NEEDS_HUMAN_TRIAGE"
    assert "UNBOUND_SQL_TABLE_REFERENCES" in result["quality"]["safety_flags"]
    assert result["proposal"]=={}

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
    # ELSE CORE PR #360 is a separate checkout. Hosted GitHub CI checks
    # pure ITIL functionality; native O5 integration runs on the QA cluster.
    pytest.importorskip("else_core.itil_nuget_o5_hand",
                        reason="Native O5 integration requires pinned ELSE CORE PR #360")
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
    # January Pareto gate intentionally refuses to treat an ITIL-only
    # receipt as proof of the effective permissions alleged by this case.
    assert result["quality"]["accepted"] is False
    assert result["status"]=="NEEDS_HUMAN_TRIAGE"
    assert result["pareto_evidence_route"]["lane"]=="ACCESS_PERMISSIONS"
    assert result["pareto_evidence_route"]["missing_receipts"]==[
        "SEC_EFFECTIVE_PERMISSION"]
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

def test_windows_catalog_only_transports_no_gold(tmp_path):
    p=Path(__file__).resolve().parents[1]/"qa"
    sys.path.insert(0,str(p))
    from qa_dynamic_nuget_windows import read_allowlist, case_for_cluster
    rows=[]
    for i in range(545):
        ident=f"ITILTEST{i:04d}"
        h=sha256(ident.encode()).hexdigest()
        rows.append({"case_ref":ident,"case_sha256":h,
                     "opened_at":"2026-09-04T10:00:00",
                     "service_code":"1","module_code":"0100100000000",
                     "classification_code":"01",
                     "description_redacted":"Synthetic description for deterministic test."})
    file=tmp_path/"allowlist.jsonl"
    file.write_bytes(b"".join(json.dumps(r).encode()+b"\n" for r in rows))
    loaded=read_allowlist(file)
    assert len(loaded)==545
    clean=case_for_cluster(rows[0])
    assert clean["historical_solution"]=="WITHHELD"
    assert "case_ref" not in clean
    assert "historical_solution_withheld" not in clean
    assert clean["model_may_execute_sql"] is False


def test_windows_allowlist_rejects_identity_drift(tmp_path):
    p=Path(__file__).resolve().parents[1]/"qa"
    sys.path.insert(0,str(p))
    from qa_dynamic_nuget_windows import read_allowlist
    rows=[]
    for i in range(545):
        ident=f"ITILTEST{i:04d}"
        rows.append({"case_ref":ident,"case_sha256":sha256(ident.encode()).hexdigest(),
                     "opened_at":"2026-09-04T10:00:00",
                     "service_code":"1","module_code":"0100100000000",
                     "classification_code":"01",
                     "description_redacted":"Synthetic description with enough length."})
    rows[123]["case_sha256"]="0"*64
    file=tmp_path/"bad_allowlist.jsonl"
    file.write_bytes(b"".join(json.dumps(r).encode()+b"\n" for r in rows))
    with pytest.raises(ValueError,match="ALLOWLIST_ID_SHA"):
        read_allowlist(file)


def test_itil_only_generic_case_can_remain_reviewable(tmp_path):
    owner,c=fixture_owner(tmp_path)
    c["description"]="Incidencia administrativa sin detalle de dominio especializado."
    model=OneResponseModel(good_plan())
    result=finish_fresh_qa_case(owner=owner,case=c,model=model,
                                tool_request=tool(owner.case_sha256))
    assert result["pareto_evidence_route"]["lane"]=="ITIL_TRIAGE"
    assert result["pareto_evidence_route"]["missing_receipts"]==[]
    assert result["quality"]["accepted"] is True
    assert result["repair_certified"] is False


def test_commercial_case_no_longer_claims_ITIL_metadata_is_domain_proof(tmp_path):
    owner,c=fixture_owner(tmp_path)
    c["description"]="Reclamo por lectura del medidor del suministro, requiere verificar orden de trabajo comercial."
    model=OneResponseModel(good_plan())
    result=finish_fresh_qa_case(owner=owner,case=c,model=model,
                                tool_request=tool(owner.case_sha256))
    assert result["pareto_evidence_route"]["lane"]=="COMMERCIAL_OT"
    assert "COMMERCIAL_OT_EXACT" in result["quality"]["missing_verified_receipts"]
    assert result["quality"]["accepted"] is False
    assert result["proposal"]=={}

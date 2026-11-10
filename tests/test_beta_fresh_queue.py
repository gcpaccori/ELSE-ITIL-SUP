"""Adversarial contracts for fresh SAP/OT queue and Windows attestation."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,os
import pytest

from else_dominance.beta_fresh_ot import (
    canonical,queue_job,validate_job,validate_tool,SOURCE_SHA,QUERY)

CASE=sha256(b"fresh-synthetic-itil-case").hexdigest()
REPO_SOURCE=Path(__file__).resolve().parents[1]/"qa/Feb100SapOtRead.cs"
ROW={
    "case_sha256":CASE,
    "opened_at":"2026-02-12T11:30:00",
    "service_code":"1",
    "module_code":"010910",
    "classification_code":"13",
    "description_redacted":"La orden de trabajo OT 12345678 tiene un incidente QA pendiente.",
}

class ExactModel:
    def __init__(self,extra=None):self.extra=extra or {}
    def complete(self,messages):
        tool={
            "type":"tool","name":"qa_sap_ot_exact_read",
            "query_id":QUERY,"parameters":{"case_sha256":CASE}}
        tool.update(self.extra)
        return json.dumps(tool)

def create(tmp_path,model=None,row=None):
    path,job=queue_job(row=dict(row or ROW),
                model=model or ExactModel(),
                requests_dir=tmp_path/"requests",
                source_file=REPO_SOURCE)
    return path,job

def test_valid_model_tool_binds_exact_case_and_not_sql(tmp_path):
    path,job=create(tmp_path)
    assert job["source_sha256"]==SOURCE_SHA
    assert path.stat().st_mode & 0o077==0
    assert job["tool_request"]["parameters"]=={"case_sha256":CASE}
    assert set(job["tool_request"]["parameters"])=={"case_sha256"}
    assert validate_job(job,{CASE:ROW},REPO_SOURCE.read_bytes())=="12345678"

@pytest.mark.parametrize("extra",[
    {"sql":"SELECT ALL"},{"host":"ELSE70"},{"path":"C:\\tmp"},
    {"query_id":"READ_ANY_TABLE"},
    {"parameters":{"case_sha256":CASE,"ot":"12345678"}},
    {"parameters":{"case_sha256":"0"*64}},
])
def test_model_cannot_choose_sql_host_path_or_order(tmp_path,extra):
    with pytest.raises(ValueError):
        create(tmp_path,model=ExactModel(extra))

@pytest.mark.parametrize("field,value",[
    ("reported_ot_sha256","0"*64),
    ("allowlist_row_sha256","0"*64),
    ("source_sha256","0"*64),
    ("source_bytes",123),
    ("query_id","EXECUTE_SQL"),
    ("business_join_certified",True),
    ("repair_certified",True),
    ("read_only",False),
    ("historical_solution_not_read",False),
])
def test_fake_requested_scope_is_rejected(tmp_path,field,value):
    path,job=create(tmp_path)
    job[field]=value
    with pytest.raises(ValueError):
        validate_job(job,{CASE:ROW},REPO_SOURCE.read_bytes())

def test_different_allowlist_row_binding_denied(tmp_path):
    path,job=create(tmp_path)
    changed={**ROW,"service_code":"999"}
    with pytest.raises(ValueError):
        validate_job(job,{CASE:changed},REPO_SOURCE.read_bytes())

def test_multiple_reported_orders_never_queue_sql(tmp_path):
    row={**ROW,"description_redacted":"Dos órdenes OT 12345678 y OT 98765432; no distinguir"}
    with pytest.raises(ValueError):
        create(tmp_path,row=row)
    assert not (tmp_path/"requests").exists()

def test_file_byte_change_cannot_be_pinned_to_wrong_reader(tmp_path):
    path,job=create(tmp_path)
    with pytest.raises(ValueError):
        validate_job(job,{CASE:ROW},REPO_SOURCE.read_bytes()+b"x")

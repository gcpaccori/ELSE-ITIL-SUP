"""Synthetic hostile receipts never substitute for the real ELSE62 QA receipt."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
import hmac,json

import pytest

import else_dominance.qa_verified_connectivity as conn
from else_dominance.qa_verified_connectivity import (
    PROFILES,SCHEMA,PROOF,RECEIPT_NAME,
    QaConnectionRejected,QaSignedConnectionCatalog,verify_qa_probe)
from else_dominance.sources import EvidenceTools
from else_dominance.agent import InvestigationAgent

@pytest.fixture(autouse=True)
def offline_synthetic_reader_source(tmp_path,monkeypatch):
    source=tmp_path/"synthetic-reader.cs"
    source.write_bytes(b"// test-only reader source, no corporate connection or SQL\n")
    monkeypatch.setattr(conn,"SOURCE",source)
    monkeypatch.setattr(conn,"SOURCE_SHA",sha256(source.read_bytes()).hexdigest())

def jsonraw(value):
    return json.dumps(value,ensure_ascii=False,separators=(",",":")).encode()

def fixture_signed(tmp_path,*,now=None):
    now=now or datetime.now(timezone.utc)
    root=tmp_path/"receipts";root.mkdir(mode=0o700)
    signer=tmp_path/"hmac.private"
    key=b"synthetic-ci-key-of-32-bytes!!!!" # This is not a corporate signing key.
    assert len(key)==32
    signer.write_bytes(key);signer.chmod(0o600)
    rows=[]
    for id,system,company,db,table,column in PROFILES:
        rows.append({
          "profile":id,"system":system,"company":company,
          "qa_target":"ELSE70/"+db,
          "source":"dbo."+table,"primary_key_column":column,
          "status":"POSITIVE_TYPED_READ_VERIFIED",
          "identity_hmac":sha256(id.encode()).hexdigest(),
          "selected_rows":1,"typed_exact_rows":1,
          "negative_control_rows":0,
          "read_only":True,"modifications":0,"error":""})
    body={
      "schema":SCHEMA,"worker":"ELSE62","qa_server":"ELSE70",
      "source_sha256":conn.SOURCE_SHA,
      "profile_count":11,"profiles_positive":11,
      "profiles_empty":0,"profiles_blocked":0,
      "observations":rows,"sql_executed_on_qa":True,
      "read_only":True,"changes_executed":False,
      "no_business_row_payload":True,
      "raw_entity_keys_disclosed":False,
      "read_utc":now.isoformat()}
    write_signed(root,signer,body,now)
    return root,signer,body,now

def write_signed(root,signer,body,now):
    raw=jsonraw(body)
    receipt_sha=sha256(raw).hexdigest()
    signed=hmac.new(signer.read_bytes(),
        (SCHEMA+":"+conn.SOURCE_SHA+":"+receipt_sha).encode(),"sha256").hexdigest()
    proof={
      "schema":PROOF,"worker":"ELSE62",
      "source_sha256":conn.SOURCE_SHA,
      "receipt_sha256":receipt_sha,
      "hmac_sha256":signed,"read_only":True,
      "changes_executed":False,"signed_utc":now.isoformat()
    }
    (root/RECEIPT_NAME).write_bytes(raw)
    (root/(RECEIPT_NAME+".proof.json")).write_bytes(jsonraw(proof))

def verify(root,signer,now):
    return verify_qa_probe(root=root,signer=signer,now=now)

def test_signed_synthetic_structure_positive(tmp_path):
    root,signer,body,now=fixture_signed(tmp_path)
    result=verify(root,signer,now)
    assert result["profiles_verified"]==11
    assert result["negative_controls_confirmed"]==11
    assert result["fresh_requery_at_call_time"] is False
    assert result["repair_certified"] is False

@pytest.mark.parametrize("fault",[
    "company_hop","extra_sql","negative_control_hit",
    "fake_positive","source_hop","profile_removed","profile_duplicate",
    "false_readonly","fake_sql","fake_repair"])
def test_resigned_adversarial_payload_is_rejected(tmp_path,fault):
    root,signer,body,now=fixture_signed(tmp_path)
    if fault=="company_hop":body["observations"][7]["company"]=1
    elif fault=="extra_sql":body["observations"][0]["sql"]="DROP TABLE X"
    elif fault=="negative_control_hit":body["observations"][0]["negative_control_rows"]=1
    elif fault=="fake_positive":body["observations"][0]["typed_exact_rows"]=0
    elif fault=="source_hop":body["observations"][7]["qa_target"]="ELSE70/dbComercial001_D"
    elif fault=="profile_removed":body["observations"].pop()
    elif fault=="profile_duplicate":body["observations"][8]=body["observations"][7].copy()
    elif fault=="false_readonly":body["read_only"]=False
    elif fault=="fake_sql":body["sql_executed_on_qa"]=False
    elif fault=="fake_repair":body["repair_certified"]=True
    write_signed(root,signer,body,now)
    with pytest.raises(QaConnectionRejected):
        verify(root,signer,now)

def test_modified_worker_receipt_without_new_signature_is_denied(tmp_path):
    root,signer,body,now=fixture_signed(tmp_path)
    p=root/RECEIPT_NAME
    p.write_bytes(p.read_bytes()+b"\n")
    with pytest.raises(QaConnectionRejected):
        verify(root,signer,now)

def test_wrong_signing_key_rejected(tmp_path):
    root,signer,body,now=fixture_signed(tmp_path)
    signer.write_bytes(b"x"*32)
    with pytest.raises(QaConnectionRejected,match="HMAC"):
        verify(root,signer,now)

def test_expired_or_future_dated_receipt_denied(tmp_path):
    root,signer,body,now=fixture_signed(tmp_path)
    past=now-timedelta(hours=13)
    body["read_utc"]=past.isoformat()
    write_signed(root,signer,body,past)
    with pytest.raises(QaConnectionRejected,match="STALE_OR_FUTURE"):
        verify(root,signer,now)
    future=now+timedelta(minutes=16)
    body["read_utc"]=future.isoformat()
    write_signed(root,signer,body,future)
    with pytest.raises(QaConnectionRejected,match="STALE_OR_FUTURE"):
        verify(root,signer,now)

def test_up_to_15min_qa_clock_skew_is_explicit(tmp_path):
    root,signer,body,now=fixture_signed(tmp_path)
    future=now+timedelta(minutes=9)
    body["read_utc"]=future.isoformat()
    write_signed(root,signer,body,future)
    out=verify(root,signer,now)
    assert out["status"]=="SIGNED_QA_SNAPSHOT_VERIFIED_CLOCK_SKEW"
    assert out["qa_windows_clock_ahead_seconds"]==540
    assert out["clock_skew_bound_seconds"]==900

def test_secret_acl_and_worker_source_integrity_fail_closed(tmp_path):
    root,signer,body,now=fixture_signed(tmp_path)
    signer.chmod(0o644)
    with pytest.raises(QaConnectionRejected,match="ACL_UNSAFE"):
        verify(root,signer,now)
    signer.chmod(0o600)
    bad_source=tmp_path/"SielseQaDomainConnectivity.cs"
    bad_source.write_bytes(conn.SOURCE.read_bytes()+b"// tamper\n")
    with pytest.raises(QaConnectionRejected,match="READER_CODE_BYTES_CHANGED"):
        verify_qa_probe(root=root,signer=signer,now=now,source=bad_source)

def test_only_fixed_profiles_and_no_ticket_evidence(tmp_path):
    root,signer,body,now=fixture_signed(tmp_path)
    cat=QaSignedConnectionCatalog(root=root,signer=signer)
    assert cat.report("UNKNOWN")["status"]=="BLOCKED"
    # Test report uses current UTC clock; use synthetic now from actual clock.
    row=cat.report("COMPANY3_ORDER")
    assert row["status"]=="QA_SNAPSHOT_SOURCE_CONFIRMED_NOT_CASE_READ"
    assert row["qa_target"]=="ELSE70/dbComercial003_D"
    assert row["business_case_evidence"] is False
    assert row["fresh_requery_at_call_time"] is False

class StubMemory:
    pass
class StubCatalog:
    pass
def test_agent_tool_enforces_exact_args_and_case_claim_cannot_be_proven(tmp_path):
    root,signer,body,now=fixture_signed(tmp_path)
    tools=EvidenceTools(StubMemory(),StubCatalog(),
                        qa_catalog=QaSignedConnectionCatalog(root=root,signer=signer))
    assert tools.execute("inspect_qa_connection",{"profile_id":"COMPANY1_ORDER","sql":"DELETE X"}, {})["status"]=="BLOCKED"
    assert tools.execute("inspect_qa_connection",{"profile_id":"COMPANY4_ORDER"}, {})["status"]=="BLOCKED"
    valid=tools.execute("inspect_qa_connection",{"profile_id":"COMPANY1_ORDER"}, {})
    assert valid["status"]=="QA_SNAPSHOT_SOURCE_CONFIRMED_NOT_CASE_READ"
    answered={
      "status":"PLAN_PROPUESTO",
      "confidence":"HIGH",
      "hypotheses":[{"cause":"business state repaired","evidence_refs":["TOOL:1"],"test":"read ticket"}],
      "proposed_steps":[{"action":"close incident","source":"QA",
                         "precondition":"owner","verification":"assess",
                         "evidence_refs":["TOOL:1"]}],
    }
    validated=InvestigationAgent._validate(answered,{
      "TOOL:1":{"name":"inspect_qa_connection","args":{},"result":valid}})
    assert validated["status"]=="INVESTIGACION_PENDIENTE"
    assert validated["live_source_evidence_available"] is False
    assert validated["can_claim_resolved"] is False
    assert validated["can_execute_mutations"] is False

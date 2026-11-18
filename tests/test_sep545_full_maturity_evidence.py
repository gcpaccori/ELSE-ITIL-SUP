"""Public evidence contracts must refuse fabricated mature/diagnostic success."""
from pathlib import Path
import json

import pytest

from qa.sep545_maturity.audit_full_545 import read_private

ROOT=Path(__file__).resolve().parents[1]

def report():
    return json.loads((ROOT/"data"/"2026_sep545_all_features_maturity_scorecard.json").read_text())

def full():
    return json.loads((ROOT/"data"/"2026_sep545_full_maturity_evidence.json").read_text())

def test_current_october_zero_is_not_claimed_as_zero_incidents_companywide():
    r=report()
    assert r["source_october_2026_cases"]==0
    assert r["source_november_1_to_18_cases"]==0
    assert r["decision"]=="NO"
    assert r["eligible_for_unsupervised_corporate_rollout"] is False
    assert r["latest_populated_month"]=="2026-09"
    assert r["september_all_incidents_bound"]==545
    assert any("source" in g.lower() for g in r["failure_gates"])

def test_full_545_historical_outputs_are_not_guided_v4_545_llm():
    x=full()
    assert x["september_unique_source_cases"]==545
    assert x["september_archived_model_plans"]==545
    assert x["september_model_metrics"]["completed"]==543
    assert x["september_model_metrics"]["structural_accepted"]==508
    assert x["september_model_metrics"]["strict_beginner_one_shot_proxy"]==5
    assert x["september_mechanical_stub_only"]["three_turns_stored"]==545
    assert x["september_mechanical_stub_only"]["stub_generated_turns"]==1635
    assert x["real_llm_calls_during_545_mechanical_check"]==0
    assert x["historical_solution_is_not_certified_ground_truth"] is True
    assert x["customer_text_or_hashes_published"] is False

def test_full_sep_windows_source_and_model_case_set_bind():
    x=full()
    assert x["september_all_cases_independently_bound_to_windows"] is True
    assert x["september_historical_nonempty_solution_records"]==455
    assert x["september_historical_closed_date_present"]==382
    assert x["identity_case_set_sha256"]=="aabbd6c4e1eebedcb116b3c490e9fe253dcfc35550cfbf49f7fb27b09b6a9a9c"
    assert x["windows_september_source_receipt_sha256"]=="d2e14b089e51789181043355e4b83143f060de939276ba8f9bc504b7b464a67e"
    assert x["business_writes"]==0
    assert x["certified_root_causes"]==0

def test_real_v4_sample_does_not_establish_diagnostic_maturity():
    r=report()
    assert r["v4_recent_paired_cases"]==24
    assert r["v4_recent_paired_turns"]==72
    assert r["v4_three_turn_cases"]==17
    assert r["v2_three_turn_cases"]==20
    assert r["v4_september_sample_three_turn_cases"]==9
    assert r["v4_september_sample_denominator"]==12
    assert r["v4_escalation_deterministic_sample"]==24
    assert r["independently_certified_diagnoses"]==0
    assert r["individual_human_reviews"]==0
    assert r["v4_synthetic_canary_first_model_quality_accepted"] is False
    assert r["v4_sample72_response_latency_seconds"]["p95_nearest_rank"]>170
    assert r["business_writes"]==0

def test_all_characteristics_gated_without_fake_production_readiness():
    r=report()
    assert len(r["maturity_domains"])==20
    statuses={x["status"] for x in r["maturity_domains"]}
    assert {"FAIL","NOT_CERTIFIED","NOT_MATURE","PARTIAL","VERIFIED_MECHANISM"}<=statuses
    assert r["eligible_for_supervised_private_pilot"] is True
    assert r["eligible_for_unsupervised_corporate_rollout"] is False
    assert not any(x["status"]=="MATURE" for x in r["maturity_domains"])
    s=(ROOT/"docs"/"AUDITORIA_ELSE_ITIL_MADUREZ_OCT2026_SEP545.md").read_text()
    assert "Octubre registró 0 incidentes en esta fuente" in s
    assert "último mes con registros disponible: septiembre" in s
    assert "piloto" in s.lower() and "NO GO" in s
    assert "no se ejecutaron 1.635 diagnósticos Qwen nuevos" in s

def test_private_receipt_hash_mismatch_fails_pre_examination(tmp_path):
    bad=tmp_path/"bad.jsonl"
    bad.write_text('{"case_sha256":"wrong"}\n')
    with pytest.raises(ValueError,match="PRIVATE_RECEIPT_SHA_MISMATCH"):
        read_private(bad,"0"*64)

def test_no_individual_customer_examples_or_secret_literals_published():
    paths=[
        ROOT/"data"/"2026_sep545_full_maturity_evidence.json",
        ROOT/"data"/"2026_sep545_all_features_maturity_scorecard.json",
    ]
    for path in paths:
        j=json.loads(path.read_text())
        s=json.dumps(j,ensure_ascii=False)
        assert "incident_text_redacted" not in s
        assert "technical_plan" not in s
        assert "historical_solution_redacted" not in s
        assert '"case_sha256"' not in s
        assert "password:" not in s.lower()

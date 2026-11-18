"""Real model evidence must not become fake corporate accuracy or SLO."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def test_real_qwen_smoke_tells_truth_about_model_and_deterministic_turn():
    doc=json.loads((ROOT/'data'/'2026_v5_live_model_guidance_synthetic.json').read_text())
    assert doc['schema']=='else.itil.qa.v5-live-synthetic-real-qwen.v1'
    assert doc['turns']==3
    assert doc['actual_qwen_requests']==2
    assert doc['fast_rule_turns_without_model']==1
    assert doc['model_selected_per_turn']==['primary','primary',None]
    assert doc['model_contract_accepted_per_turn']==[True,True,False]
    assert doc['status_per_turn'][-1]=='NEEDS_HUMAN_TRIAGE'
    assert doc['main_safety_fast_handoff_latency_under_5s'] is True
    assert doc['measured_wall_seconds_per_turn'][2]<5
    assert doc['synthetic_corporate_incidents']==0
    assert doc['business_reads_or_writes']==0
    assert doc['root_cause_truth_not_measured'] is True
    assert doc['causal_diagnoses_certified']==0
    assert doc['human_reviews_certified']==0
    assert doc['runtime_readiness']=='NO_GO'
    assert doc['not_a_slo_benchmark'] is True
    assert doc['legacy_v2_v4_not_modified'] is True

def test_no_sensitive_case_session_or_token_in_public_evidence():
    p=ROOT/'data'/'2026_v5_live_model_guidance_synthetic.json'
    text=p.read_text()
    for sensitive in ('session_id','case_ref','Authorization','principal_token',
                      'user_email','incident_text','password:'):
        assert sensitive not in text
    report=(ROOT/'docs'/'ELSE_ITIL_V5_CANARY_QWEN_REAL_20261118.md').read_text()
    assert 'NO CERTIFICADA' in report
    assert 'un único caso sintético' in report
    assert 'quality.accepted=false' in report

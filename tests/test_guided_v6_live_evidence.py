"""V6 evidence is synthetic, sourced and doesn't inflate diagnostic success."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]


def test_real_qwen_consent_transfer_evidence_no_false_diagnosis():
    d=json.loads((ROOT/'data'/
       '2026_v6_live_qwen_consent_handoff_aggregate.json').read_text())
    assert d['schema']=='else.itil.qa.v6-live-qwen-human-handoff.v1'
    assert d['case_count']==1 and d['turn_count']==3
    assert d['real_qwen_turns']==2
    assert d['deterministic_handoff_turns']==1
    assert d['model_contract_accepted_per_turn']==[True,True,False]
    assert d['status_per_turn'][2]=='NEEDS_HUMAN_TRIAGE'
    assert d['wall_seconds_per_turn'][2]<5
    assert d['consented_packet_signed_verified']
    assert d['revoke_all_online_verification_fails_with_422']
    assert d['registered_core_goals_available']==[
      'ITIL_CASE_EXISTS','ITIL_SERVICE','ITIL_MODULE']
    assert d['qa_hand_started'] is False
    assert d['corporate_ticket_identity_bound'] is False
    assert d['business_source_queried'] is False
    assert d['business_changes_executed'] is False
    assert d['root_causes_certified']==0
    assert d['human_reviews_completed']==0
    assert d['readiness']=='NO_GO'
    assert d['accuracy_not_measured'] is True


def test_public_bundle_contains_no_session_token_or_private_case_text():
    p=ROOT/'data'/'2026_v6_live_qwen_consent_handoff_aggregate.json'
    content=p.read_text()
    for token in ('session_id','case_ref','authorization','principal_token',
                  'token_sha256','handoff_key','incident_text','signed_packet'):
        assert token not in content.lower()
    report=(ROOT/'docs'/'ELSE_ITIL_V6_PRUEBA_REAL_QWEN_Y_ENTREGA_20261119.md').read_text()
    assert 'sin volver a generar respuestas de Qwen' in report
    assert 'no es una tasa de éxito' in report
    assert 'NO' in report

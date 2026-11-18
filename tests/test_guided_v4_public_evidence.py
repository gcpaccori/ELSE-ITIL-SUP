"""Static proof that the published pilot report cannot inflate model success."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def read(name):
    return json.loads((ROOT/'data'/name).read_text())

def test_real_72_turn_24_case_frozen_evaluation_is_source_bound():
    result=read('2026_aug_sep_guided_v4_final_paired_eval.json')
    paired=read('2026_aug_sep_guided_v4_final_live_paired_comparison.json')
    assert result['cases']==24
    assert result['calls']==72
    assert paired['case_set_identical'] is True
    assert paired['same_24_historical_source_cases'] is True
    assert sum(r['cases'] for r in paired['per_month'].values())==24
    assert sum(r['turns_per_version'] for r in paired['per_month'].values())==72
    assert paired['months']=={'2026-08':1819,'2026-09':545}
    assert paired['certified_diagnoses']==0
    assert paired['real_repairs_executed']==0

def test_critical_negative_comparison_is_kept_without_score_inflation():
    d=read('2026_aug_sep_guided_v4_final_live_paired_comparison.json')
    old=sum(v['counts']['prior_all_three_accepted'] for v in d['per_month'].values())
    new=sum(v['counts']['new_all_three_accepted'] for v in d['per_month'].values())
    safe_handoff=sum(v['counts']['turn3_user_handoff_visible']
                     for v in d['per_month'].values())
    assert old==20 and new==17
    assert safe_handoff==24
    assert new<old
    assert all(v['counts'].get('v4_model_accepted_but_current_gate_rejected',0)==0
               for v in d['per_month'].values())

def test_report_does_not_claim_human_diagnostic_certification():
    text=(ROOT/'docs'/'EVALUACION_ELSE_ITIL_V4_FINAL_20261118.md').read_text()
    assert '17/24' in text
    assert '20/24' in text
    assert 'SIN CERTIFICAR' in text
    assert 'NO debe sustituir' in text
    assert 'No se ha consultado ninguna solución histórica' in text
    assert 'PILOTO PRIVADO SUPERVISADO' in text

def test_new_canary_is_independent_of_v2_main_unit():
    text=(ROOT/'ops'/'deploy_specialist_v4_private_canary.sh').read_text()
    assert 'else-itil-novice-v4-canary.service' in text
    assert 'else-itil-specialist-v1.service' in text
    assert 'ROLLBACK_V2' in text or 'V2_UNTOUCHED' in text

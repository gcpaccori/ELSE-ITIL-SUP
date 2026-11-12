"""Read-only prior-history hints are bounded and do not silently prove facts."""
from copy import deepcopy
import pytest
from else_dominance.functional_investigator_v2 import run_case

CASE={
    'ticket_sha256':'a'*64,
    'incident_text_redacted':'No aparece el movimiento bancario en la consulta del módulo.'
}
HINT={
    'kind':'UPDATE_MENTIONED',
    'table':'tacobranza',
    'fields':['codigocaja'],
    'count':3,
    'historical_note_only':True,
    'execution_confirmed':False
}

@pytest.mark.parametrize('bad',[
    [{'kind':'UPDATE_MENTIONED','table':'DROP TABLE data',
      'fields':['codigocaja'],'count':1,
      'historical_note_only':True,'execution_confirmed':False}],
    [{**HINT,'execution_confirmed':True}],
    [{**HINT,'historical_note_only':False}],
    [{**HINT,'count':'3'}],
    [{**HINT,'fields':['codigocaja']*13}],
    [HINT]*6,
    'untrusted text',
    None,
])
def test_hint_validation_rejects_untrusted(bad):
    if bad is None:
        result=run_case(CASE,max_attempts=0,verified_module_name='Movimientos Bancarios',
                        historical_pattern_hints=None)
        assert result['prior_history_pattern_count']==0
    else:
        with pytest.raises(ValueError,match='HISTORICAL_PATTERN'):
            run_case(CASE,max_attempts=0,verified_module_name='Movimientos Bancarios',
                     historical_pattern_hints=bad)

def test_hint_does_not_execute_or_claim_resolution():
    result=run_case(CASE,max_attempts=0,verified_module_name='Movimientos Bancarios',
                    historical_pattern_hints=[HINT])
    assert result['prior_history_pattern_count']==1
    assert result['root_cause_certified'] is False
    assert result['repair_certified'] is False
    assert result['live_domain_evidence_verified'] is False
    assert result['historical_resolution_exposed'] is False
    assert result['prior_history_not_current_incident_solution'] is True

def test_audited_hint_is_in_prompt_but_not_source_fact(monkeypatch):
    from else_dominance import functional_investigator_v2 as mod
    captured=[]
    def mock_model(messages):
        captured.extend(messages)
        raise ValueError('MOCK_MODEL_DISABLED')
    monkeypatch.setattr(mod,'call_model',mock_model)
    result=run_case(CASE,max_attempts=1,verified_module_name='Movimientos Bancarios',
                    historical_pattern_hints=[HINT])
    assert result['status']=='FUNCTIONAL_DRAFT_REJECTED'
    assert len(captured)==2
    content=captured[1]['content']
    assert '"earlier_same_module_historical_pattern_mentions"' in content
    assert '"historical_note_only": true' in content
    assert 'no describen el estado ni la solución de este incidente' in content.lower()
    assert result['root_cause_certified'] is False


def test_hint_without_verified_module_refused():
    with pytest.raises(ValueError,match="VERIFIED_MODULE_REQUIRED"):
        run_case(CASE,max_attempts=0,historical_pattern_hints=[HINT])

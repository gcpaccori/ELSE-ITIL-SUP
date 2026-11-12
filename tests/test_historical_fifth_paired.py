"""Synthetic paired comparison checks; neither tickets nor historical notes included."""
import pytest
from qa.may2026.evaluate_private_fifth_paired import score_pairs,score_holdout
from else_dominance.historical_procedures import HistoricalProcedureCatalog
from tests.test_historical_procedure_catalog import sample

def pair(rank,a='FUNCTIONAL_DRAFT_CONTRACT_PASS',b='FUNCTIONAL_DRAFT_CONTRACT_PASS'):
    k=f'{rank:064x}'
    return {
        'rank':rank,'case_sha256':k,'gold_solution_exposed':False,
        'baseline':{'case_sha256':k,'status':a},
        'with_hints':{'case_sha256':k,'status':b}}

def grader(rank,condition,match):
    return {'rank':rank,'condition':condition,'case_sha256':f'{rank:064x}',
      'author_gold_seen':False,'status':'PROVISIONAL_JUDGE_PASS',
      'assessment':{'match':match}}

def test_paired_score_separates_passing_plan_from_specific_match():
    a=[pair(1),pair(2,'FUNCTIONAL_DRAFT_CONTRACT_PASS','FUNCTIONAL_DRAFT_REJECTED')]
    j=[grader(1,'baseline','SPECIFIC_MATCH'),grader(1,'hints','SPECIFIC_MATCH'),
       grader(2,'baseline','PARTIAL'),grader(2,'hints','NO_VALID_PLAN')]
    c=score_pairs(a,j)
    assert c['baseline_FUNCTIONAL_DRAFT_CONTRACT_PASS']==2
    assert c['hints_FUNCTIONAL_DRAFT_CONTRACT_PASS']==1
    assert c['valid_plan_loss']==1
    assert c['specific_gain']==0
    assert c['specific_loss']==0

def test_missing_judgement_rejected():
    with pytest.raises(ValueError,match='JUDGE_PAIRS_MISSING'):
        score_pairs([pair(1)],[grader(1,'baseline','PARTIAL')])

def test_retrospective_sql_mention_overlap_not_proof_of_causality(tmp_path):
    cat=HistoricalProcedureCatalog(sample(tmp_path))
    requests={'results':[{'case_sha256':f'{i:064x}',
            'module_code':'0102100100000'} for i in range(1,101)]}
    histories={'historical_records':[{'case_sha256':f'{i:064x}',
        'historical_solution_redacted':(
            'UPDATE a SET a.CodigoCaja=11 FROM taCobranza a'
            if i==1 else 'solicitud atendida')}
        for i in range(1,101)]}
    r=score_holdout(cat,requests,histories)
    assert r['rows']==100
    assert r['prior_available']==100
    assert r['historical_sql_mentioned']==1
    assert r['exact_overlap']==1
    assert 'repairs' not in r

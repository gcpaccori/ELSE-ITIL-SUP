import json
import pytest
from else_dominance.ensemble import combine


def _write(path, labels, binding='same'):
    with open(path,'w') as f:
        for name,valid in labels:
            f.write(json.dumps({'case_ref':name,'run_binding':binding,
                                'status':'PLAN_REVIEWABLE' if valid else 'PLAN_REJECTED',
                                'hard_gate':{'valid':valid},
                                'proposal':{'estado':'INVESTIGACION_ESPECIFICA'}})+'\n')


def test_dual_model_selects_valid_only(tmp_path):
    a,b,out=(tmp_path/x for x in ('a','b','out'))
    _write(a,[('case1',True),('case2',False),('case3',False)])
    _write(b,[('case1',True),('case2',True),('case3',False)])
    result=combine(a,b,out,expected_count=3)
    assert result=={'cases':3,'reviewable':2,'both_valid':1,'no_valid_plan':1,'certified_fixes':0}
    rows=[json.loads(x) for x in out.read_text().splitlines()]
    assert rows[1]['selected_model']=='secondary'
    assert rows[2]['proposal'] is None
    assert all(r['requires_human_review'] and not r['certified_fix'] for r in rows)


def test_dual_model_rejects_cohort_mismatch(tmp_path):
    a,b,out=(tmp_path/x for x in ('a','b','out'))
    _write(a,[('case1',True)])
    _write(b,[('case2',True)])
    with pytest.raises(ValueError,match='CROSS_MODEL_COHORT_MISMATCH'):
        combine(a,b,out,expected_count=1)


def test_dual_model_rejects_different_history(tmp_path):
    a,b,out=(tmp_path/x for x in ('a','b','out'))
    _write(a,[('case1',True)],binding='A')
    _write(b,[('case1',True)],binding='B')
    with pytest.raises(ValueError,match='CROSS_MODEL_INPUT_MISMATCH'):
        combine(a,b,out,expected_count=1)

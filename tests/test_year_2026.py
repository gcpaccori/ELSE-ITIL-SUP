import csv
import pytest

from else_dominance.year_2026 import summarize_months

DATA='data/qa_2026_monthly_aggregate.csv'


def test_actual_qa_2026_aggregate_totals():
    out=summarize_months(DATA)
    assert out['cases']==14950
    assert out['related_precedents']==13545
    assert out['P1_consensus_candidate_NOT_CERTIFIED']==1155
    assert out['P2_related_but_no_consensus']==12390
    assert out['P3_no_related_precedent']==1405
    assert out['lexical_agreement']=={'matches':292,'evaluable':367,'mismatches':75}
    assert out['certified_resolutions']==0
    assert len(out['monthly'])==9
    assert out['months_not_in_sample']==['2026-10','2026-11','2026-12']


def test_bad_aggregate_is_never_massaged_into_success(tmp_path):
    rows=list(csv.DictReader(open(DATA,encoding='utf-8')))
    rows[0]['related_precedent']='999999'
    out=tmp_path/'bad.csv'
    with open(out,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    with pytest.raises(ValueError,match='IMPOSSIBLE'):
        summarize_months(out)


def test_missing_month_is_not_zero_business_activity(tmp_path):
    rows=list(csv.DictReader(open(DATA,encoding='utf-8')))[:-1]
    out=tmp_path/'missing.csv'
    with open(out,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    s=summarize_months(out)
    assert '2026-09' in s['months_not_in_sample']
    assert s['sample_only_do_not_imply_no_business_activity_in_missing_months']

"""Published month-end model scorecard must be honest about its denominator."""
from pathlib import Path
import json

def test_model_not_misrepresented_as_900_llm_runs():
    root=Path(__file__).resolve().parents[1]
    x=json.loads((root/'data/2026_monthend_qwen9b_90sample.json').read_text())
    assert x['universe_last100_per_month']==900
    assert x['qwen9b_author_samples']==90
    assert x['not_a_nine_hundred_llm_plan_experiment'] is True
    assert x['sample_ranks_per_month']==[1,12,23,34,45,56,67,78,89,100]
    assert x['author_never_saw_gold'] is True
    assert x['repairs_certified']==0
    assert x['business_changes']==0

def test_monthly_model_sample_matches_public_aggregate():
    root=Path(__file__).resolve().parents[1]
    x=json.loads((root/'data/2026_monthend_qwen9b_90sample.json').read_text())
    assert len(x['months'])==9
    assert all(v['sample_n']==10 for v in x['months'].values())
    t=x['totals']
    assert t['sample_n']==90
    assert t['author_FUNCTIONAL_DRAFT_CONTRACT_PASS']==68
    assert t['author_CLARIFICATION_REQUIRED']==17
    assert t['author_FUNCTIONAL_DRAFT_REJECTED']==5
    assert t['judge_JUDGE_REJECTED']==23
    assert t['provisional_alignment_SAME_MECHANISM']==1
    assert t['provisional_alignment_PARTIAL_PROCESS_MATCH']==25
    assert t['provisional_alignment_NO_VALID_PLAN']==20

def test_public_report_contains_no_private_ticket_details():
    root=Path(__file__).resolve().parents[1]
    raw=(root/'data/2026_monthend_qwen9b_90sample.json').read_text()
    assert '"description_redacted":' not in raw
    assert '"historical_solution_redacted":' not in raw
    assert '"case_sha256":' not in raw
    assert '"evidence_quote":' not in raw
    assert '"ticket_fact_quotes":' not in raw

"""Public receipt-bound aggregate regression for real June 2026 1621-case QA."""
from pathlib import Path
import json
import pytest

from qa.june2026.run_blind_qwen_sample import SAMPLE
from qa.june2026.evaluate_all_1621 import note_buckets
from qa.monthend2026.score_history_labels import distinguish_evidence_quote

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    return json.loads((ROOT/'data'/name).read_text())

def test_all_june_1621_in_scope_and_case_binding():
    data=load('2026_june_all_1621_historical_contrast.json')
    assert data['source_cases']==1621
    assert data['case_identity_bindings_verified']==1621
    assert data['all_june_hmac_verification']=='PASS'
    assert data['previous_last100_independently_sealed_matches']==100
    assert data['selection']=='ALL_1621_JUNE_INCIDENTS'
    assert data['period_start']=='2026-06-01'
    assert data['period_end_exclusive']=='2026-07-01'
    assert data['history_hidden_during_blind_request_routing'] is True
    assert data['earlier_may_training_not_june_holdout'] is True
    assert len(data['request_source_receipt_sha256'])==64
    assert len(data['historical_source_receipt_sha256'])==64

def test_all_june_counts_preserved_without_filtering_unknown():
    data=load('2026_june_all_1621_historical_contrast.json')
    t=data['totals']
    assert t['evaluated']==t['request_nonempty']==t['known_corporate_module']==1621
    assert t['domain_routed']==1318
    assert data['domains']['UNKNOWN']==303
    assert t['eligible_for_blind_llm']==1312
    assert sum(data['domains'].values())==1621
    assert sum(data['companies'].values())==1621
    assert sum(x['evaluated'] for x in data['weeks'].values())==1621

def test_all_june_history_not_silently_equated_with_execution():
    data=load('2026_june_all_1621_historical_contrast.json')
    t=data['totals']
    assert t['history_nonempty']==1610
    assert t['history_answer_date_present']==1612
    assert t['history_close_date_present']==1605
    assert t['historical_sql_mention_structured']==462
    assert t['sql_text_only']==536
    assert t['pre_june_exact_sql_table_fields_and_kind']==69
    assert t['pre_june_same_sql_table_and_kind']==95
    assert t['pre_june_request_grounded_and_gold_both_sql']==160
    assert t['prior_may_sql_pattern_request_anchored']==299
    assert data['no_claim_that_sql_in_note_was_executed'] is True
    assert data['real_remediations_certified']==0
    assert data['business_writes_executed']==0

def test_may500_transfer_temporally_sealed_and_only_three_extra_hits():
    full=load('2026_june_all_1621_historical_contrast.json')
    val=load('2026_june_all_1621_may500_historical_transfer.json')
    assert val['train_count']==500 and val['test_count']==1621
    assert val['train_month']=='2026-05' and val['test_month']=='2026-06'
    assert val['verified_train_cohorts']==5
    assert len(val['training_receipt_sha256'])==5
    assert val['strict_earlier_month_training'] is True
    assert val['zero_june_holdout_notes_used_for_training'] is True
    assert val['totals']['exact_kind_table_fields']==72
    assert val['totals']['same_kind_and_table']==95
    assert val['totals']['request_grounded_sql_candidate']==302
    assert val['totals']['evaluated']==1621
    assert val['totals']['exact_kind_table_fields']-full['totals']['pre_june_exact_sql_table_fields_and_kind']==3
    assert val['repairs_certified']==val['business_writes_executed']==0

def test_systematic_sample_covers_both_month_boundaries():
    assert len(SAMPLE)==100 and len(set(SAMPLE))==100
    assert list(SAMPLE)==sorted(SAMPLE)
    assert SAMPLE[0]==1 and SAMPLE[-1]==1621
    assert SAMPLE[49]<811<SAMPLE[51]
    assert SAMPLE[-1]-SAMPLE[0]==1620

def test_qwen100_and_independent_judge_are_not_conflated():
    result=load('2026_june_all_1621_qwen100_blind_scorecard.json')
    c=result['counts']
    assert result['sample_completed']==100
    assert result['sample_positions']==list(SAMPLE)
    assert result['universe_all_june_incidents']==1621
    assert result['all_author_cases_blind_to_historical_gold'] is True
    assert result['all_judge_quotes_extracted_from_exact_signed_notes'] is True
    assert c['sampled_cases']==100
    assert c['author_FUNCTIONAL_DRAFT_CONTRACT_PASS']==72
    assert c['author_CLARIFICATION_REQUIRED']==22
    assert c['author_FUNCTIONAL_DRAFT_REJECTED']==6
    assert c['judge_schema_and_quote_verified']==82
    assert c['judge_rejected']==18
    assert c['judge_alignment_PARTIAL_PROCESS_MATCH']==26
    assert c['judge_alignment_SAME_MECHANISM']==5
    assert c['provisional_specific_mechanism_documentary_overlap']==5
    assert c['provisional_same_mechanism_quote_SQL_REFERENCE_ONLY_NOT_EXECUTED']==4
    assert c['provisional_same_mechanism_quote_SPECIFICITY_NOT_ESTABLISHED']==1
    assert result['judge_provisional_not_human_ground_truth'] is True
    assert result['business_repair_certified']==0

def test_public_reports_aggregate_only():
    for file in (
        '2026_june_all_1621_historical_contrast.json',
        '2026_june_all_1621_may500_historical_transfer.json',
        '2026_june_all_1621_qwen100_blind_scorecard.json'):
        raw=(ROOT/'data'/file).read_text()
        for secret in (
          '"case_sha256":', '"description_redacted":',
          '"historical_solution_redacted":','"CodigoIncidente":',
          '"module_declared_alias_bde":','"observed_value":',
          '"historial_respondedor":','"user_password":',
          '"notes_by_user":','"sql_text":'):
            assert secret not in raw,(file,secret)

def test_readers_only_fixed_june_selects_not_top100():
    s=(ROOT/'qa/june2026/JuneAllRead.cs').read_text()
    assert 'OneMonth(db,key,sourceSha,6);' in s
    assert 'SELECT COUNT_BIG(*)' in s
    assert 'SELECT CodigoIncidente' in s
    assert 'SELECT TOP(100) CodigoIncidente' not in s
    assert '2026-juneall-source.v1' in s
    assert '2026-juneall-history.v1' in s
    assert 'OneMonth' in s and 'SignedWrite' in s
    assert 'ELSE70' in s and 'dbITIL_D' in s
    assert 'DescripcionSolucion' in s and 'DescripcionSolicitud' in s
    assert 'HMACSHA256' in s and 'sp_executesql' in s

@pytest.mark.parametrize(('note','expected'),[
    ('','empty_note'),
    ('UPDATE a SET a.CodigoCaja=42 FROM taCobranza a','sql_text_only'),
    ('Incidente cerrado','generic_closure'),
    ('Se ha corregido el registro del sistema','narrated_action'),
    ('Por favor, verificar el módulo','instruction_or_recommendation')
])
def test_historical_note_quality_flags_not_execution(note,expected):
    f=note_buckets(note)
    assert f[expected] is True
    assert not f['empty_note'] or expected=='empty_note'

def test_sql_quote_never_proves_execution():
    assert distinguish_evidence_quote('UPDATE a SET CodigoEstado=3 FROM taOrdenTrabajo a')=='SQL_REFERENCE_ONLY_NOT_EXECUTED'

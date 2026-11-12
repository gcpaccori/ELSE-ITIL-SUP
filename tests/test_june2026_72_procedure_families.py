"""Freeze the difference between ticket counts and distinct procedure families."""
from pathlib import Path
import json
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'data/2026_june72_procedure_family_taxonomy.json'

def report():
    return json.loads(FILE.read_text())

def test_72_case_set_has_only_thirteen_unique_families():
    r=report()
    c=r['counts']
    assert c['cases_selected']==72
    assert c['canonical_procedure_families']==13
    assert c['case_family_memberships']==76
    assert len(r['families'])==13
    assert sum(x['unique_cases_mentioning_family'] for x in r['families'])==76
    assert r['evaluated_june_original_cases']==1621
    assert r['model_training_prior_cases']==500
    assert r['selection_is_posthoc_documentary_overlap'] is True

def test_35_collection_cases_are_one_reported_update_family_not_35_actions():
    r=report()
    x=next(f for f in r['families'] if f['table']=='tacobranza')
    assert x['operation']=='UPDATE_MENTIONED'
    assert x['fields']==['codigocaja']
    assert x['unique_cases_mentioning_family']==35
    assert x['executed_transaction_proven'] is False

def test_taxonomy_covers_six_business_areas_but_no_repairs():
    r=report(); c=r['counts']
    assert c['commercial_ot_cases']==22
    assert c['document_attachment_cases']==10
    assert c['reconnection_procedure_cases']==4
    assert c['other_cases']==15
    assert c['historical_transactions_certified']==0
    assert c['enterprise_repairs_certified']==0
    assert r['sql_reference_is_not_execution'] is True
    assert r['procedural_signature_is_table_kind_set_fields_not_exact_business_action'] is True

def test_technical_signatures_are_distinct_and_no_private_ticket_text():
    r=report()
    assert len({(x['table'],x['operation'],tuple(x['fields'])) for x in r['families']})==13
    assert all(x['unique_cases_mentioning_family']>=1 for x in r['families'])
    raw=FILE.read_text().lower()
    for marker in ('"case_sha256":','"description_redacted":',
                   '"historical_solution_redacted":',
                   '"codigo_incidente":','"codigoorden":',
                   '"user_password":','"dni":','"valoractual":'):
        assert marker not in raw
    assert len(r['source_receipt_sha256'])==64
    assert len(r['history_receipt_sha256'])==64

def test_procedure_terms_are_only_documentary_not_verified_repairs():
    assert all(f['operation'].endswith('_MENTIONED') for f in report()['families'])

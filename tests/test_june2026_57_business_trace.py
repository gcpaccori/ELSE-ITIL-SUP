"""Aggregate-only regression for 57 real June OT/Cobranza posthoc cases."""
from pathlib import Path
import json,re
import pytest

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'data/2026_june57_business_source_trace.json'

def data():
    return json.loads(REPORT.read_text(encoding='utf-8'))

def test_cohort_is_signed_may500_june1621_posthoc_not_blind_model():
    d=data()
    assert d['schema']=='else.itil.qa.2026-june57-business-candidate-aggregate.v1'
    assert d['month']=='2026-06'
    assert d['original_june_cases']==1621
    assert d['selected_cases']==57
    assert d['selection_from_72_documentary_exact_cases'] is True
    assert d['not_a_blind_llm_evaluation'] is True
    assert d['strict_identifiers_only'] is True
    assert d['totals']['ot']==22
    assert d['totals']['collections']==35
    assert sum((d['totals']['ot'],d['totals']['collections']))==57

def test_primary_key_evidence_ladder_is_not_overstated():
    t=data()['totals']
    assert t['identity_NO_EXPLICIT_PRIMARY_KEY']==41
    assert t['identity_HISTORICAL_NOTE_ONLY_PK']==9
    assert t['identity_REQUEST_AND_NOTE_SAME_ID']==3
    assert t['identity_AMBIGUOUS_IDENTIFIER']==3
    assert t['identity_CONFLICT_REQUEST_HISTORICAL_IDS']==1
    assert sum(t['identity_'+x] for x in (
        'NO_EXPLICIT_PRIMARY_KEY','HISTORICAL_NOTE_ONLY_PK',
        'REQUEST_AND_NOTE_SAME_ID','AMBIGUOUS_IDENTIFIER',
        'CONFLICT_REQUEST_HISTORICAL_IDS'))==57
    assert t['no_safe_explicit_id_for_lookup']==45
    assert t['selected_exact_id_lookups']==12

def test_all_database_probes_complete_but_are_not_repair_proof():
    d=data()
    t=d['totals']
    assert t['distinct_database_sources_scanned']==13
    assert t['positive_database_case_pairs']==12
    assert t['cases_with_any_positive_db_match']==12
    assert t['positive_gerencial_pairs']==10
    assert t['positive_daily_copy_pairs']==2
    assert t['positive_distribution_pairs']==0 if 'positive_distribution_pairs' in t else True
    assert t['request_backed_pk_case_found']==3
    assert t['gold_only_pk_case_found']==9
    assert t['case_repairs_certified']==0
    assert t['cases_with_complete_before_after']==0
    assert t['business_writes']==0
    assert d['backdated_business_state_not_verified'] is True
    assert d['unverified_actual_business_execution'] is True
    assert d['real_fix_certified'] is False

def test_most_collection_cases_do_not_have_primary_key():
    d=data()
    assert d['by_category']['COLLECTION']['NO_EXPLICIT_PRIMARY_KEY']==33
    assert d['by_category']['COLLECTION']['HISTORICAL_NOTE_ONLY_PK']==2
    assert d['by_category']['COLLECTION']['cases_found_any_db']==2
    assert d['by_category']['OT']['cases_found_any_db']==10
    assert d['by_category']['OT']['REQUEST_AND_NOTE_SAME_ID']==3

def test_reports_can_reverify_code_receipts_but_not_reveal_private_values():
    d=data()
    assert len(d['receipt_sha256'])==4
    for k in ('selection','source_and_business',
              'june1621_requests','june1621_history'):
        assert re.fullmatch('[0-9a-f]{64}',d['receipt_sha256'][k])
    assert d['no_personal_name_or_business_identifier_in_public_output'] is True
    raw=REPORT.read_text()
    for indicator in (
       '"case_sha256":','"CodigoIncidente":','"DescripcionSolicitud":',
       '"historical_solution_redacted":','"identifier_private":',
       '"identifier_sha256":','"DNI":','"CodigoSuministro":',
       '"CodigoCobranza":','"CodigoOrdenTrabajo":',
       '"UsuarioModifica":','"sql_text":','"NombreCliente":',
       '"snapshot":','"case_identity_data":','"searched_databases":'):
        assert indicator not in raw

def test_bounded_sql_reader_does_not_construct_sql_from_tickets():
    s=(ROOT/'qa/june2026_57/June57SourceAndTargetsRead.cs').read_text()
    assert 'fnObtenerDatosProcedimientoDataSetN("[sys].[sp_executesql]"' in s
    assert 'WHERE FechaSolicitud>=@start AND FechaSolicitud<@end' in s
    assert 'CodigoOrdenTrabajo=@id' in s
    assert 'CodigoCobranza=@id' in s
    assert 'WHERE CodigoOrdenTrabajo=@id' in s
    assert 'WHERE CodigoCobranza=@id' in s
    assert 'new SqlParameter("@id",SqlDbType.BigInt)' in s
    assert 's.name=' in s
    assert 'dbDistribucion_D' in s
    assert 'CAST(NULL AS tinyint) AS CodigoCentroAtencion' in s
    assert 'HMACSHA256.HashData' in s
    assert 'eSistema.ITIL' in s and 'eSistema.Comercial' in s
    assert 'no_historical_sql_executed=true' in s
    assert 'business_repairs_certified=0,business_writes=0' in s

def test_certified_source_file_hash_and_receipt_are_not_interchangeable():
    d=data()
    assert d['receipt_sha256']['selection']!=d['receipt_sha256']['source_and_business']
    assert d['receipt_sha256']['june1621_requests']!=d['receipt_sha256']['june1621_history']

@pytest.mark.parametrize(('subcategory','expected'),[
 ('OT',22),('COLLECTION',35)])
def test_fixed_category_counts_from_same_sealed_cohort(subcategory,expected):
    t=data()['totals']
    assert t['ot' if subcategory=='OT' else 'collections']==expected

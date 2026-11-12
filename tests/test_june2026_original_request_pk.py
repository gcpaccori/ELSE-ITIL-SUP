"""Frozen public report for June 57-source-only primary key discovery."""
from pathlib import Path
from collections import Counter
import json,re
ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'data/2026_june57_original_request_pk_recovery.json'

def report():
    return json.loads(FILE.read_text())

def test_619_matched_case_key_pairs_are_not_619_distinct_global_business_keys():
    r=report();t=r['totals']
    assert r['schema']=='else.itil.qa.2026-june57-request-pk-recovery-aggregate.v1'
    assert t['selected_cases']==57
    assert t['candidate_case_pk_pairs']==620
    assert t['matched_case_pk_pairs']==619
    assert t['distinct_business_primary_keys']==525
    assert t['repeated_business_keys_across_tickets']==87
    assert t['repeat_ticket_key_memberships']==94
    assert 619-525==94

def test_requests_link_to_pk_in_55_cases_with_two_unresolved():
    t=report()['totals']
    assert t['cases_with_exact_pk_matches']==55
    assert t['cases_without_exact_pk_match']==2
    assert t['cases_without_19_digit_number']==1
    assert t['unmatched_candidates']==1
    assert t['newly_rescued_vs_strict_request_pk']==52
    assert t['ot_cases_matched']==20
    assert t['collection_cases_matched']==35

def test_database_distribution_exact_with_same_itil_business_branch():
    r=report()
    assert r['matched_databases']==[
      {'category':'COLLECTION','database':'dbComercial001_Diario','match_count':489},
      {'category':'OT','database':'dbDistribucion_D','match_count':3},
      {'category':'OT','database':'dbGerencial_D','match_count':127}
    ]
    assert sum(x['match_count'] for x in r['matched_databases'])==619
    assert r['rich_text_generic_numeric_tokens_ignored'] is True
    assert r['historical_solution_not_read_for_identifier_recovery'] is True
    assert r['cohort_was_selected_posthoc_using_previous_documentary_overlap'] is True

def test_unrelated_cross_type_number_not_promoted_to_order_work():
    r=report()
    assert r['residual_cross_type_match_not_counted'] is True
    assert r['ticket_business_fk_not_formally_certified'] is True
    assert r['current_qa_pk_presence_not_a_repair'] is True
    assert r['business_writes']==0
    assert r['business_repairs_certified']==0

def test_all_six_proof_hashes_pinned_and_not_exposing_identifiers():
    r=report()
    assert len(r['receipt_proofs'])==6
    assert all(re.fullmatch(r'[0-9a-f]{64}',v) for v in r['receipt_proofs'].values())
    assert r['private_receipts_hold_unmasked_ids'] is True
    raw=FILE.read_text()
    for term in (
       '"identifier_private":','"case_sha256":','"codigo_suministro":',
       '"primary_key_19_digit":','"description_redacted":',
       '"descripcion_solicitud":','"historical_solution":',
       '"ruc":','"numero_dni":','"nombre_cliente":'):
        assert term not in raw.lower()

def test_bulk_reader_uses_only_request_text_and_bigint_params_not_raw_sql_from_notes():
    s=(ROOT/'qa/june2026_identity/June57BulkPrimaryKeyMatch.cs').read_text()
    assert 'DescripcionSolicitud FROM dbo.taIncidente' in s
    assert 'DescripcionSolucion FROM dbo.taIncidente' not in s
    assert 'no_rich_text_numbers_used=true' in s
    assert r'(?<!\d)\d{19}(?!\d)' in s
    assert 'SqlDbType.BigInt' in s
    assert 'business_writes=0,read_only=true' in s
    assert 'WHERE FechaSolicitud>=@start AND FechaSolicitud<@end' in s
    assert 'HMACSHA256.HashData' in s

def test_private_export_requires_hmac_and_stays_outside_git():
    s=(ROOT/'qa/june2026_identity/export_private_recovered_pk.py').read_text()
    assert 'verify_one(' in s
    assert 'os.chmod(dest,0o600)' in s
    assert 'dest.resolve().parent==private.resolve()' in s
    assert 'len(data[\'matches\'])==619' in s
    assert not list(ROOT.glob('**/*private.csv'))

def test_existing_unmasked_source_is_separate_from_public_aggregation():
    s=(ROOT/'qa/june2026_identity/score_request_pk_recovery.py').read_text()
    assert "value=item['identifier_private']" not in s
    assert "code=hit['identifier_private']" in s
    assert 'sha256(code.encode()).hexdigest()==sha' in s
    assert 'case_category_selected_posthoc' in s
    assert 'CROSS_TYPE_RESIDUAL' in s or 'CROSS_TYPE' in s

"""Exhaustive original request-only PK graph. No private incident in git."""
from pathlib import Path
import json,re
from else_dominance.sources import EvidenceTools
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'data/2026_june1621_source_only_link_graph.json'

def report():
    return json.loads(REPORT.read_text())

def test_all_june_cases_exhaustive_no_historical_labels():
    r=report()
    assert r['schema']=='else.itil.qa.2026-june1621-retrospective-pk-graph-summary.v1'
    assert r['month']=='2026-06'
    assert r['evaluated_original_incidents']==1621
    assert r['original_request_only'] is True
    assert r['history_or_gold_not_consulted_for_classification'] is True
    assert r['source_selection_is_exhaustive_june_not_57_posthoc'] is True
    assert r['candidate_mentions_19digit_per_ticket']==1342
    assert r['globally_distinct_candidate_numbers']==1125
    assert r['business_databases_read_only']==13
    assert r['business_qa_lookup_sql_batches']==168

def test_branch_filter_and_logical_copies_do_not_inflate_links():
    r=report()
    assert r['pk_observations_before_branch_check']==1813
    assert r['wrong_branch_observations_rejected']==215
    assert r['pk_observations_same_branch']==1598
    assert 1813-215==1598
    assert r['logical_ticket_pk_relations_after_copy_dedup']==1491
    assert r['logical_ticket_pk_present_in_multiple_databases']==88
    assert r['extra_copy_observations_removed']==107
    assert 1598-107==1491
    assert sum(x['count'] for x in r['same_branch_by_database'])==1598

def test_recovered_cases_and_ambiguous_cases_are_not_falsely_resolved():
    r=report()
    assert r['cases_with_any_pk_before_branch_check']==446
    assert r['cases_with_same_branch_pk']==333
    assert r['cases_with_only_wrong_branch_pk']==113
    assert r['cases_without_same_branch_pk']==1288
    assert r['cases_with_one_logical_pk']==158
    assert r['cases_with_multiple_logical_pks']==175
    assert r['cases_with_both_ot_and_collection_matches']==107
    assert 158+175==333 and 333+1288==1621

def test_cross_ticket_pk_reuse_is_recorded_without_claiming_causation():
    r=report()
    assert r['distinct_business_pk_values_by_type']==1236
    assert r['business_pk_shared_by_multiple_tickets']==232
    assert r['extra_ticket_memberships_for_shared_pk']==255
    assert r['max_tickets_sharing_one_pk']==5
    assert r['shared_business_pk_crosses_module']==10
    assert r['historical_june_business_state_verified'] is False
    assert r['official_itil_business_fk_verified'] is False
    assert r['business_repairs_certified']==0
    assert r['business_writes']==0
    assert r['retrospective_qa_not_historical_asof'] is True

def test_two_signed_receipts_and_private_graph_provenance_no_ids():
    r=report()
    for k in ('source_receipt_sha256','qa_dual_pk_receipt_sha256',
              'private_graph_receipt_sha256'):
        assert re.fullmatch('[0-9a-f]{64}',r[k])
    assert re.fullmatch(r'2026-11-\d\dT',r['qa_observed_at_utc'][:11])
    raw=REPORT.read_text().lower()
    for token in ('"business_pk_private":','"primary_key_private":',
                  '"case_sha256":','"numero_dni":','"nombre_cliente":',
                  '"descripcion_solicitud":','"object_handles":',
                  '"codigoordentrabajo":','"codigocobranza":'):
        assert token not in raw

def test_windows_reader_never_reads_gold_and_always_uses_typed_pk():
    s=(ROOT/'qa/june2026_full_link/JuneAllSourceOnlyPkRead.cs').read_text()
    assert 'DescripcionSolicitud' in s
    assert 'DescripcionSolucion' not in s
    assert 'SqlDbType.BigInt' in s
    assert 'ROW_NUMBER' not in s
    assert 'WHERE FechaSolicitud>=@start AND FechaSolicitud<@end' in s
    assert 'no_module_gold_labels_used=true' in s
    assert 'no_writer_sql_executed=true,read_only=true,business_writes=0' in s
    assert 'HMACSHA256.HashData' in s

def test_loader_never_exposes_business_ids_and_requires_explicit_operator_mode():
    s=(ROOT/'else_dominance/qa_june_full_source_links.py').read_text()
    assert 'verify_one(' in s
    assert 'actual==expected' in s
    assert 'retrospective_qa is not True' in s
    assert "'business_pk_private':" not in s
    assert 'RETROSPECTIVE_QA_EXPLICIT_AUTHORIZATION_REQUIRED' in s
    assert 'REQUESTED_AS_OF_BEFORE_INCIDENT_OPENED' in s
    agent=(ROOT/'else_dominance/agent.py').read_text()
    assert 'inspect_june_full_qa_business_graph' in agent

def test_agent_tool_not_available_without_operator_qa_env():
    e=EvidenceTools(None,None)
    ctx={'case_sha256':'f'*64,'module_code':'x','as_of':'2026-06-30'}
    r=e.execute('inspect_june_full_qa_business_graph',{'view':'objects'},ctx)
    assert r['status']=='BLOCKED'
    assert r['error']=='FULL_JUNE_GRAPH_OPERATOR_QA_MODE_NOT_ENABLED'
    class Scoped:
        def inspect(self,**kwargs):
            assert kwargs['retrospective_qa'] is True
            return {'status':'BLOCKED','error':'BOUND_TO_CASE'}
    e=EvidenceTools(None,None,june_full_graph=Scoped())
    assert e.execute('inspect_june_full_qa_business_graph',
            {'view':'summary'},ctx)['error']=='FULL_JUNE_GRAPH_OPERATOR_CASE_ALLOWLIST_REQUIRED'
    e=EvidenceTools(None,None,june_full_graph=Scoped(),
                    june_full_graph_authorized_case_sha256='f'*64)
    assert e.execute('inspect_june_full_qa_business_graph',
            {'view':'raw_ids'},ctx)['status']=='BLOCKED'
    assert e.execute('inspect_june_full_qa_business_graph',
            {'view':'objects','case_sha256':'f'*64},ctx)['status']=='BLOCKED'
    assert e.execute('inspect_june_full_qa_business_graph',
            {'view':'summary'},ctx)['error']=='BOUND_TO_CASE'
    cfg=(ROOT/'else_dominance/operational_cli.py').read_text()
    assert "TIC_QA_JUNE1621_RETROSPECTIVE_OPERATOR_ENABLED" in cfg
    assert "'--retrospective-qa',action='store_true'" in cfg

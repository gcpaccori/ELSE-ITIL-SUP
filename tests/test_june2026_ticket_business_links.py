"""Public QA contract: ticket to business PK linkage without false native FKs."""
from pathlib import Path
import json,re
from else_dominance.sources import EvidenceTools

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'data/2026_june57_verified_ticket_business_links.json'

def report():
    return json.loads(REPORT.read_text())

def test_link_registry_has_exact_cardinalities_without_fake_single_primary():
    r=report()
    assert r['schema']=='else.itil.qa.2026-june57-ticket-business-links-public-summary.v1'
    assert r['case_count']==57
    assert r['linked_cases']==55
    assert r['unlinked_cases']==2
    assert r['single_matched_object_cases']==13
    assert r['multiple_matched_object_cases']==42
    assert r['qa_verified_case_pk_edges']==619
    assert r['unique_business_primary_keys']==525
    assert r['same_key_reused_across_tickets']==87
    assert r['itil_ot_cases']==22
    assert r['itil_cobranza_cases']==35

def test_observational_key_equal_branch_is_not_an_official_fk_or_fix():
    r=report()
    assert r['native_sql_link_tables_with_exact_itil_and_business_pk_columns']==0
    assert r['native_declared_fks_involving_itil_taIncidente']==0
    assert r['databases_inspected_for_native_link']==14
    assert r['link_evidence']=='ORIGINAL_REQUEST_TO_QA_PK_VALUE_AND_BRANCH'
    assert r['all_links_retain_original_case_and_module_scope'] is True
    assert r['selected_cohort_posthoc_not_blind'] is True
    assert r['no_main_business_object_inferred_for_multi_object_tickets'] is True
    assert r['official_itil_business_fk_certified'] is False
    assert r['application_transactional_link_certified'] is False
    assert r['business_fix_certified'] is False
    assert r['source_business_mutations']==0

def test_public_report_pins_signed_receipts_but_no_identifying_values():
    r=report()
    assert len(r['evidence_receipts_sha256'])==4
    assert all(re.fullmatch('[0-9a-f]{64}',p) for p in
      [*r['evidence_receipts_sha256'].values(),r['private_registry_receipt_sha256']])
    text=REPORT.read_text().lower()
    for token in (
       '"pk_value_private":','"case_sha256":','"identificador":',
       '"dni":','"nombres":','"descripcion_solicitud":',
       '"identifier_private":','"object_handles":',
       '"codigoorden":','"codigocobranza":'):
        assert token not in text

def test_router_blocks_wrong_scope_and_unconfigured_private_registry():
    e=EvidenceTools(None,None)
    context={'case_sha256':'f'*64,'module_code':'ABC','as_of':'2026-06-15'}
    assert e.execute('inspect_itil_business_links',{'view':'summary'},context)['status']=='BLOCKED'
    class Scoped:
        def inspect(self,**kwargs):
            assert set(kwargs)=={'case_sha256','module_code','as_of','view'}
            return {'status':'BLOCKED','error':'TEST_DENIAL'}
    e=EvidenceTools(None,None,ticket_business_links=Scoped())
    assert e.execute('inspect_itil_business_links',{'view':'summary'},context)['status']=='BLOCKED'
    assert e.execute('inspect_itil_business_links',{'view':'objects','other':'1'},context)['status']=='BLOCKED'
    assert e.execute('inspect_itil_business_links',{'view':'raw_ids'},context)['status']=='BLOCKED'
    assert e.execute('inspect_itil_business_links',{'view':'objects'}, {})['status']=='BLOCKED'

def test_real_reader_queries_system_catalogs_with_no_business_mutation():
    s=(ROOT/'qa/june2026_link/JuneITILNativeLinkSchemaRead.cs').read_text()
    for token in ('SIELSEAccesoDatos','eSistema.ITIL','ELSE70',
                 'sys.foreign_keys','sys.foreign_key_columns',
                 'CodigoIncidente','CodigoOrdenTrabajo','CodigoCobranza',
                 'native_business_fk_not_claimed_without_application_contract=true'):
        assert token in s
    assert 'read_only=true,write_count=0' in s
    link=(ROOT/'else_dominance/qa_ticket_business_links.py').read_text()
    assert "if view=='objects':" in link
    assert 'resolve_for_authorized_reader(' in link
    assert "return {'status':'BLOCKED'" in link
    assert "'business_pk_value_private':link['pk_value_private']" in link
    assert "object_handles" in link

def test_builder_pins_original_signed_request_and_metadata_not_lm_guess():
    s=(ROOT/'qa/june2026_link/build_verified_ticket_links.py').read_text()
    assert 'verify_one(' in s
    assert 'assess(' in s
    assert "status=()" not in s
    assert 'SINGLE_MATCHED_OBJECT_NOT_OFFICIAL_FK' in s
    assert 'MULTIPLE_MATCHED_OBJECTS_NO_PRIMARY_SELECTED' in s
    assert "'business_source_authority_certified':False" in s
    assert "'official_foreign_key_verified':False" in s
    assert "'mutations_executed':0" in s
    assert 'source_database' in s
    assert 'pk_value_private' in s

"""June 2026 cross-database evidence: hard company routing and abstention."""
from pathlib import Path
import json
import pytest
from else_dominance.sources import EvidenceTools
from else_dominance.qa_june_business_route import VerifiedJuneBusinessRoute

DATA=Path(__file__).resolve().parents[1]/'data/2026_june5_business_crossdb_recovered.json'

def report():
    return json.loads(DATA.read_text())

def test_public_summary_keeps_the_five_and_recovered_cases_separate():
    data=report()
    assert data['selected_june_cases']==5
    assert data['databases_checked']==13
    assert data['company_routes_verified']==3
    assert data['official_routes']=={
       '1':'dbComercial001_D','4':'dbComercial004_D',
       '100':'dbComercial100_D'}
    assert data['cases_with_any_unique_ot_row_across_sources']==3
    assert data['cases_with_routed_company_row']==2
    assert data['historical_objects_found_in_gerencial_only']==1
    assert data['cases_with_different_routed_and_gerencial_qa_state']==1
    assert data['campaign_cases_not_found']==1
    assert data['personal_identifier_not_bound_to_request_and_ambiguous']==1

def test_documented_historical_evidence_is_not_execution():
    d=report()
    assert d['business_writes_executed']==0
    assert d['business_repairs_certified']==0
    assert d['audited_business_transitions_certified']==0
    assert d['historical_before_after_certified']==0
    assert d['cdc_enabled_in_checked_four_databases']==0
    assert d['june_backup_records_visible_in_else70_msdb_for_checked_four']==0
    assert d['external_backups_not_excluded'] is True
    assert d['current_qa_rows_cannot_prove_state_in_june'] is True

def test_statuses_reflect_partial_recovery_not_full_success():
    d=report()['status_breakdown']
    assert d=={
       'CAMPAIGN_NOT_FOUND_IN_13_ALLOWLISTED_QA_DATABASES':1,
       'GERENCIAL_ONLY_NO_ROUTED_TRANSACTIONAL_ROW':1,
       'PERSONAL_IDENTIFIER_NOTE_ONLY_AMBIGUOUS':1,
       'ROUTED_ROW_FOUND_CAUSALITY_UNVERIFIED':1,
       'ROUTED_ROW_WITH_GERENCIAL_DIVERGENCE':1,
    }

def test_recovering_nine_copies_is_not_nine_independent_fixed_cases():
    d=report()
    assert len(d['source_code_sql_receipt_bindings'])==5
    assert all(len(v)==64 for v in d['source_code_sql_receipt_bindings'].values())
    assert d['cases_with_any_unique_ot_row_across_sources']==3

def test_reports_never_expose_private_case_ids_surnames_sql_or_employee_data():
    raw=DATA.read_text()
    for marker in ('"case_sha256":','"identifier_private":',
       '"identifier_sha256":','"NumeroDNI":','"ApellidoPaterno":',
       '"ValorAnterior":','"ValorActual":','"current_rows":',
       '"historical_solution":','"DescripcionSolicitud":',
       '"nombre_cliente":','"razon_social":'):
        assert marker not in raw

def test_disallowed_cross_case_query_blocks_in_adapter():
    class FakeEvidence:
        def inspect(self,**kwargs):
            return {'status':'BLOCKED','error':'CASE_NOT_SIGNED'}
    e=EvidenceTools(None,None,june_business_route=FakeEvidence())
    ctx={'case_sha256':'f'*64,'module_code':'999',
         'as_of':'2026-06-15'}
    r=e.execute('inspect_june_business_route',{'view':'route'},ctx)
    assert r['status']=='BLOCKED'
    assert e.execute('inspect_june_business_route',
         {'view':'route','query':'SELECT *'},ctx)['status']=='BLOCKED'
    assert e.execute('inspect_june_business_route',
         {'view':'other'},ctx)['status']=='BLOCKED'
    assert e.execute('inspect_june_business_route',
         {'view':'route'}, {})['status']=='BLOCKED'

def test_adapter_requires_private_receipt_configuration():
    e=EvidenceTools(None,None)
    r=e.execute('inspect_june_business_route',{'view':'state'},
      {'case_sha256':'a'*64,'module_code':'0101','as_of':'2026-06-15'})
    assert r['status']=='BLOCKED'

def test_source_files_are_read_only_predefined_cross_db_queries():
    root=Path(__file__).resolve().parents[1]
    cross=(root/'qa/june2026_rootcause/JuneCrossDatabaseFind.cs').read_text()
    detail=(root/'qa/june2026_rootcause/JuneRecoveredObjectsRead.cs').read_text()
    route=(root/'qa/june2026_rootcause/JuneCommercialCompanyRouteRead.cs').read_text()
    for text in (cross,detail,route):
        assert 'sp_executesql' in text
        assert 'HMACSHA256.HashData' in text
        assert 'ELSE70' in text
        assert 'SIELSEAccesoDatos' in text
    assert 'SELECT COUNT_BIG(*) AS n' in cross
    assert 'CodigoOrdenTrabajo=@value' in cross or '{keycol}=@value' in cross
    assert 'WHERE CodigoOrdenTrabajo=@id' in detail
    assert 'FROM sys.databases' in cross
    assert 'DB_NAME() AS database_name' in route
    assert 'Obtener(eSistema.Comercial,company)' in route

@pytest.mark.parametrize(('code','expected'),[
  (1,'dbComercial001_D'),(4,'dbComercial004_D'),(100,'dbComercial100_D')])
def test_verified_company_codes_match_expected_route(code,expected):
    assert VerifiedJuneBusinessRoute.__module__.startswith('else_dominance')
    assert report()['official_routes'][str(code)]==expected

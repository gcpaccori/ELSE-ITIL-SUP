"""Real aggregate proof totals are checked; no private row content in Git."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
def test_ninety_signed_case_states_are_accounted():
    r=json.loads((ROOT/'data/2026_case_state_90_exact_field_evidence.json').read_text())
    assert r['case_count']==90
    assert r['months']==9
    assert r['signed_source_month_receipts']==9
    assert r['case_field_proof_count']==720
    assert r['business_domain_links_verified']==0
    assert r['cause_certified']==0
    assert r['business_repairs_certified']==0
    assert r['business_modifications']==0
    assert sum(v['cases'] for v in r['months_summary'].values())==90
    assert r['totals']['model_proposed_checks']==135
    assert r['totals']['model_checks_without_business_object_qa_proof']==135

def test_exact_reported_ot_results_are_accounted():
    r=json.loads((ROOT/'data/2026_reported_ot_900_verified_fields.json').read_text())
    assert r['itil_cases_scanned']==900
    assert r['queries_exact_reported_identifier']==42
    assert r['domain_records_returned_one_row']==9
    assert r['domain_queries_zero_rows']==33
    assert r['excluded_ambiguous_reported_identifiers']==5
    assert r['excluded_other_company']==12
    assert r['no_explicit_identifier']==841
    assert r['domain_exact_field_values_verified']==63
    assert r['formal_ITIL_OT_join_verified'] is False
    assert r['root_causes_verified']==r['repairs_executed']==r['modifications']==0
    assert sum(v.get('reported_ot_row_found',0) for v in r['months'].values())==9

def test_public_reports_never_export_ticket_text_qa_states_or_person_identifiers():
    for path in ('data/2026_case_state_90_exact_field_evidence.json',
                 'data/2026_reported_ot_900_verified_fields.json'):
        body=(ROOT/path).read_text()
        for forbidden in (
          '"case_sha256":','"reported_ot_sha256":',
          '"historical_solution_redacted":','"description_redacted":',
          '"observed_value":','"CodigoIncidente":','"password":',
          '"token":','"connection_string":'):
            assert forbidden not in body,(path,forbidden)

def test_csharp_sources_do_not_accept_model_sql():
    case=(ROOT/'qa/case_state/CaseStateRead.cs').read_text()
    ot=(ROOT/'qa/case_state/ReportedOtDomainRead.cs').read_text()
    assert 'WHERE CodigoIncidente=@case' in case
    assert 'WHERE CodigoOrdenTrabajo=@ot' in ot
    assert 'sp_executesql' in case and 'sp_executesql' in ot
    assert 'eSistema.ITIL' in case
    assert 'eSistema.Distribucion' in ot
    assert 'dbDistribucion_D' in ot
    assert 'dbITIL_D' in case
    assert 'HMACSHA256' in case and 'HMACSHA256' in ot
    assert 'UPDATE dbo.' not in case+ot
    assert 'DELETE FROM dbo.' not in case+ot

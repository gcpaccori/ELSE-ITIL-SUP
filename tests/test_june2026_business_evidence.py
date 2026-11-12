"""Business-object evidence boundary tests; no confidential QA rows in repo."""
from pathlib import Path
import json
import pytest

from qa.june2026_business.score_five_business_evidence import (
    RANKS,_judge_object_alignment,_manifest)

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'data/2026_june5_business_evidence_audit.json'

def load():
    return json.loads(PUBLIC.read_text())

def test_only_five_fixed_june_cases_with_signed_receipts():
    d=load()
    assert d['schema']=='else.itil.qa.2026-june5-business-beforeafter-evidence.v1'
    assert RANKS==(197,263,868,934,1065)
    assert d['counts']['cases']==5
    assert d['judge_initial_provisional_same_mechanism']==5
    assert all(len(d[key])==64 for key in (
       'manifest_receipt_sha256','metadata_receipt_sha256',
       'business_snapshot_receipt_sha256',
       'independent_june_request_receipt_sha256',
       'independent_june_history_receipt_sha256'))
    assert d['qa_business']=='dbComercial001_D'
    assert d['qa_itil']=='dbITIL_D'

def test_cannot_claim_a_single_unique_business_object():
    d=load();c=d['counts']
    assert c['identifier_in_original_request']==4
    assert c['request_and_note_same_id']==3
    assert c['historical_note_identifier_present']==4
    assert c['historical_only_unconfirmed_identifier']==1
    assert c['business_row_not_found']==4
    assert c['business_row_ambiguous']==1
    assert c['unique_business_row']==0
    assert c['cases_with_audit_record']==0
    assert c['audited_target_field_transition_in_june']==0
    assert c['historical_target_matched_independent_audit']==0

def test_tables_contain_rows_but_original_june_objects_not_found():
    d=load()
    assert d['business_tables_have_records_without_relevant_exact_case'] is True
    assert d['target_tables_non_temporal'] is True
    assert d['targeted_types']=={'CAMPAIGN':1,'OT':3,'PADRON':1}
    assert d['historical_sql_not_execution_proof'] is True
    assert d['current_snapshot_does_not_establish_state_in_june'] is True
    assert d['no_unique_object_no_state_before_after'] is True
    assert d['historically_certified_changes']==0
    assert d['certified_business_repairs']==0
    assert d['business_writes_executed']==0

def test_posthoc_object_review_corrects_five_optimistic_llm_hits():
    d=load()
    assert d['object_review']=={
      'BUSINESS_OBJECT_MISMATCH':1,
      'OBJECT_AND_OBSERVABLE_ALIGNED_ONLY':3,
      'REQUIRED_CAUSAL_TEST_MISSING':1,
    }
    assert d['object_alignment_is_conservative_posthoc_review_not_human_ground_truth']

def test_campaign_incident_is_not_order_work_order_even_with_incidental_word():
    plan={'checks':[{
       'business_object':'Consulta de estado y subtipo de la OT por zona y campaña',
       'observable':'Estado actual de OT y Subtipo'},
       {'business_object':'Verificación de transición de estado solicitada',
        'observable':'Historial de transiciones de estado de la OT'}]}
    assert _judge_object_alignment(1065,plan)=='BUSINESS_OBJECT_MISMATCH'

def test_missing_tariff_pliego_check_is_not_specific_causal_validation():
    plan={'checks':[{'business_object':'OT de cambio de medidor',
                     'observable':'Estado actual y subtipo de la OT'},
                    {'business_object':'Confirmación de OT',
                     'observable':'Resultado de transición'}]}
    assert _judge_object_alignment(263,plan)=='REQUIRED_CAUSAL_TEST_MISSING'

@pytest.mark.parametrize(('rank','object_name','observable'),[
  (197,'Centro de Atención de OT','Centro de atención actual de la orden'),
  (868,'Estado OT de medidor','Estado inicial y final de OT'),
  (934,'Corrección de apellido y DNI','Apellido actual del cliente')
])
def test_object_alignment_is_only_a_check_not_a_verified_fix(rank,object_name,observable):
    assert _judge_object_alignment(rank,{'checks':[{
        'business_object':object_name,'observable':observable
    }]})=='OBJECT_AND_OBSERVABLE_ALIGNED_ONLY'

def test_absent_or_unexpected_data_abstains():
    assert _judge_object_alignment(197,{'checks':[]})=='INVALID_MISSING_PROPOSAL_CHECKS'
    assert _judge_object_alignment(1065,{'checks':[{
        'business_object':'Estado de campaña de supervisión',
        'observable':'CodigoEstadoCampanaSupervision'}]})=='NEEDS_MANUAL_REVIEW'

def test_manifest_fails_closed_on_invalid_or_corrupted_proof(tmp_path):
    f=tmp_path/'june5_manifest.private.json'
    f.write_bytes(b'{"schema":"other","ranks":[197,263,868,934,1065],"rows":[]}')
    proof=tmp_path/(f.name+'.proof.json')
    proof.write_text(json.dumps({'schema':'wrong','receipt_sha256':'0'*64,'hmac_sha256':'1'*64}))
    with pytest.raises((ValueError,KeyError)):
        _manifest(tmp_path,b'a'*32)

def test_public_report_has_no_case_business_identifier_or_personal_data():
    raw=PUBLIC.read_text()
    for marker in (
       '"case_sha256":','"identifier_private":','"identifier_sha256":',
       '"historical_solution_redacted":','"description_redacted":',
       '"NumeroDNI":','"ApellidoPaterno":','"case_ranks":',
       '"historical_target_code":','"ValorAnterior":','"ValorActual":'):
        assert marker not in raw

def test_reader_uses_fixed_cross_sql_routes_and_never_executes_note_sql():
    reader=(ROOT/'qa/june2026_business/JuneFiveExactBusinessRead.cs').read_text()
    assert 'ROW_NUMBER() OVER (ORDER BY FechaSolicitud DESC,CodigoIncidente DESC)' in reader
    assert 'FechaSolicitud>=@start AND FechaSolicitud<@end' in reader
    assert 'manifest' in reader
    assert 'dbo.taOrdenTrabajoAuditoriaCambio' in reader
    assert 'dbo.taOrdenTrabajo_ModificacionIN' in reader
    assert 'dbo.taCampanaSupervision' in reader
    assert 'dbo.taPadronRuc' in reader
    assert 'WHERE CodigoOrdenTrabajo=@id' in reader
    assert 'WHERE NumeroDNI=@dni' in reader
    assert 'HMACSHA256.HashData' in reader
    assert 'eSistema.ITIL' in reader and 'eSistema.Comercial' in reader
    assert 'sp_executesql' in reader

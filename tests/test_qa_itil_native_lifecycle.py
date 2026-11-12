"""Synthetic case-bound lineage tests. No private incident data in repository."""
from pathlib import Path
import json
import pytest

from else_dominance.qa_itil_native_lifecycle import (
    VerifiedItILNativeLifecycle,verify_lifecycle_field_claim,
    OBSERVED_FIELDS,SOURCE)
from else_dominance.sources import EvidenceTools
from else_dominance.agent import InvestigationAgent

def sample():
    idx=VerifiedItILNativeLifecycle.__new__(VerifiedItILNativeLifecycle)
    idx.receipt_sha256='a'*64
    idx.events_receipt_sha256='b'*64
    from datetime import datetime,timezone
    idx.derivation_read_utc=datetime(2026,11,12,tzinfo=timezone.utc)
    case='c'*64
    idx.rows={case:{
        'month':'2026-03','module_code':'01','opened_at':'2026-03-09T10:00:00',
        'exact_key_equality_atencion':0,
        'exact_key_equality_derivacion':2,
        'exact_key_equality_encuesta':0,
        'atencion_solved_flag_count':0,
        'atencion_finish_date_count':0,
        'modulo_key_row_match':True,
        'estado_key_row_match':True,
        'codigo_estado_incidente':'6',
        'state_dictionary_atendido':1,
    }}
    idx.events={case:[
        {'sequence_number':1,'type_code':'1',
         'created_date_time_without_timezone':'2026-03-09T10:00:00',
         'modified_date_present':True},
        {'sequence_number':2,'type_code':'3',
         'created_date_time_without_timezone':'2026-03-10T09:00:00',
         'modified_date_present':False},
    ]}
    return idx,case

def test_summary_exact_case_scope_and_not_fk():
    idx,case=sample()
    r=idx.inspect(case_sha256=case,module_code='01',
      as_of='2026-03-09T10:00:00',view='summary')
    assert r['status']=='READ_VERIFIED_ITIL_NATIVE_KEY_QA'
    assert r['observed_fields']['exact_key_equality_derivacion']==2
    assert r['observed_fields']['codigo_estado_incidente']=='6'
    assert r['declared_sql_foreign_key_verified'] is False
    assert r['business_root_cause_verified'] is False
    assert r['repair_certified'] is False
    assert r['provenance_verified'] is True

def test_derivation_events_do_not_imply_operational_fix():
    idx,case=sample()
    r=idx.inspect(case_sha256=case,module_code='01',
      as_of='2026-03-11',view='derivation_events')
    assert r['derivation_event_count']==2
    assert [x['type_code'] for x in r['events']]==['1','3']
    assert r['type_codes_not_interpreted_as_business_actions'] is True
    assert r['declared_sql_foreign_key_verified'] is False

@pytest.mark.parametrize(('field','value'),[
    ('codigo_estado_incidente','7'),
    ('exact_key_equality_derivacion',1),
    ('modulo_key_row_match',1),
])
def test_false_lifecycle_field_values_rejected(field,value):
    idx,case=sample()
    claim={
       'case_sha256':case,'module_code':'01',
       'as_of':'2026-03-09','source':SOURCE,
       'field':field,'observed_value':value,
       'lifecycle_receipt_sha256':idx.receipt_sha256}
    assert verify_lifecycle_field_claim(idx,claim)['status']=='BLOCKED'

def test_only_exact_claim_passes_and_never_a_causal_conclusion():
    idx,case=sample()
    claim={
        'case_sha256':case,'module_code':'01','as_of':'2026-03-09',
        'source':SOURCE,'field':'exact_key_equality_derivacion',
        'observed_value':2,
        'lifecycle_receipt_sha256':idx.receipt_sha256,
    }
    ok=verify_lifecycle_field_claim(idx,claim)
    assert ok['status']=='EXACT_ITIL_LIFECYCLE_FIELD_VALUE_VERIFIED'
    assert ok['observed_key_relation_not_fk'] is True
    assert ok['business_cause_certified'] is False
    assert ok['repair_certified'] is False
    for k,v in [
         ('case_sha256','d'*64),('module_code','22'),
         ('as_of','2026-04-02'),('source','ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo'),
         ('lifecycle_receipt_sha256','f'*64)]:
        assert verify_lifecycle_field_claim(idx,{**claim,k:v})['status']=='BLOCKED'

def test_scope_prevents_cross_case_and_unknown_view():
    idx,case=sample()
    for arg in [
      ('0'*64,'01','2026-03-09','summary'),
      (case,'02','2026-03-09','summary'),
      (case,'01','2026-02-09','summary'),
      (case,'01','2026-03-09','SELECT * FROM taIncidente'),
    ]:
        assert idx.inspect(case_sha256=arg[0],module_code=arg[1],
          as_of=arg[2],view=arg[3])['status']=='BLOCKED'

def test_tool_fails_closed_on_extra_field_missing_case_and_no_catalog():
    class Dummy:pass
    idx,case=sample()
    tool=EvidenceTools(Dummy(),Dummy(),itil_lifecycle=idx)
    ctx={'case_sha256':case,'module_code':'01','as_of':'2026-03-09'}
    ok=tool.execute('inspect_itil_lifecycle',{'view':'summary'},ctx)
    assert ok['status']=='READ_VERIFIED_ITIL_NATIVE_KEY_QA'
    assert tool.execute('inspect_itil_lifecycle',
       {'view':'summary','sql':'DROP'},ctx)['status']=='BLOCKED'
    assert tool.execute('inspect_itil_lifecycle',
       {'view':'summary'},{})['status']=='BLOCKED'
    assert EvidenceTools(Dummy(),Dummy()).execute(
       'inspect_itil_lifecycle',{'view':'summary'},ctx)['status']=='BLOCKED'

def test_agent_retains_lifecycle_evidence_but_does_not_promote_cause():
    idx,case=sample()
    obs=idx.inspect(case_sha256=case,module_code='01',
        as_of='2026-03-09',view='summary')
    evidence={'TOOL:1':{
        'name':'inspect_itil_lifecycle','args':{'view':'summary'},
        'result':obs}}
    model_final={
      'status':'PLAN_PROPUESTO','hypotheses':[
       {'cause':'Derivación del expediente causó fallo',
        'evidence_refs':['TOOL:1'],'test':'Verificar origen de negocio'}],
      'proposed_steps':[{'action':'Revisar condición','source':'QA',
        'precondition':'Rol autorizado','evidence_refs':['TOOL:1'],
        'verification':'Comprobar estado relacionado'}],
      'confidence':'HIGH',
    }
    result=InvestigationAgent._validate(model_final,evidence)
    assert result['status']=='INVESTIGACION_PENDIENTE'
    assert result['itil_lifecycle_key_equality_observed'] is True
    assert result['itil_lifecycle_observations'][0]['declared_fk_verified'] is False
    assert result['causal_diagnosis_confirmed'] is False
    assert result['domain_business_state_verified'] is False
    assert result['can_claim_resolved'] is False
    assert 'TOOL:1' in result['invalid_references']

def test_code_contract_does_not_expose_ticket_users_or_historical_notes():
    root=Path(__file__).resolve().parents[1]
    raw=(root/'data/2026_itil_native_lifecycle_900.json').read_text()
    for secret in (
       '"case_sha256":','"UsuarioDeriva":','"UsuarioDerivado":',
       '"MotivoDerivacion":','"DescripcionSolicitud":','"DescripcionSolucion":',
       '"fecha_creacion_utc_unspecified_local":','"observed_value":'):
        assert secret not in raw
    report=json.loads(raw)
    assert report['incident_records_verified']==900
    assert report['totals']['derivation_events']==1155
    assert report['totals']['cases_with_multiple_derivations']==212
    assert report['sql_declared_foreign_keys_from_incident_tables']==0
    assert report['causes_certified']==0
    assert report['repairs_certified']==0
    assert len(OBSERVED_FIELDS)==9

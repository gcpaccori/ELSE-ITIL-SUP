"""No false ITIL⇔OT foreign-key or false global nonexistence claims."""
import json
from pathlib import Path
from else_dominance.qa_reported_ot_evidence import (
    VerifiedReportedOtIndex,verify_reported_ot_claim,CODE_FIELDS,DOMAIN)
from else_dominance.sources import EvidenceTools

def fake_index():
    idx=VerifiedReportedOtIndex.__new__(VerifiedReportedOtIndex)
    idx.receipt_sha256='9'*64
    a='a'*64;b='b'*64
    row={
      'month':'2026-07','case_sha256':a,'case_module_code':'ABC',
      'reported_ot_sha256':'2'*64,'read_utc':'2026-11-12T17:00:00+00:00',
      'row_count':1,
      'observed_fields':{
        'CodigoEstadoOrdenTrabajo':'5',
        'CodigoClaseOrdenTrabajo':'2',
        'CodigoTipoOrdenTrabajo':'1',
        'CodigoSubTipoOrdenTrabajo':'1',
        'FechaElaboracion_present':True,
        'FechaInicio_present':True,
        'FechaFin_present':False
      }
    }
    idx.rows={a:row,b:{
       **row,'case_sha256':b,'reported_ot_sha256':'3'*64,
       'row_count':0,'observed_fields':None}}
    return idx,a,b

def test_reported_order_field_claim_strictly_value_bound():
    idx,case,none=fake_index()
    obs=idx.inspect(case_sha256=case,module_code='ABC',
           as_of='2026-07-04',field='CodigoEstadoOrdenTrabajo')
    assert obs['status']=='READ_VERIFIED_REPORTED_OT_QA_FIELD'
    assert obs['observed_value']=='5'
    assert obs['formal_itil_ot_link_verified'] is False
    claim={
      'case_sha256':case,'module_code':'ABC','as_of':'2026-07-04',
      'source':DOMAIN,'field':'CodigoEstadoOrdenTrabajo',
      'observed_value':'5','receipt_sha256':'9'*64,
      'reported_ot_sha256':'2'*64}
    ok=verify_reported_ot_claim(idx,claim)
    assert ok['status']=='REPORTED_OT_FIELD_EXACT_QA_VALUE_VERIFIED'
    assert ok['official_ticket_business_relation_verified'] is False
    assert ok['causal_diagnosis_confirmed'] is False
    for key,value in (
        ('observed_value','4'),('receipt_sha256','a'*64),
        ('reported_ot_sha256','f'*64),('case_sha256','c'*64),
        ('module_code','ZZZ'),('as_of','2026-06-02')):
        assert verify_reported_ot_claim(idx,{**claim,key:value})['status']=='BLOCKED'

def test_absent_qa_order_not_global_order_absence():
    idx,case,none=fake_index()
    result=idx.inspect(case_sha256=none,module_code='ABC',
           as_of='2026-07-04',field='CodigoEstadoOrdenTrabajo')
    assert result['status']=='ZERO_ROWS_ONLY_IN_PROBED_DISTRIBUTION_QA_TABLE'
    assert result['observed_value'] is None
    assert result['global_order_absence_proven'] is False
    assert verify_reported_ot_claim(idx,{
      'case_sha256':none,'module_code':'ABC','as_of':'2026-07-04',
      'source':DOMAIN,'field':'CodigoEstadoOrdenTrabajo',
      'observed_value':None,'receipt_sha256':'9'*64,
      'reported_ot_sha256':'3'*64})['status']=='BLOCKED'

def test_reported_ot_scope_and_registered_fields():
    idx,case,none=fake_index()
    assert idx.inspect(case_sha256=case,module_code='ZZZ',
          as_of='2026-07-04',field='CodigoEstadoOrdenTrabajo')['status']=='BLOCKED'
    assert idx.inspect(case_sha256=case,module_code='ABC',
          as_of='2026-06-02',field='CodigoEstadoOrdenTrabajo')['status']=='BLOCKED'
    assert idx.inspect(case_sha256=case,module_code='ABC',
          as_of='2026-07-04',field='UPDATE taOrdenTrabajo')['status']=='BLOCKED'
    assert idx.inspect(case_sha256='0'*64,module_code='ABC',
          as_of='2026-07-04',field='CodigoEstadoOrdenTrabajo')['status'].startswith('ABSTAIN')
    assert len(CODE_FIELDS)==7
    assert 'CodigoOrdenTrabajo' not in CODE_FIELDS

def test_tool_no_cross_case_and_not_configured():
    class Dummy:pass
    idx,case,none=fake_index()
    tools=EvidenceTools(Dummy(),Dummy(),reported_ot=idx)
    ctx={'case_sha256':case,'module_code':'ABC','as_of':'2026-07-04'}
    assert tools.execute('inspect_reported_ot_qa_state',
        {'field':'CodigoEstadoOrdenTrabajo'},ctx)['status']=='READ_VERIFIED_REPORTED_OT_QA_FIELD'
    assert tools.execute('inspect_reported_ot_qa_state',
        {'field':'CodigoEstadoOrdenTrabajo','case_sha256':none},ctx)['status']=='BLOCKED'
    assert EvidenceTools(Dummy(),Dummy()).execute(
        'inspect_reported_ot_qa_state',
        {'field':'CodigoEstadoOrdenTrabajo'},ctx)['status']=='BLOCKED'

def test_published_qa_result_has_no_case_values_or_identifiers():
    root=Path(__file__).resolve().parents[1]
    for file in ('data/2026_case_state_90_exact_field_evidence.json',
                 'data/2026_reported_ot_900_verified_fields.json'):
        d=json.loads((root/file).read_text())
        assert not any('case_sha256' in str(x) for x in d.keys())
        raw=(root/file).read_text()
        assert '"case_sha256":' not in raw
        assert '"reported_ot_sha256":' not in raw
        assert '"observed_value":' not in raw
        assert '"historical_solution_redacted":' not in raw
        assert d.get('cause_certified',d.get('root_causes_verified'))==0

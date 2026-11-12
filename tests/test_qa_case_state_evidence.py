"""Synthetic case-bound evidence contracts; never use private corp IDs in CI."""
from hashlib import sha256
from pathlib import Path
import hmac,json
import pytest
from else_dominance.qa_case_state_evidence import (
    VerifiedCaseStateIndex,verify_claim,strict_json,verify_signed,
    SOURCE,SCHEMA,PROOF,CASE_FIELDS)
from else_dominance.sources import EvidenceTools

def dummy_signed(tmp_path):
    key=b'K'*32
    code=b'synthetic source only'
    source=sha256(code).hexdigest()
    body={
        'schema':SCHEMA,'source_sha256':source,'read_only':True,
        'selected':90,'months':9
    }
    p=tmp_path/'receipt.json'
    raw=json.dumps(body).encode()
    receipt=sha256(raw).hexdigest()
    p.write_bytes(raw)
    proof={
        'schema':PROOF,'source_sha256':source,
        'receipt_sha256':receipt,
        'hmac_sha256':hmac.new(key,f'{SCHEMA}:{source}:{receipt}'.encode(),sha256).hexdigest(),
        'read_only':True
    }
    (tmp_path/'receipt.json.proof.json').write_text(json.dumps(proof))
    return p,key,source

def test_receipt_hmac_and_source_code_bound(tmp_path):
    p,key,source=dummy_signed(tmp_path)
    parsed,digest=verify_signed(p,key,source,SCHEMA,PROOF)
    assert digest==sha256(p.read_bytes()).hexdigest()
    assert parsed['selected']==90
    with pytest.raises(ValueError):
        verify_signed(p,key,'0'*64,SCHEMA,PROOF)

def test_receipt_data_tamper_rejected(tmp_path):
    p,key,source=dummy_signed(tmp_path)
    p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='SIGNED_RECEIPT_BINDING'):
        verify_signed(p,key,source,SCHEMA,PROOF)

def test_duplicate_json_key_refused():
    with pytest.raises(ValueError,match='DUPLICATE_JSON_KEY'):
        strict_json(b'{"a":1,"a":2}')

def test_case_index_refuses_cross_ticket_and_field_injection():
    idx=VerifiedCaseStateIndex.__new__(VerifiedCaseStateIndex)
    case='a'*64
    idx.receipt_sha256='b'*64
    idx.rows={case:{
        'case_sha256':case,'month':'2026-05',
        'read_utc':'2026-11-12T17:00:00+00:00',
        'source_month_receipt_sha256':'c'*64,
        'observed_fields':{
            'CodigoEstadoIncidente':'6','CodigoModulo':'01',
            'CodigoEmpresa':'1','CodigoCalificacion':'2',
            'CodigoOrigenIncidente':'1','CodigoServicio':'ABC',
            'FechaCierre.present':True,
            'FechaRespuestaSolucion.present':True}
    }}
    valid={'case_sha256':case,'module_code':'01','as_of':'2026-05-15T09:00:00',
           'source':SOURCE,'field':'CodigoEstadoIncidente',
           'observed_value':'6','receipt_sha256':'b'*64}
    obs=idx.inspect(case_sha256=case,module_code='01',
       as_of='2026-05-02',field='CodigoEstadoIncidente')
    assert obs['status']=='READ_VERIFIED_QA_SNAPSHOT'
    assert obs['observed_value']=='6'
    assert obs['business_object_relation_verified'] is False
    assert verify_claim(idx,valid)['status']=='FIELD_VALUE_EXACTLY_VERIFIED_IN_QA_SNAPSHOT'
    for key,value in [
       ('observed_value','7'),('receipt_sha256','d'*64),
       ('source','ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo'),
       ('as_of','2026-06-02'),('module_code','02')]:
        tampered={**valid,key:value}
        assert verify_claim(idx,tampered)['status']=='BLOCKED'
    assert verify_claim(idx,{**valid,'observed_value':6})['status']=='BLOCKED'
    assert idx.inspect(case_sha256='1'*64,module_code='01',
         as_of='2026-05-02',field='CodigoEstadoIncidente')['status']=='BLOCKED'
    assert idx.inspect(case_sha256=case,module_code='01',
         as_of='2026-05-02',field='DELETE FROM taIncidente')['status']=='BLOCKED'

def test_tool_binding_and_qa_missing_fails_closed():
    class Dummy:pass
    state=VerifiedCaseStateIndex.__new__(VerifiedCaseStateIndex)
    state.rows={}
    state.receipt_sha256='f'*64
    tools=EvidenceTools(Dummy(),Dummy(),case_state=state)
    context={'case_sha256':'a'*64,'module_code':'01',
             'as_of':'2026-05-10'}
    assert tools.execute('inspect_case_qa_state',{'field':'CodigoEstadoIncidente'},context)['status']=='BLOCKED'
    assert tools.execute('inspect_case_qa_state',
        {'field':'CodigoEstadoIncidente','case_sha256':'b'*64},context)['status']=='BLOCKED'
    assert EvidenceTools(Dummy(),Dummy()).execute(
        'inspect_case_qa_state',{'field':'CodigoEstadoIncidente'},context)['status']=='BLOCKED'

def test_safe_field_universe_is_small_and_fixed():
    assert len(CASE_FIELDS)==8
    assert 'DescripcionSolicitud' not in CASE_FIELDS
    assert 'DescripcionSolucion' not in CASE_FIELDS
    assert 'CodigoIncidente' not in CASE_FIELDS
    assert 'CodigoCaja' not in CASE_FIELDS

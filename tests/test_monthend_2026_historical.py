"""Synthetic adversarial tests for signed month-end QA and exact historical evidence."""
from hashlib import sha256
from pathlib import Path
import hmac,json
import pytest
from qa.monthend2026.evaluate_monthend import (
    verify_one,labels_only_count)
from else_dominance.historical_procedures import (
    HistoricalProcedureCatalog,CATALOG_SCHEMA)
from else_dominance.historical_mechanism_matching import (
    MechanismIndex,SCHEMA as MECH_SCHEMA)

def qa_receipt(tmp_path):
    src=b"fixed QA CSharp source"
    code_sha=sha256(src).hexdigest()
    key=b"t"*32
    body={'schema':'else.itil.qa.2026-monthend100-source.v1',
          'source_sha256':code_sha,'read_only':True,
          'period':'2026-02'}
    raw=json.dumps(body).encode()
    digest=sha256(raw).hexdigest()
    msg=(body['schema']+':'+code_sha+':'+digest).encode()
    proof={
        'schema':'else.itil.qa.2026-monthend100-source-hmac.v1',
        'source_sha256':code_sha,'receipt_sha256':digest,
        'read_only':True,'hmac_sha256':hmac.new(key,msg,'sha256').hexdigest()}
    p=tmp_path/'monthend_202602.private.json'
    p.write_bytes(raw)
    (tmp_path/(p.name+'.proof.json')).write_text(json.dumps(proof))
    return p,key,code_sha

def test_signed_monthend_receipt_replays(tmp_path):
    p,key,sha=qa_receipt(tmp_path)
    body,receipt_sha=verify_one(
        p,key,sha,
        'else.itil.qa.2026-monthend100-source.v1',
        'else.itil.qa.2026-monthend100-source-hmac.v1')
    assert body['period']=='2026-02'
    assert receipt_sha==sha256(p.read_bytes()).hexdigest()

def test_modified_source_or_receipt_is_rejected(tmp_path):
    p,key,sha=qa_receipt(tmp_path)
    with pytest.raises(ValueError):
        verify_one(p,key,'0'*64,
                   'else.itil.qa.2026-monthend100-source.v1',
                   'else.itil.qa.2026-monthend100-source-hmac.v1')
    p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError):
        verify_one(p,key,sha,
                   'else.itil.qa.2026-monthend100-source.v1',
                   'else.itil.qa.2026-monthend100-source-hmac.v1')

def make_catalogs(tmp_path):
    prior={
        'schema':CATALOG_SCHEMA,'cohort_total':300,
        'includes_heldout_fourth':False,'source_receipts':[
            {'cohort':'may_first100'},{'cohort':'may_next100'},
            {'cohort':'may_third100'}],
        'business_changes_executed':0,'notes_with_mentions':2,
        'unique_module_patterns':1,
        'modules':{'0102100100000':{
            'total_notes':20,'notes_with_mentions':2,
            'patterns':[{
                'kind':'UPDATE_MENTIONED','table':'tacobranza',
                'fields':['codigocaja'],'count':2,
                'historical_note_only':True,'execution_confirmed':False}]}}
    }
    mechanism={
        'schema':MECH_SCHEMA,'train_cases':300,
        'training_cohorts':['may_first100','may_next100','may_third100'],
        'includes_monthend_cohorts':False,'history_not_business_execution':True,
        'business_writes':0,'notes_with_mechanisms':0,
        'modules':{'0102100100000':{'notes_seen':20,'mentions':{}}}
    }
    p=tmp_path/'p.json';p.write_text(json.dumps(prior))
    m=tmp_path/'m.json';m.write_text(json.dumps(mechanism))
    return HistoricalProcedureCatalog(p),MechanismIndex(m)

def test_case_specific_field_anchor_and_gold_exact_overlap(tmp_path):
    catalog,mech=make_catalogs(tmp_path)
    case='a'*64
    row={
     'request':{'case_sha256':case,'rank':1,
        'description_redacted':'Solicito corregir la caja que no aparece en cobranza',
        'module_code':'0102100100000'},
     'gold':{'case_sha256':case,
        'historical_solution_redacted':(
           'UPDATE a SET a.CodigoCaja=10 FROM taCobranza a'),
        'answer_date_present':True,'close_date_present':False},
     'module_mismatch':False,
    }
    score,records=labels_only_count(
        [row],catalog,mech,{'0102100100000':'Digitacion de Cobranza'})
    assert score['prior_request_anchored_sql']==1
    assert score['gold_sql_mentions']==1
    assert score['anchored_sql_overlap']==1
    assert score['history_close_date']==0
    assert records[0]['historical_change_executed_proven'] is False
    assert records[0]['actual_root_cause_proven'] is False

def test_module_only_similarity_does_not_promote_prior(tmp_path):
    catalog,mech=make_catalogs(tmp_path)
    case='b'*64
    row={
     'request':{'case_sha256':case,'rank':1,
                'description_redacted':'Falla inesperada en aplicativo sin detalle',
                'module_code':'0102100100000'},
     'gold':{'case_sha256':case,
        'historical_solution_redacted':'UPDATE a SET a.CodigoCaja=10 FROM taCobranza a',
        'answer_date_present':False,'close_date_present':False},
     'module_mismatch':False,
    }
    score,_=labels_only_count(
        [row],catalog,mech,{'0102100100000':'Digitacion de Cobranza'})
    assert score['prior_unanchored_sql']==1
    assert score['prior_request_anchored_sql']==0
    assert score['unanchored_sql_overlap']==1
    assert score['anchored_sql_overlap']==0

def test_historical_resolution_must_match_original_case_sha(tmp_path):
    catalog,mech=make_catalogs(tmp_path)
    with pytest.raises(ValueError,match='SOURCE_HISTORY_MISMATCH'):
        labels_only_count([{
            'request':{'case_sha256':'a'*64,'module_code':'0102100100000'},
            'gold':{'case_sha256':'b'*64},
            'module_mismatch':False,
        }],catalog,mech,{'0102100100000':'Digitacion de Cobranza'})

def test_query_is_last_one_hundred_per_month_not_first():
    source=(Path(__file__).resolve().parents[1]/
            'qa/monthend2026/MonthEnd100Read.cs').read_text()
    assert source.count('TOP(100)')==2
    assert source.count('ORDER BY FechaSolicitud DESC,CodigoIncidente DESC')==2
    assert 'for(int month=1;month<=11;month++)' in source
    assert 'month==11?new DateTime(2026,11,13)' in source
    assert 'history_or_resolution_read=false' in source
    assert 'solutions_not_in_model_input=true' in source
    assert 'business_modifications=0' in source
    assert 'December' not in source

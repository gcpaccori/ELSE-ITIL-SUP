import json
import sys
from pathlib import Path
from datetime import datetime
import pytest

from else_dominance.resolution_batch import (
    require_holdout,require_history,MemoryIndex,ResolutionRunner,
    evaluate_response,process_jsonl,redact,words,KNOWN_SOURCES,
)


def hist(ref,desc,sol,year=2025,service='101'):
    return {'case_ref':ref,'opened_at':f'{year}-02-01T11:00:00',
            'solution_recorded_at':f'{year}-02-03T10:00:00',
            'modified_at':f'{year}-02-04T10:00:00',
            'service_code':service,'module_code':'5','classification_code':'109',
            'description':desc,'solution_text':sol}


def hold(ref='itil-777',desc='La cuenta SIELSE esta bloqueada'):
    return {'case_ref':ref,'opened_at':'2026-09-12T10:20:00',
            'service_code':'101','module_code':'5','classification_code':'109',
            'description':desc,'privacy_reviewed':True}


def good():
    return {'estado':'PROCEDIMIENTO_CONDICIONADO','diagnostico':'Bloqueo posiblemente ligado al estado de la cuenta',
            'hipotesis':['Cuenta bloqueada','Cuenta vencida'],
            'fuentes':['SEC.taUsuario','SEC.taUsuarioBitacora'],
            'pasos':[{'condicion':'Si estado bloqueado confirmado y identidad verificada',
                      'accion':'Solicitar restablecimiento en el canal autorizado, nunca compartir clave',
                      'responsable':'Responsable IAM autorizado tras aprobación',
                      'verificacion':'Usuario realiza ingreso y la bitácora registra el evento'}],
            'faltantes':['Estado de cuenta y autorización'],
            'cierre':['Prueba de inicio de sesión por titular y trazabilidad'],
            'ejecutado':False,'confirmado':False}


class Fake:
    def __init__(self,response=None):self.response=response or good();self.messages=[]
    def complete(self,messages):self.messages.append(messages);return json.dumps(self.response)


def test_history_temporal_leak():
    x=hist('itil-10','no carga sistema','se hizo una correccion')
    x['modified_at']='2026-01-07T10:00:00'
    with pytest.raises(ValueError,match='LEAKAGE'):require_history(x)


def test_history_temporal_success():
    assert require_history(hist('itil-11','No se emite un recibo comercial','Se corrigio parametro')).case_ref=='itil-11'


def test_history_invalid_event_order():
    x=hist('itil-11','No se emite','Se corrigio');x['solution_recorded_at']='2025-01-01'
    with pytest.raises(ValueError,match='ORDER'):require_history(x)


def test_holdout_solution_leak():
    x=hold();x['solution_text']='El analista lo hizo'
    with pytest.raises(ValueError,match='LEAKAGE'):require_holdout(x)


def test_holdout_reject_without_privacy():
    x=hold();x['privacy_reviewed']=False
    with pytest.raises(ValueError,match='PRIVACY'):require_holdout(x)


def test_holdout_reject_october():
    x=hold();x['opened_at']='2026-10-10T10:00:00'
    with pytest.raises(ValueError,match='MONTH'):require_holdout(x)


def test_redact_password_email_phone():
    s=redact('password=abc123 mail abc@example.com celular 987654321')
    assert 'abc123' not in s and 'abc@example.com' not in s and '987654321' not in s


def test_memory_filter_service_and_recency():
    a=hist('itil-1','Falla de acceso al modulo comercial','Se restablecio acceso',service='101')
    b=hist('itil-2','Falla de acceso al modulo comercial','Se restablecio acceso',service='102')
    idx=MemoryIndex([require_history(a),require_history(b)])
    cand=idx.search(hold(desc='Falla de acceso al modulo comercial'))
    assert len(cand)==1 and cand[0]['ref']=='itil-1'


def test_dedup_identical_template():
    a=hist('itil-1','Falla de acceso al modulo comercial','Se restablecio acceso')
    b=hist('itil-2','Falla de acceso al modulo comercial','Se restablecio acceso')
    idx=MemoryIndex([require_history(a),require_history(b)])
    assert len(idx.search(hold(desc='Falla de acceso al modulo comercial')))==1


def test_hard_gate_good():assert evaluate_response(good())=={'valid':True,'flags':[],'certified_fix':False}


def test_hard_gate_unknown_source():
    a=good();a['fuentes'].append('SEC.taClavesInventadas')
    assert any('UNVERIFIED_SOURCE' in x for x in evaluate_response(a)['flags'])


def test_hard_gate_denied():
    a=good();a['fuentes']=['SEC.taUsuarioSesion']
    assert not evaluate_response(a)['valid']


def test_hard_gate_invalid_admin_sql():
    a=good();a['pasos'][0]['accion']='UPDATE taUsuario SET Administrador=1'
    assert 'RAW_MUTATING_SQL' in evaluate_response(a)['flags']


def test_hard_gate_incomplete():
    a=good();a['pasos'][0]['verificacion']=''
    assert not evaluate_response(a)['valid']


def test_hard_gate_claims_not_done():
    a=good();a['confirmado']=True
    assert 'FALSE_COMPLETION_CLAIM' in evaluate_response(a)['flags']


def test_model_not_given_holdout_solution():
    m=Fake();r=ResolutionRunner(m,MemoryIndex([require_history(hist('itil-2','Falla acceso modulo comercial','Se restablecio por canal oficial'))])).resolve(hold(desc='Falla acceso modulo comercial'))
    assert r['status']=='PLAN_REVIEWABLE' and r['certified_fix'] is False
    q=json.dumps(m.messages[0],ensure_ascii=False)
    assert 'gold_solution' not in q and 'analyst_solution' not in q


def test_unknown_problem_gets_conditional_plan():
    m=Fake();r=ResolutionRunner(m,MemoryIndex([])).resolve(hold(desc='Falla desconocida de servicio no catalogado'))
    assert r['status']=='PLAN_REVIEWABLE' and r['prior_refs']==[]


def test_bad_model_marked_error():
    class Bad:
        def complete(self,messages):return 'no json'
    assert ResolutionRunner(Bad(),MemoryIndex([])).resolve(hold())['status']=='MODEL_ERROR'


def test_batch_resume(tmp_path):
    h=tmp_path/'history.jsonl';q=tmp_path/'holdout.jsonl';o=tmp_path/'private_output.jsonl'
    h.write_text(json.dumps(hist('itil-2','Falla acceso modulo comercial','Se corrigio por canal oficial'))+'\n')
    q.write_text(json.dumps(hold(desc='Falla acceso modulo comercial'))+'\n')
    m=Fake();r=process_jsonl(m,str(h),str(q),str(o),expected_count=1)
    assert r['processed_this_run']==1 and r['certified_fixes']==0
    assert process_jsonl(m,str(h),str(q),str(o),expected_count=1)['skipped_resume']==1
    assert len(m.messages)==1


def test_batch_reject_missing_records(tmp_path):
    h=tmp_path/'history.jsonl';q=tmp_path/'holdout.jsonl';o=tmp_path/'out.jsonl'
    h.write_text('');q.write_text(json.dumps(hold())+'\n')
    with pytest.raises(ValueError,match='COUNT_MISMATCH'):
        process_jsonl(Fake(),str(h),str(q),str(o),expected_count=545)


def test_batch_reject_duplicate_ref(tmp_path):
    h=tmp_path/'history.jsonl';q=tmp_path/'holdout.jsonl';o=tmp_path/'out.jsonl'
    h.write_text('');q.write_text(json.dumps(hold())+'\n'+json.dumps(hold())+'\n')
    with pytest.raises(ValueError,match='DUPLICATE'):
        process_jsonl(Fake(),str(h),str(q),str(o))


def test_hard_gate_blocks_unverified_sql_columns():
    a=good();a['pasos'][0]['accion']='Hacer SELECT * FROM taUsuario para diagnosticar estado'
    assert 'RAW_SQL_WITH_UNVERIFIED_COLUMNS' in evaluate_response(a)['flags']


def test_hard_gate_generic_action_not_sufficient():
    a=good();a['pasos'][0]['accion']='revisar el sistema'
    assert 'NON_SPECIFIC_ACTION_0' in evaluate_response(a)['flags']

import json
import pytest
from else_dominance.support_desk import validate_ticket,make_attention,record_attention

def ticket(text='El operador logra ingresar pero el modulo de inventarios devuelve acceso denegado.'):
    return {'case_ref':'SUP-DEMO-009','input_scope':'synthetic','service':'SIELSE',
            'description':text,'evidence':[{'ref':'E1','observation':'Inicio de sesion validado.'}]}

def good():
    return {'estado':'PROCEDIMIENTO_CONDICIONADO',
        'diagnostico':'Permiso no demostrado y acceso al modulo restringido.',
        'hipotesis':['Falta de permiso funcional'],
        'evidence_refs':['E1'],'fuentes':['SEC.taUsuario'],
        'pasos':[{'condicion':'Si se confirma el permiso ausente con consulta autorizada',
                  'accion':'Solicitar correccion del permiso minimo tras aprobacion',
                  'responsable':'Responsable IAM segun matriz vigente',
                  'verificacion':'Verificar el acceso permitido y los modulos restantes'}],
        'faltantes':['Consulta del perfil efectivo'],
        'cierre':['Verificar acceso al modulo por el titular tras autorizacion'],
        'ejecutado':False,'confirmado':False}

class Fake:
    def __init__(self,obj):self.obj=obj;self.calls=0
    def complete(self,messages):self.calls+=1;return json.dumps(self.obj)

def test_accepts_requester_submitted_only_with_scope():
    x=ticket();x['input_scope']='requester_submitted'
    assert validate_ticket(x)['input_scope']=='requester_submitted'
    x.pop('input_scope')
    with pytest.raises(ValueError,match='REQUESTER_SCOPE_REQUIRED'):validate_ticket(x)

def test_sanitizes_access_secrets():
    x=ticket('Estoy bloqueado, password=clave123 y escribo al correo usuario@example.org.')
    c=validate_ticket(x)
    assert 'clave123' not in c['description']
    assert 'usuario@example.org' not in c['description']

def test_models_produce_reviewable_runbook():
    m=Fake(good())
    r=make_attention(ticket(),m)
    assert r['status']=='ACTION_PLAN_AUTHORIZATION_PENDING'
    assert r['model_selected']=='primary' and m.calls==1
    assert not r['certified_repair'] and not r['executed_changes']

def test_fallback_after_unverifiable_role():
    bad=good();bad['pasos'][0]['responsable']='Security_Administrator'
    first=Fake(bad);second=Fake(good())
    r=make_attention(ticket(),first,second)
    assert r['model_selected']=='secondary'
    assert first.calls==second.calls==1

def test_no_invented_fix_if_two_models_fail():
    bad=good();bad['ejecutado']=True
    r=make_attention(ticket(),Fake(bad),Fake(bad))
    assert r['status']=='NEEDS_HUMAN_TRIAGE'
    assert not r['certified_repair']

def test_private_durable_receipt_and_conflict(tmp_path):
    x=ticket();r=make_attention(x,Fake(good()))
    db=tmp_path/'private.sqlite'
    assert record_attention(db,x,r)['status']=='ACTION_PLAN_AUTHORIZATION_PENDING'
    assert record_attention(db,x,r)==r
    changed=ticket('Un incidente distinto con la misma referencia; no reutilizar.')
    with pytest.raises(ValueError,match='CASE_REF_CHANGED_CONTENT'):
        record_attention(db,changed,r)

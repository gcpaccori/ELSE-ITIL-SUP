"""Synthetic tests: explicit evidence, no historical answer leakage or false fixes."""
import json
from pathlib import Path
import pytest
from else_dominance.historical_mechanism_matching import (
    mentioned_in_history,explicitly_supported_in_request,
    MechanismIndex,build_private_mechanism_index,SCHEMA)
from else_dominance.historical_procedures import (
    request_anchored_patterns,HistoricalProcedureCatalog)
from else_dominance.sources import EvidenceTools

def make_mechanism_index(tmp_path):
    examples=[('0102100100000','Se realizó el desbloqueo de la cuenta del usuario')]*2
    examples+=[('0102100100000','Se liberó espacio del disco C')]
    examples+=[('0102100102000','Se atendió solicitud mediante orientación')]
    examples+=[('0102100102000','se realizó cambio de rol y permisos de usuario')]
    examples+=[('0001','se atendió')]*295
    assert len(examples)==300
    data=build_private_mechanism_index(examples)
    p=tmp_path/'prior.private.json';p.write_text(json.dumps(data))
    return MechanismIndex(p)

def test_request_grounded_mechanism_and_no_automatic_cause(tmp_path):
    cat=make_mechanism_index(tmp_path)
    r=cat.suggest('0102100100000','Cuenta de usuario bloqueada, se requiere desbloqueo')
    assert r['status']=='REQUEST_ANCHORED_HISTORICAL_HYPOTHESES_ONLY'
    assert r['candidates'][0]['mechanism']=='ACCOUNT_UNLOCK'
    assert r['candidates'][0]['prior_note_count']==2
    assert r['cause_confirmed'] is False
    assert r['repair_certified'] is False
    assert r['requires_case_specific_business_state'] is True

def test_same_module_generic_text_is_not_evidence(tmp_path):
    cat=make_mechanism_index(tmp_path)
    r=cat.suggest('0102100100000','SIELSE presenta un error al procesar la solicitud')
    assert r['status']=='ABSTAIN_NOT_ENOUGH_MECHANISM_EVIDENCE'
    assert r['candidates']==[]
    assert r['unanchored_patterns_suppressed']==2

def test_history_labels_are_mentions_not_verified_executions():
    assert 'DISK_SPACE_CLEANUP' in mentioned_in_history('Se liberó espacio del disco C:')
    assert 'PHISHING_SIMULATION' in mentioned_in_history('Fue simulacro de phishing')
    assert 'COORDINATES_CORRECTION' in mentioned_in_history('Se actualizaron coordenadas')
    assert mentioned_in_history('Se atendió el incidente por chat')==[]
    assert explicitly_supported_in_request('El aplicativo falla con error')==[]
    with pytest.raises(ValueError):
        mentioned_in_history('a'*30001)

def test_lexical_anchor_rejects_module_only_pattern():
    patterns=[{'kind':'UPDATE_MENTIONED','table':'tacobranza',
      'fields':['codigocaja'],'count':3,
      'execution_confirmed':False,'historical_note_only':True}]
    x=request_anchored_patterns(patterns,'No carga sistema, sin detalle')
    assert x['anchored']==[] and x['suppressed']==1
    y=request_anchored_patterns(patterns,'La caja no aparece en el listado')
    assert y['anchored'][0]['grounded_tokens']==['caja']
    assert y['anchored'][0]['not_proof_of_cause'] is True
    assert y['anchored'][0]['execution_confirmed'] is False

def test_mechanism_index_frozen_training_cohorts(tmp_path):
    idx=make_mechanism_index(tmp_path)
    obj=idx.data
    obj['includes_monthend_cohorts']=True
    p=tmp_path/'bad.json';p.write_text(json.dumps(obj))
    with pytest.raises(ValueError,match='SOURCE_NOT_FROZEN'):
        MechanismIndex(p)

def test_mechanism_index_no_unrecognized_label(tmp_path):
    idx=make_mechanism_index(tmp_path)
    x=idx.data;x['modules']['0102100100000']['mentions']['CERTIFIED_FIX']=100
    p=tmp_path/'bad.json';p.write_text(json.dumps(x))
    with pytest.raises(ValueError,match='MENTION_INVALID'):
        MechanismIndex(p)

def test_tools_require_same_module_and_request(tmp_path):
    index=make_mechanism_index(tmp_path)
    class Dummy:pass
    tools=EvidenceTools(Dummy(),Dummy(),historical_mechanisms=index)
    name='inspect_historical_mechanisms'
    ctx={'module_code':'0102100100000','description':'Usuario bloqueado de su cuenta'}
    resp=tools.execute(name,{'module_code':'0102100100000'},ctx)
    assert resp['cause_confirmed'] is False
    assert resp['status']=='REQUEST_ANCHORED_HISTORICAL_HYPOTHESES_ONLY'
    assert tools.execute(name,{'module_code':'0102100102000'},ctx)['status']=='BLOCKED'
    assert tools.execute(name,{'module_code':'0102100100000','sql':'DROP'},ctx)['status']=='BLOCKED'
    assert tools.execute(name,{'module_code':'0102100100000'},
                {'module_code':'0102100100000'})['status']=='BLOCKED'
    assert EvidenceTools(Dummy(),Dummy()).execute(name,
                {'module_code':'0102100100000'},ctx)['status']=='BLOCKED'

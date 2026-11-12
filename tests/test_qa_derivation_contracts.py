"""Conservative semantic and routing claims must not launder ITIL history."""
from pathlib import Path
import json
import pytest

from else_dominance.qa_derivation_contracts import (
    VerifiedDerivationContracts,KNOWN_TYPES)
from else_dominance.sources import EvidenceTools
from else_dominance.agent import InvestigationAgent

def sample():
    idx=VerifiedDerivationContracts.__new__(VerifiedDerivationContracts)
    idx.route_receipt_sha256='a'*64
    idx.metadata_receipt_sha256='b'*64
    idx.semantic_status='UNRESOLVED_NO_AUTHORITATIVE_SQL_DICTIONARY_OR_LOGIC'
    idx.derivation_code_semantics={'1':None,'2':None,'3':None}
    idx.events_type_counts={'1':900,'2':90,'3':165}
    sha='c'*64
    idx.rows={
      sha:{
        'case_sha256':sha,'module_code':'0102100100000',
        'service_code':'100','company_code':'1',
        'month':'2026-07','module_declared_system_code':'1',
        'module_declared_alias_bde':'adbELSE',
        'module_declared_dll':'M0102100100000',
        'module_row_matched':True,'service_row_matched':True,
        'module_alias_is_database_route_candidate_only':True,
        'physical_business_database_verified':False,
        'business_object_key_verified':False,
        'business_causal_result_verified':False,
      }
    }
    class Lifecyle:
        receipt_sha256='e'*64
        events={sha:[
          {'type_code':'1','sequence_number':1},
          {'type_code':'3','sequence_number':2}
        ]}
    idx.lifecycle=Lifecyle()
    return idx,sha

def test_semantics_unknown_even_with_global_event_counts():
    idx,case=sample()
    for code in ('1','2','3'):
        x=idx.semantics(code)
        assert x['status']=='UNRESOLVED_NO_AUTHORITATIVE_SQL_DICTIONARY_OR_LOGIC'
        assert x['meaning'] is None
        assert x['allow_business_interpretation'] is False
        assert x['causal_repair_certified'] is False
    assert set(idx.derivation_code_semantics)==KNOWN_TYPES
    assert idx.semantics('4')['status']=='BLOCKED'

def test_per_case_semantics_only_for_observed_code():
    idx,case=sample()
    observed=idx.inspect_type_for_case(
        case_sha256=case,module_code='0102100100000',
        as_of='2026-07-09',type_code='3')
    assert observed['type_observed_in_case'] is True
    assert observed['meaning'] is None
    assert observed['type_code_meaning_not_certified'] is True
    unobserved=idx.inspect_type_for_case(
        case_sha256=case,module_code='0102100100000',
        as_of='2026-07-09',type_code='2')
    assert unobserved['status']=='ABSTAIN_TYPE_NOT_OBSERVED_IN_THIS_EXACT_CASE'
    assert unobserved['meaning'] is None

def test_module_route_is_declared_not_executed():
    idx,case=sample()
    observed=idx.inspect_route(
       case_sha256=case,module_code='0102100100000',as_of='2026-07-09')
    assert observed['status']=='ITIL_MODULE_AND_SERVICE_ROWS_VERIFIED'
    assert observed['alias_bde_declared']=='adbELSE'
    assert observed['module_dll_declared']=='M0102100100000'
    assert observed['same_db_module_pk_matched'] is True
    assert observed['same_db_service_pk_matched'] is True
    assert observed['alias_to_physical_db_route_certified'] is False
    assert observed['business_entity_fk_certified'] is False
    assert observed['business_object_row_read'] is False
    assert observed['causal_repair_certified'] is False

@pytest.mark.parametrize(('key','value'),[
   ('case_sha256','0'*64),
   ('module_code','DIFFERENT_MODULE'),
   ('as_of','2026-08-01')])
def test_route_rejects_cross_case(key,value):
    idx,case=sample()
    x={'case_sha256':case,'module_code':'0102100100000',
       'as_of':'2026-07-09'}
    x[key]=value
    assert idx.inspect_route(**x)['status']=='BLOCKED'

def test_join_proposal_is_blocked_even_for_popular_table():
    idx,case=sample()
    for table in (
      'dbDistribucion_D.dbo.taOrdenTrabajo',
      'dbComercial001_D.dbo.taCobranza',
      'taIncidenteDerivacion',
      'dbSIELSEFiscalizacion.dbo.taIncidenteOperativoOrdenTrabajoComercial'):
        result=idx.proposed_business_join(
          case_sha256=case,module_code='0102100100000',
          as_of='2026-07-09',proposed_table=table)
        assert result['status']=='ABSTAIN_BUSINESS_JOIN_NOT_CERTIFIED'
        assert result['physical_database_certified'] is False
        assert result['business_row_verified'] is False
        assert result['causal_repair_certified'] is False

def test_agent_tool_argument_allowlist_and_context_gate():
    idx,case=sample()
    class Dummy:pass
    tools=EvidenceTools(Dummy(),Dummy(),derivation_contracts=idx)
    context={'case_sha256':case,'module_code':'0102100100000','as_of':'2026-07-09'}
    good=tools.execute('inspect_itil_application_contract',{'view':'module_route'},context)
    assert good['status']=='ITIL_MODULE_AND_SERVICE_ROWS_VERIFIED'
    code=tools.execute('inspect_itil_application_contract',
        {'view':'derivation_type','type_code':'1'},context)
    assert code['meaning'] is None
    assert code['type_observed_in_case'] is True
    bad=[
       {'view':'module_route','type_code':'1'},
       {'view':'derivation_type'},
       {'view':'derivation_type','type_code':'4'},
       {'view':'module_route','sql':'SELECT 1'}
    ]
    for arg in bad:
        assert tools.execute('inspect_itil_application_contract',arg,context)['status']=='BLOCKED'
    assert tools.execute('inspect_itil_application_contract',
        {'view':'module_route'},{**context,'module_code':'OTHER'})['status']=='BLOCKED'
    assert tools.execute('inspect_itil_application_contract',
        {'view':'module_route'},{})['status']=='BLOCKED'
    assert EvidenceTools(Dummy(),Dummy()).execute(
        'inspect_itil_application_contract',{'view':'module_route'},context)['status']=='BLOCKED'

def test_agent_still_does_not_promote_declared_module_alias_to_causality():
    idx,case=sample()
    obs=idx.inspect_route(
         case_sha256=case,module_code='0102100100000',as_of='2026-07-09')
    evidence={'TOOL:1':{
        'name':'inspect_itil_application_contract',
        'args':{'view':'module_route'},'result':obs}}
    proposal={
      'status':'PLAN_PROPUESTO',
      'hypotheses':[{'cause':'BDE alias demuestra que la base de cobranza está incorrecta',
         'test':'Hacer una lectura de estado real','evidence_refs':['TOOL:1']}],
      'proposed_steps':[{'action':'Analizar código autorizado',
         'source':'QA','precondition':'Permiso de lectura',
         'evidence_refs':['TOOL:1'],'verification':'Comprobar objeto exacto'}],
      'confidence':'HIGH'
    }
    v=InvestigationAgent._validate(proposal,evidence)
    assert v['status']=='INVESTIGACION_PENDIENTE'
    assert v['itil_module_route_observed'] is True
    assert v['itil_module_route_observations'][0]['business_join_certified'] is False
    assert v['causal_diagnosis_confirmed'] is False
    assert v['domain_business_state_verified'] is False
    assert v['can_claim_resolved'] is False
    assert 'TOOL:1' in v['invalid_references']

def test_public_report_does_not_disclose_case_identifiers_or_route_values():
    p=Path(__file__).resolve().parents[1]/'data/2026_derivation_semantics_module_routes_900.json'
    data=json.loads(p.read_text())
    assert data['case_count']==900
    assert data['distinct_module_codes']==128
    assert data['alias_bde_declared_cases']==662
    assert data['module_dll_declared_cases']==900
    assert data['module_pk_matched']==data['service_pk_matched']==900
    assert data['type_semantics_verified']==0
    assert data['type_semantics_unresolved']==3
    assert data['business_fk_certified']==0
    assert data['business_repairs_certified']==0
    for code in ('1','2','3'):
        assert data['semantics_'+code]['meaning'] is None
    raw=p.read_text()
    assert '"case_sha256":' not in raw
    assert '"module_declared_dll":' not in raw
    assert '"module_declared_alias_bde":' not in raw
    assert '"AliasBDE":' not in raw

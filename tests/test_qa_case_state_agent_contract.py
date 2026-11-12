"""Proven ITIL field != proven business root cause; tool refs cannot launder causality."""
from else_dominance.agent import InvestigationAgent

def answer():
    return {
     'status':'PLAN_PROPUESTO',
     'hypotheses':[{'cause':'La OT tiene estado 5 por causa específica',
        'test':'Verificar registro de dominio con ID oficial',
        'evidence_refs':['TOOL:1']}],
     'proposed_steps':[{'action':'Revisar, sin modificar',
        'source':'QA','precondition':'Permiso específico de lectura',
        'evidence_refs':['TOOL:1'],
        'verification':'Cotejar estado correcto'}],
     'confidence':'HIGH',
     'reasoning_summary':'La consulta proporcionó un valor exacto',
     'missing_evidence':['Falta vínculo oficial ITIL OT'],
     'next_question':'Confirmar la relación oficial',
    }

def test_case_itil_snapshot_receipt_not_causal_evidence():
    evidence={
      'TOOL:1':{
        'name':'inspect_case_qa_state','args':{'field':'CodigoEstadoIncidente'},
        'result':{
          'status':'READ_VERIFIED_QA_SNAPSHOT',
          'field':'CodigoEstadoIncidente',
          'source':'ELSE70/dbITIL_D/dbo.taIncidente',
          'observed_value':'6',
          'observed_at_utc':'2026-11-12T17:00:00Z',
          'receipt_sha256':'a'*64,
          'provenance_verified':True,
          'business_object_relation_verified':False,
          'repair_certified':False
        }
      }
    }
    result=InvestigationAgent._validate(answer(),evidence)
    assert result['status']=='INVESTIGACION_PENDIENTE'
    assert result['case_itil_metadata_verified'] is True
    assert result['domain_business_state_verified'] is False
    assert result['causal_diagnosis_confirmed'] is False
    assert result['can_execute_mutations'] is False
    assert result['can_claim_resolved'] is False
    assert result['case_itil_field_observations'][0]['observed_value']=='6'
    assert 'TOOL:1' in result['invalid_references']
    assert result['confidence']=='LOW'

def test_exact_reported_order_value_not_official_fk():
    evidence={
      'TOOL:1':{
        'name':'inspect_reported_ot_qa_state',
        'args':{'field':'CodigoEstadoOrdenTrabajo'},
        'result':{
          'status':'READ_VERIFIED_REPORTED_OT_QA_FIELD',
          'field':'CodigoEstadoOrdenTrabajo',
          'source':'ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo',
          'observed_value':'5',
          'observed_at_utc':'2026-11-12T17:00:00Z',
          'receipt_sha256':'a'*64,
          'provenance_verified':True,
          'formal_itil_ot_link_verified':False,
          'repair_certified':False
        }
      }
    }
    result=InvestigationAgent._validate(answer(),evidence)
    assert result['status']=='INVESTIGACION_PENDIENTE'
    assert result['reported_ot_field_evidence_available'] is True
    assert result['reported_ot_field_observations'][0]['observed_value']=='5'
    assert result['reported_ot_field_observations'][0]['formal_itil_ot_link_verified'] is False
    assert result['domain_business_state_verified'] is False
    assert result['causal_diagnosis_confirmed'] is False
    assert 'TOOL:1' in result['invalid_references']

def test_fake_reported_ot_status_not_promoted():
    evidence={
      'TOOL:1':{
        'name':'inspect_reported_ot_qa_state','args':{},
        'result':{
          'status':'READ_VERIFIED_REPORTED_OT_QA_FIELD',
          'field':'CodigoEstadoOrdenTrabajo','source':'ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo',
          'observed_value':'9','receipt_sha256':'x',
          'provenance_verified':False,
          'formal_itil_ot_link_verified':False,
          'repair_certified':False,
        }
      }
    }
    result=InvestigationAgent._validate(answer(),evidence)
    assert result['reported_ot_field_evidence_available'] is False
    assert result['status']=='INVESTIGACION_PENDIENTE'

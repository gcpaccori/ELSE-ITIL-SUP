"""Ensure no SQL, proposed instruction or generic closure becomes verified fix."""
import json
from pathlib import Path
from collections import Counter
import pytest
from qa.monthend2026.score_history_labels import distinguish_evidence_quote
from else_dominance.historical_procedures import (
    HistoricalProcedureCatalog,CATALOG_SCHEMA,request_anchored_patterns)
from else_dominance.sources import EvidenceTools

@pytest.mark.parametrize(('note','expected'),[
  ('UPDATE a SET a.CodigoCaja=42 FROM taCobranza a',
   'SQL_REFERENCE_ONLY_NOT_EXECUTED'),
  ('select * from taIncidente where CodigoEmpresa=1',
   'SQL_REFERENCE_ONLY_NOT_EXECUTED'),
  ('select* from taSuministro a',
   'SQL_REFERENCE_ONLY_NOT_EXECUTED'),
  ('exec dbo.spProcesar @id=12',
   'SQL_REFERENCE_ONLY_NOT_EXECUTED'),
  ('Por favor habilitar los permisos de aplicación',
   'REQUEST_OR_INSTRUCTION_NOT_EXECUTED'),
  ('verificar el campo ActualizarSegunPliego a valor 1',
   'REQUEST_OR_INSTRUCTION_NOT_EXECUTED'),
  ('reintente ingresar el monto correcto',
   'REQUEST_OR_INSTRUCTION_NOT_EXECUTED'),
  ('Se adjunta script para corregir datos',
   'REQUEST_OR_INSTRUCTION_NOT_EXECUTED'),
  ('Se ha copiado los permisos de la cuenta administrativa',
   'NARRATED_ACTION_NOT_INDEPENDENTLY_VERIFIED'),
  ('se le cambio de cable de vga',
   'NARRATED_ACTION_NOT_INDEPENDENTLY_VERIFIED'),
  ('completado',
   'SPECIFICITY_NOT_ESTABLISHED'),
])
def test_quote_evidence_not_execution(note,expected):
    assert distinguish_evidence_quote(note)==expected

def test_bad_oversized_historical_quote_rejected():
    with pytest.raises(ValueError):
        distinguish_evidence_quote('x'*141)

def test_previous_module_pattern_without_request_grounding_not_promoted(tmp_path):
    data={
      'schema':CATALOG_SCHEMA,'cohort_total':300,
      'includes_heldout_fourth':False,
      'source_receipts':[{'cohort':'may_first100'},
                         {'cohort':'may_next100'},
                         {'cohort':'may_third100'}],
      'business_changes_executed':0,
      'notes_with_mentions':1,'unique_module_patterns':1,
      'modules':{'0102100100000':{
        'total_notes':17,'notes_with_mentions':1,
        'patterns':[{'kind':'UPDATE_MENTIONED','table':'tacobranza',
          'fields':['codigocaja'],'count':1,
          'historical_note_only':True,'execution_confirmed':False}]}}
    }
    p=tmp_path/'verified_prior.json';p.write_text(json.dumps(data))
    cat=HistoricalProcedureCatalog(p)
    class Dummy: pass
    e=EvidenceTools(Dummy(),Dummy(),historical_patterns=cat)
    context={'module_code':'0102100100000',
             'description':'La pantalla muestra un error y no sabemos por qué'}
    g=e.execute('inspect_historical_procedures',
        {'module_code':'0102100100000'},context)
    assert g['status']=='ABSTAIN_NO_REQUEST_FIELD_GROUNDING'
    assert g['request_grounded_patterns']==[]
    context['description']='El sistema no muestra la caja de cobranza'
    h=e.execute('inspect_historical_procedures',
        {'module_code':'0102100100000'},context)
    assert h['status']=='REQUEST_ANCHORED_HISTORICAL_MENTIONS_ONLY'
    assert h['request_grounded_patterns'][0]['grounded_tokens']==['caja']
    assert h['case_specific_business_read_performed'] is False
    assert h['cause_verified'] is False

def test_public_monthly_audit_has_no_private_rows():
    root=Path(__file__).resolve().parents[1]/'data'
    for name in ('2026_monthend_historical_evaluation.json',
                 '2026_monthend_history_note_quality.json'):
        content=(root/name).read_text(encoding='utf8')
        assert 'description_redacted' not in content
        assert 'historical_solution_redacted' not in content
        assert '"CodigoIncidente":' not in content
        assert 'evidence_quote' not in content
        assert 'case_sha256' not in content

def test_2026_qa_data_is_not_fabricated_for_october_or_november():
    p=Path(__file__).resolve().parents[1]/'data/2026_monthend_historical_evaluation.json'
    obj=json.loads(p.read_text())
    assert obj['incidents_source_bound']==900
    assert obj['month_receipts_verified']==22
    assert obj['months']['2026-10']['selected_latest']==0
    assert obj['months']['2026-11']['selected_latest']==0
    assert obj['december']=='FUTURE_NOT_EVALUATED'
    assert obj['actual_cause_certified']==0
    assert obj['repairs_executed']==0

def test_historical_specific_quotes_demoted_to_not_proven_fixes():
    p=Path(__file__).resolve().parents[1]/'data/2026_monthend_history_note_quality.json'
    obj=json.loads(p.read_text())
    t=obj['totals']
    assert t['total']==900
    assert t['quality_SPECIFIC_ACTION']==104
    assert t['specific_action_with_grounded_literal_quote']==104
    assert t['specific_quote_SQL_REFERENCE_ONLY_NOT_EXECUTED']>=90
    assert t['specific_quote_REQUEST_OR_INSTRUCTION_NOT_EXECUTED']>=5
    assert obj['technical_fixes_certified']==0
    assert obj['actual_business_changes_executed']==0

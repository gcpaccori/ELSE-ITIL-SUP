import unittest,sys,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from else_dominance.engineer import ResolutionGate,ROUTING,report_md
from else_dominance.sources import SourceCatalog
from else_dominance.batch_2026 import HoldoutBatch

CAT=SourceCatalog(Path(__file__).parents[1]/'data'/'source_catalog.json')
GATE=ResolutionGate(CAT)

class GateTests(unittest.TestCase):
  def setUp(self):
    self.input={'description':'Cuenta bloqueada en SIELSE, no tengo acceso a roles','service_code':'60','module_code':'M001'}
    self.a={'change_domains':['IDENTIDAD_CREDENCIALES'],
            'proposed_steps':[{'action':'Verificar identidad antes de solicitar al responsable restablecimiento de la cuenta','precondition':'Solicitud validada','verification':'Usuario prueba acceso sin divulgación de clave','evidence_refs':[]}],
            'evidence_available':[],'hypotheses':[{'cause':'Bloqueo por política, pendiente de comprobar'}],
            'missing_evidence':['Estado de cuenta actual'],'reasoning_summary':'Aún sin causa confirmada'}
  def test_credential_handoff_requires_authorization(self):
    d=GATE.audit(self.a,self.input)
    assert d['status_operativo']=='PROCEDIMIENTO_CONDICIONADO'
    assert len(d['traspaso_autorizado'])==1
    assert 'identidad' in d['traspaso_autorizado'][0]['required_authorization'].lower()
    assert not d['puede_ejecutar_cambios'] and not d['incidencia_resuelta']
    assert not d['traspaso_autorizado'][0]['corporate_role_mapping_verified']
  def test_unknown_domain_fails(self):
    self.a['change_domains']=['SUPER_ADMIN_REAL']
    assert GATE.audit(self.a,self.input)['status_operativo']=='REQUIERE_REVISION_TECNICA'
  def test_absence_of_domain_requires_review(self):
    self.a['change_domains']=[]
    assert 'ACTOR_DOMAIN_NOT_SPECIFIED' in GATE.audit(self.a,self.input)['banderas_integridad']
  def test_no_steps_pending(self):
    self.a['proposed_steps']=[]
    assert GATE.audit(self.a,self.input)['status_operativo']=='DIAGNOSTICO_PENDIENTE'
  def test_missing_precondition(self):
    del self.a['proposed_steps'][0]['precondition']
    assert 'STEP_0_PRECONDITION_REQUIRED' in GATE.audit(self.a,self.input)['banderas_integridad']
  def test_mutation_text_hard_gate(self):
    self.a['proposed_steps'][0]['action']='UPDATE taUsuario SET Administrador=1'
    assert any('RESTRICTED_MUTATION' in e for e in GATE.audit(self.a,self.input)['banderas_integridad'])
  def test_other_dialect(self):
    self.a['proposed_steps'][0]['action']='SELECT x FROM table LIMIT 1'
    assert any('NON_TSQL' in e for e in GATE.audit(self.a,self.input)['banderas_integridad'])
  def test_denied_session(self):
    self.a['proposed_steps'][0]['action']='SELECT * FROM SEC.taUsuarioSesion WHERE LoginUsuario=1'
    assert any('DENIED_SESSION' in e for e in GATE.audit(self.a,self.input)['banderas_integridad'])
  def test_missing_ref(self):
    self.a['proposed_steps'][0]['evidence_refs']=['CASE:inventada']
    assert any('UNVERIFIED_EVIDENCE' in e for e in GATE.audit(self.a,self.input)['banderas_integridad'])
  def test_known_query_valid(self):
    d=GATE.validate_query_proposal('ITIL_READ_CASE','ITIL.taIncidente',['CodigoIncidente','CodigoModulo'])
    assert d['eligible_to_plan'] and not d['execution_performed']
  def test_query_does_not_execute_llm_sql(self):
    d=GATE.validate_query_proposal('ITIL_READ_CASE','ITIL.taIncidente',['CodigoIncidente'],sql='select 1')
    assert not d['eligible_to_plan']
  def test_unknown_column(self):
    d=GATE.validate_query_proposal('ITIL_READ_CASE','ITIL.taIncidente',['FakeAdminPassword'])
    assert 'UNVERIFIED_COLUMN:FakeAdminPassword' in d['errors']
  def test_denied_source(self):
    d=GATE.validate_query_proposal('SESSION_READ','SEC.taUsuarioSesion',['LoginUsuario'])
    assert 'SQL_SELECT_ACCESS_DENIED_AT_QA' in d['errors']
  def test_report_uses_role_without_secret(self):
    txt=report_md(GATE.audit(self.a,self.input))
    assert 'Responsable autorizado' in txt and 'No se ejecutó ninguna mutación' in txt

class BatchTests(unittest.TestCase):
  def make(self):return {'case_ref':'itil-1','opened_at':'2026-05-19T10:00:00','privacy_reviewed':True,'service_code':'11','module_code':'1','description':'No puedo ingresar'}
  def test_reject_gold_leakage(self):
    x=self.make();x['solution_text']='historial';
    with self.assertRaisesRegex(ValueError,'GOLD_SOLUTION'):HoldoutBatch.validate_case(x)
  def test_reject_no_privacy_review(self):
    x=self.make();x['privacy_reviewed']=False
    with self.assertRaisesRegex(ValueError,'PRIVACY_REVIEW'):HoldoutBatch.validate_case(x)
  def test_reject_2025_as_holdout(self):
    x=self.make();x['opened_at']='2025-02-03T10:00:00'
    with self.assertRaisesRegex(ValueError,'NOT_2026'):HoldoutBatch.validate_case(x)
  def test_accept_2026(self):
    x=HoldoutBatch.validate_case(self.make());assert x['as_of']=='2026-05-19T10:00:00' and 'solution_text' not in x
  def test_resume_without_model_call(self):
    class Dummy:
      def __init__(self):self.n=0
      def investigate(self,case,now):self.n+=1;return {'change_domains':['GESTION_SERVICIO'],'proposed_steps':[]}
    d=Dummy();batch=HoldoutBatch(d,GATE,now='2026-11-02T11:30:00')
    with tempfile.TemporaryDirectory() as temp:
      src=Path(temp)/'source.jsonl';dst=Path(temp)/'result.jsonl'
      src.write_text(json.dumps(self.make())+'\n')
      a=batch.run(src,dst);b=batch.run(src,dst)
      assert a['evaluated_this_run']==1 and b['resumed_skipped']==1 and d.n==1

if __name__=='__main__':unittest.main()

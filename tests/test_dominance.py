import json
import tempfile
from pathlib import Path
import unittest

from else_dominance.memory import CaseMemory
from else_dominance.sources import SourceCatalog, EvidenceTools
from else_dominance.agent import InvestigationAgent, OpenAICompatibleModel

CATALOG=Path(__file__).parents[1]/'data'/'source_catalog.json'

class FakeModel:
    """Fake used ONLY for unit tests; never presented as a deployed model."""
    def __init__(self,*answers):self.answers=iter(answers)
    def complete(self,messages):return json.dumps(next(self.answers),ensure_ascii=False)


def case(ref='itil-123', opened='2025-05-01T00:00:00',solved='2025-05-03T00:00:00', modified='2025-05-04T00:00:00',
         svc='70',mod='X1',req='Error al generar reporte comercial en modulo X1',sol='Se ajustó configuración del reporte y se comprobó con usuario',version='2025'):
    return {'case_ref':ref,'opened_at':opened,'solution_at':solved,'modified_at':modified,
        'service_code':svc,'module_code':mod,'classification_code':'101',
        'system_version':version,'request_text':req,'solution_text':sol,
        'provenance':'APPROVED_QA_HISTORY','privacy_reviewed':True}

class DominanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.memory=CaseMemory(Path(self.tmp.name)/'kb.sqlite')
        self.addCleanup(self.memory.close)
        self.catalog=SourceCatalog(CATALOG)
        self.tools=EvidenceTools(self.memory,self.catalog)
        self.now='2026-11-02T10:00:00'
        self.context={'description':'Error al generar reporte comercial en modulo X1',
                      'service_code':'70','module_code':'X1','classification_code':'101','as_of':'2026-01-01T00:00:00'}

    def test_empty(self):self.assertEqual(self.memory.count(),0)
    def test_ingest(self):self.assertEqual(self.memory.ingest([case()],captured_at=self.now)['inserted'],1)
    def test_dedup(self):
        self.memory.ingest([case()],captured_at=self.now)
        self.assertEqual(self.memory.ingest([case()],captured_at=self.now)['rejected']['DUPLICATE'],1)
    def test_conflicting_hash(self):
        self.memory.ingest([case()],captured_at=self.now)
        with self.assertRaises(ValueError):
            self.memory.ingest([case(sol='Otra reparación completamente diferente')],captured_at=self.now)
    def test_late_solution(self):
        d=case(solved='2026-02-01T00:00:00',modified='2026-02-02T00:00:00')
        self.assertEqual(self.memory.ingest([d],captured_at=self.now)['rejected']['HOLDOUT_LEAKAGE'],1)
    def test_late_modification(self):
        d=case(modified='2026-01-10T00:00:00')
        self.assertEqual(self.memory.ingest([d],captured_at=self.now)['rejected']['HOLDOUT_LEAKAGE'],1)
    def test_unapproved_source(self):
        d=case();d['provenance']='some.other.db'
        self.assertEqual(self.memory.ingest([d],captured_at=self.now)['rejected']['UNAPPROVED_PROVENANCE'],1)
    def test_privacy_requirement(self):
        d=case();d['privacy_reviewed']=False
        self.assertEqual(self.memory.ingest([d],captured_at=self.now)['rejected']['PRIVACY_REVIEW_REQUIRED'],1)
    def test_invalid_timestamp(self):
        d=case(opened='not-a-date')
        self.assertEqual(self.memory.ingest([d],captured_at=self.now)['rejected']['LOCAL_ISO_DATETIME_REQUIRED'],1)
    def test_future_capture(self):
        d=case()
        self.assertEqual(self.memory.ingest([d],captured_at='2025-01-01T00:00:00')['rejected']['INVALID_TEMPORAL_ORDER'],1)
    def test_empty_solution(self):
        d=case(sol=' ')
        self.assertEqual(self.memory.ingest([d],captured_at=self.now)['rejected']['EMPTY_TEXT'],1)
    def test_fts_case_lookup(self):
        self.memory.ingest([case()],captured_at=self.now)
        hits=self.memory.search(query='Error generar reporte comercial',service_code='70',module_code='X1',classification_code='101')
        self.assertEqual(hits[0]['case_ref'],'itil-123')
        self.assertEqual(hits[0]['evidence_status'],'HISTORICAL_ANALYST_NOT_INDEPENDENTLY_VERIFIED')
    def test_service_scope(self):
        self.memory.ingest([case()],captured_at=self.now)
        self.assertEqual(self.memory.search(query='Error generar reporte',service_code='90'),[])
    def test_module_and_class_filter(self):
        self.memory.ingest([case()],captured_at=self.now)
        self.assertEqual(self.memory.search(query='Error generar reporte',service_code='70',module_code='WRONG',classification_code='WRONG'),[])
    def test_version_match(self):
        self.memory.ingest([case()],captured_at=self.now)
        self.assertTrue(self.memory.search(query='Error generar reporte',service_code='70',system_version='2025')[0]['version_match'])
    def test_deduplicate_identical_tickets(self):
        self.memory.ingest([case(ref='itil-123'),case(ref='itil-456')],captured_at=self.now)
        self.assertEqual(len(self.memory.search(query='Error generar reporte comercial',service_code='70')),1)
    def test_source_catalog_count(self):self.assertGreaterEqual(len(self.catalog.sources),20)
    def test_source_lookup(self):self.assertTrue(self.catalog.search('Usuario cuenta bloqueada'))
    def test_source_unknown(self):
        with self.assertRaises(ValueError):self.catalog.describe('otherdb.secret')
    def test_relations_present(self):self.assertEqual(len(self.catalog.data['relations']),8)
    def test_tool_unknown(self):self.assertEqual(self.tools.execute('bogus',{},self.context)['error'],'UNKNOWN_TOOL')
    def test_tool_no_connector(self):self.assertEqual(self.tools.execute('query_live',{'query_id':'x'},self.context)['status'],'BLOCKED')
    def test_scope_override_rejected(self):
        self.assertEqual(self.tools.execute('search_precedents',{'service_code':'1'},self.context)['error'],'SERVICE_SCOPE_VIOLATION')
    def test_agent_model_driven_tool(self):
        self.memory.ingest([case()],captured_at=self.now)
        model=FakeModel(
           {'type':'tool','name':'search_precedents','args':{'query':'Error generar reporte comercial'}},
           {'type':'final','status':'PLAN_PROPUESTO','system_and_operation':'SIELSE, reportes','problem':'Generación de reporte',
            'hypotheses':[{'cause':'Configuración inconsistente','evidence_refs':['CASE:itil-123'],
                            'test':'Verificar configuración del reporte'}],
            'proposed_steps':[{'action':'Comparar parámetros del reporte con plantilla autorizada',
                               'source':'ITIL.taIncidente','precondition':'Acceso de solo lectura',
                               'evidence_refs':['CASE:itil-123'],'verification':'Generar reporte en QA y comparar el contenido'}],
            'missing_evidence':['Configuración actual'],'next_question':'¿Qué módulo presenta el error?',
            'reasoning_summary':'El antecedente es indicio, no certeza','confidence':'LOW'})
        result=InvestigationAgent(model,self.tools,self.memory).investigate(self.context,now=self.now)
        self.assertEqual(result['status'],'PLAN_PROPUESTO')
        self.assertEqual(result['tool_calls'],1)
        self.assertTrue(self.memory.verify_ledger(result['session_id']))
        self.assertFalse(result['can_claim_resolved'])
    def test_agent_hallucinated_evidence(self):
        model=FakeModel({'type':'final','status':'PLAN_PROPUESTO','hypotheses':[{'cause':'Error de red','evidence_refs':['FAKE:1']}],
                 'proposed_steps':[]})
        answer=InvestigationAgent(model,self.tools,self.memory).investigate(self.context,now=self.now)
        self.assertEqual(answer['status'],'INVESTIGACION_PENDIENTE')
        self.assertIn('FAKE:1',answer['invalid_references'])
    def test_agent_no_tool_no_support(self):
        model=FakeModel({'type':'final','status':'PLAN_PROPUESTO','hypotheses':[],'proposed_steps':[]})
        answer=InvestigationAgent(model,self.tools,self.memory).investigate(self.context,now=self.now)
        self.assertEqual(answer['status'],'INVESTIGACION_PENDIENTE')
    def test_blocked_tool_not_valid_evidence(self):
        model=FakeModel(
            {'type':'tool','name':'query_live','args':{'query_id':'UNAUTHORIZED'}},
            {'type':'final','status':'PLAN_PROPUESTO',
             'hypotheses':[{'cause':'An error','evidence_refs':['TOOL:1']}],
             'proposed_steps':[],'confidence':'HIGH'})
        answer=InvestigationAgent(model,self.tools,self.memory).investigate(self.context,now=self.now)
        self.assertEqual(answer['status'],'INVESTIGACION_PENDIENTE')
        self.assertIn('TOOL:1',answer['invalid_references'])
        self.assertEqual(answer['confidence'],'LOW')
    def test_agent_illegal_resolved(self):
        model=FakeModel({'type':'final','status':'RESUELTO','hypotheses':[],'proposed_steps':[]})
        answer=InvestigationAgent(model,self.tools,self.memory).investigate(self.context,now=self.now)
        self.assertFalse(answer['can_claim_resolved'])
    def test_agent_invalid_json_exhaustion(self):
        class Broken:
            def complete(self,messages):return '{broken'
        answer=InvestigationAgent(Broken(),self.tools,self.memory,max_steps=2).investigate(self.context,now=self.now)
        self.assertEqual(answer['status'],'INVESTIGACION_PENDIENTE')
    def test_ledger_tamper_detected(self):
        self.memory.start_session({},'sid',self.now)
        self.memory.append('sid',{'step':'first'},self.now)
        self.assertTrue(self.memory.verify_ledger('sid'))
        self.memory.db.execute('UPDATE session_events SET event_json=? WHERE session_id=?',('bad','sid'))
        self.memory.db.commit()
        self.assertFalse(self.memory.verify_ledger('sid'))
    def test_model_url_guard(self):
        with self.assertRaises(ValueError):OpenAICompatibleModel('http://remote-not-secure','a').complete([])
    def test_memory_no_case_text_seeded(self):self.assertEqual(self.memory.count(),0)

if __name__=='__main__':unittest.main()

import tempfile, unittest
from pathlib import Path
from else_dominance.learning import ProcedureMemory

class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=ProcedureMemory(Path(self.tmp.name)/'learning.sqlite');self.addCleanup(self.db.close)
        self.p={'procedure_id':'P-1','title':'Correccion reporte','service':'70','module':'M1','version':'2025',
                'symptom':'Reporte falla','action_steps':['Validar parametros','Probar en QA'],
                'diagnosis_tests':['Compare service configs'],
                'outcome_tests':['Mismo reporte se genera y datos coinciden'],
                'evidence_refs':['CASE:123'],'created_at':'2026-11-02T10:00:00'}
    def test_propose(self):self.assertEqual(self.db.propose(self.p)['state'],'DRAFT')
    def test_reject_missing(self):
        x=dict(self.p);x['evidence_refs']=[]
        with self.assertRaises(ValueError):self.db.propose(x)
    def test_single_reviewer_not_certified(self):
        self.db.propose(self.p)
        r=self.db.check('P-1',reviewer='tech',role='ANALYST',evidence_ref='CASE:123',decision='APPROVE',observed_result='Reviewed',at='2026-11-02T10:00:00')
        self.assertEqual(r['state'],'UNDER_REVIEW')
    def test_two_roles_without_test_not_certified(self):
        self.db.propose(self.p)
        self.db.check('P-1',reviewer='a',role='ANALYST',evidence_ref='CASE:123',decision='APPROVE',observed_result='Reviewed',at='2026-11-02T10:00:00')
        r=self.db.check('P-1',reviewer='b',role='QA',evidence_ref='DOC:123',decision='APPROVE',observed_result='Reviewed',at='2026-11-02T10:00:00')
        self.assertEqual(r['state'],'UNDER_REVIEW')
    def test_two_roles_and_test_certifies(self):
        self.db.receipt_verifier=lambda ref, proc: ref=='TEST_RECEIPT:3' and proc=='P-1'
        self.db.propose(self.p)
        self.db.check('P-1',reviewer='a',role='ANALYST',evidence_ref='CASE:123',decision='APPROVE',observed_result='Reviewed',at='2026-11-02T10:00:00')
        r=self.db.check('P-1',reviewer='b',role='QA',evidence_ref='TEST_RECEIPT:3',decision='APPROVE',observed_result='Verified test',at='2026-11-02T10:00:00')
        self.assertEqual(r['state'],'VALIDATED')
        self.assertEqual(len(self.db.export_supervision()),1)
    def test_string_receipt_not_enough(self):
        self.db.propose(self.p)
        self.db.check('P-1',reviewer='a',role='ANALYST',evidence_ref='CASE:123',decision='APPROVE',observed_result='Reviewed',at='2026-11-02T10:00:00')
        r=self.db.check('P-1',reviewer='b',role='QA',evidence_ref='TEST_RECEIPT:3',decision='APPROVE',observed_result='Verified',at='2026-11-02T10:00:00')
        self.assertEqual(r['state'],'UNDER_REVIEW')
    def test_duplicate_reviewer(self):
        self.db.propose(self.p)
        self.db.check('P-1',reviewer='a',role='ANALYST',evidence_ref='CASE:123',decision='APPROVE',observed_result='Reviewed',at='2026-11-02T10:00:00')
        with self.assertRaises(ValueError):
            self.db.check('P-1',reviewer='a',role='QA',evidence_ref='TEST_RECEIPT:3',decision='APPROVE',observed_result='Verified',at='2026-11-02T10:00:00')
    def test_rejection(self):
        self.db.propose(self.p)
        r=self.db.check('P-1',reviewer='a',role='ANALYST',evidence_ref='CASE:123',decision='REJECT',observed_result='Faulty',at='2026-11-02T10:00:00')
        self.assertEqual(r['state'],'REJECTED')
        self.assertEqual(self.db.export_supervision(),[])
    def test_no_missing_procedure(self):
        with self.assertRaises(ValueError):
            self.db.check('NA',reviewer='a',role='ANALYST',evidence_ref='CASE:123',decision='APPROVE',observed_result='Reviewed',at='2026-11-02T10:00:00')

if __name__=='__main__':unittest.main()

import unittest
from else_dominance.qa_adapter import QAReadOnlyAdapter, Query

class Cursor:
 def __init__(self): self.description=None; self.calls=[]; self.rows=[]; self.bad_server=False
 def execute(self,sql,args=None):
  self.calls.append((sql,args))
  if 'SERVERPROPERTY' in sql: self.rows=[('TEST-QA','QA_DB')]
  else:
   self.rows=[(12,'read-only result')]
   self.description=[('CaseId',),('Description',)]
 def fetchone(self): return ('PROD','QA_DB') if self.bad_server else self.rows[0]
 def fetchmany(self,n): return self.rows[:n]
 def close(self): pass
class Conn:
 def __init__(self,c):self.c=c
 def __enter__(self):return self
 def __exit__(self,*_):pass
 def cursor(self):return self.c
class Tests(unittest.TestCase):
 def setUp(self):
  self.cursor=Cursor()
  query=Query('TEST','SELECT TOP (1) CaseId,Description FROM TestCases WHERE CaseId=?',('CaseId',),1,'TEST.Cases',{'CaseId':'case_id'})
  self.adapter=QAReadOnlyAdapter(lambda _:Conn(self.cursor),expected_server='TEST-QA',db_names={'TEST':'QA_DB'},queries={'READ_CASE':query})
 def test_registered_read(self):
  out=self.adapter.run('READ_CASE',{'CaseId':12},scope={'case_id':12})
  self.assertEqual(out['status'],'READ_VERIFIED')
  self.assertTrue(out['read_only'])
 def test_unregistered(self):self.assertEqual(self.adapter.run('DELETE',{},scope={})['status'],'BLOCKED')
 def test_scope(self):self.assertEqual(self.adapter.run('READ_CASE',{'CaseId':12},scope={'case_id':13})['error'],'SCOPE_VIOLATION')
 def test_extras(self):self.assertEqual(self.adapter.run('READ_CASE',{'CaseId':12,'sql':'DROP'},scope={'case_id':12})['error'],'PARAMETER_SET_MISMATCH')
 def test_invalid_parameter(self):self.assertEqual(self.adapter.run('READ_CASE',{'CaseId':{}},scope={'case_id':{}})['error'],'INVALID_PARAMETER')
 def test_wrong_server(self):
  self.cursor.bad_server=True
  self.assertEqual(self.adapter.run('READ_CASE',{'CaseId':12},scope={'case_id':12})['error'],'WRONG_QA_DATABASE')
 def test_mutating_config_rejected(self):
  with self.assertRaises(ValueError): QAReadOnlyAdapter(lambda _:None,expected_server='TEST-QA',db_names={'TEST':'QA_DB'},queries={'BAD':Query('TEST','UPDATE Accounts SET role=1',(),1,'TEST.X',{})})
 if __name__=='__main__':unittest.main()

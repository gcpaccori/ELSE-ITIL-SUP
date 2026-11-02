"""Curriculum and procedure-memory promotion. No synthetic label is ground truth.

This module does NOT train neural weights. It prepares reviewed supervision pairs.
Training requires a separately approved model/compute workflow.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path

class ProcedureMemory:
    def __init__(self,path:str|Path, receipt_verifier=None):
        self.receipt_verifier=receipt_verifier
        self.db=sqlite3.connect(str(path))
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS proposals (
          procedure_id TEXT PRIMARY KEY, title TEXT NOT NULL,
          service TEXT NOT NULL, module TEXT NOT NULL, version TEXT NOT NULL,
          symptom TEXT NOT NULL, action_steps_json TEXT NOT NULL,
          diagnosis_tests_json TEXT NOT NULL, outcome_tests_json TEXT NOT NULL,
          evidence_refs_json TEXT NOT NULL, state TEXT NOT NULL,
          created_at TEXT NOT NULL, content_sha256 TEXT NOT NULL,
          CHECK(state IN ('DRAFT','UNDER_REVIEW','REJECTED','VALIDATED')));
        CREATE TABLE IF NOT EXISTS procedure_checks (
          check_id INTEGER PRIMARY KEY, procedure_id TEXT NOT NULL REFERENCES proposals(procedure_id),
          reviewer TEXT NOT NULL, role TEXT NOT NULL, evidence_ref TEXT NOT NULL,
          decision TEXT NOT NULL CHECK(decision IN ('APPROVE','REJECT')),
          observed_result TEXT NOT NULL,
          reviewed_at TEXT NOT NULL);
        ''')
    def propose(self,p:dict):
        required=('procedure_id','title','service','module','version','symptom',
                  'action_steps','diagnosis_tests','outcome_tests','evidence_refs','created_at')
        if any(not p.get(k) for k in required):raise ValueError('INCOMPLETE_PROCEDURE')
        if not isinstance(p['action_steps'],list) or not isinstance(p['diagnosis_tests'],list):raise ValueError('BAD_STRUCTURE')
        if not isinstance(p['outcome_tests'],list) or not isinstance(p['evidence_refs'],list):raise ValueError('BAD_STRUCTURE')
        digest=hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        row=(p['procedure_id'],p['title'],p['service'],p['module'],p['version'],p['symptom'],
             json.dumps(p['action_steps'],ensure_ascii=False),json.dumps(p['diagnosis_tests'],ensure_ascii=False),
             json.dumps(p['outcome_tests'],ensure_ascii=False),json.dumps(p['evidence_refs'],ensure_ascii=False),
             'DRAFT',p['created_at'],digest)
        with self.db:self.db.execute('INSERT INTO proposals VALUES ('+','.join('?'*13)+')',row)
        return {'procedure_id':p['procedure_id'],'state':'DRAFT'}
    def check(self,procedure_id:str,*,reviewer:str,role:str,evidence_ref:str,decision:str,observed_result:str,at:str):
        if not evidence_ref or not reviewer or not observed_result:raise ValueError('REVIEW_EVIDENCE_REQUIRED')
        if decision not in ('APPROVE','REJECT'):raise ValueError('BAD_DECISION')
        row=self.db.execute('SELECT state FROM proposals WHERE procedure_id=?',(procedure_id,)).fetchone()
        if not row:raise ValueError('UNKNOWN_PROCEDURE')
        if row['state']=='VALIDATED':raise ValueError('IMMUTABLE_VALIDATED_PROCEDURE')
        if self.db.execute('SELECT 1 FROM procedure_checks WHERE procedure_id=? AND reviewer=?',(procedure_id,reviewer)).fetchone():
            raise ValueError('DUPLICATE_REVIEWER')
        with self.db:
            self.db.execute('INSERT INTO procedure_checks(procedure_id,reviewer,role,evidence_ref,decision,observed_result,reviewed_at) VALUES (?,?,?,?,?,?,?)',
                          (procedure_id,reviewer,role,evidence_ref,decision,observed_result,at))
            if decision=='REJECT': state='REJECTED'
            else:
                approvals=self.db.execute('SELECT role,evidence_ref FROM procedure_checks WHERE procedure_id=? AND decision=?',(procedure_id,'APPROVE')).fetchall()
                independent=len({r['role'] for r in approvals})>=2
                outcome=bool(self.receipt_verifier) and any(
                    r['evidence_ref'].startswith('TEST_RECEIPT:') and self.receipt_verifier(r['evidence_ref'],procedure_id)
                    for r in approvals)
                state='VALIDATED' if independent and outcome else 'UNDER_REVIEW'
            self.db.execute('UPDATE proposals SET state=? WHERE procedure_id=?',(state,procedure_id))
        return {'state':state,'procedure_id':procedure_id}
    def export_supervision(self,*,approved_only=True)->list[dict]:
        sql='SELECT * FROM proposals WHERE state=?' if approved_only else 'SELECT * FROM proposals'
        rows=self.db.execute(sql,('VALIDATED',) if approved_only else ()).fetchall()
        # Does not output personal information unless author added it to procedure.
        return [{'procedure_id':r['procedure_id'],'state':r['state'],
                 'input':{'service':r['service'],'module':r['module'],'system_version':r['version'],
                          'symptom':r['symptom']},
                 'verified_procedure':{'steps':json.loads(r['action_steps_json']),
                          'tests':json.loads(r['diagnosis_tests_json']),
                          'expected_results':json.loads(r['outcome_tests_json']),
                          'evidence_refs':json.loads(r['evidence_refs_json'])}} for r in rows]
    def close(self):self.db.close()

"""Secure-by-deployment, versioned knowledge memory and FTS5 retrieval.

Store corporate case text ONLY in an authorized corporate environment. The
package ships without case texts. SQLite is not an access-control boundary.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


def iso(s: str) -> datetime:
    if not isinstance(s, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d', s):
        raise ValueError('LOCAL_ISO_DATETIME_REQUIRED')
    return datetime.fromisoformat(s)


def words(s: str) -> list[str]:
    # Only for FTS candidate lookup; diagnosis remains the LLM's job.
    return list(dict.fromkeys(re.findall(r'[^\W\d_]{3,}', str(s).lower(), flags=re.UNICODE)))[:24]


class CaseMemory:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS cases (
          case_ref TEXT PRIMARY KEY, opened_at TEXT NOT NULL,
          solution_at TEXT NOT NULL, modified_at TEXT NOT NULL,
          service_code TEXT NOT NULL, module_code TEXT NOT NULL,
          classification_code TEXT NOT NULL, system_version TEXT NOT NULL,
          request_text TEXT NOT NULL, solution_text TEXT NOT NULL,
          evidence_status TEXT NOT NULL, provenance TEXT NOT NULL,
          content_sha256 TEXT NOT NULL, recorded_at TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS case_fts USING fts5(
          case_ref UNINDEXED, request_text, solution_text,
          tokenize='unicode61 remove_diacritics 2');
        CREATE TABLE IF NOT EXISTS review (
          review_id INTEGER PRIMARY KEY, case_ref TEXT NOT NULL REFERENCES cases(case_ref),
          reviewer_role TEXT NOT NULL, reviewed_at TEXT NOT NULL,
          correctness TEXT NOT NULL, independent_evidence_ref TEXT,
          rationale TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          session_id TEXT PRIMARY KEY, opened_at TEXT NOT NULL,
          input_json TEXT NOT NULL, status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS session_events (
          event_id INTEGER PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(session_id),
          at TEXT NOT NULL, event_json TEXT NOT NULL,
          previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_case_scope ON cases(service_code,module_code,classification_code,opened_at);
        ''')

    def count(self):
        return self.db.execute('SELECT COUNT(*) FROM cases').fetchone()[0]

    def ingest(self, items: list[dict[str, Any]], *, captured_at: str,
               approved_source='APPROVED_QA_HISTORY') -> dict:
        """Reject holdout/future/modified-later solutions. Do NOT redact here;
        caller must provide already privacy-reviewed records inside authorized QA.
        """
        captured = iso(captured_at)
        good = []
        reasons = {}
        for item in items:
            try:
                if item.get('provenance') != approved_source:
                    raise ValueError('UNAPPROVED_PROVENANCE')
                ref = str(item['case_ref'])
                if not ref.startswith('itil-'):
                    raise ValueError('INVALID_REF')
                opened, solved, modified = [iso(item[k]) for k in ('opened_at','solution_at','modified_at')]
                if not (opened <= solved <= captured and modified <= captured):
                    raise ValueError('INVALID_TEMPORAL_ORDER')
                if solved >= datetime(2026,1,1) or modified >= datetime(2026,1,1):
                    raise ValueError('HOLDOUT_LEAKAGE')
                req, sol = str(item['request_text']), str(item['solution_text'])
                if not req.strip() or not sol.strip():
                    raise ValueError('EMPTY_TEXT')
                if len(req)>8000 or len(sol)>12000:
                    raise ValueError('OVERSIZED_TEXT_REQUIRES_REVIEW')
                if item.get('privacy_reviewed') is not True:
                    raise ValueError('PRIVACY_REVIEW_REQUIRED')
                data=(ref,opened.isoformat(timespec='seconds'),solved.isoformat(timespec='seconds'),
                      modified.isoformat(timespec='seconds'),str(item.get('service_code') or ''),
                      str(item.get('module_code') or ''),str(item.get('classification_code') or ''),
                      str(item.get('system_version') or 'UNKNOWN'),req,sol,
                      'HISTORICAL_ANALYST_NOT_INDEPENDENTLY_VERIFIED',approved_source,
                      hashlib.sha256(json.dumps(item,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
                      captured.isoformat(timespec='seconds'))
                if not data[4]:
                    raise ValueError('SERVICE_REQUIRED')
                good.append(data)
            except (ValueError,KeyError,TypeError) as e:
                reasons[str(e)] = reasons.get(str(e),0)+1
        inserted=0
        with self.db:
            for d in good:
                prior=self.db.execute('SELECT content_sha256 FROM cases WHERE case_ref=?',(d[0],)).fetchone()
                if prior:
                    if prior['content_sha256']!=d[12]:
                        raise ValueError('CONFLICTING_IMMUTABLE_CASE_REF')
                    reasons['DUPLICATE'] = reasons.get('DUPLICATE',0)+1
                    continue
                self.db.execute('INSERT INTO cases VALUES ('+','.join('?'*14)+')',d)
                self.db.execute('INSERT INTO case_fts(case_ref,request_text,solution_text) VALUES (?,?,?)', (d[0],d[8],d[9]))
                inserted+=1
        return {'inserted':inserted,'rejected':reasons,'total':self.count()}

    def search(self, *, query: str, service_code: str, module_code: str = '',
               classification_code: str='', system_version: str='',
               as_of='2026-01-01T00:00:00', limit: int = 8) -> list[dict]:
        """Broad retrieval + meaningful structured filters; unlike the old engine
        module disagreement is down-ranked, not wrongly equated to an impossible issue.
        """
        cutoff=iso(as_of)
        if cutoff > datetime(2026,12,31,23,59,59):
            raise ValueError('OUTSIDE_HISTORICAL_EVAL_WINDOW')
        term=words(query)
        if not term or not service_code:
            return []
        # Match *candidate* via FTS, then rerank by domain structure and valid time.
        fts=' OR '.join('"'+w.replace('"','')+'"' for w in term)
        rows=self.db.execute('''SELECT c.*, bm25(case_fts,0.0,1.0,0.0) AS fts_score
          FROM case_fts JOIN cases c ON case_fts.case_ref=c.case_ref
          WHERE case_fts MATCH ? AND c.service_code=?
          AND c.solution_at<? AND c.modified_at<?
          ORDER BY bm25(case_fts,0.0,1.0,0.0) LIMIT 300''',
          (fts,str(service_code),cutoff.isoformat(timespec='seconds'),cutoff.isoformat(timespec='seconds'))).fetchall()
        scored=[]
        for r in rows:
            mr=bool(module_code and r['module_code']==str(module_code))
            cr=bool(classification_code and r['classification_code']==str(classification_code))
            vr=bool(system_version and system_version!='UNKNOWN' and r['system_version']==system_version)
            if module_code and not mr and classification_code and not cr:
                continue
            # BM25 score is negative for better matches. Use bounded bonuses.
            age=max(0,cutoff.year-int(r['opened_at'][:4]))
            score=-float(r['fts_score']) + (1.2 if mr else 0)+(0.45 if cr else 0)+(1 if vr else 0)-0.05*age
            scored.append((score,{'evidence_ref':'CASE:'+r['case_ref'],
                'case_ref':r['case_ref'],'service_code':r['service_code'],
                'module_code':r['module_code'],'classification_code':r['classification_code'],
                'system_version':r['system_version'],'opened_at':r['opened_at'],
                'solution_at':r['solution_at'],'historical_request':r['request_text'][:1000],
                'historical_solution':r['solution_text'][:1600],
                'evidence_status':r['evidence_status'],'score':round(score,4),
                'module_match':mr,'classification_match':cr,'version_match':vr}))
        scored.sort(key=lambda x:-x[0])
        # Same text is not independent corroboration: limit duplicates.
        dedup=set(); out=[]
        for _,r in scored:
            signature=hashlib.sha256((r['historical_request'].strip().lower()+'|'+r['historical_solution'].strip().lower()).encode()).hexdigest()
            if signature in dedup:
                continue
            dedup.add(signature);out.append(r)
            if len(out)>=max(1,min(20,limit)):
                break
        return out

    def start_session(self, case: dict, session_id: str, at: str):
        iso(at)
        with self.db:
            self.db.execute('INSERT INTO sessions VALUES (?,?,?,?)',
              (session_id,at,json.dumps(case,ensure_ascii=False,sort_keys=True),'OPEN'))

    def append(self, session_id: str, event: dict, at: str) -> dict:
        iso(at)
        raw=json.dumps(event,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        row=self.db.execute('SELECT event_hash FROM session_events WHERE session_id=? ORDER BY event_id DESC LIMIT 1',(session_id,)).fetchone()
        prev=row['event_hash'] if row else 'GENESIS'
        digest=hashlib.sha256((prev+'|'+session_id+'|'+at+'|'+raw).encode()).hexdigest()
        with self.db:
            self.db.execute('INSERT INTO session_events(session_id,at,event_json,previous_hash,event_hash) VALUES(?,?,?,?,?)',
                      (session_id,at,raw,prev,digest))
        return {'hash':digest,'previous':prev}

    def verify_ledger(self, session_id: str) -> bool:
        rows=self.db.execute('SELECT * FROM session_events WHERE session_id=? ORDER BY event_id',(session_id,)).fetchall()
        prev='GENESIS'
        for r in rows:
            expected=hashlib.sha256((prev+'|'+session_id+'|'+r['at']+'|'+r['event_json']).encode()).hexdigest()
            if expected!=r['event_hash'] or r['previous_hash']!=prev:return False
            prev=expected
        return True

    def close(self): self.db.close()

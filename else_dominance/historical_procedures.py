"""Read-only patterns *mentioned* in archived ITIL resolution notes.

A SQL statement written in a ticket can be a proposal, comment, or discarded
experiment; this library never claims it was executed. It cannot execute SQL.
Index data must remain in a private authorized location.
"""
from __future__ import annotations

from pathlib import Path
import json
import re

CATALOG_SCHEMA="else.itil.qa.historical-procedure-mentions.v1"
WORD=r"[A-Za-z_][A-Za-z_0-9]*"
IDENT=rf"(?:{WORD}\.)?{WORD}"
UPDATE_RE=re.compile(
    rf"\bupdate\s+(?P<alias>{IDENT})\s+set\s+"
    rf"(?P<set>.{{1,1200}}?)\s+from\s+(?P<table>{IDENT})\b",
    flags=re.I|re.S)
DELETE_RE=re.compile(rf"\bdelete\s+from\s+(?P<table>{IDENT})\b",flags=re.I)
EXEC_RE=re.compile(rf"\bexec(?:ute)?\s+(?P<proc>{IDENT})\b",flags=re.I)
FIELD_RE=re.compile(rf"(?:\b{WORD}\.)?({WORD})\s*=",flags=re.I)
MODULE_RE=re.compile(r"[0-9A-Z]{1,20}\Z")
SAFE_REF_RE=re.compile(r"[a-z][a-z_0-9.]{1,95}\Z")

def normalize_ref(value:str)->str:
    if not isinstance(value,str):
        return ''
    name=value.lower().strip()
    if SAFE_REF_RE.fullmatch(name):
        return name
    return ''

def extract_note_mentions(note:str,*,allow_table_columns:dict[str,set[str]]|None=None)->list[dict]:
    """Return bounded, non-executable procedural references, without values.

    If QA metadata is passed, preserve only SQL table/column combinations
    observed in that metadata. No rows or SQL values are returned.
    """
    if type(note) is not str:
        raise TypeError('HISTORICAL_NOTE_MUST_BE_TEXT')
    if len(note)>30000:
        raise ValueError('HISTORICAL_NOTE_OVERSIZED')
    allowed=allow_table_columns
    outcomes=[]
    for match in UPDATE_RE.finditer(note):
        table=normalize_ref(match['table'])
        fields=sorted(set(x.lower() for x in FIELD_RE.findall(match['set'])[:16]))
        if not table or not fields:continue
        leaf=table.rsplit('.',1)[-1]
        if allowed is not None:
            candidate=allowed.get(table) or allowed.get(leaf)
            if not candidate or not set(fields).issubset(candidate):continue
        outcomes.append({
          'kind':'UPDATE_MENTIONED','table':table,'fields':fields[:12],
          'execution_confirmed':False,'historical_note_only':True})
    for match in DELETE_RE.finditer(note):
        table=normalize_ref(match['table'])
        if not table:continue
        leaf=table.rsplit('.',1)[-1]
        if allowed is not None and table not in allowed and leaf not in allowed:continue
        outcomes.append({
          'kind':'DELETE_MENTIONED','table':table,'fields':[],
          'execution_confirmed':False,'historical_note_only':True})
    for match in EXEC_RE.finditer(note):
        proc=normalize_ref(match['proc'])
        if not proc or len(proc.rsplit('.',1)[-1])<4:continue
        # Proc metadata is not equivalent to table metadata; never infer execution.
        outcomes.append({
          'kind':'PROCEDURE_CALL_MENTIONED','table':proc,'fields':[],
          'execution_confirmed':False,'historical_note_only':True})
    unique={}
    for item in outcomes:
        key=(item['kind'],item['table'],tuple(item['fields']))
        unique[key]=item
    return list(unique.values())[:30]

class HistoricalProcedureCatalog:
    def __init__(self,path:str|Path):
        path=Path(path)
        obj=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(obj,dict) or obj.get('schema')!=CATALOG_SCHEMA:
            raise ValueError('HISTORICAL_PROCEDURE_CATALOG_SCHEMA_MISMATCH')
        if obj.get('cohort_total')!=300 or obj.get('includes_heldout_fourth') is not False:
            raise ValueError('HISTORICAL_PROCEDURE_COHORT_CONTAMINATION')
        receipts=obj.get('source_receipts')
        if (type(receipts) is not list or len(receipts)!=3
            or [r.get('cohort') for r in receipts if type(r) is dict]
               !=['may_first100','may_next100','may_third100']):
            raise ValueError('HISTORICAL_SOURCE_RECEIPTS_NOT_TRAINING_ONLY')
        if obj.get('business_changes_executed')!=0:
            raise ValueError('HISTORICAL_CATALOG_FALSE_EXECUTION_CLAIM')
        modules=obj.get('modules')
        if type(modules) is not dict:
            raise ValueError('HISTORICAL_PROCEDURE_MODULE_INDEX_BAD')
        for module,details in modules.items():
            if not MODULE_RE.fullmatch(module):
                raise ValueError('HISTORICAL_PROCEDURE_MODULE_ID_INVALID')
            if type(details) is not dict or type(details.get('total_notes')) is not int:
                raise ValueError('HISTORICAL_PROCEDURE_COUNTER_INVALID')
            patterns=details.get('patterns')
            if (type(details.get('notes_with_mentions')) is not int
                or details['notes_with_mentions']>details['total_notes']
                or details['notes_with_mentions']<0):
                raise ValueError('HISTORICAL_PROCEDURE_NOTE_COUNTER_INVALID')
            if type(patterns) is not list:
                raise ValueError('HISTORICAL_PROCEDURE_PATTERN_LIST_BAD')
            for p in patterns:
                if (type(p) is not dict
                   or set(p)!={'kind','table','fields','count','execution_confirmed','historical_note_only'}
                   or p.get('execution_confirmed') is not False
                   or p.get('historical_note_only') is not True
                   or p.get('kind') not in ('UPDATE_MENTIONED','DELETE_MENTIONED','PROCEDURE_CALL_MENTIONED')
                   or not normalize_ref(p.get('table'))
                   or type(p.get('count')) is not int or p['count']<1
                   or p['count']>details['total_notes']
                   or type(p.get('fields')) is not list
                   or not all(normalize_ref(x) for x in p['fields'])):
                    raise ValueError('HISTORICAL_PROCEDURE_PATTERN_INVALID')
        self.data=obj
        self.modules=modules

    def describe(self,module_code:str)->dict:
        if type(module_code) is not str or not MODULE_RE.fullmatch(module_code):
            return {'status':'BLOCKED','error':'INVALID_MODULE_CODE'}
        data=self.modules.get(module_code)
        if data is None:
            return {'status':'NO_HISTORICAL_PATTERN_AVAILABLE',
                'module_code':module_code,'notes_seen':0,'candidate_patterns':[],
                'diagnosis_verified':False,'repairs_certified':0}
        return {
          'status':'HISTORICAL_NOTES_ONLY_NOT_VERIFIED_EXECUTIONS',
          'module_code':module_code,'notes_seen':data['total_notes'],
          'notes_with_structured_mentions':data['notes_with_mentions'],
          'candidate_patterns':data['patterns'][:12],
          'historical_source_cohorts':3,
          'candidate_mechanisms_not_causal_claims':True,
          'requires_ticket_specific_read':True,
          'diagnosis_verified':False,'repairs_certified':0,
        }

    def summary(self)->dict:
        return {
          'status':'PRIVATE_300_CASE_HISTORICAL_MENTION_INDEX',
          'training_source_notes':self.data['cohort_total'],
          'modules_with_cases':len(self.modules),
          'notes_with_structured_mentions':self.data['notes_with_mentions'],
          'unique_module_patterns':self.data['unique_module_patterns'],
          'heldout_fourth_used':False,
          'technical_fixes_certified':0,
          'repair_operations_executed':0,
        }

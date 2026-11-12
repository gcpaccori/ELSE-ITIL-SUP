"""Public aggregate of separately adjudicated 900 month-end technician notes.

Every item must match the HMAC-authenticated private cohort's SHA-256 case key;
an exact quote is checked byte-for-byte against its source note. No private
sentences or identifiers may be written into published reports.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path
from qa.monthend2026.evaluate_monthend import verify_one
from hashlib import sha256

SCHEMA='else.itil.qa.2026-monthend-history-note-quality-summary.v1'

# A model's label "specific" is NOT sufficient. SQL pasted into a note,
# imperatives, and future instructions do not document a performed repair.
SQL_FRAGMENT=re.compile(
    r'(?i)\b(?:select\s*\*?|update|insert|delete|exec(?:ute)?|alter)\s*(?:\*|\w+|dbo\.)')
INSTRUCTION=re.compile(
    r'(?i)^\s*(?:por favor\b|favor\b|solicito\b|necesito\b|'
    r'se requiere\b|se solicita\b|verificar\b|revisar\b|'
    r'reintente\b|suspender\b|se adjunta script\b|'
    r'debe\b|deberia\b)')
NARRATED_ACTION=re.compile(
    r'(?i)\b(?:se ha copiado|se le cambio|se actualizo|se realizo|'
    r'se reinicio|se libero|se instalo|se configuro|se procedio a)\b')

def distinguish_evidence_quote(text:str)->str:
    """Return a kind of *written reference*, never verified execution."""
    if not isinstance(text,str) or len(text)>140:
        raise ValueError('HISTORICAL_QUOTE_INVALID')
    if SQL_FRAGMENT.search(text):
        return 'SQL_REFERENCE_ONLY_NOT_EXECUTED'
    if INSTRUCTION.search(text):
        return 'REQUEST_OR_INSTRUCTION_NOT_EXECUTED'
    if NARRATED_ACTION.search(text):
        return 'NARRATED_ACTION_NOT_INDEPENDENTLY_VERIFIED'
    return 'SPECIFICITY_NOT_ESTABLISHED'


def score(private:Path,reader:Path,key:bytes,journal:Path)->dict:
    labels=[json.loads(x) for x in journal.read_text(encoding='utf-8').splitlines() if x.strip()]
    if len(labels)!=900:
        raise ValueError('HISTORY_NINE_HUNDRED_LABELS_NOT_COMPLETE')
    keyed={}
    for row in labels:
        pair=(row['month'],row['rank'])
        if pair in keyed or row['schema']!='else.itil.qa.monthend2026-all900-history-labels.v1':
            raise ValueError('HISTORY_LABEL_DUPLICATED_OR_WRONG_SCHEMA')
        keyed[pair]=row
    source_sha=sha256(reader.read_bytes()).hexdigest()
    outcomes={}
    for month in range(1,10):
        ym=f'2026{month:02d}'
        gold,_=verify_one(
            private/f'monthend_{ym}_history.private.json',key,source_sha,
            'else.itil.qa.2026-monthend100-history.v1',
            'else.itil.qa.2026-monthend100-history-hmac.v1')
        orig,_=verify_one(
            private/f'monthend_{ym}.private.json',key,source_sha,
            'else.itil.qa.2026-monthend100-source.v1',
            'else.itil.qa.2026-monthend100-source-hmac.v1')
        if orig['selected']!=100 or gold['historical_count']!=100:
            raise ValueError('NOT_HUNDRED_MONTH_QA')
        counts=Counter()
        for request,history in zip(orig['results'],gold['historical_records']):
            k=(ym,request['rank'])
            label=keyed.pop(k,None)
            if (label is None or label['case_sha256']!=request['case_sha256']
                or label['case_sha256']!=history['case_sha256']
                or label['author_model_did_not_see_note'] is not True):
                raise ValueError('HISTORY_LABEL_COULD_NOT_BIND_CASE')
            note=history['historical_solution_redacted']
            quoted=label['evidence_quote']
            if quoted and quoted not in note:
                raise ValueError('HISTORY_LABEL_QUOTE_UNGROUNDED')
            if (label['quality']=='SPECIFIC_ACTION' and
                (not quoted or label['status']!='PROVISIONAL_QUOTE_GROUNDED')):
                raise ValueError('HISTORY_SPECIFIC_ACTION_WITHOUT_EXACT_QUOTE')
            if not note.strip() and label['quality']!='EMPTY_OR_UNCLEAR':
                raise ValueError('MISSING_HISTORY_NOT_ABSTAINED')
            counts['total']+=1
            counts['notes_nonempty']+=bool(note.strip())
            counts['quality_'+label['quality']]+=1
            counts['status_'+label['status']]+=1
            if label['quality']=='SPECIFIC_ACTION':
                counts['specific_action_with_grounded_literal_quote']+=1
                counts['specific_quote_'+distinguish_evidence_quote(quoted)]+=1
        outcomes[f'2026-{month:02d}']=dict(sorted(counts.items()))
    if keyed:
        raise ValueError('HISTORY_LABELS_CONTAIN_NONEXISTENT_MONTHS')
    totals=Counter()
    for row in outcomes.values():totals.update(row)
    return {
       'schema':SCHEMA,
       'months_with_100':9,
       'case_ids_hmac_bound':900,
       'historical_note_model':'Qwen3.5-4B',
       'labels_are_provisional_not_human_verified':True,
       'notes_used_only_by_historical_evaluator':True,
       'model_rejected_notes_not_counted_as_specific':True,
       'technical_fixes_certified':0,
       'actual_business_changes_executed':0,
       'months':outcomes,
       'totals':dict(sorted(totals.items()))
    }

def main():
    p=argparse.ArgumentParser()
    for arg in ('private','reader','key','journal','output'):
        p.add_argument('--'+arg,required=True,type=Path)
    a=p.parse_args()
    result=score(a.private,a.reader,a.key.read_bytes(),a.journal)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    for m,d in result['months'].items():
        print(m,'labelled',d['total'],
              'specific',d.get('quality_SPECIFIC_ACTION',0),
              'generic',d.get('quality_GENERIC_CLOSURE',0),
              'rejected',d.get('quality_UNSCORED',0))
    print('TOTAL',result['totals'])
if __name__=='__main__':main()

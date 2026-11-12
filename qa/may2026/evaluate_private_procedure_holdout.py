"""Strict comparison of frozen prior-history patterns with untouched fourth cohort.

This evaluates exact SQL statement *mentions*, not proof of execution or
resolution accuracy. The holdout cases are never imported into the catalog.
"""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
from hashlib import sha256
import json
from else_dominance.historical_procedures import (
    HistoricalProcedureCatalog,extract_note_mentions)
from qa.may2026.score_private_history import verify_receipt

def score(catalog:HistoricalProcedureCatalog,requests:dict,gold:dict)->dict:
    if catalog.data['includes_heldout_fourth'] is not False:
        raise ValueError('HOLDOUT_IN_CATALOG')
    if requests['selected']!=100 or gold['historical_count']!=100:
        raise ValueError('HOLDOUT_SIZE_MISMATCH')
    counts=Counter()
    for req,answer in zip(requests['results'],gold['historical_records']):
        if req['case_sha256']!=answer['case_sha256']:
            raise ValueError('HOLDOUT_CASE_NOT_BOUND')
        candidates=catalog.describe(req['module_code'])['candidate_patterns']
        actual=extract_note_mentions(answer['historical_solution_redacted'])
        predicted={(
            x['kind'],x['table'],tuple(x['fields'])) for x in candidates}
        recorded={(
            x['kind'],x['table'],tuple(x['fields'])) for x in actual}
        counts['cases']+=1
        counts['candidate_available']+=bool(predicted)
        counts['recorded_sql_mention']+=bool(recorded)
        counts['both_available']+=bool(predicted and recorded)
        counts['exact_overlap']+=bool(predicted & recorded)
        counts['gold_mention_but_no_candidate']+=bool(recorded and not predicted)
        counts['gold_mention_and_nonmatching_candidate']+=bool(
            recorded and predicted and not (predicted & recorded))
    if counts['cases']!=100:
        raise ValueError('HOLDOUT_NOT_HUNDRED')
    return {
        'schema':'else.itil.qa.historical-procedure-holdout-score.v1',
        'heldout_cases':counts['cases'],
        'cohort_training_source_cases':300,
        'candidate_hints_available':counts['candidate_available'],
        'holdout_with_sql_mentions':counts['recorded_sql_mention'],
        'both_pattern_sets_nonempty':counts['both_available'],
        'exact_kind_table_field_overlap':counts['exact_overlap'],
        'historical_sql_mention_no_prior_hint':counts['gold_mention_but_no_candidate'],
        'historical_sql_mention_different_prior_hint':counts[
            'gold_mention_and_nonmatching_candidate'],
        'matched_root_causes_verified':0,
        'fixes_executed':0,
        'meanings':{
            'candidate_hints_available':'Earlier notes in the same module mention structured procedures',
            'exact_kind_table_field_overlap':'Same kind/table/field set appears in holdout historical note; NOT causality or executed action',
        },
        'private_ticket_text_exported':False,
    }

def main():
    p=argparse.ArgumentParser()
    for arg in ('private','catalog','signing-key','output'):
        p.add_argument('--'+arg,required=True,type=Path)
    a=p.parse_args()
    reader='MayFourth100Read.cs'
    qa=Path(__file__).resolve().parent
    key=a.signing_key.read_bytes()
    source,sha=verify_receipt(a.private,qa,key,'may_fourth100',reader)
    historical,gold_sha=verify_receipt(a.private,qa,key,'may_fourth100',reader,history=True)
    if historical['cohort_source_sha256']!=sha:
        raise ValueError('HISTORICAL_COULD_NOT_BIND_TO_HOLDOUT')
    cat=HistoricalProcedureCatalog(a.catalog)
    if 'may_fourth100' in json.dumps(cat.data['source_receipts']):
        raise ValueError('FOURTH_COHORT_EXPOSED_TO_CATALOG')
    data=score(cat,source,historical)
    data['source_receipt_sha256']=sha
    data['gold_receipt_sha256']=gold_sha
    data['catalog_sha256']=sha256(a.catalog.read_bytes()).hexdigest()
    a.output.parent.mkdir(exist_ok=True,parents=True)
    a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:data[key] for key in (
        'heldout_cases','candidate_hints_available','holdout_with_sql_mentions',
        'both_pattern_sets_nonempty','exact_kind_table_field_overlap',
        'matched_root_causes_verified','fixes_executed')}))
if __name__=='__main__':
    main()

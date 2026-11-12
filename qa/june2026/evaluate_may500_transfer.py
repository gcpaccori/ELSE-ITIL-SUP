"""Full June 1621 temporal holdout against 500 HMAC-verified May precedents.

May includes five previously signed cohorts, all before June 1. Predictions
use ONLY module+request and prior May historical SQL *mentions*; the June
resolution is read only after each prediction is frozen. No asserted SQL
execution, future case leakage or business writes.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from hashlib import sha256
from pathlib import Path
from argparse import ArgumentParser
import json,gzip

from qa.may2026.score_private_history import verify_receipt
from qa.monthend2026.evaluate_monthend import verify_one
from else_dominance.historical_procedures import (
    extract_note_mentions,request_anchored_patterns)

COHORTS=(
 ('may_first100','MayFirst100Read.cs'),
 ('may_next100','MayNext100Read.cs'),
 ('may_third100','MayThird100Read.cs'),
 ('may_fourth100','MayFourth100Read.cs'),
 ('may_fifth100','MayFifth100Read.cs'),
)
SCHEMA='else.itil.qa.2026-may500-to-june1621-temporal-transfer.v1'

def may500(private:Path,qa:Path,key:bytes,atlas:Path,module_dir:Path)->tuple[dict,list[dict]]:
    with gzip.open(atlas,'rt',encoding='utf-8') as fp:
        db=json.load(fp)
    allowed=defaultdict(set)
    for entry in db['table_dictionary'].values():
        if str(entry['database']).endswith('_D'):
            allowed[entry['table'].lower()].update(k.lower() for k in entry['columns'])
    modules={r['codigo_modulo_trimmed_for_repo_name'] for r in json.loads(module_dir.read_bytes())}
    train=defaultdict(Counter)
    n_by_module=Counter()
    training_receipts=[]
    unique=set()
    for prefix,source in COHORTS:
        req,req_sha=verify_receipt(private,qa,key,prefix,source)
        gold,gold_sha=verify_receipt(private,qa,key,prefix,source,history=True)
        if (req.get('selected')!=100 or gold.get('historical_count')!=100
            or gold['cohort_source_sha256']!=req_sha
            or len(req.get('results',[]))!=100 or len(gold.get('historical_records',[]))!=100
            or req.get('history_or_resolution_read') is not False):
            raise ValueError('MAY_500_PRECEDENTS_INVALID_SCOPE')
        training_receipts.append({'cohort':prefix,'request_sha256':req_sha,'history_sha256':gold_sha})
        for r,g in zip(req['results'],gold['historical_records']):
            key_sha=r['case_sha256']
            if (key_sha!=g['case_sha256'] or key_sha in unique
                or r['module_code'] not in modules
                or not r['opened_at'].startswith('2026-05')):
                raise ValueError('MAY500_PRECEDENT_CASE_NOT_MAY_OR_DUPLICATED')
            unique.add(key_sha)
            n_by_module[r['module_code']]+=1
            for a in extract_note_mentions(
                    g['historical_solution_redacted'],
                    allow_table_columns=allowed):
                train[r['module_code']][(
                    a['kind'],a['table'],tuple(a['fields']))]+=1
    if len(unique)!=500:
        raise ValueError('MAY500_NOT_FIVE_HUNDRED_DISTINCT_CASES')
    model={}
    for module,counts in train.items():
        patterns=[{
            'kind':kind,'table':table,'fields':list(fields),'count':n,
            'historical_note_only':True,'execution_confirmed':False}
            for (kind,table,fields),n in counts.items()]
        patterns.sort(key=lambda x:(-x['count'],x['kind'],x['table'],x['fields']))
        model[module]=patterns[:12]
    return model,training_receipts

def score(model:dict,full_private:Path,reader:Path,key:bytes,train_receipts:list[dict],ledger:Path)->dict:
    source_sha=sha256(reader.read_bytes()).hexdigest()
    req,req_hash=verify_one(full_private/'juneall_202606.private.json',
        key,source_sha,'else.itil.qa.2026-juneall-source.v1','else.itil.qa.2026-juneall-source-hmac.v1')
    gold,gold_hash=verify_one(full_private/'juneall_202606_history.private.json',
        key,source_sha,'else.itil.qa.2026-juneall-history.v1','else.itil.qa.2026-juneall-history-hmac.v1')
    if req['selected']!=1621 or gold['historical_count']!=1621 or gold['cohort_source_sha256']!=req_hash:
        raise ValueError('JUNE_ALL_HOLDOUT_WRONG')
    counts=Counter()
    private_records=[]
    for i,(r,g) in enumerate(zip(req['results'],gold['historical_records'])):
        if (r['case_sha256']!=g['case_sha256']
            or r['rank']!=i+1 or g['rank']!=i+1):
            raise ValueError('MAY500_HOLDOUT_CASE_DRIFT')
        # blind May-only historical predictor before seeing June history
        source_patterns=model.get(r['module_code'],[])
        anchored=request_anchored_patterns(source_patterns,r['description_redacted'])['anchored']
        pred={(x['kind'],x['table'],tuple(x['fields'])) for x in anchored}
        # June gold unlocked ONLY for scoring the frozen prediction.
        observed=extract_note_mentions(g['historical_solution_redacted'])
        actual={(x['kind'],x['table'],tuple(x['fields'])) for x in observed}
        flags={
          'evaluated':True,
          'prior_may500_pattern_for_module':bool(source_patterns),
          'request_grounded_sql_candidate':bool(pred),
          'same_kind_and_table':bool({(x[0],x[1]) for x in pred}&{(x[0],x[1]) for x in actual}),
          'exact_kind_table_fields':bool(pred&actual),
          'both_predicted_and_gold_structured':bool(pred and actual),
          'gold_has_sql_reference':bool(actual),
          'note_nonempty':bool(g['historical_solution_redacted'].strip()),
        }
        counts.update(flags)
        private_records.append({
          'rank':i+1,'case_sha256':r['case_sha256'],'flags':flags,
          'model': 'MAY500_ONLY_FROZEN_BEFORE_JUNE',
          'gold_was_not_used_to_make_predictions':True,
          'changes_executed':False,'repair_certified':False,
        })
    if counts['evaluated']!=1621:
        raise ValueError('JUNE_HOLDOUT_INCOMPLETE')
    ledger.parent.mkdir(parents=True,exist_ok=True)
    ledger.write_text(json.dumps({
        'schema':'else.itil.qa.juneall-may500-private-ledger.v1',
        'source_sha256':req_hash,'history_sha256':gold_hash,
        'cases':private_records},ensure_ascii=False))
    ledger.chmod(0o600)
    return {
       'schema':SCHEMA,
       'train_month':'2026-05','train_count':500,
       'test_month':'2026-06','test_count':1621,
       'verified_train_cohorts':len(train_receipts),
       'training_receipt_sha256':[x['history_sha256'] for x in train_receipts],
       'june_request_receipt_sha256':req_hash,
       'june_history_receipt_sha256':gold_hash,
       'zero_june_holdout_notes_used_for_training':True,
       'strict_earlier_month_training':True,
       'all_1621_tested':True,
       'outcomes_are_lexical_historical_sql_overlap_not_verified_technical_fixes':True,
       'repairs_certified':0,'business_writes_executed':0,
       'totals':dict(sorted(counts.items()))
    }

def main():
    p=ArgumentParser()
    for name in ('may-private','may-qa','key','atlas','module-dir',
                 'june-private','june-reader','private-ledger','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    model,receipts=may500(a.may_private,a.may_qa,a.key.read_bytes(),a.atlas,a.module_dir)
    report=score(model,a.june_private,a.june_reader,a.key.read_bytes(),receipts,a.private_ledger)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('MAY500_JUNE1621_REPORT',json.dumps(report['totals'],ensure_ascii=False,sort_keys=True))
if __name__=='__main__':main()

"""Verify fifth-cohort QA and aggregate blinded paired model/judge results.

All case texts and historical notes stay private. No PII, SQL or per-case
identifiers are persisted to the repository.
"""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import argparse
import json
from else_dominance.historical_procedures import (
    HistoricalProcedureCatalog,extract_note_mentions)
from qa.may2026.score_private_history import verify_receipt

def score_pairs(pairs:list[dict],judgements:list[dict])->dict:
    by={(j['rank'],j['condition']):j for j in judgements}
    if len(by)!=len(judgements) or len(by)!=len(pairs)*2:
        raise ValueError('JUDGE_PAIRS_MISSING_OR_DUPLICATED')
    stats=Counter()
    for p in pairs:
        rank=p['rank']
        assert p['gold_solution_exposed'] is False
        statuses={}
        labels={}
        for cond,key in (('baseline','baseline'),('hints','with_hints')):
            author=p[key]
            judge=by[(rank,cond)]
            assert author['case_sha256']==p['case_sha256']==judge['case_sha256']
            assert judge['author_gold_seen'] is False
            assert judge['status']=='PROVISIONAL_JUDGE_PASS'
            statuses[cond]=author['status']
            labels[cond]=judge['assessment']['match']
            stats[cond+'_'+statuses[cond]]+=1
            stats[cond+'_judge_'+labels[cond]]+=1
        a=labels['baseline'];b=labels['hints']
        stats['same_grade']+=(a==b)
        stats['specific_gain']+=(a!='SPECIFIC_MATCH' and b=='SPECIFIC_MATCH')
        stats['specific_loss']+=(a=='SPECIFIC_MATCH' and b!='SPECIFIC_MATCH')
        stats['valid_plan_gain']+=(statuses['baseline']!='FUNCTIONAL_DRAFT_CONTRACT_PASS'
                                   and statuses['hints']=='FUNCTIONAL_DRAFT_CONTRACT_PASS')
        stats['valid_plan_loss']+=(statuses['baseline']=='FUNCTIONAL_DRAFT_CONTRACT_PASS'
                                   and statuses['hints']!='FUNCTIONAL_DRAFT_CONTRACT_PASS')
    return dict(sorted(stats.items()))

def score_holdout(cat:HistoricalProcedureCatalog,requests:dict,history:dict)->dict:
    stats=Counter()
    for case,gold in zip(requests['results'],history['historical_records']):
        if case['case_sha256']!=gold['case_sha256']:
            raise ValueError('CASE_GOLD_NOT_BOUND')
        prior=cat.describe(case['module_code'])['candidate_patterns']
        actual=extract_note_mentions(gold['historical_solution_redacted'])
        before={(p['kind'],p['table'],tuple(p['fields'])) for p in prior}
        after={(p['kind'],p['table'],tuple(p['fields'])) for p in actual}
        stats['rows']+=1
        stats['prior_available']+=bool(before)
        stats['historical_sql_mentioned']+=bool(after)
        stats['exact_overlap']+=bool(before&after)
    return dict(sorted(stats.items()))

def main():
    p=argparse.ArgumentParser()
    for key in ('private','catalog','hmac-key','output'):
        p.add_argument('--'+key,required=True,type=Path)
    p.add_argument('--expected-pairs',type=int,default=43)
    a=p.parse_args()
    cat=HistoricalProcedureCatalog(a.catalog)
    receipts=[]
    all_cases=set()
    qa=Path(__file__).resolve().parent
    key=a.hmac_key.read_bytes()
    for name,reader in (
        ('may_first100','MayFirst100Read.cs'),
        ('may_next100','MayNext100Read.cs'),
        ('may_third100','MayThird100Read.cs'),
        ('may_fourth100','MayFourth100Read.cs'),
        ('may_fifth100','MayFifth100Read.cs'),
    ):
        info,sha=verify_receipt(a.private,qa,key,name,reader)
        gold,gsha=verify_receipt(a.private,qa,key,name,reader,history=True)
        assert info['selected']==gold['historical_count']==100
        assert gold['cohort_source_sha256']==sha
        for row,h in zip(info['results'],gold['historical_records']):
            assert row['case_sha256']==h['case_sha256']
            assert row['case_sha256'] not in all_cases
            all_cases.add(row['case_sha256'])
        receipts.append((info,gold))
    if len(all_cases)!=500:
        raise ValueError('FIVE_HUNDRED_UNIQUE_QA_CASES_REQUIRED')
    request,history=receipts[4]
    eligible={v['rank'] for v in request['results'] if cat.describe(v['module_code'])['candidate_patterns']}
    assert len(eligible)==43
    pairs=[json.loads(s) for s in (a.private/'may_fifth100_paired_model.private.jsonl').read_text().splitlines() if s.strip()]
    judges=[json.loads(s) for s in (a.private/'may_fifth100_paired_judge.private.jsonl').read_text().splitlines() if s.strip()]
    if len(pairs)!=a.expected_pairs or len({x['rank'] for x in pairs})!=len(pairs):
        raise ValueError('PAIRED_EVALUATION_INCOMPLETE')
    assert set(x['rank'] for x in pairs)<=eligible
    expected_catalog_sha=sha256(a.catalog.read_bytes()).hexdigest()
    for pair in pairs:
        assert pair['prior_catalog_sha256']==expected_catalog_sha
        assert pair['source_receipt_sha256']==sha256(
            (a.private/'may_fifth100.private.json').read_bytes()).hexdigest()
    result={
        'schema':'else.itil.qa.may2026-fifth100-procedure-evaluation.v1',
        'evaluation':'Fifth independent 100-case cohort, paired test restricted to cases with historical hints',
        'unique_may_cases_qa_verified':500,
        'qa_hmac_receipts_verified':10,
        'trained_historical_notes':300,
        'heldout_used_in_catalog':False,
        'fifth_cohort':score_holdout(cat,request,history),
        'paired_cases':len(pairs),
        'paired_experimental_catalog_sha256':expected_catalog_sha,
        'paired_plan_and_provisional_judge':score_pairs(pairs,judges),
        'notes':'Judge is Qwen 3.5 4B; specific matches are provisional, not proven technician actions.',
        'qa_mutations':0,
        'repairs_verified':0,
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'fifth':result['fifth_cohort'],
      'paired_cases':result['paired_cases'],
      'paired_outcome':result['paired_plan_and_provisional_judge']}))
if __name__=='__main__':
    main()

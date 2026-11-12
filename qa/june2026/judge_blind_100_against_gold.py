"""Independent Qwen3.5-4B judgement of 100 sealed Qwen9B June plans.

Scorer is NOT author and sees history ONLY AFTER complete 100-plan blind
author journal exists. Positive classifications remain provisional, no proof
of executed SQL or historically correct root cause.
"""
from __future__ import annotations
from argparse import ArgumentParser
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from hashlib import sha256
import json
from qa.monthend2026.evaluate_monthend import verify_one
from qa.monthend2026.judge_private_sample import judge
from qa.june2026.run_blind_qwen_sample import SAMPLE,SCHEMA as AUTHOR_SCHEMA
from else_dominance.functional_investigator_v2 import canon

def main():
    p=ArgumentParser()
    for name in ('private','reader','key','author-journal','journal'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--workers',type=int,default=6)
    p.add_argument('--start',type=int,default=0)
    p.add_argument('--count',type=int,default=100)
    p.add_argument('--url',default='http://127.0.0.1:8003/v1/chat/completions')
    p.add_argument('--model',default='qwen35-4b')
    args=p.parse_args()
    if not 1<=args.workers<=8 or not 0<=args.start<100 or not 1<=args.count<=100:
        p.error('Invalid batch')
    key=args.key.read_bytes()
    code_sha=sha256(args.reader.read_bytes()).hexdigest()
    source,source_hash=verify_one(args.private/'juneall_202606.private.json',key,code_sha,
         'else.itil.qa.2026-juneall-source.v1','else.itil.qa.2026-juneall-source-hmac.v1')
    historical,history_hash=verify_one(args.private/'juneall_202606_history.private.json',key,code_sha,
         'else.itil.qa.2026-juneall-history.v1','else.itil.qa.2026-juneall-history-hmac.v1')
    if (len(source['results'])!=1621 or len(historical['historical_records'])!=1621
         or historical['cohort_source_sha256']!=source_hash):
        raise ValueError('FULL_JUNE_GOLD_SOURCE_NOT_VERIFIED')
    authors=[json.loads(s) for s in args.author_journal.read_text().splitlines() if s.strip()]
    by={}
    for rec in authors:
        rank=rec['rank']
        if (rank not in SAMPLE or rank in by or rec['schema']!=AUTHOR_SCHEMA
            or rec['source_receipt_sha256']!=source_hash
            or rec['gold_exposed'] is not False
            or rec['case_sha256']!=source['results'][rank-1]['case_sha256']):
            raise ValueError('UNSEALED_AUTHOR_IN_JUDGE_JOURNAL')
        by[rank]=rec
    if len(by)!=100:
        raise ValueError('ALL_100_AUTHORS_MUST_FINISH_BEFORE_JUDGING')
    done={}
    if args.journal.exists():
        for line in args.journal.read_text().splitlines():
            if not line:continue
            r=json.loads(line)
            rank=r['rank']
            if (rank in done or rank not in SAMPLE
                or r['case_sha256']!=by[rank]['case_sha256']
                or r['schema']!='else.itil.qa.2026-monthend-qwen4b-historical-evaluation.v1'
                or r['author_no_historical_gold'] is not True):
                raise ValueError('UNBOUND_JUDGE_RESULT')
            done[rank]=r
    todo=[]
    for rank in SAMPLE[args.start:args.start+args.count]:
        if rank in done:continue
        author=by[rank]
        req=source['results'][rank-1]
        gold=historical['historical_records'][rank-1]
        if author['case_sha256']!=req['case_sha256']!=gold['case_sha256']:
            raise ValueError('JUDGE_CROSS_CASE_COUPLING_INVALID')
        todo.append((author,req,gold))
    args.journal.parent.mkdir(parents=True,exist_ok=True)
    with args.journal.open('ab') as stream,ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(judge,a,r,h,args.url,args.model) for a,r,h in todo]
        for f in as_completed(futures):
            result=f.result()
            if result['case_sha256']!=by[result['rank']]['case_sha256']:
                raise ValueError('JUDGE_MODEL_WRONG_CASE')
            stream.write(canon(result)+b'\n')
            stream.flush()
            done[result['rank']]=result
            print(json.dumps({'rank':result['rank'],
               'status':result['status'],
               'history_quality':result.get('judge',{}).get('history_quality'),
               'alignment':result.get('judge',{}).get('plan_alignment')},
               ensure_ascii=False),flush=True)
    print('JUDGE_BATCH_END',json.dumps({'finished':len(done),
        'statuses':dict(Counter(x['status'] for x in done.values()))}))
if __name__=='__main__':main()

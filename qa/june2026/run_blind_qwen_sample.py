"""Prespecified systematic 100 / ALL 1621 June cases: real Qwen9B blind.

The module never opens June history/solution files. Its 100 positions evenly
span the entire June month's descending chronology, not just last 100.
Results remain a PRIVATE journal; an independent historical scorer opens
gold later. No business reads or edits by LLM.
"""
from __future__ import annotations
from argparse import ArgumentParser
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json
from qa.monthend2026.evaluate_monthend import verify_one
from else_dominance.functional_investigator_v2 import run_case,canon

SAMPLE=tuple(round(1+i*1620/99) for i in range(100))
assert len(SAMPLE)==len(set(SAMPLE))==100 and SAMPLE[0]==1 and SAMPLE[-1]==1621
SCHEMA='else.itil.qa.2026-juneall-qwen9b-100-systematic-author.v1'

def load_blind(private:Path,reader:Path,key:bytes,module_dir:Path):
    source,source_sha=verify_one(private/'juneall_202606.private.json',
        key,sha256(reader.read_bytes()).hexdigest(),
        'else.itil.qa.2026-juneall-source.v1',
        'else.itil.qa.2026-juneall-source-hmac.v1')
    if (source['selected']!=1621 or len(source['results'])!=1621
        or source['history_or_resolution_read'] is not False):
        raise ValueError('BLIND_JUNE_FULL_SOURCE_INVALID')
    modules={x['codigo_modulo_trimmed_for_repo_name']:x['nombre_modulo_itil']
             for x in json.loads(module_dir.read_bytes())}
    for rank in SAMPLE:
        row=source['results'][rank-1]
        if row['rank']!=rank or row['module_code'] not in modules:
            raise ValueError('BLIND_SAMPLE_CASE_MODULE_NOT_SIGNED')
    return source,source_sha,modules

def author(rank,row,source_sha,module):
    try:
        result=run_case({
             'ticket_sha256':row['case_sha256'],
             'incident_text_redacted':row['description_redacted']},
             max_attempts=2,verified_module_name=module)
    except Exception as ex:
        result={'schema':'else.itil.functional-v2-result.v1',
            'status':'MODEL_CALL_FAILED','case_sha256':row['case_sha256'],
            'domain':'UNKNOWN','attempts':0,
            'quality':{'accepted':False,'flags':[type(ex).__name__]},
            'historical_resolution_exposed':False,'repair_certified':False,
            'root_cause_certified':False,'executed':False}
    if (result['case_sha256']!=row['case_sha256']
        or result['repair_certified'] is not False
        or result.get('historical_resolution_exposed') is not False):
        raise ValueError('BLIND_MODEL_OUTPUT_NOT_CASE_BOUND')
    return {
        'schema':SCHEMA,
        'month':'202606','rank':rank,
        'case_sha256':row['case_sha256'],
        'source_receipt_sha256':source_sha,
        'gold_exposed':False,
        'result':result,
        'evaluated_utc':datetime.now(timezone.utc).isoformat()
    }

def main():
    p=ArgumentParser()
    for arg in ('private','reader','key','module-dir','journal'):
        p.add_argument('--'+arg,required=True,type=Path)
    p.add_argument('--start',type=int,default=0)
    p.add_argument('--count',type=int,default=15)
    p.add_argument('--workers',type=int,default=2)
    a=p.parse_args()
    if not 0<=a.start<100 or not 1<=a.count<=100 or not 1<=a.workers<=2:
        p.error('Invalid sample batch boundaries')
    source,source_sha,modules=load_blind(
        a.private,a.reader,a.key.read_bytes(),a.module_dir)
    done={}
    if a.journal.exists():
        for line in a.journal.read_bytes().splitlines():
            if not line:continue
            item=json.loads(line)
            rank=item['rank']
            if (item['schema']!=SCHEMA or rank in done or rank not in SAMPLE
                or item['case_sha256']!=source['results'][rank-1]['case_sha256']
                or item['source_receipt_sha256']!=source_sha
                or item['gold_exposed'] is not False):
                raise ValueError('BLIND_JUNE_AUTHOR_JOURNAL_INVALID')
            done[rank]=item
    selected=SAMPLE[a.start:a.start+a.count]
    todo=[(rank,source['results'][rank-1]) for rank in selected if rank not in done]
    a.journal.parent.mkdir(parents=True,exist_ok=True)
    with a.journal.open('ab') as fp,ThreadPoolExecutor(max_workers=a.workers) as pool:
        jobs={pool.submit(author,rank,row,source_sha,modules[row['module_code']]):rank
              for rank,row in todo}
        for future in as_completed(jobs):
            rec=future.result()
            fp.write(canon(rec)+b'\n')
            fp.flush()
            done[rec['rank']]=rec
            print(json.dumps({'sample_position':list(SAMPLE).index(rec['rank'])+1,
              'rank':rec['rank'],'status':rec['result']['status'],
              'domain':rec['result']['domain'],
              'attempts':rec['result']['attempts']}),flush=True)
    print('BATCH_DONE',json.dumps({
      'selected_this_batch':len(selected),'sample_total':len(done),
      'statuses':dict(Counter(x['result']['status'] for x in done.values()))}))
if __name__=='__main__':main()

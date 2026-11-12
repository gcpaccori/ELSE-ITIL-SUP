"""Public aggregate of blinded Qwen9B 10-per-month sample and separate Qwen4B judgement."""
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path
from hashlib import sha256
from qa.monthend2026.evaluate_monthend import verify_one

SAMPLE=(1,12,23,34,45,56,67,78,89,100)
def score(private:Path,reader:Path,key:bytes,authors_file:Path,judges_file:Path)->dict:
    authors=[json.loads(x) for x in authors_file.read_text(encoding='utf-8').splitlines() if x.strip()]
    judges=[json.loads(x) for x in judges_file.read_text(encoding='utf-8').splitlines() if x.strip()]
    if len(authors)!=90 or len(judges)!=90:
        raise ValueError('NINETY_SAMPLE_INCOMPLETE')
    author_by={(x['month'],x['rank']):x for x in authors}
    judge_by={(x['month'],x['rank']):x for x in judges}
    if len(author_by)!=90 or len(judge_by)!=90:
        raise ValueError('MONTHLY_SAMPLE_DUPLICATED')
    source_sha=sha256(reader.read_bytes()).hexdigest()
    months={}
    for month in range(1,10):
        ym=f'2026{month:02}'
        src,s_hash=verify_one(private/f'monthend_{ym}.private.json',key,source_sha,
              'else.itil.qa.2026-monthend100-source.v1',
              'else.itil.qa.2026-monthend100-source-hmac.v1')
        gold,_=verify_one(private/f'monthend_{ym}_history.private.json',key,source_sha,
              'else.itil.qa.2026-monthend100-history.v1',
              'else.itil.qa.2026-monthend100-history-hmac.v1')
        if src['selected']!=100 or len(gold['historical_records'])!=100:
            raise ValueError('MONTHLY_SAMPLE_SOURCE_NOT_HUNDRED')
        c=Counter()
        for rank in SAMPLE:
            keypair=(ym,rank)
            a=author_by.pop(keypair,None)
            j=judge_by.pop(keypair,None)
            req=src['results'][rank-1]
            h=gold['historical_records'][rank-1]
            if (not a or not j or
                len({req['case_sha256'],h['case_sha256'],a['case_sha256'],j['case_sha256']})!=1 or
                a['source_receipt_sha256']!=s_hash or
                a['gold_exposed'] is not False or
                j['author_no_historical_gold'] is not True):
                raise ValueError('MONTHLY_SAMPLE_CASE_SOURCE_NOT_BOUND')
            c['sample_n']+=1
            c['author_'+a['result']['status']]+=1
            c['judge_'+j['status']]+=1
            if j['status']=='PROVISIONAL_JUDGE_PASS':
                x=j['judge']
                if x['evidence_quote'] and x['evidence_quote'] not in h['historical_solution_redacted']:
                    raise ValueError('JUDGE_QUOTE_UNGROUNDED')
                if (x['plan_alignment']=='SAME_MECHANISM' and
                    (x['history_quality']!='SPECIFIC_ACTION' or not x['evidence_quote'])):
                    raise ValueError('JUDGE_MECHANISM_UNGROUNDED')
                c['historical_quality_'+x['history_quality']]+=1
                c['provisional_alignment_'+x['plan_alignment']]+=1
        months[f'2026-{month:02d}']=dict(sorted(c.items()))
    if author_by or judge_by:
        raise ValueError('EXTRANEOUS_SAMPLE_CASES')
    total=Counter()
    for c in months.values():total.update(c)
    return {
      'schema':'else.itil.qa.2026-monthend90-llm-sampled-comparison.v1',
      'universe_last100_per_month':900,
      'month_count_with_real_data':9,
      'qwen9b_author_samples':90,
      'sample_ranks_per_month':list(SAMPLE),
      'author_model':'else-itil-riv-qwen9b-gpu6',
      'independent_evaluator':'qwen35-4b',
      'independent_judge_provisional_not_ground_truth':True,
      'not_a_nine_hundred_llm_plan_experiment':True,
      'author_never_saw_gold':True,
      'business_changes':0,'repairs_certified':0,
      'months':months,'totals':dict(sorted(total.items()))
    }
def main():
    p=argparse.ArgumentParser()
    for field in ('private','reader','key','authors','judges','output'):
        p.add_argument('--'+field,required=True,type=Path)
    a=p.parse_args()
    report=score(a.private,a.reader,a.key.read_bytes(),a.authors,a.judges)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for month,values in report['months'].items():
      print(month,values)
    print('TOTAL',report['totals'])
if __name__=='__main__':main()

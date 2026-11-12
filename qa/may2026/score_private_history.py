"""Compare sealed, blind 2026-05 cohort plans to independently fetched ITIL history.

Reads private signed QA receipts and private model/evaluator files, writes
aggregate-only evidence suitable for a public PR. No incident descriptions,
person identifiers, SQL, case ids or solution text are included in the report.
This proves data binding, not semantic accuracy of the smaller LLM judge.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
from pathlib import Path
import hmac
import json

COHORTS=(
    ('may_first100','MayFirst100Read.cs'),
    ('may_next100','MayNext100Read.cs'),
    ('may_third100','MayThird100Read.cs'),
    ('may_fourth100','MayFourth100Read.cs'),
)
VALID_MODEL={'FUNCTIONAL_DRAFT_CONTRACT_PASS','CLARIFICATION_REQUIRED','FUNCTIONAL_DRAFT_REJECTED','EXECUTION_FAILED'}
VALID_JUDGE={'JUDGE_PROVISIONAL_PASS','JUDGE_REJECTED'}
VALID_HISTORY={'SPECIFIC_TECHNICAL_ACTION','GENERIC_CLOSURE_NOTE','UNCLEAR'}
VALID_ALIGN={'RELEVANT_DIAGNOSTIC_CHECKS','PARTIALLY_RELEVANT','UNRELATED_CHECKS','NO_VALID_MODEL_PLAN','NOT_EVALUABLE'}

def digest(data:bytes)->str:
    return sha256(data).hexdigest()

def load_json(path:Path):
    return json.loads(path.read_bytes())

def load_journal(path:Path)->dict[int,dict]:
    rows=[json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]
    ranks=[x["rank"] for x in rows]
    if len(ranks)!=len(set(ranks)) or any(type(i) is not int or i not in range(1,101) for i in ranks):
        raise ValueError('DUPLICATED_OR_INVALID_CASE_RANK')
    return {r["rank"]:r for r in rows}

def verify_receipt(private:Path, qa:Path, key:bytes, name:str, code:str, *,history=False):
    suffix='_history' if history else ''
    body_file=private/f'{name}{suffix}.private.json'
    proof_file=private/f'{name}{suffix}.private.json.proof.json'
    body=body_file.read_bytes()
    data=json.loads(body)
    proof=load_json(proof_file)
    actual_code=digest((qa/code).read_bytes())
    assert proof['source_sha256']==data['source_sha256']==actual_code
    assert proof['receipt_sha256']==digest(body)
    assert proof['read_only'] is True
    assert data.get('schema','').startswith(f'else.itil.qa.may2026-')
    sig=f"{data['schema']}:{actual_code}:{digest(body)}".encode()
    assert len(key)==32 and hmac.compare_digest(
        hmac.new(key,sig,'sha256').hexdigest(),proof['hmac_sha256'])
    return data,digest(body)

def summarize_judge(predictions:dict,judge:dict)->dict:
    counts=Counter()
    for rank in range(1,101):
        p=predictions[rank];j=judge[rank]
        assert p['case_sha256']==j['case_sha256']
        status=p['result']['status']
        assert status in VALID_MODEL
        counts['model_'+status]+=1
        assert p['historical_gold_exposed'] is False
        assert j['historical_solution_not_shown_to_author_model'] is True
        assert j['status'] in VALID_JUDGE
        counts['judge_'+j['status']]+=1
        if j['status']=='JUDGE_REJECTED':
            continue
        r=j['judge_output']
        assert r['history_actionability'] in VALID_HISTORY
        assert r['plan_vs_history'] in VALID_ALIGN
        counts['history_'+r['history_actionability']]+=1
        counts['alignment_'+r['plan_vs_history']]+=1
        if status!='FUNCTIONAL_DRAFT_CONTRACT_PASS':
            assert r['plan_vs_history']=='NO_VALID_MODEL_PLAN'
        if status=='FUNCTIONAL_DRAFT_CONTRACT_PASS' and r['history_actionability']=='SPECIFIC_TECHNICAL_ACTION':
            counts['model_pass_specific_history']+=1
            if r['plan_vs_history']=='RELEVANT_DIAGNOSTIC_CHECKS':
                counts['specific_related_candidates']+=1
                if r['quote_grounded'] and r['history_evidence_quote']:
                    counts['literal_quote_grounded_candidates']+=1
                    if r['confidence']=='HIGH':
                        counts['literal_grounded_high_confidence_candidates']+=1
        if status=='FUNCTIONAL_DRAFT_CONTRACT_PASS' and r['plan_vs_history']=='UNRELATED_CHECKS':
            counts['valid_plan_unrelated']+=1
    counts['total']=100
    return dict(sorted(counts.items()))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--private',type=Path,required=True)
    ap.add_argument('--signing-key',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    qa=Path(__file__).resolve().parent
    key=args.signing_key.read_bytes()
    assert len(key)==32
    cohorts={}
    hashes=set()
    entries={}
    for index,(prefix,code) in enumerate(COHORTS,1):
        current,source_sha=verify_receipt(args.private,qa,key,prefix,code)
        gold,gold_sha=verify_receipt(args.private,qa,key,prefix,code,history=True)
        assert current['selected']==100 and len(current['results'])==100
        assert current['month_records']==1714
        assert gold['historical_count']==100 and len(gold['historical_records'])==100
        assert current['history_or_resolution_read'] is False
        assert gold['solutions_not_in_model_input'] is True
        assert gold['cohort_source_sha256']==source_sha
        assert current['business_modifications']==0
        for row,answer in zip(current['results'],gold['historical_records']):
            assert row['case_sha256']==answer['case_sha256']
            assert row['opened_at'][:7]=='2026-05'
            assert row['historical_solution_not_read'] is True
            assert row['case_sha256'] not in hashes
            hashes.add(row['case_sha256'])
        cohorts[str(index)]={
          'rank_range_in_month':[1+(index-1)*100,index*100],
          'sql_records':100,'source_receipt_sha256':source_sha,
          'history_receipt_sha256':gold_sha,'history_nonempty':gold['historical_nonempty'],
          'first_date':current['results'][0]['opened_at'][:10],
          'last_date':current['results'][-1]['opened_at'][:10],
          'record_identity_verified':True,
        }
        entries[prefix]=current
    assert len(hashes)==400
    baseline=load_journal(args.private/'may100_blind_model.private.jsonl')
    improved=load_journal(args.private/'may100_module_ontology_replay.private.jsonl')
    fresh=load_journal(args.private/'may_fourth100_blind_predictions.private.jsonl')
    judge=load_journal(args.private/'may_fourth100_historical_judge.private.jsonl')
    assert len(baseline)==len(improved)==len(fresh)==len(judge)==100
    for rank in range(1,101):
        first=entries['may_first100']['results'][rank-1]['case_sha256']
        fourth=entries['may_fourth100']['results'][rank-1]['case_sha256']
        assert baseline[rank]['case_sha256']==improved[rank]['case_sha256']==first
        assert fresh[rank]['case_sha256']==judge[rank]['case_sha256']==fourth
        assert fresh[rank]['blind_source_sha256']==cohorts['4']['source_receipt_sha256']
        assert judge[rank]['history_sha256']==load_json(args.private/'may_fourth100_history.private.json')['historical_records'][rank-1]['historical_solution_sha256']
    before=Counter(x['result']['status'] for x in baseline.values())
    after=Counter(x['result']['status'] for x in improved.values())
    fresh_counts=Counter(x['result']['status'] for x in fresh.values())
    fresh_known=sum(x['route_domain']!='UNKNOWN' for x in fresh.values())
    assert before['FUNCTIONAL_DRAFT_CONTRACT_PASS']==56 and after['FUNCTIONAL_DRAFT_CONTRACT_PASS']==97
    assert fresh_counts['FUNCTIONAL_DRAFT_CONTRACT_PASS']==85 and fresh_known==88
    history=summarize_judge(fresh,judge)
    report={
      'schema':'else.itil.qa.may2026-four-cohorts-historical-comparison.v1',
      'purpose':'functional diagnosis vs corporate historical procedures; NOT autonomous execution',
      'qa_source':'ELSE70/dbITIL_D/dbo.taIncidente',
      'qa_month':'2026-05',
      'qa_month_total':1714,
      'cohort_selection':'FechaSolicitud ASC, CodigoIncidente ASC; contiguous non-overlapping 100-record pages',
      'distinct_qa_incidents':400,
      'corp_qa_receipts_hmac_verified':8,
      'all_private_case_keys_unique':True,
      'historical_solutions_hidden_from_author_model':True,
      'business_modifications':0,
      'development_cohort':{
        'cases':100,'old_valid_plans':before['FUNCTIONAL_DRAFT_CONTRACT_PASS'],
        'replay_valid_plans':after['FUNCTIONAL_DRAFT_CONTRACT_PASS'],
        'replay_unknown':after['CLARIFICATION_REQUIRED'],
        'replay_rejected':after['FUNCTIONAL_DRAFT_REJECTED'],
        'disposition':'regression-only; cohort used to design the routing ontology',
      },
      'untouched_fourth_cohort':{
        'cases':100,'recognized_domain':fresh_known,
        'valid_plan':fresh_counts['FUNCTIONAL_DRAFT_CONTRACT_PASS'],
        'needs_clarification':fresh_counts['CLARIFICATION_REQUIRED'],
        'draft_rejected':fresh_counts['FUNCTIONAL_DRAFT_REJECTED'],
        'historical_judge':history,
        'disposition':'fresh at time of first blind evaluation; subsequent history review means no longer untouched',
      },
      'cohorts':cohorts,
      'methodology':{
        'evaluating_author_model':'qwen35-9b (blind)',
        'historical_judge':'qwen35-4b (independent model; provisional comparisons)',
        'quote_grounding':'exact normalized substring of historical note, not semantic proof',
        'no_claim_of_ground_truth_procedure_accuracy':True,
        'manual_error_examples_audited':True,
        'root_causes_independently_verified':0,
        'repairs_e2e_verified':0,
        'notes':'Historical SQL snippets describe what was written in ticket, not necessarily executed; do not turn SQL comments into performed changes.'
      }
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({
      'unique':400,'hmac_verified':8,
      'baseline_plans':56,'replay_plans':97,'fresh_plans':85,
      'fresh_domain_known':88,'specific_historical':history.get('history_SPECIFIC_TECHNICAL_ACTION'),
      'specific_candidate':history.get('specific_related_candidates'),
      'quote_supported_candidate':history.get('literal_quote_grounded_candidates'),
      'matched_cause_independently_verified':0
    },ensure_ascii=False))

if __name__=='__main__':
    main()

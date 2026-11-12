"""Publish aggregate-only June 2026 Qwen9B vs Qwen4B historical evaluation.

Compare source, model author & independent judge on the same systematic 100
HMAC-bound cases; reject quote drift, cross-case, duplicate and false repair
claims. Judges are provisional, historical SQL isn't execution. No private
note or individual case is exported to repo.
"""
from __future__ import annotations
from argparse import ArgumentParser
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

from qa.monthend2026.evaluate_monthend import verify_one
from qa.monthend2026.score_history_labels import distinguish_evidence_quote
from qa.june2026.run_blind_qwen_sample import SAMPLE,SCHEMA as AUTHOR_SCHEMA

SCHEMA='else.itil.qa.2026-juneall-100-llm-historical-eval.v1'
JUDGE_SCHEMA='else.itil.qa.2026-monthend-qwen4b-historical-evaluation.v1'
ALIGNS={'SAME_MECHANISM','PARTIAL_PROCESS_MATCH','UNRELATED','NOT_EVALUABLE','NO_VALID_PLAN'}
QUALITIES={'SPECIFIC_ACTION','GENERIC_CLOSURE','EMPTY_OR_UNCLEAR'}

def audit(private:Path,reader:Path,key:bytes,authors:Path,judges:Path)->dict:
    source_sha=sha256(reader.read_bytes()).hexdigest()
    source,source_hash=verify_one(private/'juneall_202606.private.json',
        key,source_sha,'else.itil.qa.2026-juneall-source.v1',
        'else.itil.qa.2026-juneall-source-hmac.v1')
    gold,gold_hash=verify_one(private/'juneall_202606_history.private.json',
        key,source_sha,'else.itil.qa.2026-juneall-history.v1',
        'else.itil.qa.2026-juneall-history-hmac.v1')
    if (source['selected']!=1621 or gold['historical_count']!=1621
        or gold['cohort_source_sha256']!=source_hash
        or len(source['results'])!=1621 or len(gold['historical_records'])!=1621):
        raise ValueError('JUNE_1621_SOURCE_SCOPE_NOT_VERIFIED')
    a=[json.loads(line) for line in authors.read_text().splitlines() if line.strip()]
    j=[json.loads(line) for line in judges.read_text().splitlines() if line.strip()]
    a_by={}
    j_by={}
    for row in a:
        rank=row['rank']
        if (rank in a_by or rank not in SAMPLE or
            row['schema']!=AUTHOR_SCHEMA or row['gold_exposed'] is not False
            or row['source_receipt_sha256']!=source_hash
            or row['case_sha256']!=source['results'][rank-1]['case_sha256']):
            raise ValueError('AUTHOR_CASE_NOT_FROZEN_SOURCE')
        a_by[rank]=row
    for row in j:
        rank=row['rank']
        if (rank in j_by or rank not in SAMPLE or
            row['schema']!=JUDGE_SCHEMA
            or row['author_no_historical_gold'] is not True
            or row['case_sha256']!=source['results'][rank-1]['case_sha256']):
            raise ValueError('JUDGE_CASE_NOT_FROZEN_SOURCE')
        j_by[rank]=row
    if len(a_by)!=100 or len(j_by)!=100:
        raise ValueError('NOT_ALL_ONE_HUNDRED_PAIRS_COMPLETED')
    counts=Counter()
    domains=Counter()
    for rank in SAMPLE:
        author=a_by[rank]
        reviewer=j_by[rank]
        source_row=source['results'][rank-1]
        note=gold['historical_records'][rank-1]
        if len({author['case_sha256'],reviewer['case_sha256'],
                source_row['case_sha256'],note['case_sha256']})!=1:
            raise ValueError('JUNE_SAMPLE_CASES_MISBOUND')
        result=author['result']
        if (result['repair_certified'] is not False
            or result['historical_resolution_exposed'] is not False
            or result['case_sha256']!=author['case_sha256']):
            raise ValueError('AUTHOR_INCORRECTLY_CLAIMED_EXECUTION_OR_GOLD')
        status=result['status']
        if status not in ('FUNCTIONAL_DRAFT_CONTRACT_PASS','CLARIFICATION_REQUIRED',
                          'FUNCTIONAL_DRAFT_REJECTED','MODEL_CALL_FAILED'):
            raise ValueError('AUTHOR_STATUS_NOT_PERMITTED')
        counts['sampled_cases']+=1
        counts['author_'+status]+=1
        domains[result['domain']]+=1
        counts['sample_history_nonempty']+=bool(note['historical_solution_redacted'].strip())
        if reviewer['status']=='JUDGE_REJECTED':
            counts['judge_rejected']+=1
            continue
        if reviewer['status']!='PROVISIONAL_JUDGE_PASS':
            raise ValueError('JUDGE_NOT_VALID_STATUS')
        counts['judge_schema_and_quote_verified']+=1
        jval=reviewer['judge']
        if (jval['history_quality'] not in QUALITIES
            or jval['plan_alignment'] not in ALIGNS
            or jval['confidence'] not in ('HIGH','MEDIUM','LOW')
            or type(jval['evidence_quote']) is not str
            or len(jval['evidence_quote'])>140
            or (jval['evidence_quote'] and
                jval['evidence_quote'] not in note['historical_solution_redacted'])):
            raise ValueError('JUDGE_LITERAL_QUOTE_OR_ENUM_NOT_SUPPORTED')
        counts['judge_history_quality_'+jval['history_quality']]+=1
        counts['judge_alignment_'+jval['plan_alignment']]+=1
        if status!='FUNCTIONAL_DRAFT_CONTRACT_PASS' and jval['plan_alignment']!='NO_VALID_PLAN':
            raise ValueError('JUDGE_NONPASS_AUTHOR_PROMOTED')
        if not note['historical_solution_redacted'].strip() and jval['history_quality']!='EMPTY_OR_UNCLEAR':
            raise ValueError('JUDGE_EMPTY_GOLD_FALSE_SPECIFIC')
        if jval['plan_alignment']=='SAME_MECHANISM':
            if (status!='FUNCTIONAL_DRAFT_CONTRACT_PASS'
                or jval['history_quality']!='SPECIFIC_ACTION'
                or not jval['evidence_quote']):
                raise ValueError('JUDGE_FALSE_SAME_MECHANISM')
            counts['provisional_specific_mechanism_documentary_overlap']+=1
            kind=distinguish_evidence_quote(jval['evidence_quote'])
            counts['provisional_same_mechanism_quote_'+kind]+=1
        if jval['history_quality']=='SPECIFIC_ACTION':
            counts['specific_history_note_with_literal_quote']+=bool(jval['evidence_quote'])
    if counts['sampled_cases']!=100:
        raise ValueError('SAMPLE_CARDINALITY_INVALID')
    return {
      'schema':SCHEMA,
      'month':'2026-06','universe_all_june_incidents':1621,
      'sample_strategy':'100_SYSTEMATIC_POSITIONS_OVER_ALL_1621',
      'sample_positions':list(SAMPLE),
      'sample_completed':100,
      'source_receipt_sha256':source_hash,'history_receipt_sha256':gold_hash,
      'author_model':'Qwen3.5-9B',
      'independent_judge_model':'Qwen3.5-4B',
      'all_author_cases_blind_to_historical_gold':True,
      'all_judge_quotes_extracted_from_exact_signed_notes':True,
      'judge_provisional_not_human_ground_truth':True,
      'author_contract_pass_does_not_equal_historical_accuracy':True,
      'sql_in_historical_note_does_not_prove_execution':True,
      'no_independent_domain_business_state_or_repair_validation':True,
      'business_repair_certified':0,'business_writes_executed':0,
      'counts':dict(sorted(counts.items())),
      'sample_domain_counts':dict(sorted(domains.items())),
    }

def main():
    p=ArgumentParser()
    for name in ('private','reader','key','authors','judges','output'):
        p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args()
    result=audit(a.private,a.reader,a.key.read_bytes(),a.authors,a.judges)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('JUNE_BLIND_100_CONTRAST',json.dumps(result['counts'],ensure_ascii=False))
if __name__=='__main__':main()

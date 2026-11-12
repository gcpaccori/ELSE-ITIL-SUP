"""Reproducible case-bound QA field-evidence scoring for frozen 90 Qwen plans.

Never reads historical GOLD; only the signed NEW physical exact-row evidence,
the separately signed month source receipts and blind author plans. The
private per-case ledger is not committed, only month aggregate metrics.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from hashlib import sha256
from pathlib import Path

from else_dominance.qa_case_state_evidence import (
    CASE_FIELDS,SOURCE,VerifiedCaseStateIndex,verify_claim)
from qa.monthend2026.evaluate_monthend import verify_one

SCHEMA="else.itil.qa.2026-case-state-90-evidence-gate-summary.v1"
RANKS=(1,12,23,34,45,56,67,78,89,100)

def audit(index:VerifiedCaseStateIndex,month_private:Path,
          month_reader:Path,key:bytes,author_journal:Path)->tuple[dict,dict]:
    author=[json.loads(s) for s in author_journal.read_text().splitlines() if s.strip()]
    author_by={}
    for row in author:
        k=(row['month'],row['rank'])
        if k in author_by or row['gold_exposed'] is not False:
            raise ValueError('MODEL_AUTHOR_NOT_BLIND_OR_DUPLICATE')
        author_by[k]=row
    if len(author_by)!=90:
        raise ValueError('AUTHOR_NINETY_CASES_REQUIRED')
    source_sha=sha256(month_reader.read_bytes()).hexdigest()
    all_cases=set()
    audit_private=[]
    per_month={}
    for month in range(1,10):
        code=f"2026{month:02d}"
        ym=f"2026-{month:02d}"
        source,s_hash=verify_one(
          month_private/f"monthend_{code}.private.json",key,source_sha,
          "else.itil.qa.2026-monthend100-source.v1",
          "else.itil.qa.2026-monthend100-source-hmac.v1")
        counts=Counter()
        for rank in RANKS:
            x=author_by.pop((code,rank))
            req=source['results'][rank-1]
            case=req['case_sha256']
            if x['case_sha256']!=case or x['source_receipt_sha256']!=s_hash or case in all_cases:
                raise ValueError('AUTHOR_AND_QA_RECEIPT_NOT_BOUND')
            all_cases.add(case)
            obs={}
            for field in CASE_FIELDS:
                result=index.inspect(case_sha256=case,module_code=req['module_code'],
                                     as_of=req['opened_at'],field=field)
                if result['status']!='READ_VERIFIED_QA_SNAPSHOT':
                    raise ValueError('SIGNED_CASE_FIELD_READ_NOT_VERIFIED')
                obs[field]=result
                assert result['row_count']==1 and result['provenance_verified'] is True
                # Construct a native full fact claim; do not use guessed values
                claim={
                   'case_sha256':case,'module_code':req['module_code'],
                   'as_of':req['opened_at'],
                   'source':SOURCE,'field':field,
                   'observed_value':result['observed_value'],
                   'receipt_sha256':result['receipt_sha256']}
                test=verify_claim(index,claim)
                if test['status']!='FIELD_VALUE_EXACTLY_VERIFIED_IN_QA_SNAPSHOT':
                    raise ValueError('EXACT_QA_FIELD_BINDING_REJECTED')
            if obs['CodigoEstadoIncidente']['observed_value']!=req['status_code']:
                counts['case_status_drift_since_month_snapshot']+=1
            status=x['result']['status']
            plan=x['result'].get('proposal') or {}
            checks=plan.get('checks',[]) if status=='FUNCTIONAL_DRAFT_CONTRACT_PASS' else []
            if type(checks) is not list:checks=[]
            counts['cases']+=1
            counts['itil_fields_verified']+=len(obs)
            counts['author_'+status]+=1
            counts['model_proposed_checks']+=len(checks)
            counts['model_checks_without_business_object_qa_proof']+=len(checks)
            counts['verified_business_object_join']+=0
            counts['model_causal_repair_claims_certified']+=0
            counts['historical_procedures_verified_executed']+=0
            audit_private.append({
                'month':ym,'rank':rank,'case_sha256':case,
                'status':status,
                'qa_state_receipt_sha256':index.receipt_sha256,
                'itil_verified_fields':sorted(obs),
                'field_observations_verified':len(obs),
                'model_proposed_checks':len(checks),
                'model_domain_checks_unverified':len(checks),
                'business_domain_link_proven':False,
                'root_cause_certified':False,
                'repairs_certified':False,
            })
        per_month[ym]=dict(sorted(counts.items()))
    if author_by or len(all_cases)!=90:
        raise ValueError('MODEL_UNMATCHED_OR_CROSS_BOUND_CASES')
    total=Counter()
    for m in per_month.values():total.update(m)
    report={
      'schema':SCHEMA,'qa_source':SOURCE,
      'case_state_receipt_sha256':index.receipt_sha256,
      'case_count':90,
      'months':9,
      'signed_source_month_receipts':9,
      'case_field_proof_count':total['itil_fields_verified'],
      'itil_observation_not_business_domain_relation':True,
      'case_state_observed_at_utc':index.read_utc.isoformat(),
      'historical_gold_hidden_from_proposal_generator':True,
      'model_author_plan_checks_not_assumed_executed':True,
      'cause_certified':0,'business_repairs_certified':0,
      'business_domain_links_verified':0,'business_modifications':0,
      'months_summary':per_month,'totals':dict(sorted(total.items()))
    }
    return report,{'schema':SCHEMA,'cases':audit_private}

def main():
    p=argparse.ArgumentParser()
    for key in ('case-private','case-source','month-private','month-source',
                'key','authors','output','private-ledger'):
        p.add_argument('--'+key,required=True,type=Path)
    args=p.parse_args()
    key=args.key.read_bytes()
    index=VerifiedCaseStateIndex(
        private_root=args.case_private,source_file=args.case_source,
        month_private=args.month_private,month_source=args.month_source,
        key_file=args.key)
    report,ledger=audit(index,args.month_private,args.month_source,key,args.authors)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    args.private_ledger.parent.mkdir(parents=True,exist_ok=True)
    args.private_ledger.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
    args.private_ledger.chmod(0o600)
    print(json.dumps({
       'cases':report['case_count'],
       'exact_qa_fields':report['case_field_proof_count'],
       'model_checks':report['totals']['model_proposed_checks'],
       'unverified_domain_checks':report['totals']['model_checks_without_business_object_qa_proof'],
       'business_domain_links_verified':0,
       'causes_certified':0,'repairs_certified':0
    }))
if __name__=='__main__':main()

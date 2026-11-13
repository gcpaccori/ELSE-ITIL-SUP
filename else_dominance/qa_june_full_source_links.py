"""Read-only, retrospectively verified 1,621-ticket June business-PK graph.

The evidence was observed in ELSE70 QA in November, NOT at incident time.
All 1,621 cases were chosen without historical solution labels. Any tool
use requires an explicit operator-controlled retrospective QA flag.
No raw business PK is exposed to CLI/LLM, and no row is deemed causal.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import date,datetime,time
from hashlib import sha256
from pathlib import Path
import json,re

from qa.monthend2026.evaluate_monthend import verify_one
from qa.june2026_full_link.build_signed_june1621_links import (
    build,LINK_SCHEMA,LINK_PROOF,PUBLIC_SCHEMA
)

SHA=re.compile(r'^[0-9a-f]{64}$')
DATE=re.compile(r'^2026-06-\d\d(?:T\d\d:\d\d(?::\d\d)?)?$')

def need(ok,why):
    if not ok:raise ValueError(why)

class VerifiedJuneFullBusinessGraph:
    def __init__(self,*,repo:Path|str,private:Path|str,
                 june_source:Path|str,key_file:Path|str):
        self.repo=Path(repo)
        self.private=Path(private)
        self.key_file=Path(key_file)
        expected,report=build(self.repo,self.private,Path(june_source),self.key_file)
        actual,digest=verify_one(
            self.private/'june1621_verified_case_graph.private.json',
            self.key_file.read_bytes(),
            sha256((self.repo/'qa/june2026_full_link/build_signed_june1621_links.py').read_bytes()).hexdigest(),
            LINK_SCHEMA,LINK_PROOF
        )
        need(actual==expected,'FULL_GRAPH_SIGNED_PAYLOAD_NOT_DERIVED_FROM_QA')
        report['private_graph_receipt_sha256']=digest
        pinned=json.loads(
          (self.repo/'data/2026_june1621_source_only_link_graph.json').read_text())
        need(report==pinned,'FULL_GRAPH_PUBLIC_SUMMARY_DRIFT')
        self.cases={}
        self.key_occurrences=defaultdict(list)
        for case in actual['linked_cases']:
            key=case['case_sha256']
            need(type(key) is str and SHA.fullmatch(key) is not None
              and key not in self.cases
              and case['logical_object_count']==len(case['links'])
              and case['no_object_primary_assumed'] is True
              and case['historical_business_state_unproven'] is True,
              'FULL_GRAPH_CASE_SCOPE_INVALID')
            self.cases[key]=case
            for item in case['links']:
                internal=(item['kind'],item['business_pk_sha256'])
                self.key_occurrences[internal].append((
                    key,case['module_code'],item['handle']
                ))
        need(len(self.cases)==1621 and
             sum(len(x['links']) for x in self.cases.values())==1491 and
             len(self.key_occurrences)==1236,'FULL_GRAPH_INDEX_COUNTS_INVALID')
        self.qa_observed_at_utc=actual['qa_observed_at_utc']
        self.receipt_sha256=digest
        self.summary_counts=report

    def _case(self,*,case_sha256:str,module_code:str,as_of:str,retrospective_qa:bool):
        if retrospective_qa is not True:
            return None,'RETROSPECTIVE_QA_EXPLICIT_AUTHORIZATION_REQUIRED'
        if (type(case_sha256) is not str or SHA.fullmatch(case_sha256) is None
            or type(module_code) is not str or not module_code
            or type(as_of) is not str or DATE.fullmatch(as_of) is None):
            return None,'EXACT_JUNE_2026_SIGNED_CASE_SCOPE_REQUIRED'
        try:
            stamp=date.fromisoformat(as_of[:10])
        except ValueError:
            return None,'EXACT_JUNE_2026_SIGNED_CASE_SCOPE_REQUIRED'
        row=self.cases.get(case_sha256)
        if row is None or row['module_code']!=module_code:
            return None,'CASE_NOT_IN_SIGNED_JUNE_COHORT_OR_MODULE_MISMATCH'
        try:
            ticket_opened=datetime.fromisoformat(row['opened_at'])
            if 'T' in as_of:
                requested_time=datetime.fromisoformat(as_of)
            else:
                # Date-only retrospective lookup means end of that local day.
                requested_time=datetime.combine(stamp,time(23,59,59))
        except ValueError:
            return None,'EXACT_JUNE_2026_SIGNED_CASE_SCOPE_REQUIRED'
        if requested_time<ticket_opened:
            return None,'REQUESTED_AS_OF_BEFORE_INCIDENT_OPENED'
        return row,None

    def inspect(self,*,case_sha256:str,module_code:str,as_of:str,
                view:str='summary',retrospective_qa:bool=False)->dict:
        case,err=self._case(case_sha256=case_sha256,
                            module_code=module_code,
                            as_of=as_of,retrospective_qa=retrospective_qa)
        if err:return {'status':'BLOCKED','error':err}
        if view not in ('summary','objects','overlaps'):
            return {'status':'BLOCKED','error':'FULL_GRAPH_VIEW_NOT_ALLOWLISTED'}
        links=case['links']
        count=len(links)
        status=('NO_SAME_BRANCH_QA_PRIMARY_KEY' if count==0
                else 'SINGLE_LOGICAL_PK_RETROSPECTIVE' if count==1
                else 'MULTIPLE_LOGICAL_PKS_PRIMARY_UNDETERMINED')
        by_kind=Counter(x['kind'] for x in links)
        shared=[(item,len(self.key_occurrences[(item['kind'],item['business_pk_sha256'])]))
                for item in links]
        cross_module=sum(len({
           m for _,m,_ in self.key_occurrences[(item['kind'],item['business_pk_sha256'])]
           })>1 for item in links)
        reply={
           'status':status,
           'case_sha256':case_sha256,
           'module_code':module_code,
           'qa_period':'2026-06',
           'original_incident_opened_at':case['opened_at'],
           'retrospective_qa_only':True,
           'business_data_observed_at_utc':self.qa_observed_at_utc,
           'business_state_at_incident_time_verified':False,
           'source_receipt_sha256':self.receipt_sha256,
           'link_evidence':'ORIGINAL_REQUEST_NUMBER_EQUALS_QA_PRIMARY_KEY_AND_BRANCH',
           'business_candidate_count':count,
           'business_candidate_types':dict(sorted(by_kind.items())),
           'cross_type_candidates_need_review':len(by_kind)>1,
           'multiple_candidates_no_primary_inferred':count>1,
           'shared_business_key_count':sum(n>1 for _,n in shared),
           'shared_across_modules_count':cross_module,
           'sql_native_fk_verified':False,
           'application_semantic_link_verified':False,
           'causal_business_fix_verified':False,
           'business_mutations':0,
           'read_only':True
        }
        if view=='objects':
            reply['object_handles']=[
                {'handle':v['handle'],'kind':v['kind'],
                 'source_databases':v['source_databases'],
                 'source_count':len(v['source_databases']),
                 'business_branch_matches_itil':True,
                 'reused_in_other_tickets':len(self.key_occurrences[
                     (v['kind'],v['business_pk_sha256'])])>1,
                 'source_authority_proven':False,
                 'specific_object_causality_proven':False}
                for v in links
            ]
        elif view=='overlaps':
            reply['overlap_summary']={
                'objects_used_by_multiple_tickets':sum(n>1 for _,n in shared),
                'objects_used_by_multiple_modules':cross_module,
                'max_tickets_for_one_object':max((n for _,n in shared),default=0),
                'source_copy_relation_count':sum(len(item['source_databases'])-1
                                                  for item in links),
                'other_ticket_identities_not_disclosed':True,
                'overlap_does_not_certify_common_cause':True
            }
        return reply

    def public_summary(self)->dict:
        return dict(self.summary_counts)

"""Verified, scoped, read-only ITIL ticket → business object link registry.

Only a *verified observational key match*, not a native SQL foreign key,
application transaction, historical state or chosen primary object.

Tool presentations never expose raw business primary keys. A downstream
authorized connector may resolve a handle inside this private trust boundary,
but that method is not registered as an LLM/CLI tool.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from datetime import date
import json,re

from qa.monthend2026.evaluate_monthend import verify_one
from qa.june2026_link.build_verified_ticket_links import (
    construct,SCHEMA,PROOF,SUMMARY
)

HASH=re.compile(r'^[0-9a-f]{64}$')
def need(predicate,error):
    if not predicate:raise ValueError(error)

class VerifiedTicketBusinessLinks:
    def __init__(self,*,repo:Path|str,private:Path|str,
                 request_private:Path|str,prior_private:Path|str,
                 june_private:Path|str,key_file:Path|str):
        self.repo=Path(repo)
        self.private=Path(private)
        self.key_file=Path(key_file)
        expected,public=construct(self.repo,self.private,Path(request_private),
                                  Path(prior_private),Path(june_private),self.key_file)
        actual,receipt_sha=verify_one(
           self.private/'verified_ticket_business_links.private.json',
           self.key_file.read_bytes(),
           sha256((self.repo/'qa/june2026_link/build_verified_ticket_links.py').read_bytes()).hexdigest(),
           SCHEMA,PROOF)
        need(actual==expected,'LINK_REGISTRY_DOES_NOT_MATCH_SIGNED_QA_SOURCES')
        public['private_registry_receipt_sha256']=receipt_sha
        pinned=json.loads((self.repo/'data/2026_june57_verified_ticket_business_links.json').read_text())
        need(public==pinned,'LINK_PUBLIC_AGGREGATE_NOT_BOUND_TO_SIGNED_QA')
        need(len(actual['cases'])==57,'LINK_REGISTRY_NOT_57_CASES')
        self.cases={}
        for record in actual['cases']:
            case_sha=record['case_sha256']
            need(HASH.fullmatch(case_sha) is not None
               and case_sha not in self.cases
               and record['object_count']==len(record['links'])
               and record['primary_business_object_not_inferred'] is True
               and record['business_fix_not_inferred'] is True,
               'LINK_BAD_CASE_SCOPE')
            self.cases[case_sha]=record
        self.receipt_sha256=receipt_sha
        self.summary_counts=public
    def _scoped(self,*,case_sha256:str,module_code:str,as_of:str):
        if (type(case_sha256) is not str or HASH.fullmatch(case_sha256) is None
                or type(module_code) is not str or not module_code
                or type(as_of) is not str
                or not re.fullmatch(r'2026-06-\d\d(?:T\d\d:\d\d(?::\d\d)?)?',as_of)):
            return None,'LINK_EXACT_JUNE_CASE_SCOPE_REQUIRED'
        try:
            stamp=date.fromisoformat(as_of[:10])
        except ValueError:
            return None,'LINK_EXACT_JUNE_CASE_SCOPE_REQUIRED'
        if stamp.year!=2026 or stamp.month!=6:
            return None,'LINK_EXACT_JUNE_CASE_SCOPE_REQUIRED'
        row=self.cases.get(case_sha256)
        if row is None or row['module_code']!=module_code:
            return None,'LINK_CASE_NOT_IN_SIGNED_COHORT_OR_MODULE_WRONG'
        return row,None
    def inspect(self,*,case_sha256:str,module_code:str,as_of:str,
                view:str='summary')->dict:
        row,error=self._scoped(case_sha256=case_sha256,module_code=module_code,as_of=as_of)
        if error:return {'status':'BLOCKED','error':error}
        if view not in ('summary','objects'):
            return {'status':'BLOCKED','error':'LINK_ONLY_SUMMARY_OR_OBJECTS_ALLOWED'}
        n=row['object_count']
        status=('UNRESOLVED' if n==0 else 'SINGLE_QA_PK_MATCH'
                if n==1 else 'MULTIPLE_QA_PK_MATCHES_PRIMARY_UNDETERMINED')
        response={
          'status':status,'case_sha256':case_sha256,'module_code':module_code,
          'qa_period':'2026-06','business_category':row['category'],
          'source':'ITIL_ORIGINAL_REQUEST_EQUALS_QA_BUSINESS_PRIMARY_KEY_AND_BRANCH',
          'qa_evidence_links':n,
          'case_has_multiple_objects':n>1,
          'primary_object_selected':False,
          'native_sql_foreign_key_verified':False,
          'application_semantic_relation_certified':False,
          'business_causal_diagnosis_certified':False,
          'historical_fix_certified':False,
          'business_mutations':0,
          'read_only':True,
          'receipt_sha256':self.receipt_sha256,
        }
        if view=='objects':
            # No sensitive identifiers or text. Handles are scoped to the
            # incident and don't grant standalone read/change capabilities.
            response['object_handles']=[
               {'handle':obj['handle'],
                'category':obj['category'],
                'database':obj['source_database'],
                'primary_key_column':obj['pk_column'],
                'business_branch':obj['business_branch'],
                'identifier_sha256':obj['pk_sha256'],
                'source_is_authoritative_transactional_db':False,
                'specific_ticket_intent_certified':False}
               for obj in row['links']
            ]
        return response
    def resolve_for_authorized_reader(self,*,case_sha256:str,module_code:str,
                                      as_of:str,handle:str)->dict:
        """Trust-boundary method, NOT registered as agent or CLI action.

        This returns a raw business PK only for a handle backed by the
        exact signed case/module/source. The caller must separately enforce
        business read-only ACLs; this registry does not execute SQL.
        """
        row,error=self._scoped(case_sha256=case_sha256,module_code=module_code,as_of=as_of)
        if error:raise ValueError(error)
        need(type(handle) is str and HASH.fullmatch(handle) is not None,
             'BUSINESS_HANDLE_INVALID')
        matches=[x for x in row['links'] if x['handle']==handle]
        need(len(matches)==1,'BUSINESS_HANDLE_NOT_IN_SIGNED_CASE')
        link=matches[0]
        return {
          'source_database':link['source_database'],
          'business_table':'taOrdenTrabajo' if link['category']=='OT' else 'taCobranza',
          'business_pk_column':link['pk_column'],
          'business_pk_value_private':link['pk_value_private'],
          'business_branch':link['business_branch'],
          'read_only':True,'no_business_write_permission':True,
          'application_link_still_uncertified':True
        }
    def summary(self)->dict:
        return dict(self.summary_counts)

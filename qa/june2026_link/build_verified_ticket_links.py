"""Construct an exact case-scoped *observational* ITIL→business PK link registry.

No SQL access in this module. Inputs are previously signed corporate QA
read-only receipts; links remain in private 0600 JSON with an HMAC proof.
A link is not a declared FK, an intended main business object or a repair.
"""
from __future__ import annotations
from argparse import ArgumentParser
from collections import Counter,defaultdict
from hashlib import sha256
from pathlib import Path
import hmac,json,os,re
from qa.monthend2026.evaluate_monthend import verify_one
from qa.june2026_identity.score_request_pk_recovery import assess

SCHEMA='else.itil.qa.2026-june57-ticket-business-pk-link-registry.v1'
PROOF='else.itil.qa.2026-june57-ticket-business-pk-link-registry-hmac.v1'
SUMMARY='else.itil.qa.2026-june57-ticket-business-links-public-summary.v1'
NATIVE='else.itil.qa.2026-native-itil-business-link-metadata.v1'
NATIVE_PROOF='else.itil.qa.2026-native-itil-business-link-metadata-hmac.v1'
BULK='else.itil.qa.2026-june57-request-bulk-primary-key-lookup.v1'
BULK_PROOF='else.itil.qa.2026-june57-request-bulk-primary-key-lookup-hmac.v1'
PROFILE='else.itil.qa.2026-june57-request-identity-candidates.v1'
PROFILE_PROOF='else.itil.qa.2026-june57-request-identity-candidates-hmac.v1'
SHA=re.compile(r'^[0-9a-f]{64}$')
VALID_DATABASES={
 'OT':{'dbGerencial_D','dbDistribucion_D'},
 'COLLECTION':{'dbComercial001_Diario'}
}

def require(cond,msg):
    if not cond:raise ValueError(msg)

def verify_sources(repo:Path,private:Path,request_private:Path,
                   prior:Path,june:Path,keyfile:Path):
    report=assess(repo,request_private,prior,june,keyfile)
    key=keyfile.read_bytes()
    def load(folder,name,code,schema,proof):
        return verify_one(folder/name,key,sha256((repo/code).read_bytes()).hexdigest(),schema,proof)
    native,native_sha=load(
       private,'native_itil_link_metadata.private.json',
       'qa/june2026_link/JuneITILNativeLinkSchemaRead.cs',
       NATIVE,NATIVE_PROOF)
    bulk,bulk_sha=load(request_private,'june57_bulk_pk_request_matches.private.json',
       'qa/june2026_identity/June57BulkPrimaryKeyMatch.cs',BULK,BULK_PROOF)
    profile,profile_sha=load(request_private,'june57_request_ids.private.json',
       'qa/june2026_identity/June57RequestIdentifiersRead.cs',PROFILE,PROFILE_PROOF)
    require(
       len(native['inspected_databases'])==14
       and len(native['failed_or_invisible_sources'])==0
       and native['direct_table_same_name_itil_and_ot_or_cobranza_pairs']==0
       and native['itil_taIncidente_foreign_keys']==[]
       and native['codigo_incidente_operativo_is_not_itil_codigo_incidente'] is True
       and native['native_business_fk_not_claimed_without_application_contract'] is True
       and native['read_only'] is True and native['write_count']==0,
       'NATIVE_LINK_QA_METADATA_CONTRACT_NOT_PASSED')
    require(bulk_sha==report['receipt_proofs']['bulk']
       and profile_sha==report['receipt_proofs']['profile']
       and len(bulk['matches'])==619 and len(profile['rows'])==57,
       'LINK_SOURCE_RECEIPTS_NOT_RECONCILED')
    return report,key,native_sha,bulk_sha,profile_sha,bulk,profile

def construct(repo:Path,private:Path,request_private:Path,
              prior:Path,june:Path,keyfile:Path):
    report,key,native_sha,bulk_sha,profile_sha,bulk,profile=verify_sources(
      repo,private,request_private,prior,june,keyfile)
    profiles={x['rank']:x for x in profile['rows']}
    seen=set();links_by_case=defaultdict(list);ids=Counter()
    for hit in bulk['matches']:
        rank=hit['rank'];category=hit['category']
        p=profiles.get(rank)
        value=hit['identifier_private']
        db=hit['found_in_database']
        code_hash=hit['source_candidate_sha256']
        require(p is not None and p['category']==category
          and hit['case_sha256']==p['case_sha256']
          and db in VALID_DATABASES[category]
          and hit['business_branch_equals_itil_branch'] is True
          and hit['business_branch']==hit['itil_branch']==p['itil_branch']
          and sha256(value.encode()).hexdigest()==code_hash
          and len(value)==19 and value.isdecimal()
          and (rank,category,value) not in seen,
          'LINK_OBJECT_KEY_NOT_EXACT_OR_DUPLICATED')
        seen.add((rank,category,value))
        # Stable scoped handle, not a transferable authority token:
        # the registry requires the same ticket SHA + module + period.
        handle=sha256(
          (p['case_sha256']+'|'+category+'|'+db+'|'+value).encode()).hexdigest()
        links_by_case[rank].append({
           'handle':handle,
           'category':category,
           'pk_column':'CodigoOrdenTrabajo' if category=='OT' else 'CodigoCobranza',
           'pk_value_private':value,
           'pk_sha256':code_hash,
           'source_database':db,
           'business_branch':hit['business_branch'],
           'evidence':'SOURCE_TEXT_19_DIGIT_EQUALS_BUSINESS_PK_AND_BRANCH',
           'business_row_seen_on_qa':True,
           'official_foreign_key_verified':False,
           'historical_write_verified':False,
           'business_source_authority_certified':False,
        })
        ids[(category,code_hash)]+=1
    require(len(seen)==619 and len(ids)==525,
            'LINK_REGISTRY_WRONG_SOURCE_RELATION_COUNT')
    cases=[]
    statuses=Counter()
    for rank in sorted(profiles):
        p=profiles[rank];entries=sorted(links_by_case[rank],key=lambda x:x['handle'])
        status=(
          'NO_TYPE_CORRECT_PK_MATCH' if not entries
          else 'SINGLE_MATCHED_OBJECT_NOT_OFFICIAL_FK' if len(entries)==1
          else 'MULTIPLE_MATCHED_OBJECTS_NO_PRIMARY_SELECTED')
        statuses[status]+=1
        cases.append({
          'rank':rank,
          'case_sha256':p['case_sha256'],
          'module_code':p['module_code'],
          'itil_company':p['itil_company'],
          'itil_branch':p['itil_branch'],
          'request_sha256':p['request_sha256'],
          'category':p['category'],
          'status':status,'object_count':len(entries),
          'links':entries,
          'primary_business_object_not_inferred':True,
          'business_fix_not_inferred':True,
        })
    require(
       statuses==Counter({
        'NO_TYPE_CORRECT_PK_MATCH':2,
        'SINGLE_MATCHED_OBJECT_NOT_OFFICIAL_FK':13,
        'MULTIPLE_MATCHED_OBJECTS_NO_PRIMARY_SELECTED':42,
       })
       and sum(len(x['links']) for x in cases)==619
       and sum(x['category']=='OT' for x in cases)==22
       and sum(x['category']=='COLLECTION' for x in cases)==35,
       'LINK_REGISTRY_CARDINALITIES_CHANGED')
    code_sha=sha256((repo/'qa/june2026_link/build_verified_ticket_links.py').read_bytes()).hexdigest()
    payload={
       'schema':SCHEMA,'source_sha256':code_sha,
       'qa_period':'2026-06',
       'source_selection_is_posthoc':True,
       'source_itil_table':'ELSE70/dbITIL_D.dbo.taIncidente',
       'business_link_kind':'EXPLICIT_REQUEST_VALUE_EQUALS_QA_BUSINESS_PRIMARY_KEY',
       'native_sql_fk_declared':False,
       'application_semantic_link_certified':False,
       'business_repairs_certified':0,
       'mutations_executed':0,
       'read_only':True,
       'original_request_bulk_receipt_sha256':bulk_sha,
       'original_request_profile_receipt_sha256':profile_sha,
       'native_schema_metadata_receipt_sha256':native_sha,
       'original_june_signed_receipt_sha256':report['receipt_proofs']['june_1621_original_request'],
       'cohort_selection_sha256':report['receipt_proofs']['cohort'],
       'cases':cases
    }
    public={
       'schema':SUMMARY,'qa_period':'2026-06',
       'case_count':57,'linked_cases':55,'unlinked_cases':2,
       'single_matched_object_cases':13,
       'multiple_matched_object_cases':42,
       'itil_ot_cases':22,'itil_cobranza_cases':35,
       'qa_verified_case_pk_edges':619,
       'unique_business_primary_keys':525,
       'same_key_reused_across_tickets':87,
       'native_sql_link_tables_with_exact_itil_and_business_pk_columns':0,
       'native_declared_fks_involving_itil_taIncidente':0,
       'databases_inspected_for_native_link':14,
       'link_evidence':'ORIGINAL_REQUEST_TO_QA_PK_VALUE_AND_BRANCH',
       'all_links_retain_original_case_and_module_scope':True,
       'selected_cohort_posthoc_not_blind':True,
       'no_main_business_object_inferred_for_multi_object_tickets':True,
       'official_itil_business_fk_certified':False,
       'application_transactional_link_certified':False,
       'business_fix_certified':False,
       'source_business_mutations':0,
       'evidence_receipts_sha256':{
          'bulk':bulk_sha,'profile':profile_sha,
          'native_schema':native_sha,'itil_original':report['receipt_proofs']['june_1621_original_request']
       }
    }
    return payload,public

def write_private(repo:Path,private:Path,request:Path,prior:Path,june:Path,keyfile:Path,public:Path):
    payload,summary=construct(repo,private,request,prior,june,keyfile)
    key=keyfile.read_bytes()
    raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
    digest=sha256(raw).hexdigest()
    p=private/'verified_ticket_business_links.private.json'
    p.write_bytes(raw);os.chmod(p,0o600)
    proof={
       'schema':PROOF,'source_sha256':payload['source_sha256'],
       'receipt_sha256':digest,
       'hmac_sha256':hmac.new(
          key,f'{SCHEMA}:{payload["source_sha256"]}:{digest}'.encode(),
          'sha256').hexdigest(),'read_only':True
    }
    q=p.with_name(p.name+'.proof.json')
    q.write_text(json.dumps(proof,indent=2));os.chmod(q,0o600)
    summary['private_registry_receipt_sha256']=digest
    public.parent.mkdir(parents=True,exist_ok=True)
    public.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print('TICKET_BUSINESS_LINK_REGISTRY=SIGNED','CASES=57','EDGES=619',
          'SINGLE_CASES=13','MULTI_CASES=42','UNLINKED=2',
          'NATIVE_FOREIGN_KEYS=0','BUSINESS_WRITES=0')

def main():
    p=ArgumentParser()
    for name in ('repo','private','request-private','prior-private','june-private','key','public-output'):
        p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args()
    write_private(a.repo,a.private,a.request_private,a.prior_private,a.june_private,
                  a.key,a.public_output)
if __name__=='__main__':main()

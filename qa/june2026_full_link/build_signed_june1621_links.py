"""Rebuild ALL June request-only corporate PK observations from signed QA.

This is a retrospective **November QA observation**, NEVER a historical
June business state or a blind historical model label. The author does not
read solutions. Relational edges may be cross-type or from reporting copies.
"""
from __future__ import annotations
from argparse import ArgumentParser
from collections import defaultdict,Counter
from hashlib import sha256
from datetime import datetime,timezone
from pathlib import Path
from hmac import new as hmac_new,compare_digest
import json,os,re
from qa.monthend2026.evaluate_monthend import verify_one

RAW_SCHEMA="else.itil.qa.2026-june1621-source-only-dual-pk-discovery.v1"
RAW_PROOF="else.itil.qa.2026-june1621-source-only-dual-pk-discovery-hmac.v1"
LINK_SCHEMA="else.itil.qa.2026-june1621-retrospective-ticket-pk-graph.v1"
LINK_PROOF="else.itil.qa.2026-june1621-retrospective-ticket-pk-graph-hmac.v1"
PUBLIC_SCHEMA="else.itil.qa.2026-june1621-retrospective-pk-graph-summary.v1"
JUNE_SCHEMA="else.itil.qa.2026-juneall-source.v1"
JUNE_PROOF="else.itil.qa.2026-juneall-source-hmac.v1"
HEX=re.compile(r'^[0-9a-f]{64}$')
PK19=re.compile(r'^\d{19}$')
ALLOW={
 'dbComercial001_D','dbComercial003_D','dbComercial004_D',
 'dbComercial006_D','dbComercial007_D','dbComercial008_D',
 'dbComercial100_D','dbComercial200_D',
 'dbComercial001_Diario','dbComercial001_20230131',
 'dbComercial003_mayo','dbGerencial_D','dbDistribucion_D'
}

def check(ok,why):
    if not ok:raise ValueError(why)
def source(repo,private,june,keyfile):
    key=keyfile.read_bytes()
    check(len(key)==32,'JUNE_GRAPH_SIGNING_KEY_MISSING')
    raw,digest=verify_one(
       private/'june1621_source_only_dualpk.private.json',key,
       sha256((repo/'qa/june2026_full_link/JuneAllSourceOnlyPkRead.cs').read_bytes()).hexdigest(),
       RAW_SCHEMA,RAW_PROOF)
    june_original,june_digest=verify_one(
       june/'juneall_202606.private.json',key,
       sha256((repo/'qa/june2026/JuneAllRead.cs').read_bytes()).hexdigest(),
       JUNE_SCHEMA,JUNE_PROOF)
    check(
       raw['original_june1621_receipt_sha256']==june_digest
       and raw['source_cases']==1621
       and raw['input_request_only'] is True
       and raw['known_history_not_read'] is True
       and raw['no_module_gold_labels_used'] is True
       and raw['actual_june_as_of_business_state_not_proven'] is True
       and raw['no_writer_sql_executed'] is True
       and raw['business_writes']==0
       and raw['read_only'] is True
       and raw['qa_itil']=='ELSE70/dbITIL_D'
       and raw['qa_search_databases']==13
       and raw['lookup_errors']==[]
       and len(raw['table_lookup_coverage'])==26
       and raw['business_sql_select_batches']==168
       and raw['valid_case_candidate_count']==1342
       and raw['overflow_19_digit_candidates']==0
       and raw['distinct_candidate_numbers']==1125
       and june_original['period']=='2026-06'
       and june_original['selected']==1621
       and june_original['history_or_resolution_read'] is False
       and june_original['business_modifications']==0,
       'JUNE_GRAPH_SOURCE_FROZEN_QA_CONTRACT_CHANGED')
    coverage={(r['database'],r['kind']):r for r in raw['table_lookup_coverage']}
    check(
      set(coverage)=={(db,kind) for db in ALLOW for kind in ('OT','COLLECTION')}
      and all(
       r['branch_column_present'] is True if r['table_present']
       else r['branch_column_present'] is False
       for r in raw['table_lookup_coverage'])
      and all((r['lookup_batches']>0 if r['table_present'] else
               r['lookup_batches']==0) for r in raw['table_lookup_coverage']),
      'JUNE_GRAPH_SOURCE_DB_COVERAGE_UNVERIFIED')
    return raw,digest,june_original,june_digest,key

def build(repo,private,june,keyfile):
    raw,digest,original,june_digest,key=source(repo,private,june,keyfile)
    src_original=original['results']
    check(len(raw['case_metadata'])==len(src_original)==1621,
          'JUNE_GRAPH_SOURCE_CASE_COUNT_DRIFT')
    scope={}
    for i,(case,ref) in enumerate(zip(raw['case_metadata'],src_original),start=1):
        rank=case['rank'];nums=case['numeric_candidates_sha256']
        check(
          rank==ref['rank']==i
          and case['case_sha256']==ref['case_sha256']
          and case['request_sha256']==ref['description_sha256']
          and case['module_code']==ref['module_code']
          and case['service_code']==ref['service_code']
          and case['itil_company']==ref['company']
          and case['opened_at']==ref['opened_at']
          and case['source_original_request_only'] is True
          and case['known_history_not_read'] is True
          and len(nums)==case['request_numeric_candidates']
          and len(set(nums))==len(nums)
          and all(HEX.fullmatch(x) for x in nums)
          and ref['historical_solution_not_read'] is True,
          'JUNE_GRAPH_CASE_SCOPE_OR_ORIGINAL_REQUEST_TAMPERED')
        scope[rank]=case
    raw_matches=raw['business_key_matches']
    check(len(raw_matches)==1813,'JUNE_GRAPH_RAW_BUSINESS_MATCH_COUNT_CHANGED')
    matched_case_keys=defaultdict(dict)
    unaccepted=Counter()
    by_db=Counter()
    seen=set()
    for match in raw_matches:
        rank=match['rank'];case=scope.get(rank)
        kind=match['kind'];db=match['source_database'];pkcol=match['primary_key_column']
        val=match['primary_key_private'];h=match['primary_key_sha256']
        check(
          case is not None
          and kind in ('OT','COLLECTION')
          and db in ALLOW
          and pkcol==('CodigoOrdenTrabajo' if kind=='OT' else 'CodigoCobranza')
          and PK19.fullmatch(val) is not None
          and int(val)<=9223372036854775807
          and h==sha256(val.encode()).hexdigest()
          and h in case['numeric_candidates_sha256']
          and match['case_sha256']==case['case_sha256']
          and match['module_code']==case['module_code']
          and match['itil_branch']==case['itil_branch']
          and match['business_branch_matches_itil'] is (
              match['itil_branch']==match['business_branch'])
          and match['current_qa_row_found'] is True
          and match['history_not_read'] is True
          and match['native_ticket_business_fk_certified'] is False
          and (rank,kind,db,h) not in seen,
          'JUNE_GRAPH_MATCH_WRONG_PK_CASE_OR_BRANCH')
        seen.add((rank,kind,db,h))
        if not match['business_branch_matches_itil']:
            unaccepted['wrong_branch_observations']+=1
            unaccepted[db]+=1
            continue
        by_db[(kind,db)]+=1
        key2=(kind,h)
        grp=matched_case_keys[rank].setdefault(key2,{
          'kind':kind,'pk_column':pkcol,
          'primary_key_private':val,'primary_key_sha256':h,
          'case_sha256':case['case_sha256'],
          'branch':case['itil_branch'],
          'source_databases':[]
        })
        check(grp['primary_key_private']==val and
              db not in grp['source_databases'],'JUNE_GRAPH_COLLISION_OR_DB_DUPLICATE')
        grp['source_databases'].append(db)
    check(len(seen)==1813 and unaccepted['wrong_branch_observations']==215
      and sum(by_db.values())==1598,
      'JUNE_GRAPH_BRANCH_FILTER_WRONG')
    global_keys=defaultdict(set)
    statuses=Counter()
    case_links=[]
    all_both=0;copies=0;extra_copies=0
    logical_edges=0
    for rank,case in scope.items():
        groups=list(matched_case_keys[rank].values())
        links=[]
        for grp in groups:
            key_tuple=(grp['kind'],grp['primary_key_sha256'])
            global_keys[key_tuple].add(rank)
            databases=sorted(grp['source_databases'])
            handle=hmac_new(key,(
              'june1621-v1|'+case['case_sha256']+'|'+case['module_code']+
              '|'+grp['kind']+'|'+grp['primary_key_private']).encode(),'sha256').hexdigest()
            copies+=len(databases)>1
            extra_copies+=len(databases)-1
            links.append({
              'handle':handle,
              'kind':grp['kind'],
              'pk_column':grp['pk_column'],
              'business_pk_private':grp['primary_key_private'],
              'business_pk_sha256':grp['primary_key_sha256'],
              'branch':grp['branch'],
              'source_databases':databases,
              'possible_copy_or_multiple_business_schemas':len(databases)>1,
              'business_authority_certified':False,
              'application_fk_certified':False,
              'state_at_ticket_date_certified':False,
              'functional_role_in_ticket_certified':False
            })
        links.sort(key=lambda r:r['handle'])
        logical_edges+=len(links)
        kinds={x['kind'] for x in links}
        mixed=len(kinds)>1
        all_both+=mixed
        status='NO_SAME_BRANCH_QA_PRIMARY_KEY' if len(links)==0 else (
          'SINGLE_LOGICAL_PK_OBSERVED_RETROSPECTIVELY'
          if len(links)==1 else 'MULTIPLE_LOGICAL_PKS_NO_PRIMARY_SELECTED')
        statuses[status]+=1
        case_links.append({
          'rank':rank,'case_sha256':case['case_sha256'],
          'request_sha256':case['request_sha256'],
          'module_code':case['module_code'],
          'service_code':case['service_code'],
          'opened_at':case['opened_at'],
          'itil_company':case['itil_company'],
          'itil_branch':case['itil_branch'],
          'source_numeric_candidate_count':case['request_numeric_candidates'],
          'logical_object_count':len(links),
          'object_kind_count':len(kinds),
          'cross_kind_match_requires_manual_interpretation':mixed,
          'status':status,
          'links':links,
          'no_object_primary_assumed':True,
          'historical_business_state_unproven':True
        })
    repeats={key:len(value) for key,value in global_keys.items() if len(value)>1}
    cross_module=sum(len({scope[i]['module_code'] for i in ranks})>1
                     for key,ranks in global_keys.items())
    check(
       logical_edges==1491 and len(global_keys)==1236
       and statuses==Counter({
          'NO_SAME_BRANCH_QA_PRIMARY_KEY':1288,
          'SINGLE_LOGICAL_PK_OBSERVED_RETROSPECTIVELY':158,
          'MULTIPLE_LOGICAL_PKS_NO_PRIMARY_SELECTED':175})
       and all_both==107 and copies==88 and extra_copies==107
       and len(repeats)==232 and sum(n-1 for n in repeats.values())==255
       and max(map(len,global_keys.values()))==5 and cross_module==10,
       'JUNE_GRAPH_FROZEN_DERIVED_COUNTS_CHANGED_REQUIRE_REVIEW')
    observed=raw['observed_at_utc']
    # .NET DateTime.UtcNow round-trip uses seven fractional digits; Python
    # accepts six. Trimming *only* the seventh digit preserves chronology.
    normalized=re.sub(r'(\.\d{6})\d(?=Z$|\+00:00$)',r'\1',observed)
    parsed=datetime.fromisoformat(normalized.replace('Z','+00:00'))
    check(parsed.tzinfo is not None
       and parsed.astimezone(timezone.utc).date().isoformat()>='2026-11-12',
       'JUNE_GRAPH_QA_OBSERVATION_TIMESTAMP_MISSING')
    source_sha=sha256((repo/'qa/june2026_full_link/build_signed_june1621_links.py').read_bytes()).hexdigest()
    payload={
      'schema':LINK_SCHEMA,'source_sha256':source_sha,
      'period':'2026-06','qa_observed_at_utc':observed,
      'qa_itil':'ELSE70/dbITIL_D',
      'original_source_receipt_sha256':june_digest,
      'dual_pk_qa_receipt_sha256':digest,
      'retrospective_only':True,
      'historical_causal_or_write_evidence_certified':False,
      'official_application_business_fk_certified':False,
      'full_month_selected_without_gold_notes':True,
      'linked_cases':case_links,
      'read_only':True,'writes':0
    }
    summary={
      'schema':PUBLIC_SCHEMA,'month':'2026-06',
      'evaluated_original_incidents':1621,
      'original_request_only':True,
      'history_or_gold_not_consulted_for_classification':True,
      'source_cohort_selected_without_gold_labels':True,
      'qa_observed_at_utc':observed,
      'retrospective_qa_not_historical_asof':True,
      'candidate_mentions_19digit_per_ticket':1342,
      'globally_distinct_candidate_numbers':1125,
      'business_qa_lookup_sql_batches':168,
      'business_databases_read_only':13,
      'pk_observations_before_branch_check':1813,
      'wrong_branch_observations_rejected':215,
      'pk_observations_same_branch':1598,
      'cases_with_any_pk_before_branch_check':446,
      'cases_with_same_branch_pk':333,
      'cases_with_only_wrong_branch_pk':113,
      'cases_without_same_branch_pk':1288,
      'cases_with_one_logical_pk':158,
      'cases_with_multiple_logical_pks':175,
      'cases_with_both_ot_and_collection_matches':107,
      'logical_ticket_pk_relations_after_copy_dedup':1491,
      'distinct_business_pk_values_by_type':1236,
      'logical_ticket_pk_present_in_multiple_databases':copies,
      'extra_copy_observations_removed':extra_copies,
      'business_pk_shared_by_multiple_tickets':232,
      'extra_ticket_memberships_for_shared_pk':255,
      'max_tickets_sharing_one_pk':5,
      'shared_business_pk_crosses_module':cross_module,
      'historical_june_business_state_verified':False,
      'official_itil_business_fk_verified':False,
      'business_repairs_certified':0,
      'business_writes':0,
      'source_receipt_sha256':june_digest,
      'qa_dual_pk_receipt_sha256':digest,
      'same_branch_by_database':[
        {'kind':kind,'database':db,'count':n}
        for (kind,db),n in sorted(by_db.items())
      ],
      'source_selection_is_exhaustive_june_not_57_posthoc':True,
    }
    return payload,summary

def create(repo,private,june,keyfile,output):
    payload,summary=build(repo,private,june,keyfile)
    key=keyfile.read_bytes()
    raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
    digest=sha256(raw).hexdigest()
    p=private/'june1621_verified_case_graph.private.json'
    p.write_bytes(raw);os.chmod(p,0o600)
    proof={
      'schema':LINK_PROOF,'source_sha256':payload['source_sha256'],
      'receipt_sha256':digest,'hmac_sha256':hmac_new(key,
          f'{LINK_SCHEMA}:{payload["source_sha256"]}:{digest}'.encode(),'sha256').hexdigest(),
      'read_only':True
    }
    q=p.with_name(p.name+'.proof.json')
    q.write_text(json.dumps(proof,indent=2));os.chmod(q,0o600)
    summary['private_graph_receipt_sha256']=digest
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print('JUNE1621_GRAPH_SIGNED=PASS',
          'CASES=1621','RETROSPECTIVE_LINKED=333','LOGICAL_EDGES=1491',
          'PK_GLOBAL=1236','CROSS_KIND=107','SHARED_KEYS=232','WRITES=0')
def main():
    p=ArgumentParser()
    for arg in ('repo','private','june-source','key','public-output'):
        p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args()
    create(a.repo,a.private,a.june_source,a.key,a.public_output)
if __name__=='__main__':main()

"""HMAC-verified audit of 57 June requests against exact business PKs.

Only public aggregates are written. The signed private Windows QA receipts
retain business identifiers; nothing personal is copied into Git.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter,defaultdict
from argparse import ArgumentParser
import json,re
from qa.monthend2026.evaluate_monthend import verify_one

SCHEMA='else.itil.qa.2026-june57-request-pk-recovery-aggregate.v1'
SOURCES={
 'cohort':('june57_manifest.private.json',
     'qa/june2026_57/build_private_57_manifest.py',
     'else.itil.qa.2026-june57-source-and-history-reference-selection.v1',
     'else.itil.qa.2026-june57-source-and-history-reference-hmac.v1'),
 'old':('june57_business_candidates.private.json',
     'qa/june2026_57/June57SourceAndTargetsRead.cs',
     'else.itil.qa.2026-june57-business-candidate-scan.v1',
     'else.itil.qa.2026-june57-business-candidate-scan-hmac.v1'),
 'profile':('june57_request_ids.private.json',
     'qa/june2026_identity/June57RequestIdentifiersRead.cs',
     'else.itil.qa.2026-june57-request-identity-candidates.v1',
     'else.itil.qa.2026-june57-request-identity-candidates-hmac.v1'),
 'bulk':('june57_bulk_pk_request_matches.private.json',
     'qa/june2026_identity/June57BulkPrimaryKeyMatch.cs',
     'else.itil.qa.2026-june57-request-bulk-primary-key-lookup.v1',
     'else.itil.qa.2026-june57-request-bulk-primary-key-lookup-hmac.v1'),
 'residual':('june57_residual_source_relation.private.json',
     'qa/june2026_identity/June57ResidualRelationRead.cs',
     'else.itil.qa.2026-june57-two-residual-request-key-probe.v1',
     'else.itil.qa.2026-june57-two-residual-request-key-probe-hmac.v1'),
}
def demand(cond,code):
    if not cond:raise ValueError(code)
def assess(repo,private,prior,june,keyfile):
    key=keyfile.read_bytes()
    demand(len(key)==32,'KEY_INVALID')
    data={};digests={}
    for label,(filename,code,schema,proof) in SOURCES.items():
        folder=prior if label in ('cohort','old') else private
        data[label],digests[label]=verify_one(folder/filename,key,
            sha256((repo/code).read_bytes()).hexdigest(),schema,proof)
    orig,orig_sha=verify_one(june/'juneall_202606.private.json',key,
        sha256((repo/'qa/june2026/JuneAllRead.cs').read_bytes()).hexdigest(),
        'else.itil.qa.2026-juneall-source.v1',
        'else.itil.qa.2026-juneall-source-hmac.v1')
    a,b,c,d,e=(data[k] for k in ('cohort','old','profile','bulk','residual'))
    demand(a['source_june1621_receipt_sha256']==orig_sha
       and b['signed_selection_sha256']==c['original_june57_manifest_sha256']
         ==d['june57_selection_receipt_sha256']
         ==e['june57_selection_receipt_sha256']==digests['cohort']
       and a['selected']==b['case_count']==c['cohort_count']==d['selected_cases']==57
       and a['categories']=={'OT':22,'COLLECTION':35}
       and c['historical_note_column_selected'] is False
       and d['historical_note_column_selected'] is False
       and d['original_request_only'] is True
       and d['no_rich_text_numbers_used'] is True
       and d['case_category_selected_posthoc'] is True
       and e['no_historical_note_read'] is True
       and e['source_cases']==2 and e['select_queries']==102
       and c['read_only'] is d['read_only'] is e['read_only'] is True
       and c['business_writes']==d['business_writes']==0
       and e['no_writes'] is True and e['repairs_certified']==0,
       'SIGNED_SOURCE_CHAIN_OR_READONLY_MISMATCH')
    reference={r['rank']:r for r in orig['results']}
    expected={}
    old_status={}
    demand(len(a['rows'])==len(b['case_identity_data'])==
        len(c['rows'])==len(d['case_metadata'])==57,
        'COHORT_LENGTH_MISMATCH')
    for x,y,z,w in zip(a['rows'],b['case_identity_data'],c['rows'],d['case_metadata']):
        rank=x['rank']; source=reference[rank]
        demand(rank not in expected
          and rank==y['rank']==z['rank']==w['rank']
          and len({x['case_sha256'],y['case_sha256'],z['case_sha256'],
                   w['case_sha256'],source['case_sha256']})==1
          and len({x['request_sha256'],z['request_sha256'],
                   w['source_request_sha256'],source['description_sha256']})==1
          and x['category']==y['category']==z['category']==w['category']
          and x['module_code']==z['module_code']==source['module_code']
          and x['itil_company']==z['itil_company']==source['company']
          and z['only_request_fields_read'] is True
          and source['historical_solution_not_read'] is True
          and w['request_19digit_bigint_distinct']==len(w['candidate_sha256'])
          and len(set(w['candidate_sha256']))==len(w['candidate_sha256']),
          'CASE_BOUND_SOURCE_OR_HASH_DRIFT')
        expected[rank]=(z,w)
        old_status[rank]=y['identity_status']
    demand(d['literal_19digit_bigint_candidates']==620
      and d['numeric_overflow_candidates']==0
      and d['business_lookup_statements']==43
      and d['scanned_database_count']==13
      and sum(w['request_19digit_bigint_distinct'] for z,w in expected.values())==620,
      'BULK_NUMERIC_COHORT_DRIFT')
    matches=defaultdict(set);totals=Counter();sources=Counter();seen=set()
    distinct_business_keys=Counter()
    for hit in d['matches']:
        rank=hit['rank']; z,w=expected[rank]
        code=hit['identifier_private']
        family=hit['category']; db=hit['found_in_database']
        sha=hit['source_candidate_sha256']
        demand(re.fullmatch(r'\d{19}',code) is not None
           and int(code)<=9223372036854775807
           and sha256(code.encode()).hexdigest()==sha
           and sha in w['candidate_sha256']
           and hit['case_sha256']==z['case_sha256']
           and family==w['category']
           and (rank,sha) not in seen
           and hit['business_branch_equals_itil_branch'] is True
           and hit['business_branch']==hit['itil_branch']==z['itil_branch']
           and hit['current_qa_row_only'] is True
           and hit['historical_target_not_read'] is True
           and hit['unique_ticket_object_not_proven'] is True
           and (family,db) in (
              ('COLLECTION','dbComercial001_Diario'),
              ('OT','dbGerencial_D'),('OT','dbDistribucion_D')),
           'FALSE_POSITIVE_OR_CROSS_CASE_PRIMARY_KEY')
        seen.add((rank,sha));matches[rank].add(sha);sources[(family,db)]+=1
        distinct_business_keys[(family,sha)]+=1
    for rank,(z,w) in expected.items():
        n=len(matches[rank]);cat=w['category'];tot=w['request_19digit_bigint_distinct']
        demand(n<=tot,'MATCHED_MORE_KEYS_THAN_IN_SOURCE')
        totals['selected_cases']+=1
        totals['candidate_case_pk_pairs']+=tot
        totals['matched_case_pk_pairs']+=n
        totals['unmatched_candidates']+=tot-n
        totals['cases_with_exact_pk_matches']+=n>0
        totals['cases_without_exact_pk_match']+=n==0
        totals['cases_with_multiple_pk_matches']+=n>1
        totals['cases_with_single_pk_match']+=n==1
        totals['cases_without_19_digit_number']+=tot==0
        totals['ot_cases_matched']+=n>0 and cat=='OT'
        totals['collection_cases_matched']+=n>0 and cat=='COLLECTION'
        totals['newly_rescued_vs_strict_request_pk']+=n>0 and old_status[rank] not in (
             'REQUEST_AND_NOTE_SAME_ID','REQUEST_ONLY_PK')
    totals['distinct_business_primary_keys']=len(distinct_business_keys)
    totals['repeated_business_keys_across_tickets']=sum(
         count>1 for count in distinct_business_keys.values())
    totals['repeat_ticket_key_memberships']=sum(
         count-1 for count in distinct_business_keys.values())
    demand(totals['selected_cases']==57
        and totals['candidate_case_pk_pairs']==620
        and totals['matched_case_pk_pairs']==619
        and totals['unmatched_candidates']==1
        and totals['cases_with_exact_pk_matches']==55
        and totals['cases_without_exact_pk_match']==2
        and totals['ot_cases_matched']==20
        and totals['collection_cases_matched']==35
        and totals['newly_rescued_vs_strict_request_pk']==52
        and totals['distinct_business_primary_keys']==525
        and totals['repeated_business_keys_across_tickets']==87
        and totals['repeat_ticket_key_memberships']==94
        and sources==Counter({
           ('COLLECTION','dbComercial001_Diario'):489,
           ('OT','dbGerencial_D'):127,
           ('OT','dbDistribucion_D'):3
        }),'FROZEN_REAL_QA_METRICS_CHANGED_REQUIRE_REVIEW')
    demand(set(r['rank'] for r in e['cases'])=={120,800}
       and not matches[120] and not matches[800]
       and len(e['lookup_results'])==1
       and e['lookup_results'][0]['rank']==120
       and e['lookup_results'][0]['column']=='CodigoCobranza'
       and e['lookup_results'][0]['database']=='dbComercial001_Diario'
       and e['lookup_results'][0]['same_itil_branch']==0,
       'CROSS_TYPE_RESIDUAL_MUST_NOT_PROMOTE_FALSE_OT')
    return {
       'schema':SCHEMA,'period':'2026-06',
       'source':'ELSE70/dbITIL_D - DescripcionSolicitud',
       'cohort_was_selected_posthoc_using_previous_documentary_overlap':True,
       'historical_solution_not_read_for_identifier_recovery':True,
       'rich_text_generic_numeric_tokens_ignored':True,
       'current_qa_pk_presence_not_a_repair':True,
       'ticket_business_fk_not_formally_certified':True,
       'business_writes':0,'business_repairs_certified':0,
       'totals':dict(sorted(totals.items())),
       'matched_databases':[{'category':k,'database':v,'match_count':n}
           for (k,v),n in sorted(sources.items())],
       'residual_cross_type_match_not_counted':True,
       'receipt_proofs':dict(sorted({**digests,
         'june_1621_original_request':orig_sha}.items())),
       'private_receipts_hold_unmasked_ids':True
    }

def main():
    p=ArgumentParser()
    for x in ('repo','private','prior','june','key','output'):
        p.add_argument('--'+x,required=True,type=Path)
    a=p.parse_args()
    d=assess(a.repo,a.private,a.prior,a.june,a.key)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    print('HMAC_VERIFIED_RECOVERY',
       {k:d['totals'][k] for k in (
        'candidate_case_pk_pairs','matched_case_pk_pairs',
        'cases_with_exact_pk_matches','newly_rescued_vs_strict_request_pk')})
if __name__=='__main__':main()

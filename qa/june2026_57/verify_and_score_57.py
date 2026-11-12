"""Bounded source-backed evidence audit of 57 June OT/Cobranza tickets.

Selection is post-hoc based on May500-vs-June reference overlap; not a new
blind benchmark, not historical execution. All raw tickets and business
snapshots stay in private QA. Public JSON contains aggregate-only metrics.
"""
from __future__ import annotations
from pathlib import Path
from argparse import ArgumentParser
from hashlib import sha256
from collections import Counter,defaultdict
import json,hmac

from qa.monthend2026.evaluate_monthend import verify_one

SCHEMA='else.itil.qa.2026-june57-business-candidate-aggregate.v1'
DISTRIBUTION='dbDistribucion_D'
def fail(msg):raise ValueError(msg)
def require(cond,msg):
    if not cond:fail(msg)

def audit(root:Path, repo:Path, key_file:Path,
          full_june_root:Path, aggregate_file:Path|None=None)->dict:
    key=key_file.read_bytes()
    require(len(key)==32,'JUNE57_SIGNER_MISSING')
    signed_source=repo/'qa/june2026_57/build_private_57_manifest.py'
    source=repo/'qa/june2026_57/June57SourceAndTargetsRead.cs'
    manifest,manifest_digest=verify_one(
       root/'june57_manifest.private.json',key,
       sha256(signed_source.read_bytes()).hexdigest(),
       'else.itil.qa.2026-june57-source-and-history-reference-selection.v1',
       'else.itil.qa.2026-june57-source-and-history-reference-hmac.v1')
    scan,scan_digest=verify_one(
       root/'june57_business_candidates.private.json',key,
       sha256(source.read_bytes()).hexdigest(),
       'else.itil.qa.2026-june57-business-candidate-scan.v1',
       'else.itil.qa.2026-june57-business-candidate-scan-hmac.v1')
    orig_source,orig_sha=verify_one(
       full_june_root/'juneall_202606.private.json',key,
       sha256((repo/'qa/june2026/JuneAllRead.cs').read_bytes()).hexdigest(),
       'else.itil.qa.2026-juneall-source.v1',
       'else.itil.qa.2026-juneall-source-hmac.v1')
    orig_gold,gold_sha=verify_one(
       full_june_root/'juneall_202606_history.private.json',key,
       sha256((repo/'qa/june2026/JuneAllRead.cs').read_bytes()).hexdigest(),
       'else.itil.qa.2026-juneall-history.v1',
       'else.itil.qa.2026-juneall-history-hmac.v1')
    require(manifest['source_june1621_receipt_sha256']==orig_sha
       and manifest['history_june1621_receipt_sha256']==gold_sha
       and scan['june1621_request_sha256']==orig_sha
       and scan['june1621_history_sha256']==gold_sha
       and scan['signed_selection_sha256']==manifest_digest
       and manifest['selected']==scan['case_count']==57
       and manifest['categories']=={'OT':22,'COLLECTION':35}
       and scan['ot_count']==22 and scan['collection_count']==35
       and manifest['posthoc_gold_use_for_fixed_test_selection'] is True
       and manifest['prior_may500_only_training'] is True
       and scan['no_historical_sql_executed'] is True
       and scan['read_only'] is True
       and scan['business_writes']==scan['business_repairs_certified']==0,
       'JUNE57_RECEIPTS_NOT_BOUND_TO_ORIGINAL_JUNE')
    by_rank={}
    for expected,seen in zip(manifest['rows'],scan['case_identity_data']):
       rank=expected['rank']
       src=orig_source['results'][rank-1]
       gold=orig_gold['historical_records'][rank-1]
       require(rank not in by_rank and 1<=rank<=1621
         and seen['rank']==rank
         and src['rank']==gold['rank']==rank
         and expected['case_sha256']==src['case_sha256']==gold['case_sha256']==seen['case_sha256']
         and expected['request_sha256']==src['description_sha256']
         and expected['history_sha256']==gold['historical_solution_sha256']
         and expected['module_code']==src['module_code']
         and expected['itil_company']==src['company']==seen['itil_company']
         and expected['category']==seen['category']
         and seen['opened_month']=='2026-06',
         'JUNE57_WRONG_SIGNED_CASE_OR_GOLD')
       id_code=seen['identity_status']
       req=seen['source_request_identifier_present']
       note=seen['historical_note_identifier_present']
       agreement=seen['identifier_agreement']
       id_hash=seen['identifier_sha256']
       id_value=seen['identifier_private']
       permitted={
          'NO_EXPLICIT_PRIMARY_KEY':(False,False,False,False),
          'HISTORICAL_NOTE_ONLY_PK':(False,True,False,True),
          'REQUEST_ONLY_PK':(True,False,False,True),
          'REQUEST_AND_NOTE_SAME_ID':(True,True,True,True),
          'AMBIGUOUS_IDENTIFIER':(False,False,False,False),
          'CONFLICT_REQUEST_HISTORICAL_IDS':(True,True,False,False)
       }
       signature_ok=(id_code in permitted
          and ((not agreement and not bool(id_value)) if id_code=='AMBIGUOUS_IDENTIFIER'
               else (req,note,agreement,bool(id_value))==permitted[id_code]))
       require(signature_ok
        and (id_hash==sha256(id_value.encode()).hexdigest() if id_value else id_hash=="")
        and (len(id_value)<=19 and id_value.isdigit() if id_value else True),
        'JUNE57_IDENTIFIER_MALFORMED_OR_FALSE_CORROBORATION')
       by_rank[rank]=seen
    require(len(by_rank)==57 and len(scan['case_identity_data'])==57
       and len(manifest['rows'])==57,
       'JUNE57_NOT_EXACT_FIFTY_SEVEN')
    if aggregate_file is not None:
        pinned=json.loads(aggregate_file.read_bytes())
        require(pinned['schema']==SCHEMA
            and pinned['receipt_sha256']=={
              'selection':manifest_digest,'source_and_business':scan_digest,
              'june1621_requests':orig_sha,'june1621_history':gold_sha},
            'JUNE57_POSTHOC_RECEIPT_NOT_PINNED_TO_CERTIFIED_REPORT')
    # Cross-check the May-trained selection labels; historical notes selected
    # after the original blind author experiment, not used during inference.
    labels_path=full_june_root/'june1621_may500_case_labels.private.json'
    labels=json.loads(labels_path.read_bytes())
    proven={x['rank']:x for x in labels['cases'] if x['flags']['exact_kind_table_fields']}
    require(len(proven)==72 and set(by_rank)<=set(proven)
       and all(by_rank[r]['case_sha256']==proven[r]['case_sha256'] for r in by_rank),
       'JUNE57_INCORRECT_MAY500_LABEL_SELECTION')
    counts=Counter()
    per_kind=defaultdict(Counter)
    found_cases=set()
    found_across={}
    db_table_map={}
    errors=[]
    require(len(scan['searched_databases'])==13,
        'JUNE57_NOT_ALL_THIRTEEN_DATABASES')
    seen_dbs=set()
    for db in scan['searched_databases']:
       dbname=db['db']
       require(dbname not in seen_dbs
           and db['metadata'] in ('VISIBLE','NOT_VISIBLE_ONLINE','ACCESS_DENIED'),
           'JUNE57_DUPLICATE_OR_INVALID_DB')
       seen_dbs.add(dbname)
       db_table_map[dbname]=db['tables']
       if db['metadata']!='VISIBLE':
          errors.append(dbname)
       for hit in db['results']:
          rank=hit['rank'];category=hit['category']
          require(rank in by_rank and category==by_rank[rank]['category']
              and by_rank[rank]['identifier_private']
              and hit['id_sha256']==by_rank[rank]['identifier_sha256'],
              'JUNE57_CROSS_CASE_QUERY_RESULT')
          if hit['found_rows']<0 or hit.get('query_error'):
             errors.append(f'{dbname}/query')
          else:
             require(hit['found_rows']>=1 and hit['found_rows']<=3
                 and len(hit['snapshot'])==hit['found_rows']
                 and hit['source_transaction_not_certified'] is True,
                 'JUNE57_POSITIVE_DB_RESULT_UNBOUND')
             found_cases.add(rank)
             key2=(rank,dbname)
             require(key2 not in found_across,'JUNE57_DUPLICATE_POSITIVE')
             found_across[key2]=hit
             counts['positive_database_case_pairs']+=1
             counts['positive_business_rows_at_most']+=hit['found_rows']
             per_kind[category]['database_case_positive']+=1
             if dbname=='dbGerencial_D':
                counts['positive_gerencial_pairs']+=1
             if dbname=='dbComercial001_Diario':
                counts['positive_daily_copy_pairs']+=1
             if dbname==DISTRIBUTION:
                counts['positive_distribution_pairs']+=1
    require(not errors,'JUNE57_UNSEARCHED_OR_ERROR_DB_DETECTED')
    counts['selected_cases']=len(by_rank)
    counts['historical_exact_sql_overlap_selection']=len(by_rank)
    counts['ot']=sum(x['category']=='OT' for x in by_rank.values())
    counts['collections']=sum(x['category']=='COLLECTION' for x in by_rank.values())
    for rank,row in by_rank.items():
       category=row['category']
       id_status=row['identity_status']
       counts['identity_'+id_status]+=1
       per_kind[category][id_status]+=1
       counts['cases_with_any_positive_db_match']+=rank in found_cases
       per_kind[category]['cases_found_any_db']+=rank in found_cases
       if row['source_request_identifier_present'] and rank in found_cases:
          counts['request_backed_pk_case_found']+=1
       if row['identity_status']=='HISTORICAL_NOTE_ONLY_PK' and rank in found_cases:
          counts['gold_only_pk_case_found']+=1
    counts['distinct_database_sources_scanned']=len(seen_dbs)
    counts['selected_exact_id_lookups']=sum(bool(x['identifier_private']) for x in by_rank.values())
    counts['no_safe_explicit_id_for_lookup']=57-counts['selected_exact_id_lookups']
    counts['cases_with_complete_before_after']=0
    counts['case_repairs_certified']=0
    counts['business_writes']=0
    require(counts['selected_exact_id_lookups']==12
        and counts['cases_with_any_positive_db_match']==12
        and counts['identity_REQUEST_AND_NOTE_SAME_ID']==3
        and counts['identity_NO_EXPLICIT_PRIMARY_KEY']==41
        and counts['identity_HISTORICAL_NOTE_ONLY_PK']==9
        and counts['identity_AMBIGUOUS_IDENTIFIER']==3
        and counts['identity_CONFLICT_REQUEST_HISTORICAL_IDS']==1
        and counts['request_backed_pk_case_found']==3
        and counts['gold_only_pk_case_found']==9
        and counts['positive_database_case_pairs']==12,
        'JUNE57_EVIDENCE_DISTRIBUTION_CHANGED_REVIEW_REQUIRED')
    # A found PK in Gerencial is not an authoritative commercial transaction.
    # Only existing certified company-route receipts could attest such a link.
    return {
       'schema':SCHEMA,
       'month':'2026-06',
       'source':'ELSE62 SQL QA ELSE70, read-only',
       'selection_posthoc':'57_MAY500_JUNE1621_EXACT_SQL_OVERLAP_OT_COLLECTION',
       'selected_cases':57,
       'original_june_cases':1621,
       'selection_from_72_documentary_exact_cases':True,
       'not_a_blind_llm_evaluation':True,
       'strict_identifiers_only':True,
       'unverified_actual_business_execution':True,
       'no_personal_name_or_business_identifier_in_public_output':True,
       'receipt_sha256':{
         'selection':manifest_digest,
         'source_and_business':scan_digest,
         'june1621_requests':orig_sha,
         'june1621_history':gold_sha,
       },
       'totals':dict(sorted(counts.items())),
       'by_category':{k:dict(sorted(v.items())) for k,v in sorted(per_kind.items())},
       'dbs_with_ot_and_collection_tables':sum(
          v.get('taOrdenTrabajo',False) and v.get('taCobranza',False)
          for v in db_table_map.values()),
       'outcome':'PROVISIONAL_OBJECT_RECOVERY_ONLY',
       'backdated_business_state_not_verified':True,
       'real_fix_certified':False,
       'business_mutations':0,
    }

def main():
    p=ArgumentParser()
    for name in ('private','repo','key','full-june-private','output'):
        p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args()
    data=audit(a.private,a.repo,a.key,a.full_june_private)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('JUNE57_REAL_SOURCE_AUDIT',json.dumps(data['totals'],ensure_ascii=False,sort_keys=True))
if __name__=='__main__':main()

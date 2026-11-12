"""Score five June 2026 Qwen4B SAME_MECHANISM items against exact SQL QA.

This program is deliberately post-hoc for evidence audit, not a blind
predictor. It checks independently signed ITIL identifiers, signed business
snapshots and metadata, then conservatively downgrades model-object conflicts.

All case identifiers, business values, historical notes and names remain in
private server receipts, never the public summary.
"""
from __future__ import annotations
from argparse import ArgumentParser
from collections import Counter
from hashlib import sha256
from pathlib import Path
import hmac,json,re

from qa.monthend2026.evaluate_monthend import verify_one

SCHEMA='else.itil.qa.2026-june5-business-beforeafter-evidence.v1'
RANKS=(197,263,868,934,1065)
MANIFEST_SCHEMA='else.itil.qa.2026-june5-selected-manifest.v1'
PROOF_SCHEMA='else.itil.qa.2026-june5-selected-manifest-hmac.v1'

def _manifest(private:Path,key:bytes):
    p=private/'june5_manifest.private.json'
    raw=p.read_bytes()
    proof=json.loads((private/(p.name+'.proof.json')).read_bytes())
    if (proof['schema']!=PROOF_SCHEMA
        or sha256(raw).hexdigest()!=proof['receipt_sha256']
        or not hmac.compare_digest(
            hmac.new(key,raw,'sha256').hexdigest(),proof['hmac_sha256'])):
        raise ValueError('JUNE_FIVE_MANIFEST_HMAC_INVALID')
    doc=json.loads(raw)
    if (doc['schema']!=MANIFEST_SCHEMA
        or tuple(doc['ranks'])!=RANKS
        or len(doc['rows'])!=5
        or tuple(x['rank'] for x in doc['rows'])!=RANKS):
        raise ValueError('JUNE_FIVE_WRONG_SIGNED_CASE_SCOPE')
    return doc,proof['receipt_sha256']

def _judge_object_alignment(rank:int,proposal:dict)->str:
    checks=proposal.get('checks')
    if not isinstance(checks,list) or not checks:
        return 'INVALID_MISSING_PROPOSAL_CHECKS'
    combined=' '.join(
        str(x.get('business_object',''))+' '+str(x.get('observable',''))
        for x in checks if type(x) is dict).lower()
    if rank==1065:
        # Mention of "campaña" as incidental context cannot certify that
        # checks targeting an OT are checks against taCampanaSupervision.
        object_names=' '.join(str(x.get('business_object','')) for x in checks
                              if type(x) is dict).lower()
        return ('BUSINESS_OBJECT_MISMATCH'
                if re.search(r'\bot\b',object_names)
                else 'NEEDS_MANUAL_REVIEW')
    if rank==263:
        # Historic note: missing pliego tarifario for contracted power.
        # Checking only OT state/subtype cannot confirm tariff incompatibility.
        return ('REQUIRED_CAUSAL_TEST_MISSING'
                if not any(x in combined for x in
                           ('pliego','tarifa','potencia','monofásic','monofasic'))
                else 'NEEDS_MANUAL_REVIEW')
    targets={197:('centro','atención'),868:('estado','ot'),934:('apellido','dni')}
    required=targets[rank]
    return 'OBJECT_AND_OBSERVABLE_ALIGNED_ONLY' if all(
        value in combined for value in required) else 'NEEDS_MANUAL_REVIEW'

def audit(private:Path,qa:Path,key:bytes,authors:Path,judges:Path)->dict:
    manifest,manifest_sha=_manifest(private,key)
    snap,snap_sha=verify_one(
       private/'june5_exact_business.private.json',
       key,sha256((qa/'JuneFiveExactBusinessRead.cs').read_bytes()).hexdigest(),
       'else.itil.qa.2026-june5-exact-business-snapshot.v1',
       'else.itil.qa.2026-june5-exact-business-snapshot-hmac.v1')
    meta,meta_sha=verify_one(
       private/'june5_metadata.private.json',
       key,sha256((qa/'JuneBusinessMetaRead.cs').read_bytes()).hexdigest(),
       'else.itil.qa.2026-june5-business-metadata.v1',
       'else.itil.qa.2026-june5-business-metadata-hmac.v1')
    if (snap['selected']!=5 or snap['business_modifications']!=0
        or snap['read_only'] is not True
        or tuple(snap['selected_ranks'])!=RANKS
        or snap['original_five_manifest_sha256']!=manifest_sha
        or snap['cohort_source_receipt_sha256']!=manifest['june_source_receipt_sha256']
        or snap['cohort_history_receipt_sha256']!=manifest['june_history_receipt_sha256']
        or snap['qa_itil']!='ELSE70/dbITIL_D'
        or snap['qa_business']!='ELSE70/dbComercial001_D'
        or meta['qa']!='ELSE70/dbComercial001_D'
        or meta['read_only'] is not True
        or meta['modifications']!=0):
        raise ValueError('JUNE_FIVE_BUSINESS_SCOPE_INVALID')
    temporal={x['table']:x for x in meta['temporal']}
    for name in ('taOrdenTrabajo','taCampanaSupervision','taPadronRuc'):
        if name not in temporal or temporal[name]['temporal']!='NON_TEMPORAL_TABLE':
            raise ValueError('JUNE_FIVE_TEMPORAL_ASSUMPTION_DRIFT')
    if not all(snap['business_table_has_any_rows'].values()):
        raise ValueError('JUNE_FIVE_SOURCE_TABLE_EMPTY_REQUIRES_REVIEW')
    model={}
    reviewers={}
    for line in authors.read_text().splitlines():
        if not line.strip():continue
        x=json.loads(line)
        if x['rank'] in RANKS:
            if x['rank'] in model or x['gold_exposed'] is not False:
                raise ValueError('JUNE_FIVE_AUTHOR_NOT_BLINDED')
            model[x['rank']]=x
    for line in judges.read_text().splitlines():
        if not line.strip():continue
        x=json.loads(line)
        if x['rank'] in RANKS:
            if x['rank'] in reviewers:
                raise ValueError('JUNE_FIVE_DUPLICATED_REVIEWER')
            reviewers[x['rank']]=x
    if len(model)!=len(reviewers)!=5:
        raise ValueError('JUNE_FIVE_QWEN_JOURNALS_INCOMPLETE')
    counts=Counter()
    classifications=Counter()
    for sig,row in zip(manifest['rows'],snap['rows']):
        rank=row['rank']
        if (rank not in model or rank not in reviewers or
            row['case_sha256']!=sig['case_sha256']
            or row['case_sha256']!=model[rank]['case_sha256']
            or row['case_sha256']!=reviewers[rank]['case_sha256']
            or row['module_code']!=sig['module_code']
            or model[rank]['result']['status']!='FUNCTIONAL_DRAFT_CONTRACT_PASS'
            or reviewers[rank]['status']!='PROVISIONAL_JUDGE_PASS'
            or reviewers[rank]['judge']['plan_alignment']!='SAME_MECHANISM'
            or not row['source_month']=='2026-06'
            or not row['action_executed_by_agent'] is False
            or not row['repair_certified'] is False
            or row['same_case_full_historical_before_after_certified'] is not False):
            raise ValueError('JUNE_FIVE_CASE_OR_QWEN_CROSS_SOURCE_MISMATCH')
        counts['cases']+=1
        counts['historical_note_identifier_present']+=bool(row['historical_note_identifier_present'])
        counts['identifier_in_original_request']+=bool(row['original_request_id_corrobated'])
        counts['request_and_note_same_id']+=bool(row['request_and_note_id_match'])
        counts['historical_only_unconfirmed_identifier']+=bool(row['identifier_only_from_historical_note'])
        counts['business_row_not_found']+=row['business_row_count']==0
        counts['business_row_ambiguous']+=row['business_row_count']>1
        counts['unique_business_row']+=row['business_row_count']==1
        counts['cases_with_audit_record']+=row['audit_event_count']>0
        counts['audited_target_field_transition_in_june']+=row['june_exact_field_audit_seen']
        counts['historical_target_matched_independent_audit']+=row['june_exact_field_audit_matches_historical_target']
        if row['business_row_count']>1 and row['kind']!='PADRON':
            raise ValueError('JUNE_FIVE_MULTIPLE_BUSINESS_OBJECTS_NOT_AUDITED')
        if row['kind']=='PADRON' and row['original_request_id_corrobated']:
            raise ValueError('JUNE_FIVE_DNI_REQUEST_ASSERTION_UNEXPECTED')
        grade=_judge_object_alignment(rank,model[rank]['result']['proposal'])
        if grade=='NEEDS_MANUAL_REVIEW' or grade.startswith('INVALID'):
            raise ValueError('JUNE_FIVE_OBJECT_GRADE_REQUIRES_REVIEW')
        classifications[grade]+=1
    if counts['cases']!=5 or counts['unique_business_row']!=0:
        raise ValueError('JUNE_FIVE_BUSINESS_SCORE_CHANGED_REQUIRE_REVIEW')
    by_table=Counter(row['kind'] for row in snap['rows'])
    return {
      'schema':SCHEMA,
      'purpose':'RECLASSIFY_PROVISIONAL_QWEN_JUDGE_MATCHES_AGAINST_EXACT_BUSINESS_QA',
      'historical_period':'2026-06',
      'source':'ELSE62/ELSE70',
      'qa_itil':'dbITIL_D',
      'qa_business':'dbComercial001_D',
      'manifest_receipt_sha256':manifest_sha,
      'metadata_receipt_sha256':meta_sha,
      'business_snapshot_receipt_sha256':snap_sha,
      'independent_june_request_receipt_sha256':manifest['june_source_receipt_sha256'],
      'independent_june_history_receipt_sha256':manifest['june_history_receipt_sha256'],
      'business_tables_have_records_without_relevant_exact_case':True,
      'target_tables_non_temporal':True,
      'audit_table_names_verified':[
        'dbo.taOrdenTrabajoAuditoriaCambio',
        'dbo.taOrdenTrabajo_ModificacionIN'],
      'author_model':'Qwen3.5-9B',
      'independent_judge':'Qwen3.5-4B',
      'judge_initial_provisional_same_mechanism':5,
      'object_alignment_is_conservative_posthoc_review_not_human_ground_truth':True,
      'targeted_types':dict(sorted(by_table.items())),
      'counts':dict(sorted(counts.items())),
      'object_review':dict(sorted(classifications.items())),
      'historical_sql_not_execution_proof':True,
      'current_snapshot_does_not_establish_state_in_june':True,
      'no_unique_object_no_state_before_after':True,
      'historically_certified_changes':0,
      'certified_business_repairs':0,
      'business_writes_executed':0
    }

def main():
    p=ArgumentParser()
    for name in ('private','qa','key','authors','judges','output'):
        p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args()
    data=audit(a.private,a.qa,a.key.read_bytes(),a.authors,a.judges)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('FIVE_BUSINESS_EVIDENCE',json.dumps({
      'cases':data['counts']['cases'],
      'request_identifier':data['counts']['identifier_in_original_request'],
      'case_original_note_id_matches':data['counts']['request_and_note_same_id'],
      'unique_rows':data['counts']['unique_business_row'],
      'business_row_not_found':data['counts']['business_row_not_found'],
      'ambiguous':data['counts']['business_row_ambiguous'],
      'audit_transitions':data['counts']['audited_target_field_transition_in_june'],
      'object_review':data['object_review'],
      'repairs':data['certified_business_repairs']},ensure_ascii=False))
if __name__=='__main__':main()

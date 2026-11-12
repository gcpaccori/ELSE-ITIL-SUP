"""Aggregate verified signed native ITIL workflow history for 900 QA incidents.

Source data and event timestamps remain private. Publication is only grouped
month stats and source-receipt SHA-256 digests, never case hashes or user text.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import argparse,json
from else_dominance.qa_itil_native_lifecycle import VerifiedItILNativeLifecycle

SCHEMA="else.itil.qa.2026-native-lifecycle-900-summary.v1"

def report(index:VerifiedItILNativeLifecycle)->dict:
    months={}
    total=Counter()
    for n in range(1,10):
        ym=f"2026-{n:02d}"
        rows=[x for x in index.rows.values() if x['month']==ym]
        if len(rows)!=100:
            raise ValueError("MONTH_LIFECYCLE_NOT_ONE_HUNDRED")
        types=Counter()
        for row in rows:
            for item in index.events[row['case_sha256']]:
                types[item['type_code']]+=1
        a=Counter()
        a['itil_cases_with_original_source_receipt']=len(rows)
        a['cases_with_attention_rows']=sum(r['exact_key_equality_atencion']>0 for r in rows)
        a['cases_with_derivation_rows']=sum(r['exact_key_equality_derivacion']>0 for r in rows)
        a['cases_with_survey_rows']=sum(r['exact_key_equality_encuesta']>0 for r in rows)
        a['cases_with_one_derivation']=sum(r['exact_key_equality_derivacion']==1 for r in rows)
        a['cases_with_multiple_derivations']=sum(r['exact_key_equality_derivacion']>=2 for r in rows)
        a['attention_rows']=sum(r['exact_key_equality_atencion'] for r in rows)
        a['derivation_events']=sum(r['exact_key_equality_derivacion'] for r in rows)
        a['survey_rows']=sum(r['exact_key_equality_encuesta'] for r in rows)
        a['module_exact_key_rows_observed']=sum(r['modulo_key_row_match'] for r in rows)
        a['state_exact_key_rows_observed']=sum(r['estado_key_row_match'] for r in rows)
        a['derivation_event_creation_dates_present']=sum(
          bool(x['created_date_time_without_timezone'])
          for row in rows for x in index.events[row['case_sha256']])
        for typ,count in types.items():
            a['derivation_type_code_'+typ+'_rows']=count
        months[ym]=dict(sorted(a.items()))
        total.update(a)
    if total['itil_cases_with_original_source_receipt']!=900:
        raise ValueError('NOT_NINE_HUNDRED_ITIL_CASES')
    if total['derivation_events']!=sum(len(e) for e in index.events.values()):
        raise ValueError('DERIVATION_EVENTS_SOURCE_BOUNDARY_DRIFT')
    if total['cases_with_multiple_derivations']!=212:
        raise ValueError('MULTIPLE_DERIVATION_COHORT_DRIFT')
    return {
      'schema':SCHEMA,
      'qa_source':'ELSE70/dbITIL_D/dbo.taIncidente',
      'internal_child_sources':[
         'ELSE70/dbITIL_D/dbo.taIncidenteAtencion',
         'ELSE70/dbITIL_D/dbo.taIncidenteDerivacion',
         'ELSE70/dbITIL_D/dbo.taIncidenteEncuesta'],
      'unique_lookup_sources':[
         'ELSE70/dbITIL_D/dbo.taModulo',
         'ELSE70/dbITIL_D/dbo.gnEstadoIncidente'],
      'lifecycle_receipt_sha256':index.receipt_sha256,
      'derivation_events_receipt_sha256':index.events_receipt_sha256,
      'incident_records_verified':900,
      'all_nine_month_cohorts_hmac_verified':True,
      'sql_primary_key_shapes_verified':6,
      'sql_declared_foreign_keys_from_incident_tables':0,
      'native_key_equality_observed':True,
      'key_equality_does_not_certify_foreign_key':True,
      'type_codes_without_certified_semantic_dictionary':True,
      'derived_rows_do_not_certify_human_completion_or_repair':True,
      'business_domain_links_certified':0,
      'causes_certified':0,'repairs_certified':0,
      'business_changes_executed':0,
      'months':months,'totals':dict(sorted(total.items()))
    }

def main():
    p=argparse.ArgumentParser()
    for a in ('private','source','events-source','monthly-private','monthly-source','key','output'):
        p.add_argument('--'+a,required=True,type=Path)
    x=p.parse_args()
    index=VerifiedItILNativeLifecycle(
      private_root=x.private,reader_file=x.source,events_reader_file=x.events_source,
      monthly_root=x.monthly_private,month_source_file=x.monthly_source,key_file=x.key)
    doc=report(index)
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    print('ITIL_LIFECYCLE_900',json.dumps({
       'case_count':doc['incident_records_verified'],
       'derivation_events':doc['totals']['derivation_events'],
       'cases_with_multiple':doc['totals']['cases_with_multiple_derivations'],
       'state_lookups':doc['totals']['state_exact_key_rows_observed'],
       'module_lookups':doc['totals']['module_exact_key_rows_observed'],
       'foreign_keys_declared':doc['sql_declared_foreign_keys_from_incident_tables'],
       'business_causes_confirmed':doc['causes_certified']
    },ensure_ascii=False))
if __name__=='__main__':main()

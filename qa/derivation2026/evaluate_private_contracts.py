"""Aggregate signed module route declarations and unresolved derivation types.

Never publishes case hashes, names of specific users, raw SQL or monthly
private case entries; all route details remain in HMAC worker receipts.
"""
from __future__ import annotations
from argparse import ArgumentParser
from pathlib import Path
from collections import Counter
import json
from else_dominance.qa_derivation_contracts import VerifiedDerivationContracts
from else_dominance.qa_itil_native_lifecycle import VerifiedItILNativeLifecycle

def score(index:VerifiedDerivationContracts)->dict:
    counts={}
    for month in range(1,10):
        ym=f'2026-{month:02d}'
        rows=[r for r in index.rows.values() if r['month']==ym]
        if len(rows)!=100:
            raise ValueError('MODULE_ROUTE_MONTH_NOT_COMPLETE')
        counts[ym]={
          'cases':len(rows),
          'module_pk_matches':sum(bool(r['module_row_matched']) for r in rows),
          'service_pk_matches':sum(bool(r['service_row_matched']) for r in rows),
          'alias_bde_declared':sum(bool(r['module_declared_alias_bde']) for r in rows),
          'module_dll_declared':sum(bool(r['module_declared_dll']) for r in rows),
          'module_codes_unique':len(set(r['module_code'] for r in rows)),
          'physical_business_db_routes_certified':0,
          'official_business_fk_certified':0
        }
    total=Counter()
    for group in counts.values():
        for name,count in group.items():
            if name!='module_codes_unique':total[name]+=count
    if (total['cases']!=900 or total['module_pk_matches']!=900
        or total['service_pk_matches']!=900
        or total['alias_bde_declared']!=index.alias_count
        or total['module_dll_declared']!=index.dll_count):
        raise ValueError('MODULE_ROUTE_PUBLIC_AGGREGATE_DRIFT')
    report=index.summary()
    return {
      **report,
      'read_only_sources':['ELSE70/dbITIL_D/dbo.taIncidente',
        'ELSE70/dbITIL_D/dbo.taModulo',
        'ELSE70/dbITIL_D/dbo.taServicio',
        'ELSE70/dbITIL_D/dbo.taIncidenteDerivacion'],
      'module_and_service_relations':'OBSERVED_SAME_DATABASE_PRIMARY_KEY_MATCH_ONLY',
      'source_alias_bde_is_not_a_physical_database_route':True,
      'source_dll_name_is_not_execution_trace':True,
      'no_derivation_type_lookup_table_observed_in_signed_sql_probe':True,
      'sql_routine_definitions_not_found_in_metadata_probe':True,
      'other_application_definitions_not_examined_as_proof':True,
      'semantics_1':index.semantics('1'),
      'semantics_2':index.semantics('2'),
      'semantics_3':index.semantics('3'),
      'per_month':counts,
      'totals':dict(sorted(total.items())),
    }

def main():
    p=ArgumentParser()
    for arg in ('private','reader','route-reader','lifecycle-private',
                'lifecycle-reader','events-reader','month-private','month-reader',
                'key','output'):
        p.add_argument('--'+arg,required=True,type=Path)
    a=p.parse_args()
    lifecycle=VerifiedItILNativeLifecycle(
       private_root=a.lifecycle_private,
       reader_file=a.lifecycle_reader,events_reader_file=a.events_reader,
       monthly_root=a.month_private,month_source_file=a.month_reader,
       key_file=a.key)
    contracts=VerifiedDerivationContracts(
       private_root=a.private,metadata_source=a.reader,
       route_source=a.route_reader,monthly_root=a.month_private,
       month_reader=a.month_reader,signing_key=a.key,lifecycle=lifecycle)
    output=score(contracts)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print('APPLICATION_ROUTE_900',json.dumps({
       'case_count':output['case_count'],'modules':output['distinct_module_codes'],
       'pk_module':output['module_pk_matched'],'pk_service':output['service_pk_matched'],
       'alias_bde':output['alias_bde_declared_cases'],
       'dll':output['module_dll_declared_cases'],
       'types_unknown':output['type_semantics_unresolved'],
       'business_fk':output['business_fk_certified'],
       'business_repair':output['business_repairs_certified']
    },ensure_ascii=False))
if __name__=='__main__':main()

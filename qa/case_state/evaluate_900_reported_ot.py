"""Aggregate-only verified QA operational OT reads from signed ticket mentions.

A reported code is NOT an enterprise FK. No broad non-existence conclusions.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path

from else_dominance.qa_reported_ot_evidence import (
   VerifiedReportedOtIndex,CODE_FIELDS)

def score(index:VerifiedReportedOtIndex)->dict:
    by={}
    for month in range(1,10):
        ym=f"2026-{month:02d}"
        by[ym]=Counter()
        by[ym]['selected_itil_cases']=100
    for v in index.rows.values():
        ym=v['month']
        by[ym]['explicit_reported_ot_domain_queries']+=1
        by[ym]['reported_ot_row_found']+=v['row_count']==1
        by[ym]['no_row_in_probed_qa_table']+=v['row_count']==0
        if v['row_count']==1:
            for field in CODE_FIELDS:
                obs=index.inspect(case_sha256=v['case_sha256'],
                    module_code=v['case_module_code'],
                    as_of=ym+'-01',field=field)
                if (obs['status']!='READ_VERIFIED_REPORTED_OT_QA_FIELD'
                    or obs['row_count']!=1 or obs['formal_itil_ot_link_verified'] is not False):
                    raise ValueError('REPORTED_OT_DOMAIN_FIELD_NOT_BOUND')
                by[ym]['domain_fields_value_verified']+=1
    total=Counter()
    for v in by.values():total.update(v)
    if (total['explicit_reported_ot_domain_queries']!=index.reported
        or total['reported_ot_row_found']!=index.found
        or total['no_row_in_probed_qa_table']!=index.empty
        or total['domain_fields_value_verified']!=index.found*len(CODE_FIELDS)):
        raise ValueError('REPORTED_OT_AGGREGATE_SCOPE_DRIFT')
    return {
       'schema':'else.itil.qa.2026-reported-ot-900-domain-proof-summary.v1',
       'source':'ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo',
       'source_ticket_table':'ELSE70/dbITIL_D/dbo.taIncidente',
       'receipt_sha256':index.receipt_sha256,
       'itil_cases_scanned':900,
       'queries_exact_reported_identifier':index.reported,
       'excluded_ambiguous_reported_identifiers':index.ambiguous,
       'excluded_other_company':index.other_company,
       'no_explicit_identifier':index.no_code,
       'domain_records_returned_one_row':index.found,
       'domain_queries_zero_rows':index.empty,
       'domain_exact_field_values_verified':index.found*len(CODE_FIELDS),
       'formal_ITIL_OT_join_verified':False,
       'root_causes_verified':0,
       'repairs_executed':0,
       'modifications':0,
       'note':'Identifier is reported in ticket text; not a certified FK. Zero rows only covers this table at QA read time.',
       'months':{k:dict(sorted(v.items())) for k,v in by.items()}
    }

def main():
    p=argparse.ArgumentParser()
    for name in ('private','source','monthly-private','monthly-source','key','output'):
        p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args()
    index=VerifiedReportedOtIndex(private_root=a.private,source_file=a.source,
        month_private=a.monthly_private,month_source=a.monthly_source,
        key_file=a.key)
    result=score(index)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in (
        'itil_cases_scanned','queries_exact_reported_identifier',
        'domain_records_returned_one_row','domain_queries_zero_rows',
        'domain_exact_field_values_verified','formal_ITIL_OT_join_verified',
        'root_causes_verified','repairs_executed')},ensure_ascii=False))
if __name__=='__main__':main()

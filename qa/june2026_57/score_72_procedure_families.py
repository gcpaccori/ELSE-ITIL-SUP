"""Count *families* rather than cases among 72 May→June SQL references.

Historical note references are posthoc, never a blind predictor or a
certificate that the indicated SQL was executed. Case and history hashes
are reverified against two separately signed June QA receipts.
"""
from __future__ import annotations
from argparse import ArgumentParser
from pathlib import Path
from collections import defaultdict,Counter
from hashlib import sha256
import json
from qa.monthend2026.evaluate_monthend import verify_one
from else_dominance.historical_procedures import extract_note_mentions

SCHEMA='else.itil.qa.2026-june72-historical-procedure-families.v1'

def score(repo:Path,private:Path,keyfile:Path)->dict:
    key=keyfile.read_bytes()
    src_code_sha=sha256((repo/'qa/june2026/JuneAllRead.cs').read_bytes()).hexdigest()
    requests,req_sha=verify_one(private/'juneall_202606.private.json',
       key,src_code_sha,'else.itil.qa.2026-juneall-source.v1',
       'else.itil.qa.2026-juneall-source-hmac.v1')
    history,hist_sha=verify_one(private/'juneall_202606_history.private.json',
       key,src_code_sha,'else.itil.qa.2026-juneall-history.v1',
       'else.itil.qa.2026-juneall-history-hmac.v1')
    labels=json.loads((private/'june1621_may500_case_labels.private.json').read_bytes())
    previous=json.loads((repo/'data/2026_june_all_1621_may500_historical_transfer.json').read_bytes())
    if (previous['june_request_receipt_sha256']!=req_sha
       or previous['june_history_receipt_sha256']!=hist_sha
       or previous['train_count']!=500 or previous['test_count']!=1621
       or previous['totals']['exact_kind_table_fields']!=72
       or len(labels['cases'])!=1621
       or len(requests['results'])!=1621
       or len(history['historical_records'])!=1621):
        raise ValueError('FAMILY_SCORER_SOURCE_PROVENANCE_INVALID')
    family_cases=defaultdict(set)
    per_table=defaultdict(set)
    selected=[]
    for item in labels['cases']:
        if not item['flags']['exact_kind_table_fields']:continue
        rank=item['rank']
        req=requests['results'][rank-1]
        gold=history['historical_records'][rank-1]
        if (req['rank']!=rank or gold['rank']!=rank
           or len({req['case_sha256'],gold['case_sha256'],item['case_sha256']})!=1):
            raise ValueError('FAMILY_SCORER_CASE_NOT_IDENTITY_BOUND')
        notes=extract_note_mentions(gold['historical_solution_redacted'])
        if not notes:raise ValueError('FAMILY_SCORER_GOLD_WITHOUT_STRUCTURED_REFERENCES')
        selected.append(rank)
        for n in notes:
            table=n['table'].lower()
            kind=n['kind']
            fields=tuple(sorted(n['fields']))
            family=(table,kind,fields)
            family_cases[family].add(rank)
            per_table[table].add(rank)
    if len(selected)!=72 or len(set(selected))!=72 or len(family_cases)!=13:
        raise ValueError('FAMILY_SCORER_FROZEN_COUNTS_CHANGED')
    families=[
      {'table':table,'operation':kind,'fields':list(fields),
       'unique_cases_mentioning_family':len(ranks),
       'executed_transaction_proven':False}
      for (table,kind,fields),ranks in sorted(
          family_cases.items(),key=lambda x:(-len(x[1]),x[0][0],x[0][1],x[0][2]))
    ]
    counts={
        'cases_selected':len(selected),
        'canonical_procedure_families':len(families),
        'case_family_memberships':sum(len(v) for v in family_cases.values()),
        'collection_cases':len(per_table['tacobranza']),
        'commercial_ot_cases':len(per_table['taordentrabajo']),
        'document_attachment_cases':len(per_table['tadocumentotramiteadjunto']),
        'reconnection_procedure_cases':len(per_table['spregistrarotreconexion']),
        'other_cases':len(selected)-len(
           per_table['tacobranza']|per_table['taordentrabajo']),
        'historical_transactions_certified':0,
        'enterprise_repairs_certified':0,
    }
    if (counts['collection_cases']!=35 or counts['commercial_ot_cases']!=22
       or counts['document_attachment_cases']!=10
       or counts['reconnection_procedure_cases']!=4
       or counts['other_cases']!=15
       or counts['case_family_memberships']!=76
       or families[0]['table']!='tacobranza'
       or families[0]['operation']!='UPDATE_MENTIONED'
       or families[0]['fields']!=['codigocaja']
       or families[0]['unique_cases_mentioning_family']!=35):
        raise ValueError('FAMILY_SCORER_OBSERVED_RESULTS_CHANGED')
    return {
       'schema':SCHEMA,
       'period':'2026-06',
       'source_month':'2026-05',
       'model_training_prior_cases':500,
       'evaluated_june_original_cases':1621,
       'selection_is_posthoc_documentary_overlap':True,
       'same_case_history_never_available_during_blind_authoring':True,
       'procedural_signature_is_table_kind_set_fields_not_exact_business_action':True,
       'sql_reference_is_not_execution':True,
       'source_receipt_sha256':req_sha,
       'history_receipt_sha256':hist_sha,
       'counts':counts,
       'families':families,
    }

def main():
    p=ArgumentParser()
    for name in ('repo','private','key','output'):
        p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args()
    report=score(a.repo,a.private,a.key)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('JUNE72_SIGNATURE_FAMILY_QA',json.dumps(report['counts'],ensure_ascii=False))
if __name__=='__main__':main()

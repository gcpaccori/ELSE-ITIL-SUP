"""Verify 2026 per-month latest-100 QA receipts and score request-vs-history.

Requests and historical solutions are separate HMAC-verified data products.
All comparisons are lexical/structural, never certified causal correctness.
Only month-level aggregate metrics are published to the repo. Individual
case indicators stay in the caller's protected --private directory.
"""
from __future__ import annotations
import argparse,hmac,json
from collections import Counter,defaultdict
from hashlib import sha256
from pathlib import Path
from else_dominance.functional_domain_v2 import route_with_verified_module
from else_dominance.historical_procedures import (
    HistoricalProcedureCatalog, extract_note_mentions)
from else_dominance.historical_mechanism_matching import (
    MechanismIndex,mentioned_in_history,explicitly_supported_in_request)

SCHEMA='else.itil.qa.2026-monthend100-multimonth-audit.v1'

def verify_one(path:Path,key:bytes,source_sha:str,expected_schema:str,expected_proof:str)->tuple[dict,str]:
    raw=path.read_bytes()
    doc=json.loads(raw)
    proof=json.loads((path.parent/(path.name+'.proof.json')).read_bytes())
    digest=sha256(raw).hexdigest()
    if (doc['schema']!=expected_schema or proof['schema']!=expected_proof
       or proof['source_sha256']!=source_sha or doc['source_sha256']!=source_sha
       or proof['receipt_sha256']!=digest or proof['read_only'] is not True
       or doc['read_only'] is not True):
        raise ValueError('QA_MONTHLY_RECEIPT_IDENTITY_MISMATCH')
    msg=f"{doc['schema']}:{source_sha}:{digest}".encode()
    if len(key)!=32 or not hmac.compare_digest(
        hmac.new(key,msg,'sha256').hexdigest(),proof['hmac_sha256']):
        raise ValueError('QA_MONTHLY_RECEIPT_HMAC_INVALID')
    return doc,digest

def labels_only_count(rows:list[dict],catalog:HistoricalProcedureCatalog,
                      mechanism_index:MechanismIndex,module_dir:dict)->tuple[dict,list[dict]]:
    totals=Counter()
    case_labels=[]
    for row in rows:
        request=row['request']
        gold=row['gold']
        code=request['module_code']
        if code not in module_dir:
            raise ValueError('MONTHLY_MODULE_NOT_FOUND_IN_CORPORATE_DIRECTORY')
        if row['module_mismatch'] or request['case_sha256']!=gold['case_sha256']:
            raise ValueError('MONTHLY_SOURCE_HISTORY_MISMATCH')
        text=request['description_redacted']
        historic=gold['historical_solution_redacted']
        domain=route_with_verified_module(text,module_name=module_dir[code])
        old=catalog.describe(code)
        new=catalog.describe_for_request(code,text)
        legacy=old.get('candidate_patterns',[])
        anchored=new.get('request_grounded_patterns',[])
        past={(x['kind'],x['table'],tuple(x['fields'])) for x in legacy}
        scoped={(x['kind'],x['table'],tuple(x['fields'])) for x in anchored}
        observed=extract_note_mentions(historic)
        actual={(x['kind'],x['table'],tuple(x['fields'])) for x in observed}
        direct=set(explicitly_supported_in_request(text))
        gold_mech=set(mentioned_in_history(historic))
        matched_mech=set(x['mechanism'] for x in mechanism_index.suggest(code,text).get('candidates',[]))
        flags={
            'routed':domain['domain']!='UNKNOWN',
            'llm_input_eligible':domain['domain']!='UNKNOWN' and len(text.strip())>=35,
            'history_nonempty':bool(historic.strip()),
            'prior_unanchored_sql':bool(past),
            'prior_request_anchored_sql':bool(scoped),
            'gold_sql_mentions':bool(actual),
            'unanchored_sql_overlap':bool(actual&past),
            'anchored_sql_overlap':bool(actual&scoped),
            'request_direct_mechanism':bool(direct),
            'gold_mechanism_mentioned':bool(gold_mech),
            'request_history_mechanism_overlap':bool(direct&gold_mech),
            'historical_prior_mechanism_candidate':bool(matched_mech),
            'historical_prior_mechanism_gold_overlap':bool(matched_mech&gold_mech),
            'gold_any_structured':bool(actual or gold_mech),
        }
        for key,value in flags.items():
            totals[key]+=bool(value)
        totals['cases']+=1
        totals['history_answer_date']+=bool(gold['answer_date_present'])
        totals['history_close_date']+=bool(gold['close_date_present'])
        case_labels.append({
            'rank':request['rank'],'case_sha256':request['case_sha256'],
            'module_code':code,'route_domain':domain['domain'],
            'request_explicit_mechanisms':sorted(direct),
            'gold_mentioned_mechanisms':sorted(gold_mech),
            'prior_scoped_mechanisms':sorted(matched_mech),
            'flags':flags,
            'actual_root_cause_proven':False,
            'historical_change_executed_proven':False,
        })
    return dict(sorted(totals.items())),case_labels

def audit(private:Path,reader:Path,key:bytes,modules:Path,
          catalog:HistoricalProcedureCatalog,mechanism_index:MechanismIndex)->tuple[dict,dict]:
    source_sha=sha256(reader.read_bytes()).hexdigest()
    module_raw=json.loads(modules.read_bytes())
    directory={x['codigo_modulo_trimmed_for_repo_name']:x['nombre_modulo_itil'] for x in module_raw}
    months={}
    case_labels={}
    seen=set()
    closed=0
    for mm in range(1,12):
        month=f'2026-{mm:02d}'
        file_month=month.replace('-','')
        base=private/f'monthend_{file_month}.private.json'
        orig,o_sha=verify_one(base,key,source_sha,
              'else.itil.qa.2026-monthend100-source.v1',
              'else.itil.qa.2026-monthend100-source-hmac.v1')
        gold,g_sha=verify_one(private/f'monthend_{file_month}_history.private.json',key,source_sha,
              'else.itil.qa.2026-monthend100-history.v1',
              'else.itil.qa.2026-monthend100-history-hmac.v1')
        n=orig['selected']
        if (n!=min(orig['month_records'],100)
           or len(orig['results'])!=n or len(gold['historical_records'])!=n
           or gold['historical_count']!=n or gold['cohort_source_sha256']!=o_sha
           or orig['period']!=month or gold['period']!=month
           or orig['history_or_resolution_read'] is not False
           or gold['solutions_not_in_model_input'] is not True
           or orig['business_modifications']!=0 or gold['business_modifications']!=0):
            raise ValueError('MONTHLY_SQL_COHORT_SOURCE_BINDING_FAILED')
        for a,b in zip(orig['results'],gold['historical_records']):
            if a['case_sha256']!=b['case_sha256'] or a['case_sha256'] in seen:
                raise ValueError('MONTHLY_DUPLICATE_OR_GOLD_REBOUND')
            seen.add(a['case_sha256'])
        if mm<11:
            closed+=n
        if n:
            opened=[a['opened_at'] for a in orig['results']]
            if opened!=sorted(opened,reverse=True):
                # For equal timestamp, the original SQL also sorts by descending
                # incident ID (not present as plaintext), validated by Windows worker.
                raise ValueError('MONTHLY_DATE_ORDER_BROKEN')
            records=[
                {'request':a,'gold':b,'module_mismatch':False}
                for a,b in zip(orig['results'],gold['historical_records'])]
            score,case_result=labels_only_count(records,catalog,mechanism_index,directory)
        else:
            score={'cases':0}
            case_result=[]
        months[month]={
          'status':('NO_QA_INCIDENT_RECORDS' if n==0 else
                   'MONTH_INCOMPLETE_CUTOFF' if mm==11 else 'EVALUATED_FROM_QA'),
          'month_closed':mm<11,
          'month_qa_total':orig['month_records'],
          'selected_latest':n,'source_receipt_sha256':o_sha,
          'history_receipt_sha256':g_sha,
          'last_opened_at':orig['results'][0]['opened_at'] if n else None,
          **score
        }
        case_labels[month]=case_result
    assert len(seen)==sum(v['selected_latest'] for v in months.values())
    report={
      'schema':SCHEMA,
      'data_source':'ELSE70/dbITIL_D/dbo.taIncidente',
      'order':'FechaSolicitud DESC, CodigoIncidente DESC',
      'date_asof':'2026-11-12',
      'months_2026_covered':11,
      'december':'FUTURE_NOT_EVALUATED',
      'valid_months_with_100':sum(v['selected_latest']==100 for v in months.values()),
      'incidents_source_bound':len(seen),
      'month_receipts_verified':22,
      'catalog_source_train_cases':300,
      'request_and_gold_separate':True,
      'scoring_is_structural_and_lexical_not_full_llm':True,
      'historical_sql_mentions_are_not_executed_changes':True,
      'actual_cause_certified':0,
      'repairs_executed':0,
      'months':months,
    }
    return report,case_labels

def main():
    p=argparse.ArgumentParser()
    for field in ('private','reader','key','module-dir','catalog','mechanism-index','output'):
        p.add_argument('--'+field,required=True,type=Path)
    a=p.parse_args()
    report,labels=audit(
        a.private,a.reader,a.key.read_bytes(),a.module_dir,
        HistoricalProcedureCatalog(a.catalog),MechanismIndex(a.mechanism_index))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    private_out=a.private/'monthend_2026_case_labels.private.json'
    private_out.write_text(json.dumps({'schema':SCHEMA,'months':labels},ensure_ascii=False,indent=2)+'\n')
    private_out.chmod(0o600)
    for month,x in report['months'].items():
        print(json.dumps({'month':month,'qa_total':x['month_qa_total'],
             'selected':x['selected_latest'],
             'routed':x.get('routed',0),
             'request_anchored_sql':x.get('prior_request_anchored_sql',0),
             'gold_sql_mentions':x.get('gold_sql_mentions',0),
             'strict_sql_overlap':x.get('anchored_sql_overlap',0),
             'gold_mechanism':x.get('gold_mechanism_mentioned',0),
             'strict_prior_mechanism_match':x.get('historical_prior_mechanism_gold_overlap',0)}))
    print('AUDIT_TOTAL',report['incidents_source_bound'],report['month_receipts_verified'])
if __name__=='__main__':main()

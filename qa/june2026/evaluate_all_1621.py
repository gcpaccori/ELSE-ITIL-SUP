"""June 2026 complete HMAC-bound historical contrast, read-only.

ALL June tickets are classified deterministically using only the signed
original request, module directory, and May historic precedents (earlier).
The sealed same-case June historical solution is opened only in the
evaluation phase. Outcomes are provisional historical concordance signals,
NOT proof of corporate writes, repairs, verified causes, or valid SQL.

Public JSON is aggregate-only; private per-ticket ledger stays on server.
"""
from __future__ import annotations
from argparse import ArgumentParser
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,re

from qa.monthend2026.evaluate_monthend import verify_one
from else_dominance.functional_domain_v2 import route_with_verified_module,route
from else_dominance.historical_procedures import HistoricalProcedureCatalog,extract_note_mentions
from else_dominance.historical_mechanism_matching import (
    MechanismIndex,explicitly_supported_in_request,mentioned_in_history)

SRC_SCHEMA='else.itil.qa.2026-juneall-source.v1'
GOLD_SCHEMA='else.itil.qa.2026-juneall-history.v1'
SRC_PROOF='else.itil.qa.2026-juneall-source-hmac.v1'
GOLD_PROOF='else.itil.qa.2026-juneall-history-hmac.v1'
REPORT_SCHEMA='else.itil.qa.2026-juneall-historical-contrast.v1'

SQL_PATTERN=re.compile(
    r'\b(?:update\s+\w+|select\s+|delete\s+from|insert\s+into|exec(?:ute)?\s+\w+|'
    r'alter\s+(?:table|procedure)|merge\s+into)\b',re.I)
CLOSURE_GENERIC=re.compile(
    r'^\s*(?:incidente\s+(?:cerrado|atendido|solucionado)|'
    r'se\s+(?:ha\s+)?(?:realiz[oó]|procedi[oó]|atendi[oó]|solucion[oó])\s+lo\s+solicitado\.?|'
    r'se\s+brind[oó]\s+el\s+soporte\s+(?:correspondiente|solicitado)\.?|'
    r'solucionado\.?|atendido\.?|'
    r'problema\s+solucionado\.?|se\s+ha\s+corregido\s+el\s+incidente\.?)\s*$',re.I)
INSTRUCTION=re.compile(
    r'\b(?:por favor|se requiere|debe(?:rá|n)?\s+|se solicita|solicito|'
    r'reintente|favor\s+de|realizar\s+pruebas|'
    r'se recomienda|verifique|verificar\s+(?:que|si))\b',re.I)
ACTION_PAST=re.compile(
    r'\b(?:se\s+(?:ha\s+)?(?:actualiz[oó]|corrigi[oó]|corregido|realiz[oó]|modific[oó]|'
    r'registr[oó]|configur[oó]|habilit[oó]|asign[oó]|gener[oó]|traslad[oó]|'
    r'reinici[oó]|liber[oó]|elimin[oó])|'
    r'hemos\s+(?:actualizado|corregido|configurado)|'
    r'ya\s+(?:est[aá]|se\s+encuentra)\s+)\b',re.I)

def note_buckets(note:str)->dict[str,bool]:
    text=note.strip()
    return {
        'empty_note':not bool(text),
        'sql_text_only':bool(SQL_PATTERN.search(text)),
        'generic_closure':bool(CLOSURE_GENERIC.fullmatch(text)),
        'narrated_action':bool(ACTION_PAST.search(text)),
        'instruction_or_recommendation':bool(INSTRUCTION.search(text)),
        'has_technical_details':bool(re.search(
            r'\b(?:codigo|estado|error|fecha|periodo|m[oó]dulo|perfil|'
            r'caja|cobranza|orden|lectura|suministro|servicio|'
            r'contrasena|contraseña|correo|impresora|conexion|conexi[oó]n)\b',
            text,re.I)),
        'longer_than_75':len(text)>=75,
    }

def audit(private:Path,reader:Path,monthly_private:Path,monthly_reader:Path,
          key:bytes,module_dir:Path,prior_mechanisms:Path,prior_patterns:Path,
          ledger:Path)->dict:
    read_sha=sha256(reader.read_bytes()).hexdigest()
    source,source_sha=verify_one(private/'juneall_202606.private.json',
       key,read_sha,SRC_SCHEMA,SRC_PROOF)
    gold,gold_sha=verify_one(private/'juneall_202606_history.private.json',
       key,read_sha,GOLD_SCHEMA,GOLD_PROOF)
    monthly_sha=sha256(monthly_reader.read_bytes()).hexdigest()
    prior,prior_sha=verify_one(monthly_private/'monthend_202606.private.json',
       key,monthly_sha,
       'else.itil.qa.2026-monthend100-source.v1',
       'else.itil.qa.2026-monthend100-source-hmac.v1')
    prior_gold,prior_gold_sha=verify_one(
       monthly_private/'monthend_202606_history.private.json',
       key,monthly_sha,
       'else.itil.qa.2026-monthend100-history.v1',
       'else.itil.qa.2026-monthend100-history-hmac.v1')
    if (source['period']!='2026-06'
       or source['month_closed'] is not True
       or source['start']!='2026-06-01'
       or source['end_exclusive']!='2026-07-01'
       or source['selection']!='ALL_JUNE_FECHA_SOLICITUD_DESC_CODIGO_INCIDENTE_DESC'
       or source['month_records']!=1621
       or source['selected']!=1621
       or gold['historical_count']!=1621
       or gold['cohort_source_sha256']!=source_sha
       or source['history_or_resolution_read'] is not False
       or gold['solutions_not_in_model_input'] is not True
       or source['business_modifications']!=0
       or gold['business_modifications']!=0):
        raise ValueError('JUNE_FULL_RECEIPT_SELECTION_NOT_FROZEN')
    requests=source['results']
    golds=gold['historical_records']
    if len(requests)!=1621 or len(golds)!=1621:
        raise ValueError('JUNE_EXPECTED_ALL_CASES_MISSING')
    for i in range(100):
        if (requests[i]['case_sha256']!=prior['results'][i]['case_sha256'] or
            requests[i]['description_sha256']!=prior['results'][i]['description_sha256'] or
            golds[i]['historical_solution_sha256']!=prior_gold['historical_records'][i]['historical_solution_sha256']):
            raise ValueError('JUNE_PREVIOUS_FROZEN_LAST100_MISMATCH')
    original_dir=json.loads(module_dir.read_bytes())
    modules={x['codigo_modulo_trimmed_for_repo_name']:x['nombre_modulo_itil'] for x in original_dir}
    mechanisms=MechanismIndex(prior_mechanisms)
    patterns=HistoricalProcedureCatalog(prior_patterns)
    perweek={f'week_{i}':Counter() for i in range(1,6)}
    total=Counter()
    by_domain=Counter()
    by_company=Counter()
    individual=[]
    seen=set()
    for i,(r,g) in enumerate(zip(requests,golds)):
        case=r['case_sha256']
        if (case in seen or r['rank']!=i+1 or g['rank']!=i+1
            or g['case_sha256']!=case
            or r['historical_solution_not_read'] is not True
            or r['read_only'] is not True
            or not r['opened_at'].startswith('2026-06')):
            raise ValueError('JUNE_CASE_GOLD_ID_OR_DATE_DRIFT')
        seen.add(case)
        text=r['description_redacted']
        # Important: first the blind prediction (no gold variable is accessed).
        module_known=r['module_code'] in modules
        route_decision=(route_with_verified_module(text,module_name=modules[r['module_code']])
                    if module_known else route(text))
        direct=set(explicitly_supported_in_request(text))
        prior_mech=mechanisms.suggest(r['module_code'],text)
        prior_suggested={x['mechanism'] for x in prior_mech.get('candidates',[])}
        grounded=patterns.describe_for_request(r['module_code'],text)
        pattern_count=len(grounded.get('request_grounded_patterns',[]))
        # After all request-only predictions are frozen above, score history.
        history=g['historical_solution_redacted']
        gold_mech=set(mentioned_in_history(history))
        sql_mentions=extract_note_mentions(history)
        predicted_sql=grounded.get('request_grounded_patterns',[])
        predicted_exact={(x['kind'],x['table'],tuple(x['fields'])) for x in predicted_sql}
        historical_exact={(x['kind'],x['table'],tuple(x['fields'])) for x in sql_mentions}
        predicted_table_kind={(x['kind'],x['table']) for x in predicted_sql}
        historical_table_kind={(x['kind'],x['table']) for x in sql_mentions}
        exact_structured_sql_overlap=predicted_exact&historical_exact
        same_table_kind_overlap=predicted_table_kind&historical_table_kind
        buckets=note_buckets(history)
        week=min(5,(int(r['opened_at'][8:10])-1)//7+1)
        flags={
            'evaluated':True,
            'request_nonempty':bool(text.strip()),
            'known_corporate_module':module_known,
            'domain_routed':route_decision['domain']!='UNKNOWN',
            'eligible_for_blind_llm':module_known and route_decision['domain']!='UNKNOWN' and len(text.strip())>=35,
            'history_nonempty':bool(history.strip()),
            'history_answer_date_present':g['answer_date_present'],
            'history_close_date_present':g['close_date_present'],
            'request_explicit_mechanism':bool(direct),
            'history_named_mechanism':bool(gold_mech),
            'request_and_history_mechanism_overlap':bool(direct&gold_mech),
            'prior_may_historical_suggestion':bool(prior_suggested),
            'prior_may_mechanism_and_gold_overlap':bool(prior_suggested&gold_mech),
            'prior_may_sql_pattern_request_anchored':pattern_count>0,
            'historical_sql_mention_structured':bool(sql_mentions),
            'pre_june_request_grounded_and_gold_both_sql':bool(predicted_sql and sql_mentions),
            'pre_june_same_sql_table_and_kind':bool(same_table_kind_overlap),
            'pre_june_exact_sql_table_fields_and_kind':bool(exact_structured_sql_overlap),
            **buckets,
        }
        for k,v in flags.items():
            total[k]+=bool(v)
            perweek[f'week_{week}'][k]+=bool(v)
        by_domain[route_decision['domain']]+=1
        by_company[r['company']]+=1
        individual.append({
          'rank':i+1,'case_sha256':case,
          'request_source_receipt_sha256':source_sha,
          'gold_source_receipt_sha256':gold_sha,
          'company':r['company'],
          'module_code':r['module_code'],
          'route_domain':route_decision['domain'],
          'direct_request_mechanisms':sorted(direct),
          'historical_mechanism_mentions':sorted(gold_mech),
          'pre_june_may_mechanism_candidates':sorted(prior_suggested),
          'historical_sql_mention_count':len(sql_mentions),
          'request_grounded_historical_pattern_count':pattern_count,
          'historical_overlap_exact_table_fields_kind':bool(exact_structured_sql_overlap),
          'historical_overlap_table_kind':bool(same_table_kind_overlap),
          'flags':flags,
          'repair_executed_verified':False,
          'historical_note_proves_cause':False,
        })
    if len(seen)!=1621 or total['evaluated']!=1621:
        raise ValueError('JUNE_NOT_ALL_CASES_EVALUATED')
    if total['history_nonempty']!=gold['historical_nonempty'] or (
        total['history_answer_date_present']!=gold['answer_date_present']) or (
        total['history_close_date_present']!=gold['close_date_present']):
        raise ValueError('JUNE_HISTORICAL_AGGREGATE_NOT_BOUND')
    if (sum(by_domain.values())!=1621
       or sum(by_company.values())!=1621
       or sum(x['evaluated'] for x in perweek.values())!=1621):
        raise ValueError('JUNE_GROUP_TOTALS_NOT_BOUND')
    ledger.parent.mkdir(parents=True,exist_ok=True)
    ledger.write_text(json.dumps({
        'schema':'else.itil.qa.2026-juneall-private-ledger.v1',
        'source_sha256':source_sha,'gold_sha256':gold_sha,
        'cases':individual},ensure_ascii=False,separators=(',',':')))
    ledger.chmod(0o600)
    return {
        'schema':REPORT_SCHEMA,
        'period_start':'2026-06-01','period_end_exclusive':'2026-07-01',
        'qa_source':'ELSE70/dbITIL_D/dbo.taIncidente',
        'selection':'ALL_1621_JUNE_INCIDENTS',
        'all_june_hmac_verification':'PASS',
        'previous_last100_independently_sealed_matches':100,
        'case_identity_bindings_verified':1621,
        'request_source_receipt_sha256':source_sha,
        'historical_source_receipt_sha256':gold_sha,
        'history_hidden_during_blind_request_routing':True,
        'precedent_training':'MAY_2026_FIRST_300_ONLY',
        'earlier_may_training_not_june_holdout':True,
        'all_request_mechanism_and_history_mechanism_matches_lexical_only':True,
        'no_claim_that_sql_in_note_was_executed':True,
        'no_claim_that_closed_date_is_repair':True,
        'business_writes_executed':0,
        'real_remediations_certified':0,
        'source_cases':1621,
        'totals':dict(sorted(total.items())),
        'companies':dict(sorted(by_company.items())),
        'domains':dict(sorted(by_domain.items())),
        'weeks':{k:dict(sorted(v.items())) for k,v in perweek.items()},
    }

def main():
    p=ArgumentParser()
    for name in ('private','reader','monthly-private','monthly-reader',
                 'key','module-dir','prior-mechanisms','prior-patterns','private-ledger','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    result=audit(a.private,a.reader,a.monthly_private,a.monthly_reader,
          a.key.read_bytes(),a.module_dir,a.prior_mechanisms,
          a.prior_patterns,a.private_ledger)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('JUNE_ALL_N',result['source_cases'])
    print('JUNE_ALL_TOTALS',json.dumps(result['totals'],ensure_ascii=False,sort_keys=True))
    print('DOMAINS',json.dumps(result['domains'],ensure_ascii=False))
    print('COMPANIES',json.dumps(result['companies'],ensure_ascii=False))
if __name__=='__main__':main()

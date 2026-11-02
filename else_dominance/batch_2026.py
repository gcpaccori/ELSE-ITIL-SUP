"""Fail-closed batch runner: individual tickets stay in an authorized environment.

No user/password/solution text may be exported to the summary. A 2026 gold label
is excluded from model context. Resume uses stable case IDs. The run itself is
interactive/synchronous; this module does not schedule or launch jobs.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from datetime import datetime
from .agent import InvestigationAgent
from .engineer import ResolutionGate

FORBIDDEN_HOLDOUT_FIELDS={'solution_text','DescripcionSolucion','actual_solution','gold_action','historical_solution','analyst_solution'}

class HoldoutBatch:
    def __init__(self, agent:InvestigationAgent, gate:ResolutionGate, *, now:str):
        self.agent=agent;self.gate=gate;self.now=now

    @staticmethod
    def validate_case(raw:dict)->dict:
        if not isinstance(raw,dict):raise ValueError('CASE_NOT_DICT')
        if FORBIDDEN_HOLDOUT_FIELDS.intersection(raw):raise ValueError('GOLD_SOLUTION_PRESENT_IN_INPUT')
        if raw.get('privacy_reviewed') is not True:raise ValueError('PRIVACY_REVIEW_REQUIRED')
        ref=str(raw.get('case_ref') or '')
        if not ref.startswith('itil-'):raise ValueError('CASE_REF_REQUIRED')
        time=str(raw.get('opened_at') or '')
        opened=datetime.fromisoformat(time)
        if opened.year!=2026:raise ValueError('NOT_2026')
        if not str(raw.get('description') or '').strip():raise ValueError('EMPTY_REQUEST')
        if not str(raw.get('service_code') or '').strip():raise ValueError('SERVICE_REQUIRED')
        return {'case_ref':ref,'description':str(raw['description'])[:6000],
                'service_code':str(raw['service_code']),'module_code':str(raw.get('module_code') or ''),
                'classification_code':str(raw.get('classification_code') or ''),
                'system_version':str(raw.get('system_version') or 'UNKNOWN'),
                'as_of':opened.strftime('%Y-%m-%dT%H:%M:%S'),
                'opened_at':opened.strftime('%Y-%m-%dT%H:%M:%S')}

    def run(self, input_jsonl:str|Path, output_jsonl:str|Path, *, max_cases:int=0)->dict:
        source=Path(input_jsonl);target=Path(output_jsonl)
        # Fail closed on accidental cross-environment outputs.
        if source.resolve()==target.resolve():raise ValueError('SAME_INPUT_OUTPUT')
        target.parent.mkdir(parents=True,exist_ok=True)
        seen=set()
        if target.exists():
            for line in target.read_text('utf-8').splitlines():
                if line.strip():seen.add(json.loads(line)['case_ref'])
        attempted=done=skipped=failed=0
        counts=Counter()
        with source.open(encoding='utf-8') as f,target.open('a',encoding='utf-8') as g:
            for line in f:
                if not line.strip():continue
                case=self.validate_case(json.loads(line))
                if case['case_ref'] in seen:skipped+=1;continue
                if max_cases and attempted>=max_cases:break
                attempted+=1
                try:
                    raw=self.agent.investigate(case,now=self.now)
                    dossier=self.gate.audit(raw,case)
                    # Keep detailed dossier ONLY in the authorized output file.
                    g.write(json.dumps({'case_ref':case['case_ref'],'month':case['opened_at'][:7],
                        'status':dossier['status_operativo'],'dossier':dossier,
                        'trace':{'invalid_refs':raw.get('invalid_references',[]),
                            'tool_calls':raw.get('tool_calls',0)}},ensure_ascii=False)+'\n')
                    counts[(case['opened_at'][:7],dossier['status_operativo'])]+=1
                    done+=1
                except Exception as e:
                    failed+=1
                    # Deliberately no incident text, username, or secret in error output.
                    g.write(json.dumps({'case_ref':case['case_ref'],'month':case['opened_at'][:7],
                        'status':'ERROR','error_class':type(e).__name__})+'\n')
                    counts[(case['opened_at'][:7],'ERROR')]+=1
                seen.add(case['case_ref']);g.flush()
        return {'evaluated_this_run':done,'errors_this_run':failed,'resumed_skipped':skipped,
                'aggregate_by_month_status':[{'month':m,'status':s,'count':v} for (m,s),v in sorted(counts.items())],
                'certainty':'LLM_HYPOTHESES_NOT_CERTIFIED_FIXES',
                'note':'Detailed case text remains in private output. No credentials or DB mutations were requested.'}

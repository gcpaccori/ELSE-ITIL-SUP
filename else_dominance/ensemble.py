"""Combine independently validated LLM plans without claiming incident resolution."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import argparse
import json


def _read(path):
    result = {}
    binding = None
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        key = item['case_ref']
        if key in result and result[key].get('status')!='MODEL_ERROR':
            raise ValueError('DUPLICATE_CASE_REF')
        run_binding = item.get('run_binding')
        if not run_binding:
            raise ValueError('MISSING_RUN_BINDING')
        if binding is None:
            binding = run_binding
        if binding != run_binding:
            raise ValueError('MIXED_INPUT_BINDINGS')
        result[key] = item
    return result, binding


def _valid(item):
    return item.get('status') == 'PLAN_REVIEWABLE' and item.get('hard_gate', {}).get('valid') is True


def combine(primary_path, secondary_path, output_path, expected_count):
    a, key_a = _read(primary_path)
    b, key_b = _read(secondary_path)
    if key_a != key_b:
        raise ValueError('CROSS_MODEL_INPUT_MISMATCH')
    if set(a) != set(b):
        raise ValueError('CROSS_MODEL_COHORT_MISMATCH')
    if expected_count and len(a) != expected_count:
        raise ValueError('COHORT_COUNT_MISMATCH')
    output_path = Path(output_path)
    if output_path.resolve() in {Path(primary_path).resolve(), Path(secondary_path).resolve()}:
        raise ValueError('OUTPUT_OVERWRITES_INPUT')
    decisions = []
    for case_ref in sorted(a):
        x, y = a[case_ref], b[case_ref]
        first, second = _valid(x), _valid(y)
        chosen = x if first else y if second else None
        decisions.append({
            'case_ref': case_ref, 'status': 'PLAN_REVIEWABLE' if chosen else 'NO_VALID_PLAN',
            'primary_valid': first, 'secondary_valid': second,
            'selected_model': 'primary' if first else 'secondary' if second else None,
            'requires_human_review': True, 'certified_fix': False,
            'changes_executed': False, 'run_binding': key_a,
            'proposal': chosen.get('proposal') if chosen else None,
        })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        for item in decisions:
            f.write(json.dumps(item, ensure_ascii=False)+'\n')
    return {'cases': len(decisions), 'reviewable': sum(x['status']=='PLAN_REVIEWABLE' for x in decisions),
            'both_valid': sum(x['primary_valid'] and x['secondary_valid'] for x in decisions),
            'no_valid_plan': sum(x['status']=='NO_VALID_PLAN' for x in decisions),
            'certified_fixes': 0}

def main():
    parser = argparse.ArgumentParser(description='RIV dual-model QA ensemble')
    parser.add_argument('--primary', required=True)
    parser.add_argument('--secondary', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--expected-count', type=int, default=545)
    args = parser.parse_args()
    print(json.dumps(combine(args.primary,args.secondary,args.output,args.expected_count),indent=2))


if __name__ == '__main__':
    main()

"""Privacy-preserving 2026 coverage scorecard from aggregated QA receipts.

Tiers are investigation priorities, NOT true root causes or certified repairs.
No individual incidents, identities, or human solutions are loaded.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED = ('cases','analyst_solutions_present','request_insufficient',
            'related_precedent','high_match_ge40','candidate_action_consensus',
            'evaluable_action_labels','action_label_matches','action_label_mismatches',
            'certified_resolutions')


def summarize_months(path: str | Path) -> dict:
    with open(path, encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError('EMPTY_QA_AGGREGATE')
    months = set()
    summary = []
    totals = {k: 0 for k in REQUIRED}
    for rec in rows:
        month = str(rec.get('month', ''))
        if month in months or not (month.startswith('2026-') and month[5:7].isdigit()):
            raise ValueError('DUPLICATE_OR_INVALID_MONTH')
        months.add(month)
        if any(k not in rec or not str(rec[k]).isdigit() for k in REQUIRED):
            raise ValueError('INVALID_AGGREGATE_VALUE')
        v = {k: int(rec[k]) for k in REQUIRED}
        if (v['related_precedent'] > v['cases']
            or v['candidate_action_consensus'] > v['related_precedent']
            or v['high_match_ge40'] > v['related_precedent']
            or v['evaluable_action_labels'] > v['candidate_action_consensus']
            or v['action_label_matches'] + v['action_label_mismatches'] != v['evaluable_action_labels']
            or v['analyst_solutions_present'] > v['cases']
            or v['certified_resolutions'] > v['cases']):
            raise ValueError('IMPOSSIBLE_AGGREGATE_COUNTS')
        for k in REQUIRED:
            totals[k] += v[k]
        summary.append({
            'month': month,
            'cases': v['cases'],
            'P1_consensus_candidate_NOT_CERTIFIED': v['candidate_action_consensus'],
            'P2_related_but_no_consensus': v['related_precedent']-v['candidate_action_consensus'],
            'P3_no_related_precedent': v['cases']-v['related_precedent'],
            'lexical_action_agreement_out_of': v['evaluable_action_labels'],
            'lexical_action_agreement_matches': v['action_label_matches'],
            'certified_resolutions': v['certified_resolutions'],
        })
    t = totals
    return {
        'source': 'QA 2026 aggregate from retrospective 2025-only memory evaluator',
        'method': 'lexical service-aware historic comparison; NOT LLM resolution',
        'months_present': sorted(months),
        'months_not_in_sample': [f'2026-{i:02d}' for i in range(1,13) if f'2026-{i:02d}' not in months],
        'sample_only_do_not_imply_no_business_activity_in_missing_months': True,
        'cases': t['cases'],
        'P1_consensus_candidate_NOT_CERTIFIED': t['candidate_action_consensus'],
        'P2_related_but_no_consensus': t['related_precedent']-t['candidate_action_consensus'],
        'P3_no_related_precedent': t['cases']-t['related_precedent'],
        'related_precedents': t['related_precedent'],
        'lexical_agreement': {'matches':t['action_label_matches'],
                             'evaluable':t['evaluable_action_labels'],
                             'mismatches':t['action_label_mismatches']},
        'certified_resolutions':t['certified_resolutions'],
        'monthly':summary,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='QA aggregates: prioritize investigation, never claim resolution')
    p.add_argument('--input', required=True)
    p.add_argument('--output')
    args=p.parse_args(argv)
    result=summarize_months(args.input)
    content=json.dumps(result, indent=2, ensure_ascii=False)+'\n'
    if args.output:
        Path(args.output).write_text(content,encoding='utf-8')
    print(content)


if __name__ == '__main__':
    main()

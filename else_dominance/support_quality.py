"""Evidence-bound, advisory-only support quality gate.

A model-generated procedure never certifies a repaired incident. This checker
inspects grounded references, unsupported corporate role claims and dangerous
actions, distinguishing explicit prohibitions from instructions to act.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from collections.abc import Mapping

_ROLE_CLAIM = re.compile(
    r'\b(?:Security_Administrator|Security_Incident_Response|ITIL_Admin|RRHH)\b', re.I
)
_RESTRICTION = re.compile(
    r'\b(?:congelar|bloquear|deshabilitar|suspender)\s+(?:(?:la|las)\s+)?cuentas?\b', re.I
)
_NEGATED = re.compile(
    r'\b(?:no\s+(?:se\s+)?(?:debe|puede|realizar|efectuar|proceder|autorizar|bloquear|congelar)|'
    r'prohibid[oa]|sin\s+autorizaci[oó]n|evitar|nunca)\b', re.I
)
_DONE = re.compile(
    r'\b(?:se\s+ha|han|ha)\s+(?:ejecutad[oa]|aplicad[oa]|cambiad[oa]|'
    r'completad[oa]|verificad[oa]|resuelt[oa]|restablecid[oa]|cerrad[oa])\b', re.I
)
_SQL_WRITE = re.compile(
    r'\b(?:UPDATE\s+\w+\s+SET|DELETE\s+FROM|INSERT\s+INTO|'
    r'TRUNCATE\s+TABLE|DROP\s+TABLE|GRANT\s+\w+\s+ON)\b', re.I
)
_FUTURE_TEST = re.compile(
    r'\b(?:verificar|comprobar|validar|confirmar|registrar|corroborar|'
    r'evidenciar|demostrar|probar|tras\s+la\s+aprobaci[oó]n)\b', re.I
)


@dataclass(frozen=True)
class QualityDecision:
    status: str
    hard_flags: tuple[str, ...]
    review_flags: tuple[str, ...]
    unresolved_role_mapping: bool
    real_repair_certified: bool = False

    def to_dict(self) -> dict:
        return {
            'status': self.status,
            'hard_flags': list(self.hard_flags),
            'review_flags': list(self.review_flags),
            'unresolved_role_mapping': self.unresolved_role_mapping,
            'real_repair_certified': self.real_repair_certified,
        }


def _restriction_ordered(text: str) -> bool:
    """Reject a proposed unilateral account restriction, not 'NO congelar'."""
    for match in _RESTRICTION.finditer(text):
        before = text[max(0, match.start() - 110):match.start()]
        clause = re.split(r'[.;\n]', before)[-1]
        if not _NEGATED.search(clause):
            return True
    return False


def evaluate_support_plan(
    plan: Mapping[str, object],
    *,
    evidence_registry: Mapping[str, object],
    approved_role_names: set[str] | None = None,
) -> QualityDecision:
    """Classify technical actionability, never grant an authorization.

    approved_role_names must come from an independently authenticated official
    role matrix. With None or empty set, all roles remain advisory.
    """
    hard: list[str] = []
    review: list[str] = []
    if not isinstance(plan, Mapping):
        return QualityDecision('REJECT', ('NOT_OBJECT',), (), True)
    if plan.get('performed_changes') is not False:
        hard.append('UNVERIFIED_EXECUTION_CLAIM')
    state = plan.get('ticket_state')
    if state in ('CLOSED', 'RESOLVED', 'RESUELTO', 'CERRADO'):
        hard.append('FALSE_CLOSED_STATE')
    references = plan.get('evidence_refs')
    if not isinstance(references, list):
        hard.append('MISSING_EVIDENCE_REFS')
        references = []
    for ref in references:
        if not isinstance(ref, str) or ref not in evidence_registry:
            hard.append('UNKNOWN_EVIDENCE_REF')
    if not references:
        review.append('NO_CASE_EVIDENCE')
    actions = plan.get('conditional_actions')
    if not isinstance(actions, list) or not actions:
        hard.append('NO_CONDITIONAL_ACTIONS')
        actions = []
    role_unverified = False
    approved = approved_role_names or set()
    for i, action in enumerate(actions):
        if not isinstance(action, Mapping):
            hard.append(f'ACTION_{i}_NOT_OBJECT')
            continue
        for k in ('precondition', 'action', 'authorized_role', 'verification'):
            if not isinstance(action.get(k), str) or len(action[k].strip()) < 8:
                hard.append(f'ACTION_{i}_MISSING_{k.upper()}')
        step_text = str(action.get('action') or '')
        role = str(action.get('authorized_role') or '')
        if _SQL_WRITE.search(step_text):
            hard.append(f'ACTION_{i}_RAW_SQL_MUTATION')
        if _restriction_ordered(step_text):
            hard.append(f'ACTION_{i}_ACCOUNT_RESTRICTION_NOT_AUTHORIZED')
        if _ROLE_CLAIM.search(role):
            hard.append(f'ACTION_{i}_UNVERIFIED_ROLE_CLAIM')
        if not role or role not in approved:
            role_unverified = True
        if role and role not in approved:
            review.append(f'ACTION_{i}_ROLE_MAPPING_PENDING')
    closure = plan.get('closure_tests')
    if not isinstance(closure, list) or not closure:
        hard.append('MISSING_CLOSURE_TESTS')
        closure = []
    for i, test in enumerate(closure):
        text = str(test)
        # A proof written in the past cannot stand in for a future functional test.
        if _DONE.search(text) and not _FUTURE_TEST.match(text.strip()):
            hard.append(f'CLOSURE_{i}_CLAIMS_COMPLETION_WITHOUT_RECEIPT')
    if hard:
        status = 'REJECT'
    elif not references or state == 'INVESTIGATION_REQUIRED':
        status = 'INVESTIGATION_REQUIRED'
    elif role_unverified or state == 'PENDING_AUTHORIZATION':
        status = 'AUTHORIZED_HANDOFF_REQUIRED'
    else:
        # Even with a certified role directory, no automated execution occurs.
        status = 'PROCEDURE_FOR_HUMAN_REVIEW'
    return QualityDecision(
        status, tuple(sorted(set(hard))), tuple(sorted(set(review))),
        role_unverified, False
    )


def main(argv=None):
    """Independent QA audit of a synthetic or authorized-private support plan."""
    from pathlib import Path
    import argparse
    p = argparse.ArgumentParser(description='Independently audit one support plan without mutations')
    p.add_argument('--plan', required=True, help='Local JSON; never publish corporate descriptions')
    p.add_argument('--evidence-registry', required=True, help='Local trusted evidence references JSON')
    p.add_argument('--output', help='Private result, JSON')
    p.add_argument('--approved-role-names', help='Official locally verified role-name JSON list')
    a = p.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text(encoding='utf-8'))
    registry = json.loads(Path(a.evidence_registry).read_text(encoding='utf-8'))
    if not isinstance(registry, dict):
        p.error('EVIDENCE_REGISTRY_MUST_BE_OBJECT')
    roles = None
    if a.approved_role_names:
        parsed = json.loads(Path(a.approved_role_names).read_text(encoding='utf-8'))
        if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
            p.error('ROLE_NAMES_MUST_BE_STRING_ARRAY')
        # A role list is a caller input, not independent proof of IAM authority.
        roles = set(parsed)
    outcome = evaluate_support_plan(plan, evidence_registry=registry,
                                    approved_role_names=roles).to_dict()
    if a.output:
        Path(a.output).write_text(json.dumps(outcome, ensure_ascii=False, indent=2)+'\n',
                                  encoding='utf-8')
    print(json.dumps(outcome, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

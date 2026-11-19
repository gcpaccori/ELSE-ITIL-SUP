"""Source and release contracts: additive V6 only, no repair or false maturity."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_v6_release_must_keep_v2_v4_v5_and_private_port():
    runner=(ROOT/'ops'/'run_specialist_v6_workbench_canary.sh').read_text()
    deploy=(ROOT/'ops'/'deploy_specialist_v6_workbench_canary.sh').read_text()
    unit=(ROOT/'ops'/'systemd'/'else-itil-workbench-v6-canary.service').read_text()
    assert '--host 127.0.0.1 --port 18915' in runner
    assert '0.0.0.0' not in runner
    assert '--guided-principals-file' in runner
    assert '--handoff-signing-key-file' in runner
    assert '--guided-fast-handoff' in runner
    assert '--guided-max-inflight 2' in runner
    assert '--maturity-scorecard' in runner
    assert '--qa-queue-db' not in runner
    assert 'HANDOFF_RELEASE_LEASE_MISMATCH' in deploy
    assert 'V6_ROLLBACK_V2_V4_V5_UNMODIFIED' in deploy
    assert 'qa_support_01.token' in deploy
    assert 'V6_QA_CONSENT_SIGN_VERIFY_REVOKE_BROWSER_AND_READYNESS_PASS' in deploy
    assert 'PREDECESSOR_SERVICE_NOT_ACTIVE' in deploy
    assert 'else-itil-specialist-v1.service' in deploy
    assert 'else-itil-novice-v4-canary.service' in deploy
    assert 'else-itil-novice-v5-canary.service' in deploy
    assert 'NoNewPrivileges=true' in unit
    assert 'UMask=0077' in unit


def test_report_distinguishes_signatures_from_corporate_case_authorization():
    text=(ROOT/'docs'/'ELSE_ITIL_V6_FLUJO_UNIFICADO_USUARIO_SOPORTE.md').read_text()
    assert 'USER_REPORTED_NO_CORPORATE_BINDING' in text
    assert 'ningún Hand QA automáticamente' in text
    assert 'SSO y autorización' in text
    assert 'NO' in text
    assert 'ITIL_CASE_EXISTS' in text
    assert 'ITIL_SERVICE' in text
    assert 'ITIL_MODULE' in text
    assert 'No abrir públicamente' in text
    assert 'no repara ingesta' in text

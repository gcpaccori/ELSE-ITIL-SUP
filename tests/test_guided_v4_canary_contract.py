"""Fail-closed separation of V2 production and V4 private QA pilot."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_canary_runner_separate_loopback_and_private_storage():
    s=(ROOT/"ops"/"run_specialist_v4_canary.sh").read_text()
    assert "set -euo pipefail" in s and "umask 077" in s
    assert "--host 127.0.0.1 --port 18913" in s
    assert "0.0.0.0" not in s
    assert "--guided-db " in s
    assert "canary_private/guided_sessions.sqlite" in s
    assert "support_live_private/service.token" in s
    assert "--model else-itil-riv-qwen9b-gpu6" in s
    assert "--fallback-model qwen35-4b" in s
    assert "--qa-queue-db" not in s
    assert "19883" not in s

def test_canary_systemd_does_not_override_main_support():
    s=(ROOT/"ops"/"systemd"/"else-itil-novice-v4-canary.service").read_text()
    assert "NoNewPrivileges=true" in s and "UMask=0077" in s
    assert "ExecStart=" in s
    assert "run_specialist_v4_canary.sh" in s
    assert "30-guided-v2.conf" not in s
    assert "40-guided-v4.conf" not in s

def test_canary_deploy_requires_exact_sha_isolation_and_reversal():
    s=(ROOT/"ops"/"deploy_specialist_v4_private_canary.sh").read_text()
    assert "EXPECTED_SHA" in s and "RELEASE_SHA_MISMATCH" in s
    assert "CANARY_ALREADY_INSTALLED" in s
    assert "V2_MUST_REMAIN_ACTIVE" in s
    assert "CANARY_ROLLBACK_V2_UNTOUCHED" in s
    assert 'rm -f "$DEST"' in s
    assert "trap rollback ERR" in s
    assert "(18883,True)" in s
    assert "127.0.0.1:18913" in s
    assert "AUTH_MISSING_BUT_ACCEPTED" in s
    assert "QA_HISTORICAL_READY" in s
    assert "repairs_enabled" in s
    assert "else-itil-specialist-v1.service" in s

"""No shell execution; safety contract of opt-in service launcher."""
from pathlib import Path
from else_dominance import support_http

def test_guided_launcher_preserves_qa_and_is_loopback():
    path=Path(__file__).parents[1]/'ops'/'run_specialist_v2_guided.sh'
    s=path.read_text()
    assert 'set -euo pipefail' in s
    assert 'umask 077' in s
    assert '--host 127.0.0.1 --port 18883' in s
    assert '--guided-db ' in s
    assert '--token-file ' in s
    assert '--qa-queue-db ' in s
    assert '--qa-allowlist ' in s
    assert '--model else-itil-riv-qwen9b-gpu6' in s
    assert '--fallback-model qwen35-4b' in s
    assert 'chmod 777' not in s and '0.0.0.0' not in s
    assert 'main' in dir(support_http)


def test_deployment_requires_exact_release_sha_and_rolls_back_if_health_fails():
    p=Path(__file__).parents[1]/'ops'/'deploy_specialist_guided_v2_with_rollback.sh'
    s=p.read_text()
    assert 'EXPECTED_SHA="${1:?Expected verified main SHA required}"' in s
    assert 'RELEASE_SHA_MISMATCH' in s
    assert 'REFUSE_OVERWRITE_EXISTING_DROPIN' in s
    assert 'trap rollback ERR' in s
    assert 'rm -f "$DROP"' in s
    assert 'systemctl --user daemon-reload' in s
    assert 'guided_dialogue_enabled' in s
    assert 'qa_dispatch' in s and 'QA_HISTORICAL_READY' in s
    assert 'repairs_enabled' in s
    assert 'UNAUTHENTICATED_REQUEST_ACCEPTED' in s
    assert '127.0.0.1:18883' in s
    assert '0.0.0.0:18883' not in s

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

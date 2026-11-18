"""Offline deployment safety specification: rollback to V2 and no new privileges."""
from pathlib import Path
from else_dominance.guided_dialogue import SCHEMA

def test_additive_guided_v4_dropin_is_lease_locked_and_rollback_safe():
    root=Path(__file__).resolve().parents[1]
    s=(root/'ops'/'deploy_specialist_guided_v4_with_rollback.sh').read_text()
    assert "EXPECTED_SHA" in s and "RELEASE_SHA_MISMATCH" in s
    assert "40-guided-v4.conf" in s
    assert "30-guided-v2.conf" in s
    assert "REFUSE_OVERWRITE_V4_DROPIN" in s
    assert 'rm -f "$DROP"' in s
    assert "trap rollback ERR" in s
    assert "systemctl --user restart" in s
    assert '"guided_dialogue_enabled"' in s
    assert '"qa_dispatch"' in s
    assert '"repairs_enabled"' in s
    assert "UNAUTHENTICATED_REQUEST_ACCEPTED" in s
    assert "127.0.0.1:18883" in s
    assert "0.0.0.0:18883" not in s
    assert "RUN_WITH_ADMIN" not in s
    assert SCHEMA=="else.itil.guided-novice.v2"

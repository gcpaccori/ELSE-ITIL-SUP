"""No production V2/V4 replacement and no synthetic workload metric inflation."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]


def test_new_canary_is_lease_locked_and_uses_separate_private_storage():
    runner=(ROOT/"ops"/"run_specialist_v5_governed_canary.sh").read_text()
    deploy=(ROOT/"ops"/"deploy_specialist_v5_governed_canary.sh").read_text()
    unit=(ROOT/"ops"/"systemd"/"else-itil-novice-v5-canary.service").read_text()
    assert "--host 127.0.0.1 --port 18914" in runner
    assert "0.0.0.0" not in runner
    assert "--guided-principals-file" in runner
    assert "--guided-fast-handoff" in runner
    assert "--guided-max-inflight 2" in runner
    assert "--guided-primary-timeout 35" in runner
    assert "--guided-fallback-timeout 20" in runner
    assert "--human-review-status-file" in runner
    assert "4017383" not in runner
    assert 'SHA_LEASE_MISMATCH' in deploy
    assert 'V2_MUST_STAY_ACTIVE' in deploy
    assert 'V4_MUST_STAY_ACTIVE' in deploy
    assert 'V5_UNIT_ALREADY_EXISTS' in deploy
    assert 'V5_CANARY_ROLLBACK_V2_V4_UNCHANGED' in deploy
    assert 'guided_principal_required' in deploy
    assert 'immediate_safe_handoffs' in deploy
    assert "NoNewPrivileges=true" in unit
    assert "UMask=0077" in unit
    assert "else-itil-specialist-v1.service" not in unit
    assert "else-itil-novice-v4-canary.service" not in unit


def test_published_load_sample_does_not_claim_real_diagnoses():
    r=json.loads((ROOT/"data"/"2026_v5_1000_isolated_synthetic_sessions.json").read_text())
    assert r["results"]["sessions"]==1000
    assert r["results"]["subjects"]==10
    assert r["results"]["fast_no_model_turns"]==3000
    assert r["source"]=="SYNTHETIC_ONLY"
    assert r["no_llm_requests"] is True
    assert r["no_model_quality_or_causal_accuracy_measured"] is True
    assert r["root_causes_certified"]==0
    assert r["no_business_reads_or_writes"] is True


def test_docs_explicitly_reject_fake_full_maturity():
    text=(ROOT/"docs"/"ELSE_ITIL_V5_INTEGRACION_GOBERNADA.md").read_text()
    assert "NO_GO" in text
    assert "No se" in text or "no se" in text
    assert "1000" not in text or "1.000" in text
    assert "SSO corporativo" in text
    assert "0 personas" in text
    assert "No es" in text or "NO" in text

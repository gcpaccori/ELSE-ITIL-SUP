"""A private human-review packet is not an automatically proven diagnosis."""
import json
from pathlib import Path

import pytest

from qa.maturity_v5.human_review_gate import inspect


def packet(tmp_path):
    p=tmp_path/"private_packet.jsonl"
    items=[{
      "blind_case_code":f"QA-{i:02d}",
      "month":"2026-09",
      "request_privately_redacted":"INTERNAL_TEST_ONLY",
      "turns":[{"turn":j} for j in (1,2,3)],
    } for i in range(1,25)]
    p.write_text("".join(json.dumps(r)+"\n" for r in items))
    from hashlib import sha256
    m=tmp_path/"meta.json"
    m.write_text(json.dumps({
       "schema":"else.itil.qa.human-novice-review-packet.v1",
       "cases":24,"turns":72,
       "private_packet_sha256":sha256(p.read_bytes()).hexdigest(),
    }))
    return p,m


def marks(tmp_path,items):
    r=tmp_path/"submitted_reviews.jsonl"
    r.write_text("".join(json.dumps(x)+"\n" for x in items))
    r.chmod(0o600)
    return r


def rating(case,alias,role,seen=True):
    return {
      "blind_case_code":case,"reviewer_alias":alias,
      "role":role,"saw_model_identity":False,
      "observed_real_person":seen,
      "privacy_review_approved":True,
      "scores":[1,2,0],
    }


def test_missing_human_reviews_is_pending_not_failed_or_certified(tmp_path):
    p,m=packet(tmp_path)
    r=inspect(p,m)
    assert r["status"]=="PENDING_HUMAN_REVIEW"
    assert r["rating_records_provided"]==0
    assert r["causal_diagnosis_certified"] is False
    assert not r["review_coverage_complete"]


def test_complete_self_reported_review_still_not_causal_truth(tmp_path):
    p,m=packet(tmp_path)
    rr=[]
    for i in range(1,25):
        case=f"QA-{i:02d}"
        rr.append(rating(case,"tech_alpha","technician"))
        rr.append(rating(case,"tech_beta","technician"))
        rr.append(rating(case,f"novice_{i:02d}","novice_observer"))
    r=inspect(p,m,marks(tmp_path,rr))
    assert r["review_coverage_complete"]
    assert r["status"]=="PENDING_CORPORATE_VERIFICATION"
    assert r["cases_with_two_technical_reviews"]==24
    assert r["unique_observed_novice_aliases"]==24
    assert r["causal_diagnosis_certified"] is False
    assert not r["human_identity_externally_verified"]


def test_unobserved_person_never_counts_as_actual_novice(tmp_path):
    p,m=packet(tmp_path)
    rr=[rating("QA-01","novice_example","novice_observer",False)]
    with pytest.raises(ValueError,match="UNOBSERVED"):
        inspect(p,m,marks(tmp_path,rr))


def test_no_privacy_clearance_no_review(tmp_path):
    p,m=packet(tmp_path)
    rr=[rating("QA-01","tech_alpha","technician")]
    rr[0]["privacy_review_approved"]=False
    with pytest.raises(ValueError,match="PRIVACY"):
        inspect(p,m,marks(tmp_path,rr))


def test_tampered_packet_is_rejected_before_processing(tmp_path):
    p,m=packet(tmp_path)
    p.write_text(p.read_text()+"\n")
    with pytest.raises(ValueError,match="HASH_MISMATCH"):
        inspect(p,m)


def test_identical_reviewer_cannot_vote_twice(tmp_path):
    p,m=packet(tmp_path)
    r=rating("QA-01","tech_alpha","technician")
    with pytest.raises(ValueError,match="DUPLICATE"):
        inspect(p,m,marks(tmp_path,[r,r]))


def test_private_rating_permissions_enforced(tmp_path):
    p,m=packet(tmp_path)
    path=marks(tmp_path,[rating("QA-01","tech_alpha","technician")])
    path.chmod(0o644)
    with pytest.raises(ValueError,match="PERMISSIONS"):
        inspect(p,m,path)


def test_public_pending_review_snapshot_has_no_case_text_or_false_success():
    root=Path(__file__).resolve().parents[1]
    v=json.loads((root/"data"/"novice_human_review_readiness_v5.json").read_text())
    assert v["rating_records_provided"]==0
    assert v["cases_in_private_packet"]==24
    assert v["causal_diagnosis_certified"] is False
    assert v["status"]=="PENDING_HUMAN_REVIEW"
    assert "request_privately_redacted" not in json.dumps(v)
    assert "historical_solution" not in json.dumps(v)

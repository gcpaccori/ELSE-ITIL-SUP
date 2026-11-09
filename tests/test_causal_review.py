import copy
from collections import Counter
from hashlib import sha256
import json
import pytest
from else_dominance.causal_review import verify_audit, make_review_queue, CausalAuditDenied

def fixture():
    cases=[]
    for i,(gate,relation,quality) in enumerate([
        (True,"SUPPORTED","ACTIONABLE"),(True,"INDETERMINATE","VAGUE"),
        (False,"INDETERMINATE","VAGUE")]):
        cases.append({"digest_prefix":f"{i+1:016x}","service":str(i+1),
        "gate_pass":gate,"relation":relation,"history_quality":quality,
        "technical_gap":"NONE" if i==0 else "NO_CAUSAL_TEST",
        "decision":"INVALID_PLAN" if not gate else
                   ("DOCUMENTARY_COMPATIBILITY_ONLY" if i==0 else "NEEDS_REVIEW"),
        "plan_sha256":"a"*64,"review_sha256":"b"*64,"repair_certified":False})
    return {"schema":"else.itil.causal-calibration-independent-audit.v1",
       "scope":"CALIBRATION_ONLY_NOT_FRESH_BLIND_EXAM",
       "source":"ELSE70/dbITIL_D/Jan2026 authorized snapshot",
       "training_performed":False,"corporate_mutations":False,
       "gold_exposed_to_generator":False,"repairs_certified":0,
       "functional_root_causes_certified":0,"supervision_examples_authorized":0,
       "human_review_pending":len(cases),"total":len(cases),
       "independent_negative_tests_passed":3,
       "gate_pass":sum(c["gate_pass"] for c in cases),
       "gate_failed":sum(not c["gate_pass"] for c in cases),
       "documentary_relation_counts":dict(Counter(c["relation"] for c in cases)),
       "decisions":dict(Counter(c["decision"] for c in cases)),"cases":cases}
def bind(obj):
    b=json.dumps(obj,sort_keys=True).encode()
    return b,sha256(b).hexdigest()
def test_provenance_pinned_and_no_promotion():
    b,h=bind(fixture())
    out=make_review_queue(b,pinned_sha256=h)
    assert len(out["cases"])==3 and out["promotion_decision"]=="BLOCKED"
    assert all(not x["eligible_for_training"] for x in out["cases"])
    assert out["cases"][0]["next_action"]=="GET_INDEPENDENT_FUNCTIONAL_QA_AND_HUMAN_SIGNOFF"
    assert out["cases"][2]["next_action"]=="FIX_SOURCE_BINDING_AND_REEVALUATE"
def test_byte_tamper_fail_before_evaluation():
    b,h=bind(fixture())
    with pytest.raises(CausalAuditDenied,match="AUDIT_BYTES_DRIFT"):
        verify_audit(b+b" ",pinned_sha256=h)
@pytest.mark.parametrize("change",[
 lambda d:d.update(training_performed=True),
 lambda d:d.update(repairs_certified=1),
 lambda d:d["cases"][0].update(repair_certified=True),
 lambda d:d["cases"][0].update(decision="VALIDATED"),
 lambda d:d["cases"][2].update(decision="DOCUMENTARY_COMPATIBILITY_ONLY"),
 lambda d:d["cases"][0].update(digest_prefix=d["cases"][1]["digest_prefix"]),
 lambda d:d["cases"][0].update(plan_sha256="0"*63),
 lambda d:d.update(gate_pass=3),
 lambda d:d.update(human_review_pending=0),
 lambda d:d.update(supervision_examples_authorized=1),
 lambda d:d.update(gold_exposed_to_generator=True),
 lambda d:d.update(source="production/unsafe"),
])
def test_false_pass_attempts(change):
    d=fixture();change(d);b,h=bind(d)
    with pytest.raises(CausalAuditDenied): verify_audit(b,pinned_sha256=h)
def test_invalid_schema_and_pin():
    d=fixture();d["schema"]="else.itil.fake";b,h=bind(d)
    with pytest.raises(CausalAuditDenied): verify_audit(b,pinned_sha256=h)
    with pytest.raises(CausalAuditDenied):verify_audit(b,pinned_sha256="A"*64)

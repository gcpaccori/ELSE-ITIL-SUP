"""Independent exact-cohort audit of February grounding-v2 replay.

Compare append-only original 100-case QA and 100 newly regenerated responses,
without accessing historical resolutions. Every accepted claim must list only
actual native O5-observed ITIL source. A higher PASS rate is NOT causal quality.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,re

from else_core.itil_feb100_o5_hand import AuthorizedNugetReceipt
from else_dominance.qa_feb100_native import verify_native_o5
from else_dominance.qa_evidence_grounding import (
    evidence_provenance_gate,OBSERVED)
from qa.qa_feb100_windows import read_allowlist

ROOT=Path("/home/u23u/else_itil_feb100_qa_20261110")
QA=Path("/home/u23u/else_itil_feb100_grounding_qa_20261110")
REPO=Path("/home/u23u/else_itil_feb100_grounding_20261110")
ALLOW=ROOT/"feb100_allowlist.private.jsonl"
INPUT=ROOT/"runs"
OUTPUT=QA/"outputs"
OUT=QA/"independent_grounding_v2_audit.json"
CASE_FILE=QA/"independent_grounding_v2_per_case.private.jsonl"
SOURCE=REPO/"qa/Feb100ExactRead.cs"


def require(ok,code):
    if not ok:raise ValueError(code)


def audit():
    require(not OUT.exists() and not CASE_FILE.exists(),
            "NO_OVERWRITE_AUDIT")
    allowed=read_allowlist(ALLOW)
    require(len(allowed)==100,"ALLOWED_NOT_100")
    files=sorted(OUTPUT.glob("*.private.json"))
    require(len(files)==100,"V2_COMPLETION_NOT_100")
    source_bytes=SOURCE.read_bytes()
    source_sha=sha256(source_bytes).hexdigest()
    summary=Counter()
    transitions=Counter()
    flags=Counter()
    per=[]
    originals={}
    for p in INPUT.glob("case_*/verified_final.private.json"):
        obj=json.loads(p.read_bytes())
        sha=obj["case_sha256"]
        require(sha not in originals,"ORIGINAL_DUPLICATE")
        originals[sha]=(obj,p.parent)
    require(set(originals)==set(allowed),"ORIGINAL_100_SCOPE")
    for file in files:
        row=json.loads(file.read_bytes())
        sha=row["case_sha256"]
        require(file.stem==sha+".private","V2_FILENAME_MISMATCH")
        require(sha in allowed,"V2_CASE_NOT_ALLOWLISTED")
        old,parent=originals[sha]
        final=row["new_result"]
        require(row["parent_run_id"]==parent.name and
                row["original_final_sha256"]==
                sha256((parent/"verified_final.private.json").read_bytes()).hexdigest(),
                "V2_NOT_BOUND_ORIGINAL_RESULT")
        receipt=(parent/"receipt.private.json").read_bytes()
        digest=sha256(receipt).hexdigest()
        require(digest==row["source_receipt_sha256"] and
                final["source_receipt_sha256"]==digest and
                final["hand_source_sha256"]==source_sha,
                "V2_RECEIPT_SOURCE_MISMATCH")
        owner=AuthorizedNugetReceipt(parent/"receipt.private.json",
                                     digest,sha,source_sha,len(source_bytes))
        native=verify_native_o5(owner)
        require(native["guardian_o13_pass"] is True and
                native["dominance_o15_pass"] is True,
                "NATIVE_O5_NOT_REVERIFIED")
        require(final["o5_o13_o15_verified"] is True and
                final["approved_for_training"] is False and
                final["repair_certified"] is False and
                final["root_cause_certified"] is False and
                final["executed_mutations"] is False and
                final["requires_human_verification"] is True and
                final["observed_sources"]==sorted(OBSERVED),
                "FALSE_V2_CERTIFICATION")
        accepted=final["quality"].get("accepted") is True
        require(final.get("model_attempts") in (1,2),
                "MODEL_ATTEMPT_BUDGET_BROKEN")
        proposal=final.get("proposal",{})
        if accepted:
            gate=evidence_provenance_gate(
                proposal,native_o5_verified=True,
                source_receipt_sha256=digest)
            require(gate["accepted"] is True and
                    proposal["fuentes"]==sorted(OBSERVED),
                    "POSTHOC_OR_UNOBSERVED_SOURCE_ACCEPTED")
            require(final["status"]!="NEEDS_HUMAN_TRIAGE" and
                    proposal["ejecutado"] is False and
                    proposal["confirmado"] is False,
                    "FALSE_MODEL_SUCCESS_STATUS")
            require(bool(proposal.get("faltantes")) and
                    bool(proposal.get("cierre")),
                    "ACCEPTED_PROCEDURE_LACKS_OPEN_EVIDENCE_OR_CLOSURE")
            summary["provenance_verified_accepted"]+=1
        else:
            require(proposal=={} and final["status"]=="NEEDS_HUMAN_TRIAGE",
                    "REJECTED_PLAN_NOT_QUARANTINED")
        was=old["quality"]["accepted"] is True
        transitions[f"{int(was)}→{int(accepted)}"]+=1
        summary["accepted"]+=int(accepted)
        summary["rejected"]+=int(not accepted)
        summary["model_second_attempts"]+=int(final["model_attempts"]==2)
        summary["accepted_after_rewrite"]+=int(accepted and
                                            final["model_attempts"]==2)
        summary["role_mapping_pending"]+=int(
            any("ROLE_MAPPING_PENDING" in f for f in
                final["quality"].get("review_flags",[])))
        if accepted:
            summary["source_table_refs_allowed_only"]+=1
        for flag in final["quality"].get("safety_flags",[]):
            flags[flag]+=1
        per.append({
            "case_sha256":sha,
            "source_receipt_sha256":digest,
            "original_accepted":was,
            "new_accepted":accepted,
            "new_source_provenance_verified":accepted,
            "attempts":final["model_attempts"],
            "new_contract_flags":final["quality"].get("safety_flags",[]),
            "model_human_review_required":True,
            "certified_causal_solution":False,
        })
    require(len(per)==100,"EXACT_COHORT_NOT_100")
    raw=("\n".join(json.dumps(x,sort_keys=True)
                  for x in sorted(per,key=lambda x:x["case_sha256"]))+"\n").encode()
    CASE_FILE.write_bytes(raw)
    report={
        "schema":"else.itil.feb100.grounded-v2-independent-audit.v1",
        "cases":100,
        "previous_contract_accepted":sum(x["quality"]["accepted"] for x,_ in originals.values()),
        "new_contract_accepted":summary["accepted"],
        "new_rejected":summary["rejected"],
        "transition_counts":dict(transitions),
        "model_second_attempts":summary["model_second_attempts"],
        "accepted_after_rewrite":summary["accepted_after_rewrite"],
        "grounded_native_o5_reverified":100,
        "accepted_source_provenance_verified":summary["provenance_verified_accepted"],
        "accepted_table_refs_observed_only":summary["source_table_refs_allowed_only"],
        "new_safety_flags":dict(flags),
        "role_mapping_pending":summary["role_mapping_pending"],
        "sql_reexecutions_during_replay":0,
        "historical_solution_shown_to_model":False,
        "historical_solution_compared_in_this_audit":False,
        "causal_precision_not_measured":True,
        "certified_repairs":0,
        "human_confirmations":0,
        "source_reader_sha256":source_sha,
        "original_audit_sha256":sha256(
            (ROOT/"independent_audit_100.json").read_bytes()).hexdigest(),
        "v2_journal_sha256":sha256(
            (QA/"grounded_v2_replay.private.jsonl").read_bytes()).hexdigest(),
        "per_case_audit_sha256":sha256(raw).hexdigest(),
    }
    OUT.write_text(json.dumps(report,sort_keys=True,indent=2))
    return report

if __name__=="__main__":
    print(json.dumps(audit(),sort_keys=True))

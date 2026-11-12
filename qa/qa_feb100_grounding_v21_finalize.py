"""Finalize the February 100-case QA policy v2.1 without altering originals.

Merge 98 untouched v2 outputs (all independently revalidated under the
stronger v2.1 source gate) and the two fresh targeted v2.1 regenerations.
Every result still points to exactly the original O5 receipt and first
frozen February outcome. New native O5/Guardian/Dominance reinspection
runs again via the independent audit.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json,os
from qa import qa_feb100_grounding_audit as verifier
from else_dominance.qa_evidence_grounding import (
    evidence_provenance_gate,SCHEMA)

ROOT=Path("/home/u23u/else_itil_feb100_grounding_qa_20261110")
BASE=ROOT/"outputs"
V21=ROOT/"v21"
PATCHES=V21/"outputs"
MERGED=V21/"merged_outputs"
RESULT=V21/"independent_grounding_v21_summary.json"
def read(path):return json.loads(path.read_bytes())
def assert_proof(row):
    result=row["new_result"]
    if result["quality"]["accepted"]:
        g=evidence_provenance_gate(result["proposal"],
                                   native_o5_verified=True,
                                   source_receipt_sha256=
                                   result["source_receipt_sha256"])
        if not g["accepted"]:
            raise ValueError("ACCEPTED_PLAN_STILL_HAS_UNVERIFIED_SQL_SOURCE")
def main():
    if MERGED.exists() or RESULT.exists():
        raise FileExistsError("REFUSE_V21_OVERWRITE")
    oldfiles={read(p)["case_sha256"]:p for p in BASE.glob("*.private.json")}
    updates={read(p)["case_sha256"]:p for p in PATCHES.glob("*.private.json")}
    if len(oldfiles)!=100 or len(updates)!=2 or not set(updates)<=set(oldfiles):
        raise ValueError("V21_CASES_NOT_PINNED_100_PLUS_2")
    for sha,p in updates.items():
        previous=read(oldfiles[sha])
        if not previous["new_result"]["quality"]["accepted"]:
            raise ValueError("V21_TARGET_WAS_NOT_OLD_ACCEPTED")
        g=evidence_provenance_gate(
            previous["new_result"]["proposal"],native_o5_verified=True,
            source_receipt_sha256=previous["new_result"]["source_receipt_sha256"])
        if g["accepted"]:
            raise ValueError("V21_TARGET_DID_NOT_NEED_REMEDITATION")
        replacement=read(p)
        if (replacement["parent_run_id"]!=previous["parent_run_id"] or
            replacement["source_receipt_sha256"]!=previous["source_receipt_sha256"] or
            replacement["original_final_sha256"]!=previous["original_final_sha256"] or
            replacement["new_result"]["grounding_policy"]!=
            "else.itil.qa.feb100.provenance-gate.v2.1"):
            raise ValueError("V21_REPLACEMENT_NOT_ORIGINAL_RECEIPT_BOUND")
    MERGED.mkdir(mode=0o700)
    for sha,p in sorted(oldfiles.items()):
        chosen=updates.get(sha,p)
        assert_proof(read(chosen))
        os.link(chosen,MERGED/(sha+".private.json"))
    verifier.OUTPUT=MERGED
    verifier.OUT=V21/"independent_grounding_v21_core_audit.json"
    verifier.CASE_FILE=V21/"independent_grounding_v21_per_case.private.jsonl"
    audited=verifier.audit()
    summary={
        "schema":"else.itil.feb100.grounded-v21-independent-summary.v1",
        "source_gate_version":SCHEMA,
        "cases":100,
        "original_baseline_accepted":audited["previous_contract_accepted"],
        "v21_accepted":audited["new_contract_accepted"],
        "v21_rejected":audited["new_rejected"],
        "v21_transition_counts":audited["transition_counts"],
        "native_o5_guardian_o15_reverified":audited["grounded_native_o5_reverified"],
        "acceptances_source_bound":audited["accepted_source_provenance_verified"],
        "original_outputs_unchanged":True,
        "targeted_model_regenerations":len(updates),
        "targeted_recipient_case_sha256_prefixes":[x[:16] for x in sorted(updates)],
        "updated_source_qa_queries_executed":0,
        "historical_solutions_exposed_to_generator":0,
        "human_root_cause_certification":0,
        "functional_repairs":0,
        "v21_core_audit_sha256":sha256(verifier.OUT.read_bytes()).hexdigest(),
        "targeted_model_journal_sha256":sha256(
            (V21/"v21_targeted_replay.private.jsonl").read_bytes()).hexdigest(),
    }
    RESULT.write_text(json.dumps(summary,sort_keys=True,indent=2))
    print(json.dumps(summary,sort_keys=True))
if __name__=="__main__":main()

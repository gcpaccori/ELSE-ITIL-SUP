"""Independent final QA audit of the supervised Feb16 dual-hand HTTP slice.

Reinspects native ITIL and SAP/OT O5/O13/O15 receipts per case, binds
the archived HTTP ledger and the v1.1 role policy, and refuses to count
a contract PASS as a functional repair or an approved corporate role.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json

from else_dominance.beta_supervision import BetaSupervisionLedger
from else_dominance.beta_vertical_slice import (
    BetaEvidenceBundle,beta_plan_gate,POLICY,PENDING_ROLE)

QA=Path("/home/u23u/else_itil_beta_vslice_qa_20261110")
ROOT=Path("/home/u23u/else_itil_feb100_qa_20261110")
REPO=Path("/home/u23u/else_itil_beta_vslice_20261110")
JOURNAL=QA/"beta_http16_e2e_v11.private.jsonl"
REPORT=QA/"beta_v11_independent_audit.json"
PRIVATE=QA/"beta_v11_case_audit.private.jsonl"
LEDGER=QA/"beta_supervision_v11.sqlite"


def require(ok,reason):
    if not ok:raise ValueError(reason)


def main():
    require(not REPORT.exists() and not PRIVATE.exists(),
            "INDEPENDENT_AUDIT_EXISTS")
    b=BetaEvidenceBundle(base=REPO,qa=ROOT,core_source=QA)
    rows=[json.loads(x) for x in JOURNAL.read_text().splitlines() if x.strip()]
    require(len(rows)==16 and len({x["case_sha256"] for x in rows})==16 and
            {x["case_sha256"] for x in rows}==set(b.sap_recs),
            "E2E16_OWNER_COHORT_NOT_EXACT")
    record=[]
    with BetaSupervisionLedger(LEDGER) as ledger:
        require(ledger.aggregate()["recorded_human_review_events"]==0,
                "UNEXPECTED_HUMAN_EVENT")
        for item in rows:
            sha=item["case_sha256"]
            proof=b.verify(sha)
            require(proof["status"]=="DUAL_NATIVE_EVIDENCE_VERIFIED",
                    "O5_SECOND_HAND_NOT_VERIFIED")
            stored=ledger.get(sha)
            require(stored is not None and
                    stored["case_sha256"]==sha and
                    stored["source_receipts"]=={
                        "itil":proof["itil_receipt_sha256"],
                        "sap_ot":proof["sap_receipt_sha256"]},
                    "LEDGER_SOURCE_RECEIPTS_NOT_BOUND")
            require(item["status"]=="E2E_VERIFIED" and
                    item["contract_accepted"]==stored["quality"]["accepted"]
                    and item["itil_receipt"]==proof["itil_receipt_sha256"]
                    and item["sap_receipt"]==proof["sap_receipt_sha256"],
                    "JOURNAL_LEDGER_SOURCE_CONFLICT")
            require(stored["native_itil_verified"] is True and
                    stored["native_sap_ot_verified"] is True and
                    stored["business_join_certified"] is False and
                    stored["repair_certified"] is False and
                    stored["root_cause_certified"] is False and
                    stored["human_review_required"] is True,
                    "UNCERTIFIED_OUTCOME_PROMOTED")
            if stored["quality"]["accepted"]:
                require(stored["quality"]["schema"]==POLICY,
                        "OLD_ROLE_POLICY_NOT_APPLIED")
                require(beta_plan_gate(stored["proposal"],proof["evidence"])["accepted"],
                        "PLAN_FAILED_INDEPENDENT_V11_ROLE_GATE")
                for action in stored["proposal"]["pasos"]:
                    require(action["responsable"].strip().casefold()==
                            PENDING_ROLE.casefold(),
                            "UNVERIFIED_ASSIGNED_ROLE")
                require(stored["proposal"]["vinculacion_comercial_verificada"] is False
                        and stored["proposal"]["rol_oficial_validado"] is False,
                        "FAKE_CORPORATE_ATTESTATION")
            else:
                require(stored["proposal"]=={} and
                        stored["status"]=="NEEDS_HUMAN_TRIAGE",
                        "REJECTED_PLAN_PUBLISHED")
            require(ledger.status(sha)["reviews_count"]==0,
                    "FALSE_TECHNICIAN_SIGNOFF")
            record.append({
                "case_sha256":sha,
                "original_itil_receipt_sha256":proof["itil_receipt_sha256"],
                "original_sap_receipt_sha256":proof["sap_receipt_sha256"],
                "both_native_o5_o13_o15_reverified":True,
                "reported_ot_found_in_table":proof["sap_observation"]["order_found"],
                "contract_accepted":stored["quality"]["accepted"],
                "source_role_join_unverified":True,
                "repair_certified":False,
                "technician_reviewed":False,
            })
        counts=ledger.aggregate()
    blob=("\n".join(json.dumps(x,sort_keys=True)
                      for x in sorted(record,key=lambda x:x["case_sha256"]))+"\n").encode()
    with PRIVATE.open("xb") as f:f.write(blob)
    result={
        "schema":"else.itil.v1beta.independent-dualhand-supervised-audit.v1",
        "historical_cohort_selected":100,
        "ot_eligible_cases":16,
        "qa_http_e2e_verified":16,
        "native_itil_o5_o13_o15_verified":16,
        "native_sap_o5_o13_o15_verified":16,
        "model_contract_accepted_v11":sum(x["contract_accepted"] for x in record),
        "model_triage_v11":sum(not x["contract_accepted"] for x in record),
        "orders_found_in_specific_qa_table":sum(
            x["reported_ot_found_in_table"] for x in record),
        "human_review_events":counts["recorded_human_review_events"],
        "official_business_joins_certified":0,
        "official_role_mappings_certified":0,
        "root_causes_certified":0,
        "functional_repairs_certified":0,
        "fresh_sql_reads_in_replay":0,
        "historical_solution_exposure":False,
        "source_reader_sha256":sha256(
            (REPO/"qa/Feb100SapOtRead.cs").read_bytes()).hexdigest(),
        "journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest(),
        "per_case_sha256":sha256(blob).hexdigest(),
    }
    with REPORT.open("x") as f:json.dump(result,f,sort_keys=True,indent=2)
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()

"""Exact operational capability inventory. A repo module is not a live service.

This endpoint reports only features attached to this HTTP process. It cannot
invent corporate data access, automated repairs, verified root causes or SSO.
"""
from __future__ import annotations


def inventory(*, guided:bool, principal_scoped:bool,
              fast_handoff:bool,qa_dispatch:bool,
              readiness:bool,admission_limited:bool,
              handoff_receipts:bool=False)->dict:
    def item(name,status,evidence_type):
        return {"capability":name,"state":status,
                "evidence_type":evidence_type}
    names=[
       item("private_authenticated_guidance",
            "PILOT_ENABLED" if guided else "DISABLED","RUNTIME"),
       item("private_principal_session_ownership",
            "PILOT_ENABLED" if guided and principal_scoped else "DISABLED","RUNTIME"),
       item("explicit_permission_and_persistent_failure_handoff",
            "PILOT_ENABLED" if guided and fast_handoff else "DISABLED","RUNTIME"),
       item("bounded_guidance_admission",
            "PILOT_ENABLED" if guided and admission_limited else "DISABLED","RUNTIME"),
       item("persistent_sqlite_dialogue",
            "PILOT_ENABLED" if guided else "DISABLED","RUNTIME"),
       item("qa_historical_dispatch",
            "READ_ONLY_QA_ENABLED" if qa_dispatch else "DISABLED","RUNTIME"),
       item("maturity_snapshot_no_go",
            "SNAPSHOT_ENABLED" if readiness else "DISABLED","AUDITED_AGGREGATE_SNAPSHOT"),
       item("automated_corporate_ticket_ingestion",
            "NOT_CONNECTED","NONE"),
       item("corporate_employee_sso_and_ticket_authorization",
            "NOT_CERTIFIED","NONE"),
       item("independent_causal_diagnosis_certification",
            "NOT_CERTIFIED","NONE"),
       item("independent_real_novice_comprehension_certification",
            "NOT_CERTIFIED","NONE"),
       item("automatic_mutations_or_repairs",
            "DISABLED","RUNTIME"),
    ]
    if handoff_receipts:
        names.append(item("user_consent_cryptographic_support_handoff",
            "PILOT_ENABLED" if guided and principal_scoped
            else "DISABLED","RUNTIME_SIGNED_CONSENT_LEDGER"))
    assert len(names)==len({x["capability"] for x in names})
    return {
       "schema":"else.itil.support-capability-inventory.v1",
       "scope":"THIS_RUNNING_HTTP_PROCESS_ONLY",
       "capability_count":len(names),
       "capabilities":names,
       "no_company_source_or_repair_claim":True,
       "pilot_is_not_maturity_certification":True,
    }

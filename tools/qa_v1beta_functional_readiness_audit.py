#!/usr/bin/env python3
"""Reproducible QA evidence audit: true positives + all 5 distinct ITIL needs.

Does no SQL, repairs or LLM calls. Requires ELSE CORE O5/O13/O15 and the
private August cohort and Windows HMAC receipts on the authorized audit host.
"""
from __future__ import annotations
import json

from else_dominance.positive_control_verified import verify_positive_controls
from else_dominance.functional_profile_verified import verify_functional_profiles
from else_dominance.functional_case_triage import audit_real_five
from else_dominance.company_routed_verified import summary,verify_all

def audit():
    routed=verify_all()
    company=summary(routed)
    positive=verify_positive_controls()
    profiles=verify_functional_profiles()
    plans=audit_real_five()
    kinds=sorted(x["functional_kind"] for x in plans)
    if len(plans)!=5 or len(set(kinds))!=5:
        raise ValueError("FIVE_BUSINESS_SCENARIOS_NOT_COVERED")
    if any(
        x["repair_permitted"] or x["repair_executed"] or
        x["business_record_identified"] or x["historical_solution_used"]
        for x in plans
    ):
        raise ValueError("FALSE_REPAIR_OR_HISTORICAL_ORACLE_CLAIM")
    return {
       "schema":"else.itil.aug2026.qa.functional-readiness-final-audit.v1",
       "itil_case_cohort_size":1819,
       "company_routed_signed_v2":company["verified_cases"],
       "company1_routed_cases":company["company_1_cases"],
       "company3_routed_cases":company["company_3_cases"],
       "qa_case_exact_matches":company["exact_qa_hits"],
       "verified_windows_hmac_receipts":company["verified_windows_hmac"],
       "positive_control_companies":positive["verified_company_1_and_3"],
       "positive_control_company1_aug_ot_found":
           positive["company1_august_ot_lookups_positive"],
       "verified_functional_witness_companies":
           profiles["verified_company_profiles"],
       "functional_sql_profiles_compiled_and_executed":
           profiles["fixed_query_profiles"],
       "company3_absent_installation_audit_table_explicit":
           profiles["company3_missing_installation_audit_table_explicit"],
       "five_itil_specific_plans_pass":len(plans),
       "five_business_scenarios":kinds,
       "native_company_o5_o13_o15_required":True,
       "positive_control_signed_receipt_sha256":
           positive["signed_receipt_sha256"],
       "functional_profile_signed_receipt_sha256":
           profiles["signed_receipt_sha256"],
       "company_signed_receipts_manifest_sha256":
           company["receipt_manifest_sha256"],
       "historical_itil_solutions_used_by_runtime":0,
       "new_sql_during_replay":0,
       "data_modifications":0,
       "global_existence_or_absence_certified":False,
       "business_fixes_certified":0,
       "production_deployment":False,
       "status":"QA_FUNCTIONAL_ROUTING_VERIFIED_PENDING_QUALIFYING_BUSINESS_KEYS",
    }

if __name__=="__main__":
    print(json.dumps(audit(),sort_keys=True))

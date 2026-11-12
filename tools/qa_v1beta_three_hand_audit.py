"""QA replay of five August tickets: SAP, Distribucion and Comercial source truth.

Reads existing HMAC-bound receipts and previously sealed Qwen outputs.
No SQL, model calls, DML, network writes or historical solutions.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

from else_dominance.aug2026_sap_ot_verified import data, eligible, verify_case
from else_dominance.operational_ot_verified import verify_case_operational
from else_dominance.commercial_ot_verified import verify_case_commercial
from else_dominance.functional_live_triple_v3_1 import check_addendum

MODEL_RESULTS = Path(
    "/home/u23u/else_itil_comm_ot_qa_20261111/triple_v3_1_diagnostics"
)

def audit():
    cohort, _ = data()
    cases = sorted(eligible(cohort))
    if len(cases) != 5:
        raise ValueError("EXACT_QA_FIVE_CASE_COHORT_REQUIRED")
    counts=Counter()
    pins=[]
    for sha in cases:
        a=verify_case(sha)
        b=verify_case_operational(sha)
        c=verify_case_commercial(sha)
        if not (a["o5_o13_o15_verified"] is True
                and b["native_o5_o13_o15_verified"] is True
                and c["native_o5_o13_o15_verified"] is True
                and a["observation"]["order_found_in_specific_table"] is False
                and b["order_found"] is False
                and c["order_found"] is False):
            raise ValueError("THREE_EVIDENCE_READS_NOT_BOUNDED")
        counts["cases_with_three_verified_hands"]+=1
        if len({a["sap_o5_receipt_sha256"],
                b["source_receipt_sha256"],c["source_receipt_sha256"]})!=3:
            raise ValueError("DUPLICATE_OR_REUSED_RECEIPT")
        file=MODEL_RESULTS/(sha+".private.json")
        if not file.is_file() or file.is_symlink():
            raise ValueError("MODEL_RESULT_MISSING")
        raw=file.read_bytes()
        result=json.loads(raw)
        if (result["case_sha256"]!=sha
            or result["verified_sap_source"]["sap_o5_receipt_sha256"]
                  !=a["sap_o5_receipt_sha256"]
            or result["verified_operational_source"]["source_receipt_sha256"]
                  !=b["source_receipt_sha256"]
            or result["verified_commercial_source"]["source_receipt_sha256"]
                  !=c["source_receipt_sha256"]
            or result["repair_certified"] is not False
            or result["root_cause_certified"] is not False
            or result["historical_solution_exposed"] is not False):
            raise ValueError("MODEL_RESULT_NOT_EXACT_RECEIPTS")
        accepted=result["quality"]["accepted"]
        counts["model_result_accepted" if accepted else "model_result_blocked"]+=1
        if accepted:
            replay=check_addendum(
               result["model_addendum"],a,b,c)
            if replay["accepted"] is not True:
                raise ValueError("MODEL_GATE_REPLAY_CHANGED")
        else:
            if result.get("model_addendum"):
                raise ValueError("BLOCKED_MODEL_RESULT_MISREPRESENTED")
        pins.append({"case_sha256":sha,
                     "sealed_model_sha256":sha256(raw).hexdigest(),
                     "sap_receipt_sha256":a["sap_o5_receipt_sha256"],
                     "operational_receipt_sha256":b["source_receipt_sha256"],
                     "commercial_receipt_sha256":c["source_receipt_sha256"]})
    return {
      "schema":"else.itil.v1beta.qa.three-native-hands-replay.v1",
      "total_cases":len(cases),
      "three_native_o5_o13_o15_verified":counts["cases_with_three_verified_hands"],
      "qwen_contract_accepted":counts["model_result_accepted"],
      "qwen_contract_blocked":counts["model_result_blocked"],
      "all_queries_read_only":True,
      "new_queries_executed_by_audit":0,
      "repairs_certified":0,
      "root_causes_certified":0,
      "historical_solutions_used_by_generator":0,
      "seal_manifest_sha256":sha256(json.dumps(
          pins,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    }

if __name__=="__main__":
    print(json.dumps(audit(),sort_keys=True))

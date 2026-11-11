#!/usr/bin/env python3
"""Offline replay: 15 signed company-authoritative QA receipts + native O5/O13/O15.

No new SQL, no raw identifiers, no model calls, no historical solutions.
Run only on the authorized audit host with sealed private August artifacts.
"""
from __future__ import annotations
import json

from else_dominance.aug2026_sap_ot_verified import data
from else_dominance.company_routed_verified import (
    ROOT,SOURCE,SOURCE_SHA,DELIVERY,verify_all,summary,digest
)
from else_dominance.company_routed_o5_hand import (
    AuthorizedCompanyRoutedReceipt,build_company_routed_router
)
from else_core.hand_kernel import Outcome

def audit():
    cohort,manifest=data()
    found=verify_all()
    checked=0
    targets=set()
    for sha,item in sorted(found.items()):
        identifier=digest((DELIVERY+":"+sha+":"+manifest["blind_sha256"]).encode())[:32]
        path=ROOT/"outbox"/(identifier+".private.json")
        owner=AuthorizedCompanyRoutedReceipt(
            path,digest(path.read_bytes()),sha,item["itil_company"],
            SOURCE_SHA,len(SOURCE.read_bytes()),
            cohort[sha]["incident_text_redacted"]
        )
        _,router,operation=build_company_routed_router(owner)
        result=router.route(operation)
        if not (
            result.outcome==Outcome.PASS
            and result.guardian_result.verification.passed is True
            and result.guardian_result.verification.independent is True
            and result.guardian_result.executions==1
        ):
            raise ValueError("COMPANY_NATIVE_O5_O13_O15_FAILED")
        output=result.guardian_result.value.outputs
        if (output["itil_company"]!=item["itil_company"]
            or output["qa_target"]!=item["qa_target"]
            or output["exact_qa_hits"]!=sum(item["counts"].values())
            or output["corporate_business_join_certified"] is not False
            or output["repair_certified"] is not False):
            raise ValueError("COMPANY_NATIVE_OUTPUT_DRIFT")
        targets.add(item["qa_target"])
        checked+=1
    out=summary(found)
    out.update({
      "schema":"else.itil.aug2026.qa.company-routed-native-replay.v2",
      "native_o5_o13_o15_pass":checked,
      "native_o5_o13_o15_blocked":len(found)-checked,
      "qa_targets_checked":sorted(targets),
      "new_sql_executed_during_replay":0,
      "historical_solutions_used_by_generator":0,
      "production_deployment":False,
    })
    return out

if __name__=="__main__":
    print(json.dumps(audit(),sort_keys=True))

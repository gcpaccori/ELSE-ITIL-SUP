"""Independent QA campaign verifier for previously created dynamic NuGet case runs.

Never issues SQL, calls Qwen, or exposes any corporate ticket content.
"""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from else_core.itil_feb100_o5_hand import AuthorizedNugetReceipt, QUERY_ID, build_nuget_qa_router
from else_core.contracts import Outcome
from .qa_feb100_native import verify_native_o5

HEX = re.compile(r"[0-9a-f]{64}\Z")


def require(ok,why):
    if not ok:raise ValueError(why)


def get(path:Path):
    require(path.is_file() and not path.is_symlink(),"INPUT_NOT_REGULAR_FILE")
    return json.loads(path.read_bytes())


def verify_all(root:Path, source:Path, *, expected:int=100, allowlist:Path|None=None) -> dict:
    require(root.is_dir() and not root.is_symlink(),"ROOT_INVALID")
    require(source.is_file() and source.name=="Feb100ExactRead.cs",
            "SOURCE_INVALID")
    files=source.read_bytes()
    source_sha=sha256(files).hexdigest()
    # Recovery attempts with incomplete transfers are NOT accepted runs.
    # Select exactly the 100 finalized original cases; never double-count.
    all_runs=[x for x in root.iterdir() if x.is_dir()]
    runs=sorted(x for x in all_runs if
                (x/"verified_final.private.json").is_file())
    require(len(runs)==expected,"FINALIZED_RUN_COUNT_NOT_EXPECTED")
    allowed=None
    if allowlist is not None:
        from qa.qa_feb100_windows import read_allowlist
        allowed=read_allowlist(allowlist)
        require(len(allowed)==expected,"OWNER_SELECTION_COUNT_DRIFT")
    results=[]
    for directory in runs:
        ticket=get(directory/"case.private.json")
        req=get(directory/"tool_request.private.json")
        proof=get(directory/"receipt.private.json")
        result=get(directory/"verified_final.private.json")
        sha=ticket["case_sha256"]
        require(HEX.fullmatch(sha) is not None,"CASE_SHA_INVALID")
        if allowed is not None:
            require(sha in allowed and
                    ticket.get("opened_at")==allowed[sha]["opened_at"] and
                    ticket.get("service_code")==allowed[sha]["service_code"] and
                    ticket.get("module_code")==allowed[sha]["module_code"],
                    "CASE_NOT_IN_ORIGINAL_100_SELECTION")
        require("2026-02-01T00:00:00" <= ticket["opened_at"] <
                "2026-03-01T00:00:00","CASE_OUTSIDE_FEB100")
        require(proof["opened_at"]==ticket["opened_at"],
                "EXACT_COHORT_DATE_NOT_BOUND")
        require(req=={"type":"tool","name":"qa_exact_read",
                     "query_id":QUERY_ID,
                     "parameters":{"case_sha256":sha}},
                "TOOL_REQUEST_NOT_EXACT")
        require(proof["case_sha256"]==sha and
                result["case_sha256"]==sha,"CROSS_FILE_CASE_MISMATCH")
        require(proof["hand_source_sha256"]==source_sha,
                "SOURCE_CODE_SHA_DRIFT")
        require(proof["scope"]=="ELSE70/dbITIL_D/dbo.taIncidente" and
                proof["row_count"]==1 and
                proof["read_only"] is True and
                proof["historical_solution_not_read"] is True,
                "SQL_READ_SCOPE_INVALID")
        require(result["source_receipt_sha256"] ==
                sha256((directory/"receipt.private.json").read_bytes()).hexdigest(),
                "FINAL_RESULT_RECEIPT_BINDING_DRIFT")
        require(result["hand_source_sha256"]==source_sha,
                "MODEL_SOURCE_SHA_MISMATCH")
        require(result["o5_o13_o15_verified"] is True and
                result["model_requested_tool"] is True and
                result["repair_certified"] is False and
                result["root_cause_certified"] is False and
                result["approved_for_training"] is False and
                result["executed_mutations"] is False,
                "FALSE_CERTIFICATION")
        owner=AuthorizedNugetReceipt(
            directory/"receipt.private.json",
            result["source_receipt_sha256"],sha,source_sha,len(files))
        require(proof["hand_manifest_sha256"] ==
                owner.source_receipt()["source_manifest_sha256"],
                "O1_MANIFEST_MISMATCH")
        independent=verify_native_o5(owner)
        require(independent["guardian_o13_pass"] is True and
                independent["dominance_o15_pass"] is True and
                independent["o15_receipt_sha256"]==
                result["o15_receipt_sha256"],
                "O15_CROSS_RUN_DRIFT")
        # Mandatory actual negative: alter exact receipt bytes while keeping
        # the source SHA pin unchanged. No Guardian execution is permitted.
        with TemporaryDirectory() as temp:
            tampered=Path(temp)/"altered.json"
            tampered.write_bytes((directory/"receipt.private.json").read_bytes()+b" ")
            owner_bad=AuthorizedNugetReceipt(tampered,
                result["source_receipt_sha256"],sha,source_sha,len(files))
            _, negative_router, negative_operation = build_nuget_qa_router(owner_bad)
            negative_result = negative_router.route(negative_operation)
            require(negative_result.outcome != Outcome.PASS and
                    negative_result.guardian_result.executions == 0,
                    "NEGATIVE_RECEIPT_TAMPER_PASSED")
        results.append({
            "case_prefix":sha[:16],
            "case_sha256":sha,
            "opened_at":ticket["opened_at"],
            "service_code":proof["service_code"],
            "o5_o13_o15_pass":True,
            "tampered_receipt_rejected":True,
            "status":result["status"],
            "quality_accepted":result["quality"].get("accepted") is True,
            "verified_receipt_sha256":result["source_receipt_sha256"],
            "final_output_sha256":sha256(
                (directory/"verified_final.private.json").read_bytes()).hexdigest(),
        })
    require(len({x["case_prefix"] for x in results})==len(results),
            "DUPLICATE_CASE_IN_RUNS")
    return {
        "schema":"else.itil.qa.feb100-independent-audit.v1",
        "source":"ELSE70/dbITIL_D/dbo.taIncidente",
        "query_id":QUERY_ID,
        "hand_source_sha256":source_sha,
        "period_start":"2026-02-01",
        "period_end_inclusive":"2026-02-28",
        "unique_calendar_days":len({x["opened_at"][:10] for x in results}),
        "runs_verified":len(results),
        "incomplete_transport_attempts_not_counted":len(all_runs)-len(runs),
        "fresh_nuget_receipts_o5_o13_o15_verified":len(results),
        "negative_sha_tamper_tests_rejected":len(results),
        "diagnostic_quality_accepted":sum(x["quality_accepted"] for x in results),
        "human_triage_required":sum(not x["quality_accepted"] for x in results),
        "repairs_certified":0,"training_promotions":0,
        "cases":results}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--expected",type=int,default=100)
    p.add_argument("--allowlist",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    result=verify_all(a.root,a.source,expected=a.expected,
                      allowlist=a.allowlist)
    raw=json.dumps(result,ensure_ascii=False,indent=2).encode()
    with a.out.open("xb") as f:f.write(raw)
    print(json.dumps({k:v for k,v in result.items() if k!="cases"},
                     ensure_ascii=False))


if __name__=="__main__":
    main()

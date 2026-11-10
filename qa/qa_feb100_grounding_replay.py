"""Re-evaluate EXACT original 100 Feb case receipts under provenance policy v2.

Never reads historical solutions, never runs SQL, never alters the first 100
outputs. Each O5/O13/O15 native receipt reverified before real Qwen9B final.
Results are append-only private to the authorized cluster host. Source
catalog is strictly limited to the source actually observed.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
from pathlib import Path
from collections import Counter
import json,os
from datetime import datetime,timezone

from else_core.itil_feb100_o5_hand import AuthorizedNugetReceipt
from else_dominance.agent import OpenAICompatibleModel
from else_dominance.qa_feb100_cluster import (
    finish_fresh_qa_case,parse_strict)
from else_dominance.qa_feb100_native import require_private_local_model_url
from qa.qa_feb100_windows import read_allowlist

SRC=Path("/home/u23u/else_itil_feb100_qa_20261110")
REPO=Path("/home/u23u/else_itil_feb100_grounding_20261110")
SOURCE=REPO/"qa/Feb100ExactRead.cs"
INPUT_RUNS=SRC/"runs"
ALLOW=SRC/"feb100_allowlist.private.jsonl"
OUT=Path("/home/u23u/else_itil_feb100_grounding_qa_20261110")
OUTPUTS=OUT/"outputs"
JOURNAL=OUT/"grounded_v2_replay.private.jsonl"
SOURCE_SHA=sha256(SOURCE.read_bytes()).hexdigest()
MODEL_URL="http://127.0.0.1:18782/v1"
MODEL_NAME="else-itil-riv-qwen9b-gpu6"

def run_one(item):
    case_sha,run=item
    target=OUTPUTS/(case_sha+".private.json")
    if target.exists():
        return {"case_sha256":case_sha,"state":"OUTPUT_EXISTS_REJECTED"}
    try:
        case=parse_strict((run/"case.private.json").read_bytes())
        tool=parse_strict((run/"tool_request.private.json").read_bytes())
        raw=(run/"receipt.private.json").read_bytes()
        proof=parse_strict(raw)
        if (case["case_sha256"]!=case_sha or
            proof["case_sha256"]!=case_sha or
            case.get("historical_solution")!="WITHHELD" or
            proof.get("historical_solution_not_read") is not True or
            proof.get("hand_source_sha256")!=SOURCE_SHA):
            raise ValueError("ORIGINAL_OWNER_PROOF_DRIFT")
        owner=AuthorizedNugetReceipt(
            run/"receipt.private.json",
            sha256(raw).hexdigest(),
            case_sha,SOURCE_SHA,len(SOURCE.read_bytes()))
        if proof.get("hand_manifest_sha256")!=owner.source_receipt()["source_manifest_sha256"]:
            raise ValueError("SOURCE_MANIFEST_NOT_PINNED")
        require_private_local_model_url(MODEL_URL)
        model=OpenAICompatibleModel(MODEL_URL,MODEL_NAME,timeout=160)
        result=finish_fresh_qa_case(
            owner=owner,case=case,model=model,tool_request=tool)
        if (result["o5_o13_o15_verified"] is not True or
            result["source_receipt_sha256"]!=sha256(raw).hexdigest() or
            result["model_requested_tool"] is not True or
            result["quality"].get("accepted") not in (True,False) or
            result["repair_certified"] is not False or
            result["root_cause_certified"] is not False or
            result["approved_for_training"] is not False):
            raise ValueError("V2_OUTPUT_BOUNDARY_INVALID")
        record={
            "schema":"else.itil.qa.feb100.evidence-grounding-v2-replay.v1",
            "case_sha256":case_sha,
            "parent_run_id":run.name,
            "source_receipt_sha256":sha256(raw).hexdigest(),
            "original_final_sha256":sha256((run/"verified_final.private.json").read_bytes()).hexdigest(),
            "new_result":result,
            "generated_utc":datetime.now(timezone.utc).isoformat(),
        }
        serialized=json.dumps(record,ensure_ascii=False,sort_keys=True,
                              separators=(",",":")).encode()
        with target.open("xb") as file:
            file.write(serialized)
        target.chmod(0o600)
        return {"case_sha256":case_sha,"state":"COMPLETED",
                "output_sha256":sha256(serialized).hexdigest(),
                "accepted":result["quality"]["accepted"],
                "attempts":result.get("model_attempts"),
                "repaired_on_second_attempt":(
                    result["quality"]["accepted"] is True and
                    result.get("model_attempts")==2),
                "model_status":result["status"],
                "table_flags":result["quality"].get("safety_flags",[])}
    except Exception as e:
        return {"case_sha256":case_sha,"state":"QA_REPLAY_FAILED",
                "error_type":type(e).__name__,
                "error_code":str(e)[:90] if str(e).isupper() else "QA_RUNTIME_ERROR"}

def main():
    if JOURNAL.exists() or OUTPUTS.exists():
        raise FileExistsError("NO_OVERWRITE_REPLAY")
    rows=read_allowlist(ALLOW)
    original={}
    for run in INPUT_RUNS.glob("case_*"):
        if not (run/"verified_final.private.json").is_file():
            continue
        final=parse_strict((run/"verified_final.private.json").read_bytes())
        sha=final["case_sha256"]
        if sha in original:
            raise ValueError("DUPLICATE_ORIGINAL_FINAL")
        original[sha]=run
    if len(rows)!=100 or len(original)!=100:
        raise ValueError("REPLAY_COHORT_COUNT_DRIFT")
    if set(rows)!=set(original):
        raise ValueError("ORIGINAL_RUNS_NOT_EXACT_OWNER_SELECTION")
    OUTPUTS.mkdir(mode=0o700)
    with JOURNAL.open("x") as writer,ThreadPoolExecutor(max_workers=3) as pool:
        fs={pool.submit(run_one,item):item[0] for item in sorted(original.items())}
        for count,future in enumerate(as_completed(fs),start=1):
            result=future.result()
            writer.write(json.dumps(result,sort_keys=True)+"\n")
            writer.flush()
            if count%10==0:
                os.fsync(writer.fileno())
                print(json.dumps({"processed":count,"total":100,
                    "accepted_so_far":sum(1 for x in OUTPUTS.glob("*.private.json")
                        if json.loads(x.read_bytes())["new_result"]["quality"]["accepted"]),
                    "last_state":result["state"]}),flush=True)
    all_results=[json.loads(line) for line in JOURNAL.read_text().splitlines()]
    print(json.dumps({
        "processed":len(all_results),
        "complete":sum(x["state"]=="COMPLETED" for x in all_results),
        "failures":sum(x["state"]!="COMPLETED" for x in all_results),
        "contract_accepted":sum(x.get("accepted") is True for x in all_results),
        "accepted_after_rewrite":sum(x.get("repaired_on_second_attempt") is True for x in all_results),
        "evidence_sql_reads_reexecuted":0,
        "historical_solutions_shown_to_model":0,
        "journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest()},sort_keys=True),flush=True)

if __name__=="__main__":
    main()

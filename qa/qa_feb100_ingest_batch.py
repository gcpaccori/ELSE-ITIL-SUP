"""Ingest exact Feb NuGet QA receipts via one immutable ZIP, no per-case SSH.

Each receipt is re-bound to genuine exact model tool request and pinned
Feb source SHA. O5/O13/O15 verifies independently during finalization.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json,zipfile,re,os
from qa_feb100_windows import read_allowlist,validate_model_tool,canonical

QA=Path("/home/u23u/else_itil_feb100_qa_20261110")
REPO=Path("/home/u23u/else_itil_feb100_20261110")
ROOT=QA/"runs"
ZIP=QA/"batch_sql_receipts.private.zip"
MANIFEST=QA/"missing_model_requests.private.jsonl"
ALLOW=QA/"feb100_allowlist.private.jsonl"
SOURCE=REPO/"qa/Feb100ExactRead.cs"
SHA=re.compile(r"[0-9a-f]{64}\Z")
RUN=re.compile(r"case_[0-9a-f]{16}_[0-9a-f]{10}\Z")
def demand(ok,code):
    if not ok:raise ValueError(code)
def main():
    rows=read_allowlist(ALLOW)
    manifest=[json.loads(x) for x in MANIFEST.read_text().splitlines() if x.strip()]
    by_run={x["run_id"]:x for x in manifest}
    demand(len(by_run)==len(manifest),"DUPLICATE_RUN_ID")
    source_sha=sha256(SOURCE.read_bytes()).hexdigest()
    accepted=[]
    with zipfile.ZipFile(ZIP,"r") as archive:
        names=archive.namelist()
        demand(len(names)==len(set(names)),"DUPLICATE_ZIP_ENTRY")
        for name in names:
            parts=name.split("/")
            demand(len(parts)==2 and parts[1]=="receipt.private.json" and
                   RUN.fullmatch(parts[0]) is not None,
                   "ARCHIVE_PATH_NOT_ALLOWED")
            run_id=parts[0]
            demand(run_id in by_run,"RECEIPT_NOT_REQUESTED")
            record=by_run[run_id]
            sha=record["case_sha256"]
            demand(sha in rows,"CASE_OUTSIDE_OWNER_ALLOWLIST")
            p=ROOT/run_id
            demand(p.is_dir() and not p.is_symlink(),"RUN_ID_NOT_EXISTING")
            case=json.loads((p/"case.private.json").read_bytes())
            tool=json.loads((p/"tool_request.private.json").read_bytes())
            demand(case.get("case_sha256")==sha and
                   case.get("historical_solution")=="WITHHELD",
                   "CASE_BINDING_FAIL")
            validate_model_tool(tool,sha)
            demand(sha256(canonical(tool)).hexdigest()==
                   record["model_tool_request_sha256"],
                   "MODEL_REQUEST_SHA_MISMATCH")
            raw=archive.read(name)
            demand(100<len(raw)<10_000,"RECEIPT_BYTES_INVALID")
            receipt=json.loads(raw)
            demand(receipt.get("case_sha256")==sha and
                   receipt.get("query_id")==
                   "ITIL_2026_02_FEB100_CASE_EXACT_READ" and
                   receipt.get("hand_source_sha256")==source_sha and
                   receipt.get("row_count")==1 and
                   receipt.get("read_only") is True and
                   receipt.get("historical_solution_not_read") is True and
                   receipt.get("functional_repair_certified") is False,
                   "RECEIPT_OWNER_SCOPE_INVALID")
            demand(receipt.get("opened_at")==rows[sha]["opened_at"] and
                   receipt.get("service_code")==rows[sha]["service_code"] and
                   receipt.get("module_code")==rows[sha]["module_code"] and
                   receipt.get("classification_code")==rows[sha]["classification_code"],
                   "RECEIPT_ROWS_NOT_BOUND")
            target=p/"receipt.private.json"
            demand(not target.exists(),"RECEIPT_OVERWRITE_DENIED")
            with target.open("xb") as out:
                out.write(raw)
            target.chmod(0o600)
            accepted.append({"run_id":run_id,"case_sha256":sha,
                            "receipt_sha256":sha256(raw).hexdigest(),
                            "pending_native_o5":True})
    report={"schema":"else.itil.feb100.batch-receipt-ingest.v1",
            "model_requested_count":len(manifest),
            "receipt_count":len(accepted),
            "zip_sha256":sha256(ZIP.read_bytes()).hexdigest(),
            "read_only":True,
            "native_o5_results_pending":True}
    target=QA/"batch_receipt_ingest.json"
    if target.exists():raise FileExistsError("NO_OVERWRITE_AUDIT")
    target.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()

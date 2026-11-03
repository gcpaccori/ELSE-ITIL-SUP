"""Monthly 2026 QA replay, fail-closed on data scope and exact inputs.

Does not extract or send corporate data on its own. An approval assertion must be
supplied through a separately managed local control plane; the signature alone
does NOT independently establish corporate legal authority.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import socket
from datetime import datetime, timezone
from collections import Counter
from .resolution_batch import (
    process_jsonl, require_holdout, require_history, OpenAICompatibleModel,
)

TARGET_MONTH = "2026-09"
EXPECTED_SEPTEMBER = 545
APPROVAL_ENV = "RIV_QA_APPROVAL_HMAC_KEY"


def _sha(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def verify_operator_approval(
    approval_path: str | Path,
    *, history_path: str | Path,
    holdout_path: str | Path,
    output_path: str | Path,
    model_name: str,
    model_url: str,
    count: int = EXPECTED_SEPTEMBER,
    month: str = TARGET_MONTH,
) -> str:
    """Technical binding; requires an independently controlled signing key."""
    secret = os.getenv(APPROVAL_ENV, "")
    if len(secret) < 32:
        raise PermissionError("INDEPENDENT_APPROVAL_KEY_REQUIRED")
    approval = json.loads(Path(approval_path).read_text("utf-8"))
    if not isinstance(approval, dict):
        raise PermissionError("APPROVAL_NOT_AN_OBJECT")
    supplied = approval.get("signature_sha256", "")
    unsigned = {k: v for k, v in approval.items() if k != "signature_sha256"}
    expected = hmac.new(secret.encode(), _canonical(unsigned), hashlib.sha256).hexdigest()
    if not isinstance(supplied, str) or not hmac.compare_digest(expected, supplied):
        raise PermissionError("INVALID_APPROVAL_SIGNATURE")
    checks = {
        "schema": "riv.qa-2026-private-batch.approval.v1",
        "status": "APPROVED",
        "purpose": "READ_ONLY_CASE_INVESTIGATION",
        "case_month": month,
        "case_count": count,
        "history_sha256": _sha(history_path),
        "holdout_sha256": _sha(holdout_path),
        "model_name": model_name,
        "model_url": model_url,
        "execution_host": socket.gethostname(),
        "output_directory": str(Path(output_path).resolve().parent),
        "data_treatment": "PRIVATE_APPROVED_INFERENCE",
    }
    for key, expected_value in checks.items():
        if approval.get(key) != expected_value:
            raise PermissionError("APPROVAL_SCOPE_MISMATCH_" + key.upper())
    for field in ("approved_by", "approval_reference", "data_owner"):
        if not isinstance(approval.get(field), str) or len(approval[field].strip()) < 5:
            raise PermissionError("APPROVAL_MISSING_" + field.upper())
    start = datetime.fromisoformat(str(approval["issued_utc"]).replace("Z", "+00:00"))
    stop = datetime.fromisoformat(str(approval["expires_utc"]).replace("Z", "+00:00"))
    if start.tzinfo is None or stop.tzinfo is None:
        raise PermissionError("APPROVAL_TIMEZONE_MISSING")
    now = datetime.now(timezone.utc)
    if not start <= now <= stop or (stop-start).total_seconds() > 86400:
        raise PermissionError("APPROVAL_EXPIRED_OR_TOO_BROAD")
    # No claim that the approving organization's identity was independently
    # verified. Corporate authorization must be confirmed out of band.
    return hashlib.sha256(_canonical(approval)).hexdigest()


def preflight(
    history_path: str | Path,
    holdout_path: str | Path,
    *,
    count: int,
    month: str,
    synthetic_only: bool = False,
) -> dict:
    if month != TARGET_MONTH:
        raise ValueError("MONTH_NOT_CONFIGURED")
    history_count, case_count, ids = 0, 0, set()
    with open(history_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            raw = json.loads(line)
            if synthetic_only and raw.get("synthetic") is not True:
                raise PermissionError("SYNTHETIC_HISTORY_MARKER_REQUIRED")
            case = require_history(raw)
            if synthetic_only and not case.case_ref.startswith("itil-SYN"):
                raise PermissionError("REAL_HISTORY_FORBIDDEN_IN_SYNTHETIC_TEST")
            history_count += 1
    with open(holdout_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            raw = json.loads(line)
            if synthetic_only and raw.get("synthetic") is not True:
                raise PermissionError("SYNTHETIC_CASE_MARKER_REQUIRED")
            if synthetic_only and not str(raw.get("case_ref", "")).startswith("itil-SYN"):
                raise PermissionError("REAL_CASE_FORBIDDEN_IN_SYNTHETIC_TEST")
            case = require_holdout(raw, month=month)
            if case["case_ref"] in ids:
                raise ValueError("DUPLICATE_CASE_REF")
            ids.add(case["case_ref"])
            case_count += 1
    if case_count != count:
        raise ValueError("EXACT_MONTH_COUNT_MISMATCH")
    return {
        "cases": case_count,
        "history": history_count,
        "history_sha256": _sha(history_path),
        "holdout_sha256": _sha(holdout_path),
    }


def run(
    model,
    history_path: str,
    holdout_path: str,
    output_path: str,
    *,
    expected_count: int = EXPECTED_SEPTEMBER,
    month: str = TARGET_MONTH,
    model_name: str,
    model_url: str,
    approval_file: str | None = None,
    synthetic_only: bool = False,
) -> dict:
    if not synthetic_only and approval_file is None:
        raise PermissionError("CORPORATE_BATCH_REQUIRES_SIGNED_APPROVAL")
    if not model_name or not model_url:
        raise ValueError("MODEL_IDENTITY_REQUIRED")
    for p in (history_path, holdout_path):
        if not Path(p).is_file():
            raise FileNotFoundError("MISSING_PRIVATE_INPUT")
    if Path(output_path).resolve() in {
        Path(history_path).resolve(), Path(holdout_path).resolve()
    }:
        raise ValueError("OUTPUT_INPUT_PATH_COLLISION")
    # The signature check occurs BEFORE reading any private incident content.
    # verify_operator_approval checks the signature before it reads content SHA.
    if synthetic_only:
        approval_digest = "SYNTHETIC_ONLY_NO_CORPORATE_APPROVAL"
    else:
        approval_digest = verify_operator_approval(
            approval_file, history_path=history_path, holdout_path=holdout_path,
            output_path=output_path, model_name=model_name, model_url=model_url,
            count=expected_count, month=month)
    manifest = preflight(history_path, holdout_path, count=expected_count,
                         month=month, synthetic_only=synthetic_only)
    identity = {
        "approval_digest": approval_digest,
        "history_sha256": manifest["history_sha256"],
        "holdout_sha256": manifest["holdout_sha256"],
        "model_name": model_name,
        "model_url": model_url,
        "month": month,
        "expected_count": expected_count,
        "synthetic_only": synthetic_only,
    }
    run_id = hashlib.sha256(_canonical(identity)).hexdigest()
    out = Path(output_path).resolve()
    marker = out.with_suffix(out.suffix + ".scope.json")
    if out.exists() or marker.exists():
        if not out.exists() or not marker.exists():
            raise ValueError("INCOMPLETE_RESUME_SCOPE_RECEIPT")
        existing = json.loads(marker.read_text("utf-8"))
        if existing.get("run_id") != run_id:
            raise ValueError("RESUME_SCOPE_CHANGED")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        marker.write_text(json.dumps({"run_id": run_id, "identity": identity},
                                     indent=2), encoding="utf-8")
        try:
            os.chmod(marker, 0o600)
        except OSError:
            pass
    result = process_jsonl(
        model, history_path, holdout_path, str(out), expected_count=expected_count)
    latest_by_case = {}
    physical_lines = 0
    with out.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                physical_lines += 1
                latest_by_case[row["case_ref"]] = row
    tally = Counter(r["status"] for r in latest_by_case.values())
    return {
        "month": month, "cases": expected_count,
        "input_records_present": manifest["cases"],
        "written_this_run": result["processed_this_run"],
        "unique_cases_with_result": len(latest_by_case),
        "physical_receipt_lines": physical_lines,
        "status_counts": dict(tally),
        "run_id": run_id[:16],
        "synthetic_only": synthetic_only,
        "corporate_repair_certified": 0,
        "private_outputs_only": True,
        "external_authority_independently_verified": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Private QA batch; exact month preflight")
    p.add_argument("--history", required=True)
    p.add_argument("--holdout", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--approval-file")
    p.add_argument("--synthetic-only", action="store_true")
    p.add_argument("--expected-count", type=int, default=EXPECTED_SEPTEMBER)
    p.add_argument("--month", default=TARGET_MONTH)
    p.add_argument("--model", default="else-itil-riv-gpu7")
    p.add_argument("--base-url", default="http://127.0.0.1:18781/v1")
    args = p.parse_args(argv)
    if args.expected_count <= 0:
        p.error("COUNT_MUST_BE_POSITIVE")
    # Reject before initializing model unless there is a separate local
    # signed assertion for private processing.
    if not args.synthetic_only and not args.approval_file:
        p.error("APPROVAL_REQUIRED")
    model = OpenAICompatibleModel(args.base_url, args.model, timeout=160)
    result = run(model, args.history, args.holdout, args.output,
                 expected_count=args.expected_count, month=args.month,
                 model_name=args.model, model_url=args.base_url,
                 approval_file=args.approval_file,
                 synthetic_only=args.synthetic_only)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

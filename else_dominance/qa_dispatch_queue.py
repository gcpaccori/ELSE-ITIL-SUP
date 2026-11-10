"""ELSE-ITIL QA dispatcher: durable request queue for an outbound Windows worker.

Only opaque SHA-256 IDs of owner-allowed historical QA incidents are accepted.
The worker connects OUTBOUND through its existing authorized SSH transport.
Successful completion re-verifies exact private NuGet receipts via native O5/O13/O15.
This is NOT a corporate repair tool, ticket mutator or source of human approvals.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import uuid

SCHEMA = "else.itil.qa.outbound-dispatch.v1"
SOURCE = "ELSE70/dbITIL_D/dbo.taIncidente"
QUERY = "ITIL_2026_09_CASE_EXACT_READ"
ROOT = Path("/home/u23u/else_itil_dynamic_nuget_qa_20261109/runs")
HEX = re.compile(r"[0-9a-f]{64}\Z")
JOB = re.compile(r"[0-9a-f]{32}\Z")
RUN = re.compile(r"case_[0-9a-f]{16}_[0-9a-f]{10}\Z")
WORKER = re.compile(r"[A-Z][A-Z0-9_-]{2,45}\Z")
ERROR = re.compile(r"[A-Z][A-Z0-9_]{2,63}\Z")


def require(cond, code):
    if not cond:
        raise ValueError(code)


def now():
    return datetime.now(timezone.utc)


def timestamp(date=None):
    return (date or now()).isoformat()


def obj(raw):
    def unique(pairs):
        z = {}
        for k, v in pairs:
            if k in z:
                raise ValueError("DUPLICATE_JSON_KEY")
            z[k] = v
        return z
    data = json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          ValueError("NONFINITE_JSON")))
    require(type(data) is dict, "JSON_OBJECT_REQUIRED")
    return data


def digest(raw):
    return sha256(raw).hexdigest()


def load_allowed(path: Path, expected_count=545) -> frozenset[str]:
    require(path.is_file() and not path.is_symlink(), "QA_ALLOWLIST_MISSING")
    lines = path.read_text(encoding="utf-8").splitlines()
    require(len(lines) == expected_count, "QA_ALLOWLIST_COUNT_DRIFT")
    require(all(HEX.fullmatch(x) for x in lines), "QA_ALLOWLIST_ID_INVALID")
    require(lines == sorted(set(lines)), "QA_ALLOWLIST_NOT_CANONICAL")
    return frozenset(lines)


def init(db: sqlite3.Connection):
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS qa_jobs (
      job_id TEXT PRIMARY KEY,
      case_sha256 TEXT NOT NULL,
      state TEXT NOT NULL CHECK(state IN
        ('QUEUED','RUNNING','COMPLETED','FAILED','EXPIRED')),
      worker TEXT,
      claim_sha256 TEXT,
      claimed_until_utc TEXT,
      created_utc TEXT NOT NULL,
      updated_utc TEXT NOT NULL,
      result_json TEXT,
      error_code TEXT
    );
    CREATE INDEX IF NOT EXISTS ix_qa_jobs_queued ON qa_jobs(state,created_utc);
    CREATE INDEX IF NOT EXISTS ix_qa_jobs_case ON qa_jobs(case_sha256,state);
    """)


class QaDispatchQueue:
    def __init__(self, db_path: Path, allowed: frozenset[str]):
        require(db_path.is_absolute() and not db_path.is_symlink(),
                "QUEUE_DB_PATH_INVALID")
        require(bool(allowed), "ALLOWED_CASES_EMPTY")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if not db_path.exists():
            fd=os.open(db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        self.conn=sqlite3.connect(str(db_path),timeout=15,isolation_level=None)
        init(self.conn)
        self.allowed=allowed

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _begin(self):
        self.conn.execute("BEGIN IMMEDIATE")

    def submit(self, sha: str) -> dict:
        require(type(sha) is str and HEX.fullmatch(sha) is not None,
                "CASE_SHA256_INVALID")
        require(sha in self.allowed, "CASE_NOT_IN_QA_ALLOWLIST")
        self._begin()
        try:
            # Same case while queued/running is the exact same job,
            # avoiding parallel independent Windows reads.
            duplicate=self.conn.execute(
                "SELECT job_id,state FROM qa_jobs WHERE case_sha256=? "
                "AND state IN ('QUEUED','RUNNING') ORDER BY created_utc DESC LIMIT 1",
                (sha,)).fetchone()
            if duplicate:
                self.conn.commit()
                return {"schema":SCHEMA,"job_id":duplicate[0],
                        "state":duplicate[1],"deduplicated":True}
            jid=uuid.uuid4().hex
            stamp=timestamp()
            self.conn.execute(
                "INSERT INTO qa_jobs (job_id,case_sha256,state,created_utc,"
                "updated_utc) VALUES(?,?,?,?,?)",
                (jid,sha,"QUEUED",stamp,stamp))
            self.conn.commit()
            return {"schema":SCHEMA,"job_id":jid,"state":"QUEUED",
                    "deduplicated":False}
        except Exception:
            self.conn.rollback()
            raise

    def _expire(self):
        stamp=timestamp()
        self.conn.execute(
            "UPDATE qa_jobs SET state='EXPIRED',updated_utc=?,"
            "claim_sha256=NULL,error_code='WORKER_LEASE_EXPIRED' "
            "WHERE state='RUNNING' AND claimed_until_utc < ?",
            (stamp,stamp))

    def claim(self, worker: str="ELSE62-QA", lease_seconds:int=900):
        require(type(worker) is str and WORKER.fullmatch(worker) is not None,
                "WORKER_ID_INVALID")
        require(type(lease_seconds) is int and 60<=lease_seconds<=1800,
                "LEASE_INVALID")
        self._begin()
        try:
            self._expire()
            row=self.conn.execute(
                "SELECT job_id,case_sha256 FROM qa_jobs WHERE state='QUEUED' "
                "ORDER BY created_utc,job_id LIMIT 1").fetchone()
            if not row:
                self.conn.commit()
                return {"schema":SCHEMA,"state":"EMPTY"}
            jid,sha=row
            require(sha in self.allowed, "CLAIM_CASE_NOT_ALLOWED")
            ticket=secrets.token_urlsafe(32)
            until=timestamp(now()+timedelta(seconds=lease_seconds))
            self.conn.execute(
                "UPDATE qa_jobs SET state='RUNNING',worker=?,claim_sha256=?,"
                "claimed_until_utc=?,updated_utc=? WHERE job_id=? AND state='QUEUED'",
                (worker,digest(ticket.encode()),until,timestamp(),jid))
            self.conn.commit()
            return {"schema":SCHEMA,"state":"CLAIMED",
                    "job_id":jid,"case_sha256":sha,
                    "claim_token":ticket,"lease_until_utc":until}
        except Exception:
            self.conn.rollback()
            raise

    def finish(self, message:dict, verifier=None):
        require(type(message) is dict and
                set(message)=={"job_id","case_sha256","claim_token",
                               "outcome","result"},
                "JOB_FINISH_SCHEMA_INVALID")
        jid=message["job_id"]
        sha=message["case_sha256"]
        token=message["claim_token"]
        require(type(jid) is str and JOB.fullmatch(jid) is not None,
                "JOB_ID_INVALID")
        require(type(sha) is str and HEX.fullmatch(sha) is not None and
                sha in self.allowed,"CASE_NOT_ALLOWED")
        require(type(token) is str and len(token)>35,
                "CLAIM_TOKEN_INVALID")
        require(message["outcome"] in ("COMPLETED","FAILED"),
                "OUTCOME_INVALID")
        self._begin()
        try:
            self._expire()
            row=self.conn.execute(
                "SELECT case_sha256,state,claim_sha256,claimed_until_utc,"
                "updated_utc FROM qa_jobs WHERE job_id=?",(jid,)).fetchone()
            require(row is not None, "JOB_NOT_FOUND")
            require(row[0]==sha and row[1]=="RUNNING",
                    "JOB_SCOPE_OR_STATE_DRIFT")
            require(row[2] is not None and
                    hmac.compare_digest(row[2],digest(token.encode())),
                    "CLAIM_TOKEN_MISMATCH")
            require(datetime.fromisoformat(row[3]) >= now(),
                    "CLAIM_LEASE_EXPIRED")
            if message["outcome"]=="COMPLETED":
                result=message["result"]
                require(type(result) is dict and
                        result.get("schema")==
                        "else.itil.qa.dynamic-nuget-hand.v1",
                        "WORKER_RESULT_SCHEMA_INVALID")
                if verifier is None:
                    summary=verify_actual_receipts(
                        result,sha,
                        min_issued_at=datetime.fromisoformat(row[4]))
                else:
                    # Injectable only for synthetic unit tests; runtime
                    # always uses native O5/O13/O15 proof verification.
                    summary=verifier(result,sha)
                new_state="COMPLETED"
                error_code=None
            else:
                result=message["result"]
                require(type(result) is dict and
                        set(result)=={"error_code"} and
                        type(result["error_code"]) is str and
                        ERROR.fullmatch(result["error_code"]) is not None,
                        "ERROR_CODE_NOT_ALLOWED")
                summary=None
                error_code=result["error_code"]
                new_state="FAILED"
            self.conn.execute(
                "UPDATE qa_jobs SET state=?,result_json=?,error_code=?,"
                "claim_sha256=NULL,updated_utc=? WHERE job_id=? AND state='RUNNING'",
                (new_state,json.dumps(summary,sort_keys=True)
                 if summary is not None else None,
                 error_code,timestamp(),jid))
            self.conn.commit()
            return {"schema":SCHEMA,"job_id":jid,"state":new_state}
        except Exception:
            self.conn.rollback()
            raise

    def status(self, jid: str) -> dict:
        require(type(jid) is str and JOB.fullmatch(jid) is not None,
                "JOB_ID_INVALID")
        row=self.conn.execute(
            "SELECT state,created_utc,updated_utc,result_json,error_code,"
            "case_sha256 FROM qa_jobs WHERE job_id=?",(jid,)).fetchone()
        require(row is not None,"JOB_NOT_FOUND")
        result={"schema":SCHEMA,"job_id":jid,"state":row[0],
                "created_utc":row[1],"updated_utc":row[2],
                "case_sha_prefix":row[5][:16],
                "functional_repair_certified":False,
                "human_confirmation":False}
        if row[3]:
            result["investigation"]=json.loads(row[3])
        if row[4]:
            result["error_code"]=row[4]
        return result


def validate_freshness(issued_at: str, min_issued_at: datetime) -> None:
    require(type(issued_at) is str and type(min_issued_at) is datetime,
            "RECEIPT_TIME_INVALID")
    try:
        observed=datetime.fromisoformat(issued_at.replace("Z","+00:00"))
    except (ValueError,TypeError) as exc:
        raise ValueError("RECEIPT_TIME_INVALID") from exc
    require(observed.tzinfo is not None and
            min_issued_at.tzinfo is not None,"RECEIPT_TIMEZONE_REQUIRED")
    require(observed >= min_issued_at-timedelta(seconds=90),
            "STALE_RECEIPT_BEFORE_JOB_CLAIM")
    require(observed <= now()+timedelta(minutes=3),
            "RECEIPT_TIMESTAMP_IN_FUTURE")


def verify_actual_receipts(payload:dict, expected_sha:str,
                           *, min_issued_at:datetime|None=None) -> dict:
    """Independent callback validation; no success based on Windows say-so."""
    from else_core.itil_nuget_o5_hand import AuthorizedNugetReceipt, QUERY_ID
    from .qa_native_runtime import verify_native_o5

    require(payload.get("model_requested_tool_before_sql") is True and
            payload.get("new_qa_sql_read_executed") is True and
            payload.get("o5_o13_o15_verified") is True and
            payload.get("model_reconsidered_after_evidence") is True and
            payload.get("repair_certified") is False,
            "FALSE_EXECUTION_OR_REPAIR_CLAIM")
    require(payload.get("case_sha_prefix")==expected_sha[:16],
            "RESULT_WRONG_CASE")
    run_id=payload.get("run_id")
    require(type(run_id) is str and RUN.fullmatch(run_id) is not None
            and run_id.startswith("case_"+expected_sha[:16]+"_"),
            "RUN_ID_NOT_ALLOWED")
    require(payload.get("private_cluster_run")==str(ROOT/run_id),
            "PRIVATE_RUN_PATH_MISMATCH")
    run_path=ROOT/run_id
    require(run_path.is_dir() and not run_path.is_symlink(),
            "QA_RUN_MISSING")
    def file(name):
        p=run_path/name
        require(p.is_file() and not p.is_symlink(),
                "REQUIRED_RUN_FILE_MISSING")
        return obj(p.read_bytes())
    case=file("case.private.json")
    request=file("tool_request.private.json")
    receipt=file("receipt.private.json")
    final=file("verified_final.private.json")
    if min_issued_at is not None:
        # Windows and Linux QA clocks may be unsynchronized. The receipt's
        # original Windows timestamp is retained for audit, but freshness
        # relies on when the authorized Linux host received exact bytes.
        # scp without -p writes local host mtime; no model can supply it.
        uploaded_at=datetime.fromtimestamp(
            (run_path/"receipt.private.json").stat().st_mtime,
            tz=timezone.utc)
        validated_at=datetime.fromtimestamp(
            (run_path/"verified_final.private.json").stat().st_mtime,
            tz=timezone.utc)
        validate_freshness(uploaded_at.isoformat(),min_issued_at)
        require(validated_at>=uploaded_at-timedelta(seconds=5),
                "MODEL_RESULT_PRECEDES_RECEIPT_TRANSFER")
        validate_freshness(validated_at.isoformat(),min_issued_at)
    require(case.get("case_sha256")==expected_sha and
            receipt.get("case_sha256")==expected_sha and
            final.get("case_sha256")==expected_sha,
            "RECEIPT_CASE_DRIFT")
    require(request=={"type":"tool","name":"qa_exact_read",
                     "query_id":QUERY_ID,
                     "parameters":{"case_sha256":expected_sha}},
            "TOOL_REQUEST_NOT_EXACT")
    require(receipt.get("scope")==SOURCE and
            receipt.get("read_only") is True and
            receipt.get("row_count")==1 and
            receipt.get("historical_solution_not_read") is True,
            "NUGET_RECEIPT_SCOPE_INVALID")
    receipt_sha=digest((run_path/"receipt.private.json").read_bytes())
    output_sha=digest((run_path/"verified_final.private.json").read_bytes())
    require(payload.get("receipt_sha256")==receipt_sha and
            payload.get("final_output_sha256")==output_sha,
            "WINDOWS_RESULT_HASH_MISMATCH")
    require(final.get("source_receipt_sha256")==receipt_sha and
            final.get("model_requested_tool") is True and
            final.get("o5_o13_o15_verified") is True and
            final.get("repair_certified") is False and
            final.get("root_cause_certified") is False and
            final.get("approved_for_training") is False and
            final.get("executed_mutations") is False,
            "FINAL_ASSERTION_INVALID")
    code=Path(__file__).resolve().parents[1]/"qa/LiveITILQARead.cs"
    require(code.is_file(),"QA_CODE_NOT_AVAILABLE")
    source_raw=code.read_bytes()
    source_sha=digest(source_raw)
    require(receipt.get("hand_source_sha256")==source_sha and
            final.get("hand_source_sha256")==source_sha,
            "EXACT_EXECUTED_SOURCE_SHA_MISMATCH")
    owner=AuthorizedNugetReceipt(
        run_path/"receipt.private.json",receipt_sha,
        expected_sha,source_sha,len(source_raw))
    require(receipt.get("hand_manifest_sha256")==
            owner.source_receipt()["source_manifest_sha256"],
            "SOURCE_MANIFEST_BINDING_FAILED")
    verified=verify_native_o5(owner)
    require(verified.get("guardian_o13_pass") is True and
            verified.get("dominance_o15_pass") is True and
            verified.get("o15_receipt_sha256")==
            final.get("o15_receipt_sha256"),
            "SECOND_O5_GUARDIAN_VERIFICATION_FAILED")
    quality=final.get("quality")
    require(type(quality) is dict and
            type(quality.get("accepted")) is bool,
            "MODEL_QUALITY_MISSING")
    accepted=quality["accepted"]
    proposal=final.get("proposal")
    if accepted:
        require(type(proposal) is dict and
                proposal.get("ejecutado") is False and
                proposal.get("confirmado") is False and
                type(proposal.get("pasos")) is list and
                1 <= len(proposal["pasos"]) <= 3,
                "MODEL_PLAN_NOT_REVIEWABLE")
    else:
        require(proposal=={},"REJECTED_MODEL_PLAN_NOT_QUARANTINED")
    context=final.get("independently_reinspected_metadata")
    require(type(context) is dict and
            context.get("service_code")==receipt.get("service_code") and
            context.get("module_code")==receipt.get("module_code") and
            context.get("classification_code")==receipt.get("classification_code"),
            "MODEL_METADATA_NOT_BOUND_TO_SQL")
    expected_status=(quality.get("status") if accepted
                     else "NEEDS_HUMAN_TRIAGE")
    require(final.get("status")==expected_status and
            payload.get("diagnosis_status")==expected_status and
            payload.get("quality_accepted")==accepted,
            "RESULT_STATUS_MISMATCH")
    return {"schema":SCHEMA,
            "qa_scope":SOURCE,"query_id":QUERY,
            "case_sha_prefix":expected_sha[:16],
            "state":"EVIDENCE_VERIFIED",
            "o5_o13_o15_verified":True,
            "fresh_read_after_model_request":True,
            "model_reconsidered_with_evidence":True,
            "diagnosis_status":expected_status,
            "quality_accepted":accepted,
            "human_review_required":True,
            "proposal":final.get("proposal",{}) if accepted else {},
            "quality":{"accepted":accepted,
                       "schema_flags":quality.get("schema_flags",[]),
                       "safety_flags":quality.get("safety_flags",[]),
                       "review_flags":quality.get("review_flags",[])},
            "receipt_sha256":receipt_sha,
            "model_output_sha256":output_sha,
            "repair_certified":False,
            "root_cause_certified":False,
            "automatic_memory_promotions":0}


def main(argv=None):
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="action",required=True)
    for action in ("claim","complete","status","summary"):
        sp=sub.add_parser(action)
        sp.add_argument("--db",required=True,type=Path)
        sp.add_argument("--allowlist",required=True,type=Path)
        if action=="claim":
            sp.add_argument("--worker",default="ELSE62-QA")
        if action=="status":
            sp.add_argument("--job-id",required=True)
    args=p.parse_args(argv)
    allowed=load_allowed(args.allowlist)
    with QaDispatchQueue(args.db,allowed) as q:
        if args.action=="claim":
            result=q.claim(worker=args.worker)
        elif args.action=="complete":
            try:
                result=q.finish(obj(sys.stdin.buffer.read()))
            except Exception as exc:
                # Never echo a claim token, case text, SQL, or traceback.
                code=str(exc)
                if ERROR.fullmatch(code) is None:
                    code="COMPLETION_VERIFIER_EXCEPTION_"+type(exc).__name__.upper()
                print(json.dumps({"error_code":code}),file=sys.stderr,flush=True)
                raise SystemExit(3)
        elif args.action=="status":
            result=q.status(args.job_id)
        else:
            rows=q.conn.execute(
                "SELECT state,count(*) FROM qa_jobs GROUP BY state").fetchall()
            result={"schema":SCHEMA,"job_state_counts":dict(rows)}
    print(json.dumps(result,ensure_ascii=False,separators=(",",":")),
          flush=True)


if __name__=="__main__":
    main()

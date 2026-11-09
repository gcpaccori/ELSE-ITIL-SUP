"""ELSE-ITIL preview: real-service synthetic E2E and human feedback ledger.

This module does not change the existing web interface, active service, SQL, or
model. A demo is NOT evidence of an actual corporate repair.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.request import Request, urlopen

SCHEMA = "else.itil.accompaniment.preview.v1"
FEEDBACK_SCHEMA = "else.itil.accompaniment.feedback.v1"
DECISIONS = ("USEFUL", "PARTIAL", "INCORRECT", "ESCALATE")
VALID_STATUSES = ("DIAGNOSTIC_GUIDANCE", "ACTION_PLAN_REVIEWABLE",
                  "ACTION_PLAN_AUTHORIZATION_PENDING", "NEEDS_HUMAN_TRIAGE")
CASE_PATTERN = re.compile(r"PREVIEW-[0-9]{8}-[A-Z0-9_-]{3,40}\Z")
ROLE_PATTERN = re.compile(r"[A-Z][A-Z0-9_-]{2,39}\Z")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(obj) -> str:
    return sha256(canonical(obj)).hexdigest()


def require(flag: bool, message: str) -> None:
    if not flag:
        raise ValueError(message)


def load_scenarios(file: Path) -> list[dict]:
    parsed = json.loads(file.read_text(encoding="utf-8"))
    require(isinstance(parsed, dict) and parsed.get("schema") == SCHEMA,
            "SCENARIO_SCHEMA_INVALID")
    cases = parsed.get("scenarios")
    require(isinstance(cases, list) and len(cases) == 5, "FIVE_SCENARIOS_REQUIRED")
    names = set()
    for row in cases:
        require(isinstance(row, dict) and set(row) == {"scenario", "goal", "ticket"},
                "SCENARIO_FIELDS_INVALID")
        ticket = row["ticket"]
        require(isinstance(ticket, dict), "TICKET_INVALID")
        ref = ticket.get("case_ref")
        require(isinstance(ref, str) and CASE_PATTERN.fullmatch(ref) is not None
                and ref not in names, "SCENARIO_REF_INVALID")
        names.add(ref)
        require(ticket.get("input_scope") == "synthetic", "SYNTHETIC_ONLY")
        require(isinstance(row["goal"], str) and len(row["goal"]) >= 12,
                "GOAL_REQUIRED")
        require(isinstance(row["scenario"], str) and len(row["scenario"]) >= 5,
                "SCENARIO_NAME_REQUIRED")
        # Exact same intake schema as the active support service.
        from .support_desk import validate_ticket
        validate_ticket(ticket)
    return cases


class FeedbackLedger:
    """Persistent, append-only reviews separate from original help-desk DB."""

    def __init__(self, file: Path):
        file.parent.mkdir(parents=True, exist_ok=True)
        if not file.exists():
            fd = os.open(file, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
            os.close(fd)
        self.conn = sqlite3.connect(str(file), timeout=15)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS demo_runs (
            case_ref TEXT PRIMARY KEY,
            scenario TEXT NOT NULL,
            goal TEXT NOT NULL,
            ticket_sha256 TEXT NOT NULL,
            response_sha256 TEXT NOT NULL,
            response_status TEXT NOT NULL,
            model_selected TEXT NOT NULL,
            schema_accepted INTEGER NOT NULL,
            persisted_in_active_service INTEGER NOT NULL,
            submitted_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS human_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_ref TEXT NOT NULL REFERENCES demo_runs(case_ref),
            reviewer_role TEXT NOT NULL,
            decision TEXT NOT NULL,
            note TEXT NOT NULL,
            observed_result TEXT NOT NULL,
            created_at TEXT NOT NULL,
            previous_sha256 TEXT NOT NULL,
            event_sha256 TEXT NOT NULL,
            CHECK(decision IN ('USEFUL','PARTIAL','INCORRECT','ESCALATE')),
            CHECK(observed_result IN ('NOT_CHECKED','CHECKED_NOT_RESOLVED',
                                      'CHECKED_RESOLVED_BY_TECHNICIAN'))
        );
        CREATE INDEX IF NOT EXISTS ix_feedback_case ON human_feedback(case_ref,id);
        """)

    def close(self):
        self.conn.close()

    def register(self, *, scenario: dict, response: dict,
                 persisted: bool) -> dict:
        ticket = scenario["ticket"]
        ref = ticket["case_ref"]
        require(response.get("case_ref") == ref, "CASE_RESPONSE_MISMATCH")
        status = response.get("status")
        require(status in VALID_STATUSES, "RESPONSE_STATUS_UNKNOWN")
        require(response.get("certified_repair") is False
                and response.get("executed_changes") is False
                and response.get("real_corporate_sources_queried") is False,
                "FALSE_CORPORATE_ACTION_CLAIM")
        require(response.get("requires_human_verification") is True,
                "HUMAN_REVIEW_CLAIM_MISSING")
        if status == "NEEDS_HUMAN_TRIAGE":
            gate = False
            selected = "NONE"
        else:
            quality = response.get("quality")
            require(isinstance(quality, dict), "QUALITY_RECEIPT_MISSING")
            gate = (quality.get("accepted") is True
                    and not quality.get("schema_flags")
                    and not quality.get("safety_flags"))
            selected = response.get("model_selected")
            require(selected in ("primary", "secondary"),
                    "MODEL_SELECTION_INVALID")
            plan = response.get("proposal")
            require(isinstance(plan, dict) and plan.get("ejecutado") is False
                    and plan.get("confirmado") is False, "FALSE_MODEL_REPAIR")
            require(isinstance(plan.get("pasos"), list)
                    and 1 <= len(plan["pasos"]) <= 3,
                    "ACTION_STEP_COUNT_INVALID")
        row = (ref, scenario["scenario"], scenario["goal"],
               digest(ticket), digest(response), status, selected,
               int(gate), int(persisted), now_utc())
        prior = self.conn.execute(
            "SELECT ticket_sha256,response_sha256 FROM demo_runs WHERE case_ref=?",
            (ref,)).fetchone()
        if prior is not None:
            require(tuple(prior) == (row[3], row[4]),
                    "DEMO_CASE_IMMUTABILITY_VIOLATION")
            return {"case_ref":ref,"status":"EXISTING_VERIFIED_RUN"}
        with self.conn:
            self.conn.execute(
                "INSERT INTO demo_runs VALUES(?,?,?,?,?,?,?,?,?,?)", row)
        return {"case_ref":ref,"status":status,"selected_model":selected,
                "contract_pass":gate,"persisted":bool(persisted),
                "response_sha256":row[4]}

    def feedback(self, *, case_ref: str, reviewer_role: str,
                 decision: str, note: str, observed_result: str) -> dict:
        require(isinstance(reviewer_role, str) and
                ROLE_PATTERN.fullmatch(reviewer_role) is not None,
                "REVIEWER_ROLE_INVALID")
        require(decision in DECISIONS, "INVALID_DECISION")
        require(observed_result in (
            "NOT_CHECKED", "CHECKED_NOT_RESOLVED",
            "CHECKED_RESOLVED_BY_TECHNICIAN"), "OUTCOME_INVALID")
        require(isinstance(note, str) and 12 <= len(note.strip()) <= 1000,
                "FEEDBACK_NOTE_REQUIRED")
        with self.conn:
            run = self.conn.execute(
                "SELECT response_sha256 FROM demo_runs WHERE case_ref=?",
                (case_ref,)).fetchone()
            require(run is not None, "UNREGISTERED_CASE")
            prior = self.conn.execute(
                "SELECT event_sha256 FROM human_feedback "
                "WHERE case_ref=? ORDER BY id DESC LIMIT 1",
                (case_ref,)).fetchone()
            prev = prior[0] if prior else "GENESIS"
            event = {"schema":FEEDBACK_SCHEMA, "case_ref":case_ref,
                     "response_sha256":run[0], "reviewer_role":reviewer_role,
                     "decision":decision, "note":note.strip(),
                     "observed_result":observed_result,
                     "created_at":now_utc(), "previous_sha256":prev}
            event_sha = digest(event)
            self.conn.execute(
                "INSERT INTO human_feedback"
                "(case_ref,reviewer_role,decision,note,observed_result,"
                "created_at,previous_sha256,event_sha256)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (case_ref,reviewer_role,decision,note.strip(),observed_result,
                 event["created_at"],prev,event_sha))
        return {"case_ref":case_ref,"decision":decision,
                "event_sha256":event_sha, "recorded":True,
                "automatic_memory_promotion":False}

    def verify_feedback(self) -> dict:
        records = self.conn.execute("""
            SELECT f.case_ref,f.reviewer_role,f.decision,f.note,
                   f.observed_result,f.created_at,f.previous_sha256,
                   f.event_sha256,r.response_sha256
            FROM human_feedback AS f JOIN demo_runs AS r
              ON r.case_ref=f.case_ref
            ORDER BY f.id
        """).fetchall()
        chains = {}
        for row in records:
            ref,role,decision,note,outcome,created,prev,actual,res_sha = row
            expected_prev = chains.get(ref, "GENESIS")
            require(prev == expected_prev, "FEEDBACK_CHAIN_BROKEN")
            event = {"schema":FEEDBACK_SCHEMA,"case_ref":ref,
                     "response_sha256":res_sha,"reviewer_role":role,
                     "decision":decision,"note":note,
                     "observed_result":outcome,"created_at":created,
                     "previous_sha256":prev}
            require(hmac.compare_digest(digest(event),actual),
                    "FEEDBACK_EVENT_TAMPER")
            chains[ref] = actual
        return {"feedback_events_valid":len(records),
                "feedback_chains":len(chains)}

    def report(self) -> dict:
        rows = self.conn.execute(
            "SELECT case_ref,response_status,model_selected,schema_accepted,"
            "persisted_in_active_service FROM demo_runs ORDER BY case_ref"
        ).fetchall()
        feedbacks = self.conn.execute(
            "SELECT case_ref,decision,reviewer_role,observed_result "
            "FROM human_feedback ORDER BY id"
        ).fetchall()
        latest = {r[0]: {"decision":r[1],"reviewer_role":r[2],
                          "observed_result":r[3]} for r in feedbacks}
        counts = Counter(r[1] for r in rows)
        per_case = [{
            "case_ref":r[0], "status":r[1],
            "model_selected":r[2],
            "contract_pass":bool(r[3]),
            "active_receipt_persisted":bool(r[4]),
            "human_feedback":latest.get(r[0], {"decision":"PENDING"})
        } for r in rows]
        return {"schema":SCHEMA,"executed_cases":len(rows),
                "complete_five_case_campaign":len(rows)==5,
                "statuses":dict(counts),
                "model_selected":dict(Counter(r[2] for r in rows)),
                "contract_passed":sum(r[3] for r in rows),
                "active_service_receipt_persisted":sum(r[4] for r in rows),
                "human_reviewed_cases":len(latest),
                "feedback_pending":sum(r[0] not in latest for r in rows),
                "latest_human_decisions":dict(Counter(
                    r["decision"] for r in latest.values())),
                "case_results":per_case,
                "feedback_ledger":self.verify_feedback(),
                "functional_repairs_certified":0,
                "automatic_memory_promotions":0}


def audit_campaign(*, scenarios_file: Path, out_dir: Path,
                   active_db: Path) -> dict:
    """Independently revalidate five exact response files and live DB rows."""
    cases = load_scenarios(scenarios_file)
    db = out_dir/"feedback.sqlite"
    require(db.is_file(), "CAMPAIGN_LEDGER_MISSING")
    ledger = FeedbackLedger(db)
    try:
        rows = {r[0]:(r[1],r[2],r[3]) for r in ledger.conn.execute(
            "SELECT case_ref,ticket_sha256,response_sha256,"
            "persisted_in_active_service FROM demo_runs")}
        require(len(rows)==5, "CAMPAIGN_RECEIPT_COUNT_MISMATCH")
        verified=0
        for scenario in cases:
            ticket=scenario["ticket"]
            ref=ticket["case_ref"]
            require(ref in rows,"CASE_MISSING_FROM_LEDGER")
            expected_ticket,expected_response,persisted=rows[ref]
            require(digest(ticket)==expected_ticket,
                    "SCENARIO_CONTENT_DRIFT")
            receipt=out_dir/(ref+".response.json")
            require(receipt.is_file() and not receipt.is_symlink(),
                    "RESPONSE_RECEIPT_MISSING")
            result=json.loads(receipt.read_text(encoding="utf-8"))
            require(result.get("case_ref")==ref and
                    digest(result)==expected_response,
                    "RESPONSE_RECEIPT_TAMPERED")
            require(persisted==1 and verify_active_persistence(
                active_db,ticket,result),"ACTIVE_SERVICE_PERSISTENCE_DRIFT")
            require(result.get("certified_repair") is False and
                    result.get("executed_changes") is False and
                    result.get("real_corporate_sources_queried") is False,
                    "FALSE_REPAIR_OR_SOURCE_CLAIM")
            verified+=1
        verified_feedback=ledger.verify_feedback()
        return {"state":"PREVIEW_E2E_RECEIPTS_VERIFIED",
                "scenarios":len(cases),"receipts_rehashed":verified,
                "active_sqlite_rows_matched":verified,
                "human_feedback_verified":verified_feedback["feedback_events_valid"],
                "functional_repairs_certified":0,
                "automatic_memory_promotions":0}
    finally:
        ledger.close()


def verify_active_persistence(db: Path, ticket: dict, result: dict) -> bool:
    require(db.is_file(), "ACTIVE_SERVICE_DB_NOT_FOUND")
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=8) as conn:
        row = conn.execute(
            "SELECT result_json FROM attention WHERE case_ref=?",
            (ticket["case_ref"],)).fetchone()
        return bool(row and digest(json.loads(row[0])) == digest(result))


def send_to_existing_service(*, url: str, token_file: Path,
                             ticket: dict, timeout: int = 240) -> dict:
    require(url == "http://127.0.0.1:18883/v1/support",
            "ACTIVE_SERVICE_URL_MISMATCH")
    token = token_file.read_text(encoding="utf-8").strip()
    require(len(token)>=32, "TOKEN_NOT_AVAILABLE")
    req = Request(url, method="POST", data=canonical(ticket),
                  headers={"Authorization":"Bearer "+token,
                           "Content-Type":"application/json"})
    with urlopen(req,timeout=timeout) as res:
        require(res.status==200,"SUPPORT_HTTP_STATUS_NOT_200")
        body = res.read(250000)
    parsed = json.loads(body)
    require(isinstance(parsed,dict), "RESPONSE_NOT_JSON_OBJECT")
    return parsed


def run_campaign(*, scenarios_file: Path, out_dir: Path, token_file: Path,
                 active_db: Path, api_url: str, send=send_to_existing_service,
                 progress=None) -> dict:
    cases = load_scenarios(scenarios_file)
    out_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    ledger = FeedbackLedger(out_dir/"feedback.sqlite")
    try:
        for row in cases:
            ticket = row["ticket"]
            ref = ticket["case_ref"]
            receipt = out_dir/(ref+".response.json")
            if receipt.exists():
                response = json.loads(receipt.read_text(encoding="utf-8"))
            else:
                if progress:
                    progress("START "+ref)
                response = send(url=api_url, token_file=token_file, ticket=ticket)
            persisted = verify_active_persistence(active_db,ticket,response)
            result = ledger.register(scenario=row,response=response,
                                     persisted=persisted)
            if not receipt.exists():
                with receipt.open("x", encoding="utf-8") as f:
                    json.dump(response,f,ensure_ascii=False,indent=2)
            if progress:
                progress("DONE "+ref+" "+result["status"]+
                         " persisted="+str(bool(persisted)))
        summary = ledger.report()
        summary["source_manifest_sha256"] = sha256(
            scenarios_file.read_bytes()).hexdigest()
        summary_file = out_dir/"campaign-summary.json"
        with summary_file.open("w",encoding="utf-8") as f:
            json.dump(summary,f,ensure_ascii=False,indent=2)
        return summary
    finally:
        ledger.close()


def main(argv=None):
    p=argparse.ArgumentParser(description="ELSE-ITIL accompaniment pilot")
    sub=p.add_subparsers(dest="command",required=True)
    run=sub.add_parser("run")
    run.add_argument("--scenarios",required=True,type=Path)
    run.add_argument("--output",required=True,type=Path)
    run.add_argument("--token-file",required=True,type=Path)
    run.add_argument("--active-db",required=True,type=Path)
    run.add_argument("--api-url",default="http://127.0.0.1:18883/v1/support")
    feedback=sub.add_parser("feedback")
    feedback.add_argument("--db",required=True,type=Path)
    feedback.add_argument("--case",required=True)
    feedback.add_argument("--role",required=True)
    feedback.add_argument("--decision",required=True,choices=DECISIONS)
    feedback.add_argument("--note",required=True)
    feedback.add_argument("--observed-result",default="NOT_CHECKED",
                          choices=["NOT_CHECKED","CHECKED_NOT_RESOLVED",
                                   "CHECKED_RESOLVED_BY_TECHNICIAN"])
    report=sub.add_parser("report")
    report.add_argument("--db",required=True,type=Path)
    audit=sub.add_parser("audit")
    audit.add_argument("--scenarios",required=True,type=Path)
    audit.add_argument("--output",required=True,type=Path)
    audit.add_argument("--active-db",required=True,type=Path)
    a=p.parse_args(argv)
    if a.command=="run":
        result=run_campaign(scenarios_file=a.scenarios,out_dir=a.output,
                            token_file=a.token_file,active_db=a.active_db,
                            api_url=a.api_url,progress=lambda msg:print(msg,flush=True))
    elif a.command=="audit":
        result=audit_campaign(scenarios_file=a.scenarios,out_dir=a.output,
                              active_db=a.active_db)
    else:
        require(a.db.is_file(),"FEEDBACK_DB_NOT_FOUND")
        ledger=FeedbackLedger(a.db)
        try:
            result=(ledger.feedback(case_ref=a.case,reviewer_role=a.role,
                    decision=a.decision,note=a.note,
                    observed_result=a.observed_result)
                    if a.command=="feedback" else ledger.report())
        finally:
            ledger.close()
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()

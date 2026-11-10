"""Append-only supervised V1 Beta QA attention + technician-review ledger.

No fake human identities. Review requires a separate authorized reviewer
credential from a private roster; the general API bearer alone cannot
produce a human signoff. No status in this ledger certifies repairs.
"""
from __future__ import annotations

from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import hmac,json,os,re,sqlite3,uuid

HEX=re.compile(r"[a-f0-9]{64}\Z")
REVIEWERS=re.compile(r"[A-Za-z][A-Za-z0-9_.-]{2,60}\Z")
DECISIONS=frozenset({
    "USEFUL_FOR_TECHNICIAN",
    "NEEDS_MORE_EVIDENCE",
    "INCORRECT_OR_UNSAFE",
})


def demand(ok,code):
    if not ok:raise ValueError(code)


class BetaSupervisionLedger:
    def __init__(self,path:Path,reviewer_registry:Path|None=None):
        demand(path.is_absolute() and not path.is_symlink(),
               "LEDGER_PATH_NOT_ALLOWED")
        self.path=path
        self.registry=reviewer_registry
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            os.close(fd)
        self.db=sqlite3.connect(path,timeout=15)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=15000")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS investigations(
            case_sha256 TEXT PRIMARY KEY,
            result_sha256 TEXT NOT NULL,
            evidence_itil_sha256 TEXT NOT NULL,
            evidence_sap_sha256 TEXT NOT NULL,
            result_json TEXT NOT NULL,
            generated_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS review_events(
            event_id TEXT PRIMARY KEY,
            case_sha256 TEXT NOT NULL,
            reviewer_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            note_sha256 TEXT NOT NULL,
            created_utc TEXT NOT NULL,
            FOREIGN KEY(case_sha256) REFERENCES investigations(case_sha256),
            UNIQUE(case_sha256,reviewer_id)
        );
        """)
        self.db.commit()

    def __enter__(self):return self

    def __exit__(self,*_):self.db.close()

    def record(self,result:dict)->dict:
        demand(type(result) is dict and
               result.get("schema")==
               "else.itil.v1beta.dual-hand.supervised-investigation.v1",
               "NOT_DUAL_NATIVE_BETA_RESULT")
        sha=result.get("case_sha256")
        demand(type(sha) is str and HEX.fullmatch(sha),
               "CASE_SHA_NOT_VALID")
        receipts=result.get("source_receipts",{})
        demand(set(receipts)=={"itil","sap_ot"} and
               all(type(x) is str and HEX.fullmatch(x)
                   for x in receipts.values()) and
               result.get("native_itil_verified") is True and
               result.get("native_sap_ot_verified") is True and
               result.get("repair_certified") is False and
               result.get("root_cause_certified") is False and
               result.get("business_join_certified") is False and
               result.get("human_review_required") is True,
               "UNVERIFIED_RESULT_CANNOT_ENTER_LEDGER")
        b=json.dumps(result,sort_keys=True,ensure_ascii=False,
                     separators=(",",":"))
        digest=sha256(b.encode()).hexdigest()
        before=self.db.execute(
            "SELECT result_sha256,result_json FROM investigations "
            "WHERE case_sha256=?",(sha,)).fetchone()
        if before:
            demand(before[0]==digest,
                   "CASE_RESULT_CHANGES_AFTER_FIRST_RECORD")
            return json.loads(before[1])
        self.db.execute(
            "INSERT INTO investigations VALUES (?,?,?,?,?,?)",
            (sha,digest,receipts["itil"],receipts["sap_ot"],b,
             datetime.now(timezone.utc).isoformat()))
        self.db.commit()
        return result

    def get(self,sha:str):
        demand(type(sha) is str and HEX.fullmatch(sha),
               "CASE_SHA_INVALID")
        r=self.db.execute(
            "SELECT result_json FROM investigations WHERE case_sha256=?",
            (sha,)).fetchone()
        if not r:return None
        return json.loads(r[0])

    def auth_reviewer(self,reviewer_id:str,secret:str):
        demand(type(reviewer_id) is str and
               REVIEWERS.fullmatch(reviewer_id),"REVIEWER_ID_INVALID")
        demand(type(secret) is str and len(secret)>=32,
               "REVIEWER_SECRET_REQUIRED")
        demand(self.registry is not None and self.registry.is_file() and
               not self.registry.is_symlink(),
               "REVIEWER_ROSTER_NOT_CONFIGURED")
        demand(self.registry.stat().st_mode & 0o077==0,
               "REVIEWER_ROSTER_PERMISSIONS")
        roster=json.loads(self.registry.read_text(encoding="utf-8"))
        demand(type(roster) is dict and
               type(roster.get(reviewer_id)) is str and
               HEX.fullmatch(roster[reviewer_id]) is not None and
               hmac.compare_digest(roster[reviewer_id],
                                   sha256(secret.encode()).hexdigest()),
               "REVIEWER_CREDENTIAL_NOT_AUTHORIZED")

    def review(self,*,case_sha256:str,reviewer_id:str,reviewer_secret:str,
               decision:str,note:str):
        self.auth_reviewer(reviewer_id,reviewer_secret)
        demand(decision in DECISIONS,"REVIEW_DECISION_NOT_ALLOWED")
        demand(type(note) is str and 20<=len(note.strip())<=2000,
               "TECHNICAL_JUSTIFICATION_REQUIRED")
        case=self.get(case_sha256)
        demand(case is not None,"UNREGISTERED_CASE")
        demand(case["status"]=="PENDING_TECHNICIAN_REVIEW",
               "NO_REVIEWABLE_PLAN")
        old=self.db.execute(
            "SELECT event_id FROM review_events "
            "WHERE case_sha256=? AND reviewer_id=?",
            (case_sha256,reviewer_id)).fetchone()
        demand(old is None,"REVIEWER_ALREADY_RECORDED_DECISION")
        eid=uuid.uuid4().hex
        self.db.execute(
            "INSERT INTO review_events VALUES (?,?,?,?,?,?)",
            (eid,case_sha256,reviewer_id,decision,
             sha256(note.encode()).hexdigest(),
             datetime.now(timezone.utc).isoformat()))
        self.db.commit()
        return {
            "schema":"else.itil.beta.human-review-receipt.v1",
            "event_id":eid,"case_sha_prefix":case_sha256[:16],
            "reviewer_id":reviewer_id,"decision":decision,
            "technical_note_sha256":sha256(note.encode()).hexdigest(),
            "human_review_recorded":True,
            "cause_confirmed":False,"repair_certified":False,
            "business_entity_join_certified":False,
        }

    def status(self,sha):
        case=self.get(sha)
        if case is None:return None
        rows=self.db.execute(
            "SELECT reviewer_id,decision,created_utc FROM review_events "
            "WHERE case_sha256=? ORDER BY created_utc",(sha,)).fetchall()
        return {
            "schema":"else.itil.beta.technical-supervision-state.v1",
            "case_sha_prefix":sha[:16],
            "model_status":case["status"],
            "reviews_count":len(rows),
            "review_decisions":[{"reviewer_id":x[0],"decision":x[1],
                                 "created_utc":x[2]} for x in rows],
            "repair_certified":False,"root_cause_certified":False,
            "human_review_required":True,
        }

    def aggregate(self):
        count=self.db.execute(
            "SELECT count(*) FROM investigations").fetchone()[0]
        reviews=self.db.execute(
            "SELECT decision,count(*) FROM review_events "
            "GROUP BY decision").fetchall()
        return {
            "schema":"else.itil.beta.qa-review-summary.v1",
            "investigations":count,
            "recorded_human_review_events":sum(x[1] for x in reviews),
            "review_decisions":{x[0]:x[1] for x in reviews},
            "certified_repairs":0,"causal_accuracy_measured":False}

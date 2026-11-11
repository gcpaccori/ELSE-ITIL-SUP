"""Private, isolated V2 functional QA API; no arbitrary SQL or external actions.

- Authenticated requests only with SHA of a frozen August 2026 ticket.
- One immutable redacted request per SHA; source manifest SHA binding.
- Synchronous bounded Qwen9B invocation, durable idempotent SQLite.
- Separate listener from production and beta historical services.
- A JSON/functional PASS means useful DRAFT, not a repaired incident.
"""
from __future__ import annotations
from hashlib import sha256
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from threading import BoundedSemaphore
from datetime import datetime,timezone
from urllib.parse import urlsplit
import argparse,hmac,json,os,re,sqlite3,time

from .functional_investigator_v2 import run_case,canon
from .functional_domain_v2 import route

SCHEMA="else.itil.functional-v2-private-http.v1"
SHA=re.compile(r'[a-f0-9]{64}\Z')
MAX_MODEL_CONCURRENT=2

def require(ok,message):
    if not ok:raise ValueError(message)

class Store:
    def __init__(self,path:Path):
        self.path=path
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self._init()

    def _connect(self):
        con=sqlite3.connect(str(self.path),timeout=5,isolation_level=None)
        con.execute("PRAGMA busy_timeout=5000")
        return con

    def _init(self):
        con=self._connect()
        try:
            con.execute("""CREATE TABLE IF NOT EXISTS runs (
                case_sha256 TEXT PRIMARY KEY,
                input_sha256 TEXT NOT NULL,
                state TEXT NOT NULL,
                result_json TEXT,
                created_utc TEXT NOT NULL,
                modified_utc TEXT NOT NULL)""")
        finally:con.close()
        os.chmod(self.path,0o600)

    def get(self,sha):
        with self._connect() as con:
            row=con.execute("SELECT input_sha256,state,result_json "
                            "FROM runs WHERE case_sha256=?",(sha,)).fetchone()
        if not row:return None
        return {"input_sha256":row[0],"state":row[1],
                "result":json.loads(row[2]) if row[2] else None}

    def claim(self,sha,input_sha):
        now=datetime.now(timezone.utc).isoformat()
        con=self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            old=con.execute("SELECT input_sha256,state FROM runs "
                            "WHERE case_sha256=?",(sha,)).fetchone()
            if old:
                require(old[0]==input_sha,"CASE_SHA_SNAPSHOT_CHANGED")
                con.execute("COMMIT")
                return False
            con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)",
                        (sha,input_sha,"RUNNING",None,now,now))
            con.execute("COMMIT")
            return True
        except BaseException:
            if con.in_transaction:con.execute("ROLLBACK")
            raise
        finally:con.close()

    def finish(self,sha,input_sha,result):
        con=self._connect()
        try:
            cur=con.execute("UPDATE runs SET state=?,result_json=?,"
                  "modified_utc=? WHERE case_sha256=? AND input_sha256=? "
                  "AND state='RUNNING'",
                  ("FINISHED",canon(result).decode(),
                   datetime.now(timezone.utc).isoformat(),sha,input_sha))
            require(cur.rowcount==1,"RESULT_NOT_BOUND_TO_ACTIVE_CLAIM")
        finally:con.close()

def frozen_cohort(source:Path,manifest:Path):
    m=json.loads(manifest.read_bytes())
    raw=source.read_bytes()
    require(m["cases"]==1819 and m["blind_sha256"]==
            sha256(raw).hexdigest() and m["gold_shown_to_model"] is False,
            "QA_AUG_SOURCE_SEAL_DRIFT")
    cases={}
    for line in raw.splitlines():
        if not line.strip():continue
        item=json.loads(line)
        sha=item["ticket_sha256"]
        require(type(sha) is str and SHA.fullmatch(sha) and sha not in cases,
                "QA_DUPLICATE_TICKET")
        require(item["historical_resolution"]=="WITHHELD"
                and item["model_tools_enabled"] is False
                and item["month"]=="2026-08",
                "QA_SOURCE_IS_NOT_BLIND")
        cases[sha]={
            "ticket_sha256":sha,
            "incident_text_redacted":item["incident_text_redacted"],
        }
    require(len(cases)==1819,"QA_COHORT_NOT_1819")
    return cases

def make_handler(*,token:str,cohort:dict,store:Store,limit:BoundedSemaphore):
    class Handler(BaseHTTPRequestHandler):
        server_version="ELSE-Functional-V2-QA"
        def log_message(self,format,*args):
            # Never log bearer tokens, case IDs or output text.
            return
        def reply(self,status,data):
            raw=canon(data)
            self.send_response(status)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Length",str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        def authorized(self):
            header=self.headers.get("Authorization","")
            value="Bearer "+token
            return hmac.compare_digest(header,value)
        def do_GET(self):
            if self.path=="/health":
                return self.reply(200,{"schema":SCHEMA,"state":"READY",
                    "source":"AUG2026_BLIND_QA_1819",
                    "host_scope":"LOOPBACK_ONLY",
                    "domain_hands_verified":0,
                    "repair_enabled":False})
            if not self.authorized():
                return self.reply(401,{"error":"AUTH_REQUIRED"})
            match=re.fullmatch(r"/v1/functional/status/([a-f0-9]{64})",
                               self.path)
            if not match:
                return self.reply(404,{"error":"NOT_FOUND"})
            sha=match.group(1)
            if sha not in cohort:return self.reply(404,{"error":"CASE_NOT_ALLOWED"})
            existing=store.get(sha)
            if existing is None:
                return self.reply(404,{"error":"NOT_REQUESTED"})
            return self.reply(200,{
                "schema":SCHEMA,"case_sha256":sha,
                "state":existing["state"],
                "result":existing["result"],
                "repair_certified":False,
                "live_domain_evidence_verified":False,
            })
        def do_POST(self):
            if self.path!="/v1/functional/investigate":
                return self.reply(404,{"error":"NOT_FOUND"})
            if not self.authorized():
                return self.reply(401,{"error":"AUTH_REQUIRED"})
            length=self.headers.get("Content-Length")
            if not length or not length.isdigit() or int(length)>256:
                return self.reply(413,{"error":"INVALID_LENGTH"})
            try:
                body=json.loads(self.rfile.read(int(length)))
                if type(body) is not dict or set(body)!={"case_sha256"}:
                    return self.reply(422,{"error":"EXACT_CASE_SHA_REQUIRED"})
                sha=body["case_sha256"]
                if type(sha) is not str or SHA.fullmatch(sha) is None or sha not in cohort:
                    return self.reply(422,{"error":"CASE_NOT_IN_BLIND_QA_ALLOWLIST"})
                req=cohort[sha]
                req_hash=sha256(canon(req)).hexdigest()
                if not limit.acquire(blocking=False):
                    return self.reply(429,{"error":"QA_MODEL_BUDGET_BUSY"})
                try:
                    if not store.claim(sha,req_hash):
                        existing=store.get(sha)
                        return self.reply(200,{
                            "schema":SCHEMA,
                            "case_sha256":sha,
                            "state":existing["state"],
                            "result":existing["result"],
                            "idempotent":True,
                            "repair_certified":False,
                        })
                    try:
                        result=run_case(req)
                    except Exception:
                        # No fabricated plan; leave explicitly failed state.
                        result={
                           "schema":SCHEMA,"case_sha256":sha,
                           "status":"QA_MODEL_FAILURE",
                           "repair_certified":False,
                           "live_domain_evidence_verified":False,
                        }
                    store.finish(sha,req_hash,result)
                    return self.reply(200,{
                        "schema":SCHEMA,"case_sha256":sha,
                        "state":"FINISHED",
                        "result":result,
                        "idempotent":False,
                        "repair_certified":False,
                    })
                finally:limit.release()
            except (ValueError,KeyError,TypeError):
                return self.reply(422,{"error":"INVALID_QA_REQUEST"})
    return Handler

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=18889)
    parser.add_argument("--token-file",type=Path,required=True)
    parser.add_argument("--cohort",type=Path,required=True)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--db",type=Path,required=True)
    a=parser.parse_args()
    if a.host!="127.0.0.1":parser.error("QA_LOOPBACK_ONLY")
    if a.token_file.stat().st_mode&0o077:parser.error("UNPROTECTED_BEARER_FILE")
    token=a.token_file.read_text().strip()
    if len(token)<20:parser.error("WEAK_BEARER_TOKEN")
    cohort=frozen_cohort(a.cohort,a.manifest)
    store=Store(a.db)
    http=ThreadingHTTPServer((a.host,a.port),make_handler(
        token=token,cohort=cohort,store=store,
        limit=BoundedSemaphore(MAX_MODEL_CONCURRENT)))
    print("ELSE_FUNCTIONAL_V2_QA_READY",flush=True)
    http.serve_forever(poll_interval=.5)

if __name__=="__main__":main()

"""QA-only real SAP/OT verified evidence HTTP: exactly five August cases.

The service replays native CORE O5/O13/O15 before any evidence display
or Qwen model call. Original Functional V2 QA remains on port 18889.
No client-supplied OT, SQL, server, path, or business identifier.
"""
from __future__ import annotations
from hashlib import sha256
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore
import argparse,hmac,json,re

from .aug2026_sap_ot_verified import data,eligible,verify_case
from .operational_ot_verified import verify_case_operational
from .functional_live_sap_v2 import diagnose_case
from .functional_api_v2 import Store
from .functional_investigator_v2 import canon

SCHEMA="else.itil.aug2026.native-dual-domain-live-http.v1"
HEX=re.compile(r"[a-f0-9]{64}\Z")

def make_handler(*,token,allowed,store,limit):
    class Handler(BaseHTTPRequestHandler):
        server_version="ELSE-QA-Aug2026-Domain-Live"
        def log_message(self,format,*args):
            # No case, credentials, ticket or receipt data in HTTP logs.
            return
        def reply(self,status,payload):
            raw=canon(payload)
            self.send_response(status)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Length",str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        def authorized(self):
            return hmac.compare_digest(
                self.headers.get("Authorization",""),"Bearer "+token)
        def do_GET(self):
            if self.path=="/health":
                return self.reply(200,{
                    "schema":SCHEMA,
                    "state":"READY",
                    "listener":"LOOPBACK_ONLY",
                    "authorized_august_ot_cases":len(allowed),
                    "sql_enabled":False,
                    "observed_source":"ELSE70/dbDistribucion_D",
                    "verified_tables":["dbo.taOrdenTrabajo",
                        "dbo.taOrdenTrabajoSAP",
                        "dbo.taOrdenTrabajoSAPEnvioRespuesta"],
                    "native_read_hands_verified":2,
                    "live_windows_nuget_sql_executed_prior":True,
                    "repair_enabled":False,
                    "official_itil_ot_join_verified":False,
                })
            if not self.authorized():
                return self.reply(401,{"error":"AUTH_REQUIRED"})
            for label,pattern in (
                ("evidence",r"/v1/domain/evidence/([a-f0-9]{64})"),
                ("status",r"/v1/domain/status/([a-f0-9]{64})")
            ):
                match=re.fullmatch(pattern,self.path)
                if not match:continue
                sha=match.group(1)
                if sha not in allowed:
                    return self.reply(404,{"error":"CASE_NOT_ELIGIBLE"})
                try:
                    # Provenance for the reader must be rechecked every
                    # time, including on a cached job status call.
                    source={"sap_ot":verify_case(sha),
                            "operational_ot":verify_case_operational(sha),
                            "business_join_certified":False,
                            "repair_certified":False}
                    if label=="evidence":
                        return self.reply(200,source)
                    old=store.get(sha)
                    return self.reply(200,{
                        "schema":SCHEMA,
                        "case_sha256":sha,
                        "state":"NOT_REQUESTED" if old is None else old["state"],
                        "result":None if old is None else old["result"],
                        "native_o5_o13_o15_verified":
                            (source["sap_ot"]["o5_o13_o15_verified"] and
                             source["operational_ot"]["native_o5_o13_o15_verified"]),
                        "repair_certified":False,
                    })
                except Exception:
                    return self.reply(503,{"error":"NATIVE_QA_RECEIPT_INVALID"})
            return self.reply(404,{"error":"NOT_FOUND"})
        def do_POST(self):
            if self.path!="/v1/domain/investigate":
                return self.reply(404,{"error":"NOT_FOUND"})
            if not self.authorized():
                return self.reply(401,{"error":"AUTH_REQUIRED"})
            length=self.headers.get("Content-Length","")
            if not length.isdigit() or int(length)>200 or int(length)<2:
                return self.reply(413,{"error":"EXACT_REQUEST_REQUIRED"})
            try:
                body=json.loads(self.rfile.read(int(length)))
            except Exception:
                return self.reply(422,{"error":"INVALID_JSON"})
            if type(body) is not dict or set(body)!={"case_sha256"}:
                return self.reply(422,{"error":"ONLY_CASE_SHA256_ALLOWED"})
            sha=body["case_sha256"]
            if type(sha) is not str or HEX.fullmatch(sha) is None or sha not in allowed:
                return self.reply(422,{"error":"CASE_NOT_IN_FIVE_QA"})
            if not limit.acquire(blocking=False):
                return self.reply(429,{"error":"MODEL_BUDGET_BUSY"})
            try:
                try:
                    proof={"sap_ot":verify_case(sha),
                           "operational_ot":verify_case_operational(sha)}
                    input_sha=sha256(canon(proof)).hexdigest()
                    if not store.claim(sha,input_sha):
                        old=store.get(sha)
                        return self.reply(200,{
                            "schema":SCHEMA,"case_sha256":sha,
                            "state":old["state"],"result":old["result"],
                            "idempotent":True,"repair_certified":False})
                    try:
                        result=diagnose_case(sha)
                    except Exception:
                        result={"schema":SCHEMA,
                                "case_sha256":sha,"status":"NATIVE_OR_MODEL_FAILURE",
                                "repair_certified":False}
                    store.finish(sha,input_sha,result)
                    return self.reply(200,{
                        "schema":SCHEMA,"case_sha256":sha,
                        "state":"FINISHED","result":result,
                        "idempotent":False,"repair_certified":False})
                except ValueError:
                    return self.reply(503,{"error":"SOURCE_QA_PROOF_INVALID"})
            finally:
                limit.release()
    return Handler

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=18890)
    parser.add_argument("--token-file",type=Path,required=True)
    parser.add_argument("--db",type=Path,required=True)
    args=parser.parse_args()
    if args.token_file.stat().st_mode&0o077:
        parser.error("QA_BEARER_PERMISSIONS_INVALID")
    token=args.token_file.read_text().strip()
    if len(token)<20:parser.error("INVALID_BEARER_TOKEN")
    cohort,_=data()
    allowed=set(eligible(cohort))
    if len(allowed)!=5:parser.error("AUG_OT_ALLOWED_SET_DRIFT")
    for sha in sorted(allowed):
        verify_case(sha)
        verify_case_operational(sha)
    store=Store(args.db)
    server=ThreadingHTTPServer(("127.0.0.1",args.port),
        make_handler(token=token,allowed=allowed,store=store,
                     limit=BoundedSemaphore(2)))
    print("ELSE_AUG_DOMAIN_REAL_SAP_O5_HTTP_READY",flush=True)
    server.serve_forever(poll_interval=.5)

if __name__=="__main__":main()

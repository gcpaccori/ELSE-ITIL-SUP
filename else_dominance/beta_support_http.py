"""Private loopback V1 Beta QA API: two native Hands + supervised ledger.

Never exposes raw historical answers or executes SQL/repairs. Only the
original February QA cohort can be requested, and only cases with a
uniquely reported OT and pinned SAP/OT receipt are dual-hand eligible.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import RLock
import hmac,json,re

from .agent import OpenAICompatibleModel
from .beta_vertical_slice import BetaEvidenceBundle,BetaInvestigator
from .beta_supervision import BetaSupervisionLedger

HEX=re.compile(r"[a-f0-9]{64}\Z")


def make_handler(*,token,bundle,model,ledger_path,reviewer_registry=None):
    if type(token) is not str or len(token)<32:
        raise ValueError("API_BEARER_NOT_CONFIGURED")
    lock=RLock()
    class Handler(BaseHTTPRequestHandler):
        server_version="ELSE-ITIL-BETA-QA/0.1"
        sys_version=""
        def log_message(self,*_):
            # Never print customer ticket, bearer or reviewer credential.
            pass

        def reply(self,status,payload):
            raw=json.dumps(payload,ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Length",str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def authorized(self):
            return hmac.compare_digest(
                self.headers.get("Authorization",""),
                "Bearer "+token)

        def strict_request(self,limit):
            size=int(self.headers.get("Content-Length","-1"))
            if not 0<size<=limit:
                raise ValueError("INPUT_SIZE_INVALID")
            pairs=self.rfile.read(size)
            def unique(seq):
                d={}
                for k,v in seq:
                    if k in d:raise ValueError("DUPLICATE_JSON_KEY")
                    d[k]=v
                return d
            value=json.loads(pairs,object_pairs_hook=unique,
                             parse_constant=lambda _: (_ for _ in ()).throw(
                                 ValueError("NONFINITE_JSON")))
            if type(value) is not dict:raise ValueError("OBJECT_REQUIRED")
            return value

        def do_GET(self):
            if self.path=="/health":
                return self.reply(200,{
                    "service":"ELSE-ITIL-SUP-V1-BETA-QA",
                    "state":"READY",
                    "listener":"LOOPBACK_ONLY",
                    "cohort":"FEB2026_FIXED_100",
                    "ot_receipts":len(bundle.sap_recs),
                    "itil_source":"QA_HISTORICAL",
                    "sap_source":"PINNED_QA_SNAPSHOT",
                    "official_business_join_certified":False,
                    "reviewer_roster_configured":(
                         reviewer_registry is not None and
                         reviewer_registry.is_file()),
                    "repairs_enabled":False,
                })
            if not self.authorized():
                return self.reply(401,{"error":"AUTH_REQUIRED"})
            if self.path=="/v1/beta/summary":
                with lock,BetaSupervisionLedger(
                        ledger_path,reviewer_registry) as ledger:
                    return self.reply(200,ledger.aggregate())
            match=re.fullmatch(r"/v1/beta/(result|status)/([a-f0-9]{64})",
                               self.path)
            if match:
                action,sha=match.groups()
                try:
                    evidence=bundle.verify(sha)
                    with lock,BetaSupervisionLedger(
                            ledger_path,reviewer_registry) as ledger:
                        if action=="result":
                            result=ledger.get(sha)
                            if result and evidence.get("status")=="DUAL_NATIVE_EVIDENCE_VERIFIED" and (
                                result["source_receipts"]=={
                                "itil":evidence["itil_receipt_sha256"],
                                "sap_ot":evidence["sap_receipt_sha256"]}):
                                return self.reply(200,result)
                            return self.reply(404,{"error":"VERIFIED_RESULT_NOT_RECORDED"})
                        status=ledger.status(sha)
                    return self.reply(200,status or {
                        "state":"NO_REVIEW_RECORDED",
                        "case_sha_prefix":sha[:16],
                        "repair_certified":False})
                except ValueError as e:
                    return self.reply(422,{"error":str(e)[:75]})
                except Exception:
                    return self.reply(503,{"error":"BETA_EVIDENCE_UNAVAILABLE"})
            return self.reply(404,{"error":"NOT_FOUND"})

        def do_POST(self):
            if not self.authorized():
                return self.reply(401,{"error":"AUTH_REQUIRED"})
            if self.path=="/v1/beta/investigate":
                try:
                    req=self.strict_request(350)
                    if set(req)!={"case_sha256"} or not (
                        type(req["case_sha256"]) is str and
                        HEX.fullmatch(req["case_sha256"])):
                        return self.reply(422,{"error":"CASE_SHA_REQUIRED"})
                    sha=req["case_sha256"]
                    with lock:
                        observed=bundle.verify(sha)
                        if observed["status"]!="DUAL_NATIVE_EVIDENCE_VERIFIED":
                            return self.reply(422,{
                                "status":"REQUIRES_OT_CORPORATE_EVIDENCE",
                                "case_sha_prefix":sha[:16],
                                "repair_certified":False})
                        with BetaSupervisionLedger(
                            ledger_path,reviewer_registry) as ledger:
                            previous=ledger.get(sha)
                            if previous:
                                if previous["source_receipts"]!={
                                    "itil":observed["itil_receipt_sha256"],
                                    "sap_ot":observed["sap_receipt_sha256"]}:
                                    raise ValueError("STALE_OWNER_EVIDENCE_RECORD")
                                return self.reply(200,previous)
                        result=BetaInvestigator(bundle,model).investigate(sha)
                        with BetaSupervisionLedger(
                            ledger_path,reviewer_registry) as ledger:
                            saved=ledger.record(result)
                    return self.reply(200,saved)
                except ValueError as e:
                    return self.reply(422,{"error":str(e)[:80]})
                except Exception:
                    return self.reply(503,{"error":"BETA_INVESTIGATION_UNAVAILABLE"})
            if self.path=="/v1/beta/review":
                try:
                    req=self.strict_request(4500)
                    if set(req)!={
                        "case_sha256","reviewer_id","reviewer_secret",
                        "decision","note"}:
                        return self.reply(422,{"error":"REVIEW_FIELDS_INVALID"})
                    with lock,BetaSupervisionLedger(
                        ledger_path,reviewer_registry) as ledger:
                        result=ledger.review(**req)
                    return self.reply(201,result)
                except ValueError as e:
                    return self.reply(422,{"error":str(e)[:80]})
                except Exception:
                    return self.reply(503,{"error":"BETA_REVIEW_UNAVAILABLE"})
            return self.reply(404,{"error":"NOT_FOUND"})
    return Handler


def main():
    p=argparse.ArgumentParser(description="Private supervised QA beta vertical slice")
    p.add_argument("--host",default="127.0.0.1")
    p.add_argument("--port",type=int,default=18886)
    p.add_argument("--token-file",required=True,type=Path)
    p.add_argument("--ledger",required=True,type=Path)
    p.add_argument("--qa-source",required=True,type=Path)
    p.add_argument("--private-root",required=True,type=Path)
    p.add_argument("--reviewer-registry",type=Path,default=None)
    p.add_argument("--model-url",default="http://127.0.0.1:18782/v1")
    p.add_argument("--model",default="else-itil-riv-qwen9b-gpu6")
    args=p.parse_args()
    if args.host!="127.0.0.1":
        p.error("LOOPBACK_REQUIRED")
    if args.token_file.stat().st_mode & 0o077:
        p.error("API_TOKEN_TOO_PUBLIC")
    token=args.token_file.read_text().strip()
    bundle=BetaEvidenceBundle(
        base=Path(__file__).resolve().parents[1],
        qa=args.qa_source,core_source=args.private_root)
    model=OpenAICompatibleModel(args.model_url,args.model,timeout=155)
    server=ThreadingHTTPServer(
        (args.host,args.port),
        make_handler(token=token,bundle=bundle,model=model,
                     ledger_path=args.ledger,
                     reviewer_registry=args.reviewer_registry))
    print("ELSE_ITIL_BETA_QA_LISTENER_READY "+str(args.port),flush=True)
    server.serve_forever(poll_interval=.5)

if __name__=="__main__":
    main()

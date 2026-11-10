"""Fresh Windows-attested SAP/OT beta API, isolated from historical QA service.

Uses the exact frozen 100-case QA owner allowlist and the original ITIL O5
receipt. Only SAP/OT evidence newly read on ELSE62 with HMAC provenance
and native O5/O13/O15 may be considered for a new model investigation.
No official ITIL↔OT entity relationship or responsible role is implied.
"""
from __future__ import annotations

from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from datetime import datetime,timezone,timedelta
import argparse,hmac,json,re

from .agent import OpenAICompatibleModel
from .beta_vertical_slice import BetaEvidenceBundle
from .beta_support_http import make_handler
from .beta_fresh_ot import (
    queue_job,validate_job,canonical,SOURCE_SHA)
from .beta_fresh_ingest import DELIVERY,ROOT,utc
from .qa_feb100_cluster import parse_strict

HEX=re.compile(r"[0-9a-f]{64}\Z")
JOBID=re.compile(r"[0-9a-f]{32}\Z")

def demand(ok,code):
    if not ok:raise ValueError(code)

class FreshBetaEvidenceBundle(BetaEvidenceBundle):
    def __init__(self,*,base:Path,qa:Path,core_source:Path,
                 fresh_root:Path=ROOT):
        super().__init__(base=base,qa=qa,core_source=core_source)
        self.archive_recs=dict(self.sap_recs)
        self.sap_recs={}
        self.fresh_root=fresh_root
        self.source_file=base/"qa/Feb100SapOtRead.cs"
        self.key_path=fresh_root/"worker_hmac.private"
        self._refresh()

    def _refresh(self):
        key=self.key_path.read_bytes()
        demand(len(key)==32 and self.key_path.stat().st_mode&0o077==0,
               "WORKER_HMAC_KEY_INVALID")
        found={}
        for proof_path in sorted(
            (self.fresh_root/"verified").glob(
                "*/verified_receipt.private.json")):
            folder=proof_path.parent
            job_id=folder.name
            demand(JOBID.fullmatch(job_id) is not None,
                   "FRESH_FOLDER_ID_NOT_VALID")
            job_path=self.fresh_root/"requests"/(job_id+".private.json")
            delivery_path=self.fresh_root/"outbox"/(job_id+".private.json")
            for file in (job_path,delivery_path,proof_path,
                         folder/"receipt.private.json"):
                demand(file.is_file() and not file.is_symlink(),
                       "FRESH_BUNDLE_EXPECTED_FILE_MISSING")
            raw_job=job_path.read_bytes()
            job=parse_strict(raw_job)
            validate_job(job,self.roster,self.sap_bytes)
            envelope=parse_strict(delivery_path.read_bytes())
            proof=parse_strict(proof_path.read_bytes())
            receipt_file=folder/"receipt.private.json"
            raw_receipt=receipt_file.read_bytes()
            demand(envelope.get("schema")==DELIVERY and
                   envelope.get("job_id")==job_id and
                   envelope.get("case_sha256")==job["case_sha256"] and
                   envelope.get("source_sha256")==SOURCE_SHA and
                   envelope.get("job_sha256")==sha256(raw_job).hexdigest() and
                   envelope.get("receipt_sha256")==sha256(raw_receipt).hexdigest() and
                   canonical(envelope.get("receipt"))==raw_receipt and
                   envelope.get("sql_executed_on_windows") is True and
                   envelope.get("read_only") is True and
                   envelope.get("repair_certified") is False and
                   envelope.get("business_join_certified") is False,
                   "FRESH_OUTBOX_NOT_EXACTLY_SIGNED")
            message=(DELIVERY+":"+job_id+":"+
                     envelope["job_sha256"]+":"+
                     envelope["receipt_sha256"]).encode()
            demand(type(envelope.get("hmac_sha256")) is str and
                   hmac.compare_digest(envelope["hmac_sha256"],
                       hmac.new(key,message,"sha256").hexdigest()),
                   "FRESH_SIGNED_PROVENANCE_INVALID")
            source=parse_strict(raw_receipt)
            demand(source["case_sha256"]==job["case_sha256"] and
                   source["reported_ot_sha256"]==job["reported_ot_sha256"] and
                   source["reader_source_sha256"]==SOURCE_SHA,
                   "FRESH_CASE_OT_SOURCE_INVALID")
            stamp=utc(source["observation"]["read_utc"])
            demand(utc(job["requested_utc"])-timedelta(seconds=45)<=stamp<=
                   utc(envelope["completed_utc"])+timedelta(seconds=45),
                   "WINDOWS_READ_TIME_NOT_AFTER_REQUEST")
            demand(proof.get("schema")==
                   "else.itil.beta.fresh-ot-o5-hmac-verified.v1" and
                   proof.get("job_id")==job_id and
                   proof.get("case_sha256")==job["case_sha256"] and
                   proof.get("sap_receipt_sha256")==envelope["receipt_sha256"] and
                   proof.get("job_sha256")==envelope["job_sha256"] and
                   proof.get("windows_delivery_sha256")==
                   sha256(delivery_path.read_bytes()).hexdigest() and
                   proof.get("o5_o13_o15_verified") is True and
                   proof.get("hmac_attested") is True and
                   proof.get("official_itil_ot_join_verified") is False and
                   proof.get("repairs_certified") is False,
                   "FRESH_NATIVE_PROOF_INVALID")
            sha=job["case_sha256"]
            demand(sha not in found,"MULTIPLE_FRESH_READS_FOR_SAME_CASE_PENDING_POLICY")
            found[sha]=receipt_file
        self.sap_recs=found

    def verify(self,sha):
        self._refresh()
        result=super().verify(sha)
        if result["status"]=="DUAL_NATIVE_EVIDENCE_VERIFIED":
            result["fresh_sap_query_verified"]=True
            result["fresh_evidence_attestation"]="WINDOWS_HMAC_PLUS_NATIVE_O5"
        return result

def make_fresh_handler(*,token,bundle,model,ledger_path):
    root=bundle.fresh_root
    refresh_lock=RLock()
    Parent=make_handler(token=token,bundle=bundle,model=model,
                        ledger_path=ledger_path,reviewer_registry=None)
    class Handler(Parent):
        def do_GET(self):
            if self.path=="/health":
                try:bundle._refresh()
                except Exception:
                    return self.reply(503,{"state":"EVIDENCE_INVALID"})
                return self.reply(200,{
                    "service":"ELSE-ITIL-V1-BETA-FRESH-OT-QA",
                    "state":"READY","listener":"LOOPBACK_ONLY",
                    "cohort":"FEB2026_FIXED_100",
                    "fresh_sap_ot_verified_cases":len(bundle.sap_recs),
                    "source_access":"WINDOWS_QA_NEW_READ_HMAC_O5",
                    "role_matrix_certified":False,
                    "official_business_join_certified":False,
                    "reviewer_roster_configured":False,
                    "repair_enabled":False,
                })
            match=re.fullmatch(
                r"/v1/beta/refresh-status/([0-9a-f]{32})",
                self.path)
            if match:
                if not self.authorized():
                    return self.reply(401,{"error":"AUTH_REQUIRED"})
                ident=match.group(1)
                file=root/"requests"/(ident+".private.json")
                if not file.is_file() or file.is_symlink():
                    return self.reply(404,{"error":"JOB_NOT_FOUND"})
                try:
                    job=parse_strict(file.read_bytes())
                    demand(job["job_id"]==ident and
                           job["case_sha256"] in bundle.roster,
                           "JOB_NOT_IN_OWNER_ALLOWLIST")
                    verified=(root/"verified"/ident/
                              "verified_receipt.private.json").exists()
                    delivered=(root/"outbox"/(ident+".private.json")).exists()
                    return self.reply(200,{
                        "job_id":ident,"case_sha_prefix":job["case_sha256"][:16],
                        "state":"O5_VERIFIED" if verified else
                                "DELIVERED_PENDING_VALIDATION" if delivered
                                else "QUEUED_FOR_WINDOWS_QA",
                        "business_join_certified":False,
                        "repair_certified":False,
                    })
                except Exception:
                    return self.reply(503,{"error":"JOB_PROOF_UNAVAILABLE"})
            return super().do_GET()

        def do_POST(self):
            if self.path=="/v1/beta/refresh-ot":
                if not self.authorized():
                    return self.reply(401,{"error":"AUTH_REQUIRED"})
                try:
                    body=self.strict_request(350)
                    if (set(body)!={"case_sha256"} or
                        type(body["case_sha256"]) is not str or
                        HEX.fullmatch(body["case_sha256"]) is None):
                        return self.reply(422,{"error":"CASE_SHA_REQUIRED"})
                    sha=body["case_sha256"]
                    demand(sha in bundle.roster,"CASE_NOT_IN_QA_SELECTION")
                    with refresh_lock:
                        existing=[]
                        for file in (root/"requests").glob("*.private.json"):
                            item=parse_strict(file.read_bytes())
                            if item["case_sha256"]==sha:
                                existing.append(item)
                        demand(len(existing)<=1,
                               "DUPLICATE_CASE_JOBS_REQUIRE_OPERATOR_REVIEW")
                        if existing:
                            job=existing[0]
                            return self.reply(200,{
                                "status":"EXISTING_REFRESH_JOB",
                                "job_id":job["job_id"],
                                "case_sha_prefix":sha[:16],
                                "repair_certified":False})
                        path,job=queue_job(
                            row=bundle.roster[sha],model=model,
                            requests_dir=root/"requests",
                            source_file=bundle.source_file)
                        return self.reply(202,{
                            "status":"QUEUED_FOR_WINDOWS_QA",
                            "job_id":job["job_id"],
                            "case_sha_prefix":sha[:16],
                            "model_requested_exact_tool":True,
                            "read_only":True,
                            "repair_certified":False})
                except ValueError as exc:
                    return self.reply(422,{"error":str(exc)[:90]})
                except Exception:
                    return self.reply(503,{"error":"FRESH_REQUEST_UNAVAILABLE"})
            return super().do_POST()
    return Handler

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--host",default="127.0.0.1")
    p.add_argument("--port",type=int,default=18887)
    p.add_argument("--token-file",required=True,type=Path)
    p.add_argument("--ledger",required=True,type=Path)
    p.add_argument("--qa-source",required=True,type=Path)
    p.add_argument("--private-root",required=True,type=Path)
    p.add_argument("--fresh-root",type=Path,default=ROOT)
    args=p.parse_args()
    if args.host!="127.0.0.1":
        p.error("QA_LOOPBACK_ONLY")
    if args.token_file.stat().st_mode&0o077:
        p.error("UNPROTECTED_BEARER_FILE")
    token=args.token_file.read_text().strip()
    model=OpenAICompatibleModel(
        "http://127.0.0.1:18782/v1",
        "else-itil-riv-qwen9b-gpu6",timeout=150)
    bundle=FreshBetaEvidenceBundle(
        base=Path(__file__).resolve().parents[1],
        qa=args.qa_source,core_source=args.private_root,
        fresh_root=args.fresh_root)
    server=ThreadingHTTPServer(
        (args.host,args.port),make_fresh_handler(
            token=token,bundle=bundle,model=model,
            ledger_path=args.ledger))
    print("ELSE_ITIL_FRESH_SAP_OT_QA_HTTP_READY",flush=True)
    server.serve_forever(poll_interval=.5)

if __name__=="__main__":main()

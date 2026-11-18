"""Loopback-only authenticated intake for requested support cases.

Do not expose directly to the Internet. No corporate ticket extraction, SQL,
permission changes, or claims of repair.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from hashlib import sha256
import hmac
import json
import secrets
from pathlib import Path
from threading import Lock, BoundedSemaphore
from collections import deque
import time

from .agent import OpenAICompatibleModel
from .support_desk import make_attention, record_attention, validate_ticket
from .guided_dialogue import GuidedStore
from .guided_principal_auth import PrincipalRegistry
from .maturity_readiness import load_readiness,load_human_review_status
from .support_capabilities import inventory
from .qa_dispatch_queue import QaDispatchQueue, load_allowed, COHORTS, obj as strict_qa_json
from .core_capability import ParetoInvestigationCore
import re


def make_handler(*, token: str, state_db: Path, primary, fallback,
                 qa_queue_db: Path | None = None,
                 qa_allowlist: Path | None = None,
                 qa_cohort: str="2026-09",
                 guided_db: Path | None = None,
                 principal_registry: PrincipalRegistry | None = None,
                 guided_primary=None, guided_fallback=None,
                 fast_handoff:bool=False, guided_max_inflight:int | None=None,
                 readiness:dict | None=None,
                 human_review_status:dict | None=None):
    if principal_registry is not None and guided_db is None:
        raise ValueError("GUIDED_PRINCIPALS_REQUIRE_GUIDED_STORE")
    if fast_handoff and guided_db is None:
        raise ValueError("GUIDED_FAST_HANDOFF_REQUIRES_STORE")
    if guided_max_inflight is not None and (
        type(guided_max_inflight) is not int or not 1<=guided_max_inflight<=16):
        raise ValueError("GUIDED_INFLIGHT_LIMIT_INVALID")
    model_guided=guided_primary if guided_primary is not None else primary
    model_guided_fallback=guided_fallback if guided_fallback is not None else fallback
    capacity=BoundedSemaphore(guided_max_inflight) if guided_max_inflight else None
    metrics_lock=Lock()
    metrics={"requests":0,"model_accepted":0,"human_triage":0,
             "immediate_safe_handoffs":0,"unverified_improvement_reports":0,
             "busy_rejected":0,"principal_busy_rejected":0}
    latencies=deque(maxlen=200)
    principal_lock=Lock()
    active_principals=set()

    def observe_guided(result:dict,elapsed:float):
        with metrics_lock:
            metrics["requests"]+=1
            metrics["model_accepted"]+=int(result["quality"]["accepted"])
            metrics["human_triage"]+=int(result["status"]=="NEEDS_HUMAN_TRIAGE")
            metrics["immediate_safe_handoffs"]+=int(
                result.get("inference_skipped_for_safe_escalation") is True)
            metrics["unverified_improvement_reports"]+=int(
                result.get("user_improvement_report_only") is True)
            latencies.append(round(max(0,elapsed)*1000))

    def runtime_metrics()->dict:
        with metrics_lock:
            lat=sorted(latencies)
            percentile95=lat[(len(lat)*95+99)//100-1] if lat else None
            return {
                **metrics,"last_200_response_latency_ms_p95":percentile95,
                "response_time_observations":len(lat),
                "monitoring_is_not_causal_accuracy":True,
            }
    lock=Lock()
    # Bounded striped locks: one session is sequential, unrelated cases are
    # concurrent. The legacy /v1/support locking behavior remains unchanged.
    guided_locks=tuple(Lock() for _ in range(64))
    if (qa_queue_db is None) != (qa_allowlist is None):
        raise ValueError("QA_DISPATCH_CONFIGURATION_INCOMPLETE")
    if qa_cohort not in COHORTS:
        raise ValueError("QA_COHORT_NOT_REGISTERED")
    allowed=(load_allowed(
        qa_allowlist,expected_count=COHORTS[qa_cohort]["allowed_count"])
        if qa_allowlist is not None else None)

    class Handler(BaseHTTPRequestHandler):
        server_version='ELSE-ITIL-RIV/0.1'
        sys_version=''
        def log_message(self, fmt, *args):
            # Do not log request body, identifiers, or ticket text.
            return

        def respond(self, status: int, payload: dict):
            raw=json.dumps(payload,ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def authorized(self):
            return hmac.compare_digest(
                self.headers.get('Authorization',''),'Bearer '+token)

        def guided_identity(self):
            if principal_registry is None:
                return self.authorized(),None
            subject=principal_registry.authenticate(
                self.headers.get('Authorization',''))
            return subject is not None,subject

        def do_GET(self):
            if self.path=='/health':
                payload={'service':'ELSE-ITIL-SUP','state':'READY',
                         'source_access':'USER_SUBMITTED_ONLY',
                         'repairs_enabled':False,
                         'guided_dialogue_enabled':guided_db is not None}
                if allowed is not None:
                    payload['qa_dispatch']='QA_HISTORICAL_READY'
                if principal_registry is not None:
                    payload["guided_principal_required"]=True
                if fast_handoff:
                    payload["guided_fast_safe_handoff"]=True
                return self.respond(200,payload)
            if self.path=='/v1/support/capabilities':
                if not self.authorized():
                    return self.respond(401,{'error':'AUTH_REQUIRED'})
                return self.respond(200,inventory(
                    guided=guided_db is not None,
                    principal_scoped=principal_registry is not None,
                    fast_handoff=fast_handoff,
                    qa_dispatch=allowed is not None,
                    readiness=readiness is not None,
                    admission_limited=guided_max_inflight is not None,
                ))
            if self.path=='/v1/support/readiness':
                if readiness is None:
                    return self.respond(404,{'error':'READINESS_NOT_CONFIGURED'})
                if not self.authorized():
                    return self.respond(401,{'error':'AUTH_REQUIRED'})
                # Only aggregate counts, never case data, names or credentials.
                return self.respond(200,{
                    **readiness,
                    "private_principal_scope_enabled":principal_registry is not None,
                    "guided_admission_limit":guided_max_inflight,
                    "guided_runtime":runtime_metrics(),
                    "human_review":human_review_status or {
                        "status":"NOT_CONFIGURED",
                        "causal_diagnosis_certified":False},
                })
            if self.path.startswith('/v1/qa/core/jobs/'):
                if allowed is None:
                    return self.respond(404,{'error':'QA_DISPATCH_DISABLED'})
                if not self.authorized():
                    return self.respond(401,{'error':'AUTH_REQUIRED'})
                jid=self.path[len('/v1/qa/core/jobs/'):]
                if re.fullmatch(r'[0-9a-f]{32}',jid) is None:
                    return self.respond(422,{'error':'JOB_ID_INVALID'})
                try:
                    with QaDispatchQueue(qa_queue_db,allowed,cohort=qa_cohort) as q:
                        result=ParetoInvestigationCore(q).inspect(jid)
                    return self.respond(200,result)
                except ValueError as exc:
                    return self.respond(404,{'error':str(exc)[:64]})
                except Exception:
                    return self.respond(503,{'error':'CORE_CAPABILITY_UNAVAILABLE'})
            if self.path.startswith('/v1/qa/jobs/'):
                if allowed is None:
                    return self.respond(404,{'error':'QA_DISPATCH_DISABLED'})
                if not self.authorized():
                    return self.respond(401,{'error':'AUTH_REQUIRED'})
                jid=self.path[len('/v1/qa/jobs/'):]
                if re.fullmatch(r'[0-9a-f]{32}',jid) is None:
                    return self.respond(422,{'error':'JOB_ID_INVALID'})
                try:
                    with QaDispatchQueue(qa_queue_db,allowed,cohort=qa_cohort) as q:
                        return self.respond(200,q.status(jid))
                except ValueError as exc:
                    return self.respond(404,{'error':str(exc)[:64]})
                except Exception:
                    return self.respond(503,{'error':'QA_DISPATCH_UNAVAILABLE'})
            return self.respond(404,{'error':'NOT_FOUND'})

        def _handle_guided_request(self,principal,started):
            try:
                size=int(self.headers.get('Content-Length','-1'))
                if not 0<size<=7000:
                    return self.respond(413,{'error':'INPUT_LIMIT'})
                request=json.loads(self.rfile.read(size))
                if not isinstance(request,dict):
                    raise ValueError('GUIDED_REQUEST_NOT_OBJECT')
                initial=self.path.endswith('/start')
                if initial and set(request) not in (
                    {'case_ref','input_scope','description'},
                    {'case_ref','input_scope','description','service'}):
                    raise ValueError('GUIDED_START_FIELDS_INVALID')
                if not initial and set(request)!={'session_id','expected_turn','reply'}:
                    raise ValueError('GUIDED_CONTINUE_FIELDS_INVALID')
                lock_key=request['case_ref'] if initial else request['session_id']
                if not isinstance(lock_key,str) or len(lock_key)>80:
                    raise ValueError('GUIDED_LOCK_KEY_INVALID')
                # Different principals sharing a visible ref must never be
                # serialized into one accidental ownership namespace.
                stripe_key=(principal+"|"+lock_key) if principal else lock_key
                stripe=int.from_bytes(sha256(stripe_key.encode()).digest()[:2],
                                      'big')%len(guided_locks)
                with guided_locks[stripe]:
                    db=GuidedStore(guided_db,
                        require_principal=principal_registry is not None,
                        fast_handoff=fast_handoff)
                    try:
                        if initial:
                            result=db.start(request,model_guided,
                                            model_guided_fallback,subject_id=principal)
                        else:
                            result=db.continue_turn(
                                request['session_id'],request['expected_turn'],
                                request['reply'],model_guided,
                                model_guided_fallback,subject_id=principal)
                    finally:
                        db.close()
                observe_guided(result,time.monotonic()-started)
                return self.respond(200,result)
            except (ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
                return self.respond(422,{'error':str(exc)[:90]})
            except Exception:
                return self.respond(503,{'error':'GUIDED_SUPPORT_UNAVAILABLE'})

        def do_POST(self):
            if self.path in ('/v1/support/guided/start',
                             '/v1/support/guided/continue'):
                if guided_db is None:
                    return self.respond(404,{'error':'GUIDED_NOT_ENABLED'})
                identity_ok,principal=self.guided_identity()
                if not identity_ok:
                    return self.respond(401,{'error':'AUTH_REQUIRED'})
                reserved=False
                if principal is not None:
                    with principal_lock:
                        if principal not in active_principals:
                            active_principals.add(principal)
                            reserved=True
                    if not reserved:
                        with metrics_lock:
                            metrics["principal_busy_rejected"]+=1
                        return self.respond(429,{
                            'error':'GUIDED_PRINCIPAL_BUSY',
                            'retry_after_seconds':5})
                admitted=(capacity is None or capacity.acquire(blocking=False))
                if not admitted:
                    if reserved:
                        with principal_lock:
                            active_principals.remove(principal)
                    with metrics_lock:
                        metrics["busy_rejected"]+=1
                    return self.respond(429,{
                        'error':'GUIDED_OVER_CAPACITY',
                        'retry_after_seconds':5})
                started=time.monotonic()
                try:
                    return self._handle_guided_request(principal,started)
                finally:
                    if capacity is not None:capacity.release()
                    if reserved:
                        with principal_lock:
                            active_principals.remove(principal)

            if self.path=='/v1/qa/core/investigate':
                if allowed is None:
                    return self.respond(404,{'error':'QA_DISPATCH_DISABLED'})
                if not self.authorized():
                    return self.respond(401,{'error':'AUTH_REQUIRED'})
                try:
                    size=int(self.headers.get('Content-Length','-1'))
                    if not 0<size<=650:
                        return self.respond(413,{'error':'INPUT_LIMIT'})
                    request=strict_qa_json(self.rfile.read(size))
                    if not set(request) <= {'case_sha256','goals'} or (
                            'case_sha256' not in request):
                        return self.respond(422,{'error':'CORE_REQUEST_FIELDS_INVALID'})
                    if 'goals' in request and not isinstance(request['goals'],list):
                        return self.respond(422,{'error':'GOALS_ARRAY_REQUIRED'})
                    with QaDispatchQueue(qa_queue_db,allowed,cohort=qa_cohort) as q:
                        response=ParetoInvestigationCore(q).start(
                            request['case_sha256'],
                            **({'goals':request['goals']}
                                if 'goals' in request else {}))
                    return self.respond(202 if response['real_hands_started']
                                        else 200,response)
                except (ValueError,TypeError,KeyError) as exc:
                    return self.respond(422,{'error':str(exc)[:64]})
                except Exception:
                    return self.respond(503,{'error':'CORE_CAPABILITY_UNAVAILABLE'})
            if self.path=='/v1/qa/investigate':
                if allowed is None:
                    return self.respond(404,{'error':'QA_DISPATCH_DISABLED'})
                if not self.authorized():
                    return self.respond(401,{'error':'AUTH_REQUIRED'})
                try:
                    size=int(self.headers.get('Content-Length','-1'))
                    if not 0<size<=350:
                        return self.respond(413,{'error':'INPUT_LIMIT'})
                    request=strict_qa_json(self.rfile.read(size))
                    if set(request)!={'case_sha256'}:
                        return self.respond(422,{'error':'QA_REQUEST_FIELDS_INVALID'})
                    with QaDispatchQueue(qa_queue_db,allowed,cohort=qa_cohort) as q:
                        queued=q.submit(request['case_sha256'])
                    return self.respond(202,queued)
                except (ValueError,TypeError,KeyError) as exc:
                    return self.respond(422,{'error':str(exc)[:64]})
                except Exception:
                    return self.respond(503,{'error':'QA_DISPATCH_UNAVAILABLE'})
            if self.path!='/v1/support':
                return self.respond(404,{'error':'NOT_FOUND'})
            if not self.authorized():
                return self.respond(401,{'error':'AUTH_REQUIRED'})
            try:
                size=int(self.headers.get('Content-Length','-1'))
                if not 0<size<=12000:
                    return self.respond(413,{'error':'INPUT_LIMIT'})
                ticket=json.loads(self.rfile.read(size))
                validate_ticket(ticket)
                with lock:
                    # Avoid reusing different content under the same case_ref.
                    response=make_attention(ticket,primary,fallback)
                    result=record_attention(state_db,ticket,response)
                self.respond(200,result)
            except (ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
                return self.respond(422,{'error':str(exc)[:90]})
            except Exception:
                return self.respond(503,{'error':'SUPPORT_UNAVAILABLE'})
    return Handler


def main():
    p=argparse.ArgumentParser(description='Private authenticated RIV support intake')
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',type=int,default=18881)
    p.add_argument('--db',required=True)
    p.add_argument('--token-file',required=True)
    p.add_argument('--base-url',default='http://127.0.0.1:18781/v1')
    p.add_argument('--model',default='else-itil-riv-gpu7')
    p.add_argument('--fallback-url',default='http://127.0.0.1:18782/v1')
    p.add_argument('--fallback-model',default='else-itil-riv-qwen9b-gpu6')
    p.add_argument('--qa-queue-db',type=Path,default=None)
    p.add_argument('--qa-allowlist',type=Path,default=None)
    p.add_argument('--qa-cohort',choices=sorted(COHORTS),default="2026-09")
    p.add_argument('--guided-db',type=Path,default=None,
                   help="Opt-in private SQLite session store for novice guidance")
    p.add_argument('--guided-principals-file',type=Path,default=None,
                   help="Private SHA256 token registry. Each subject owns only their sessions.")
    p.add_argument('--guided-fast-handoff',action='store_true',
                   help="Never call Qwen for missing-permissions or persistent third-turn escalation")
    p.add_argument('--guided-max-inflight',type=int,default=None,
                   help="Bound simultaneous guided requests (opt-in V5)")
    p.add_argument('--guided-primary-timeout',type=int,default=None)
    p.add_argument('--guided-fallback-timeout',type=int,default=None)
    p.add_argument('--maturity-scorecard',type=Path,default=None)
    p.add_argument('--maturity-source-summary',type=Path,default=None)
    p.add_argument('--human-review-status-file',type=Path,default=None)
    args=p.parse_args()
    if (args.qa_queue_db is None) != (args.qa_allowlist is None):
        p.error('QA_DISPATCH_CONFIGURATION_INCOMPLETE')
    if (args.maturity_scorecard is None)!=(args.maturity_source_summary is None):
        p.error('MATURITY_EVIDENCE_PAIR_REQUIRED')
    if args.guided_principals_file is not None and args.guided_db is None:
        p.error('GUIDED_PRINCIPALS_REQUIRE_GUIDED_STORE')
    if args.guided_fast_handoff and args.guided_db is None:
        p.error('GUIDED_FAST_HANDOFF_REQUIRES_STORE')
    for t in (args.guided_primary_timeout,args.guided_fallback_timeout):
        if t is not None and not 5<=t<=120:
            p.error('GUIDED_MODEL_TIMEOUT_OUT_OF_RANGE')
    if args.host!='127.0.0.1':
        p.error('LISTENER_MUST_BE_LOOPBACK_ONLY')
    key=Path(args.token_file)
    if key.stat().st_mode & 0o077:
        p.error('TOKEN_FILE_PERMISSIONS_TOO_BROAD')
    token=key.read_text('utf-8').strip()
    if len(token)<32:
        p.error('TOKEN_TOO_SHORT')
    one=OpenAICompatibleModel(args.base_url,args.model,timeout=100)
    two=OpenAICompatibleModel(args.fallback_url,args.fallback_model,timeout=155)
    gp=(OpenAICompatibleModel(args.base_url,args.model,
         timeout=args.guided_primary_timeout)
        if args.guided_primary_timeout is not None else None)
    gf=(OpenAICompatibleModel(args.fallback_url,args.fallback_model,
         timeout=args.guided_fallback_timeout)
        if args.guided_fallback_timeout is not None else None)
    registry=(PrincipalRegistry.from_file(args.guided_principals_file)
              if args.guided_principals_file is not None else None)
    readiness=(load_readiness(args.maturity_scorecard,
               args.maturity_source_summary)
               if args.maturity_scorecard is not None else None)
    human_review=(load_human_review_status(args.human_review_status_file)
                  if args.human_review_status_file is not None else None)
    # Fail before accepting HTTP requests if the private store cannot be
    # opened, migrated atomically, or verified for restrictive permissions.
    if args.guided_db is not None:
        bootstrap=GuidedStore(
            args.guided_db,
            require_principal=registry is not None,
            fast_handoff=args.guided_fast_handoff)
        bootstrap.close()
    server=ThreadingHTTPServer((args.host,args.port),make_handler(
        token=token,state_db=Path(args.db),primary=one,fallback=two,
        qa_queue_db=args.qa_queue_db,qa_allowlist=args.qa_allowlist,
        qa_cohort=args.qa_cohort,guided_db=args.guided_db,
        principal_registry=registry,guided_primary=gp,guided_fallback=gf,
        fast_handoff=args.guided_fast_handoff,
        guided_max_inflight=args.guided_max_inflight,
        readiness=readiness,human_review_status=human_review))
    print('SUPPORT_API_READY host=127.0.0.1 port='+str(args.port)+
          ' mode=user_submitted_no_mutations qa_dispatch='+
          str(args.qa_queue_db is not None)+
        ' guided='+str(args.guided_db is not None),flush=True)
    server.serve_forever(poll_interval=.5)

if __name__=='__main__':
    main()

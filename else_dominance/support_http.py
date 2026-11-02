"""Loopback-only authenticated intake for requested support cases.

Do not expose directly to the Internet. No corporate ticket extraction, SQL,
permission changes, or claims of repair.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import secrets
from pathlib import Path
from threading import Lock

from .agent import OpenAICompatibleModel
from .support_desk import make_attention, record_attention, validate_ticket


def make_handler(*, token: str, state_db: Path, primary, fallback):
    lock=Lock()

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

        def do_GET(self):
            if self.path=='/health':
                self.respond(200,{'service':'ELSE-ITIL-SUP','state':'READY',
                                  'source_access':'USER_SUBMITTED_ONLY',
                                  'repairs_enabled':False})
            else:self.respond(404,{'error':'NOT_FOUND'})

        def do_POST(self):
            if self.path!='/v1/support':
                return self.respond(404,{'error':'NOT_FOUND'})
            value=self.headers.get('Authorization','')
            if not hmac.compare_digest(value,'Bearer '+token):
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
    args=p.parse_args()
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
    server=ThreadingHTTPServer((args.host,args.port),make_handler(
        token=token,state_db=Path(args.db),primary=one,fallback=two))
    print('SUPPORT_API_READY host=127.0.0.1 port='+str(args.port)+' mode=user_submitted_no_mutations',flush=True)
    server.serve_forever(poll_interval=.5)

if __name__=='__main__':
    main()

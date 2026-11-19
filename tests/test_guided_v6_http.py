"""Private V6 authenticated end-to-end user -> support handoff."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import json
import secrets

from else_dominance.guided_dialogue import _safe_fallback
from else_dominance.guided_principal_auth import PrincipalRegistry
from else_dominance.support_handoff import HandoffSigner
from else_dominance.support_http import make_handler


SERVICE="only-for-technician-private-integration-tests-111"
ALICE=secrets.token_urlsafe(48)
BOB=secrets.token_urlsafe(48)


class Model:
    def complete(self,messages):
        return json.dumps(_safe_fallback(),ensure_ascii=False)


def spawn(tmp_path):
    manifest=tmp_path/"principals.json"
    manifest.write_text(json.dumps({
      "schema":"else.itil.guided-principals.v1",
      "principals":[{
        "subject":sub,
        "token_sha256":sha256(token.encode()).hexdigest(),
        "enabled":True,"roles":["guided_user"],
      } for sub,token in (("alice_qa",ALICE),("bob_qa",BOB))],
    }))
    manifest.chmod(0o600)
    auth=PrincipalRegistry.from_file(manifest)
    signer=HandoffSigner(bytes.fromhex("8c"*32))
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(
        token=SERVICE,state_db=tmp_path/"legacy.sqlite",
        primary=Model(),fallback=None,
        guided_db=tmp_path/"sessions.sqlite",
        principal_registry=auth,
        handoff_signer=signer,
        fast_handoff=True))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    return server,thread,f"http://127.0.0.1:{server.server_port}"


def post(url,path,payload,token=None):
    headers={"Content-Type":"application/json"}
    if token is not None:headers["Authorization"]="Bearer "+token
    req=Request(url+path,data=json.dumps(payload,ensure_ascii=False).encode(),
                headers=headers)
    try:
        with urlopen(req,timeout=6) as resp:
            return resp.status,json.load(resp)
    except HTTPError as err:
        return err.code,json.load(err)


def get(url,path,token=None):
    headers={}
    if token is not None:headers["Authorization"]="Bearer "+token
    try:
        with urlopen(Request(url+path,headers=headers),timeout=6) as resp:
            return resp.status,json.load(resp)
    except HTTPError as err:
        return err.code,json.load(err)


def ticket():
    return {"case_ref":"QA-V6-TEST-CASE-001",
            "input_scope":"synthetic",
            "service":"Aplicación de ejemplo",
            "description":"Mi correo empleado.privado@example.com ve un error al ingresar a la pantalla."}


def teardown(server,thread):
    server.shutdown();server.server_close();thread.join(timeout=5)


def test_authenticated_consent_handoff_verification_and_revocation_http(tmp_path):
    s,t,url=spawn(tmp_path)
    try:
        assert get(url,"/health")[1]["user_consent_handoff_enabled"] is True
        assert get(url,"/v1/support/guided/case/"+"a"*48)[0]==401
        assert post(url,"/v1/support/guided/handoff",
                    {"session_id":"a"*48},token=SERVICE)[0]==401
        status,start=post(url,"/v1/support/guided/start",ticket(),ALICE)
        assert status==200
        sid=start["session_id"]
        assert get(url,"/v1/support/guided/case/"+sid,BOB)[0]==422
        status,view=get(url,"/v1/support/guided/case/"+sid,ALICE)
        assert status==200
        assert view["last_turn"]==1
        assert view["corp_case_binding"]=="NOT_ESTABLISHED"
        assert "empleado.privado@example.com" not in json.dumps(view,ensure_ascii=False)
        consent={"session_id":sid,"consent_to_share":True,
                 "privacy_notice_acknowledged":True}
        assert post(url,"/v1/support/guided/handoff",
                    {**consent,"consent_to_share":False},ALICE)[0]==422
        assert post(url,"/v1/support/guided/handoff",consent,BOB)[0]==422
        status,envelope=post(url,"/v1/support/guided/handoff",consent,ALICE)
        assert status==200
        assert envelope["schema"]=="else.itil.guided-handoff-signed.v1"
        assert envelope["packet"]["consent_mode"]=="EXPLICIT_REQUESTER_SHARE_WITH_SUPPORT"
        assert "empleado.privado@example.com" not in json.dumps(envelope,ensure_ascii=False)
        assert envelope["packet"]["technical_review"]["qa_evidence_bound"] is False
        assert post(url,"/v1/support/technician/verify-handoff",
                    {"envelope":envelope},ALICE)[0]==401
        assert post(url,"/v1/support/technician/verify-handoff",
                    {"envelope":envelope})[0]==401
        status,report=post(url,"/v1/support/technician/verify-handoff",
                           {"envelope":envelope},SERVICE)
        assert status==200
        assert report["signature_valid"]
        assert report["consent_record_valid"]
        assert report["business_evidence_verified"] is False
        assert report["root_cause_certified"] is False
        core=report["technical_investigation_preflight"]
        assert core["registered_core_evidence_goals"]==[
            "ITIL_CASE_EXISTS","ITIL_SERVICE","ITIL_MODULE"]
        assert core["qa_hand_execution_started"] is False
        assert core["qa_case_sha256_bound"] is False
        assert core["independent_business_object_relation"]=="NOT_VERIFIED"
        modified=deepcopy(envelope)
        modified["packet"]["issue_reported"]="Esto es diferente a lo firmado y puede ser falso."
        assert post(url,"/v1/support/technician/verify-handoff",
                    {"envelope":modified},SERVICE)[0]==422
        receipt=envelope["packet"]["receipt_id"]
        assert post(url,"/v1/support/guided/revoke",
                    {"session_id":sid,"receipt_id":receipt},BOB)[0]==422
        status,done=post(url,"/v1/support/guided/revoke",
                    {"session_id":sid,"receipt_id":receipt},ALICE)
        assert status==200 and done["revoked"]
        assert post(url,"/v1/support/technician/verify-handoff",
                    {"envelope":envelope},SERVICE)[0]==422
        # The legacy support API and QA dispatch are not enabled by handoff.
        assert post(url,"/v1/support/guided/start",ticket(),SERVICE)[0]==401
        assert post(url,"/v1/qa/investigate",{"case_sha256":"a"*64},SERVICE)[0]==404
        status,cap=get(url,"/v1/support/capabilities",SERVICE)
        assert status==200 and cap["capability_count"]==13
        assert any(x["capability"]=="user_consent_cryptographic_support_handoff"
                   for x in cap["capabilities"])
        assert cap["no_company_source_or_repair_claim"] is True
    finally:teardown(s,t)


def test_revoke_all_http_invalidates_all_signed_packets(tmp_path):
    server,thread,url=spawn(tmp_path)
    try:
        status,first=post(url,"/v1/support/guided/start",ticket(),ALICE)
        assert status==200
        sid=first["session_id"]
        payload={"session_id":sid,"consent_to_share":True,
                 "privacy_notice_acknowledged":True}
        signed=[]
        for _ in range(2):
            code,out=post(url,"/v1/support/guided/handoff",payload,ALICE)
            assert code==200
            signed.append(out)
        assert post(url,"/v1/support/guided/revoke-all",
                    {"session_id":sid},BOB)[0]==422
        code,done=post(url,"/v1/support/guided/revoke-all",
                       {"session_id":sid},ALICE)
        assert code==200 and done["revoked_count"]==2
        assert done["offline_copies_deleted"] is False
        for pkg in signed:
            assert post(url,"/v1/support/technician/verify-handoff",
                        {"envelope":pkg},SERVICE)[0]==422
    finally:teardown(server,thread)

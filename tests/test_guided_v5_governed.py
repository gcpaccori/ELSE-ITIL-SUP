"""V5 private principal authorization, overload, bounded safe handoff and truth."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Event,Thread
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import json
import secrets

import pytest

from else_dominance.guided_dialogue import GuidedStore,_safe_fallback
from else_dominance.guided_principal_auth import PrincipalRegistry
from else_dominance.maturity_readiness import load_readiness
from else_dominance.support_http import make_handler

ROOT=Path(__file__).resolve().parents[1]


def ticket(ref="QA-V5-GUIDE-1001",description=None):
    return {
      "case_ref":ref,"input_scope":"synthetic",
      "service":"Aplicación sintética",
      "description":description or
        "Al entrar en el sistema de ejemplo aparece un aviso que no comprendo.",
    }


class Model:
    def __init__(self):self.calls=0
    def complete(self,messages):
        self.calls+=1
        return json.dumps(_safe_fallback(),ensure_ascii=False)


def principal_file(path:Path,tokens:dict[str,str],disabled=()):
    p={
      "schema":"else.itil.guided-principals.v1",
      "principals":[{
          "subject":subject,
          "token_sha256":sha256(token.encode()).hexdigest(),
          "roles":["guided_user"],
          "enabled":subject not in disabled,
      } for subject,token in tokens.items()],
    }
    path.write_text(json.dumps(p))
    path.chmod(0o600)
    return PrincipalRegistry.from_file(path)


def request(url,path,obj=None,token=None):
    h={"Content-Type":"application/json"}
    if token is not None:h["Authorization"]="Bearer "+token
    req=Request(url+path,
        data=json.dumps(obj).encode() if obj is not None else None,
        headers=h)
    try:
        with urlopen(req,timeout=8) as r:
            return r.status,json.load(r)
    except HTTPError as e:
        return e.code,json.load(e)


def serve(tmp_path,*,model=None, registry=None, read=None, fast=True,capacity=2):
    model=model or Model()
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(
        token="only-for-operation-do-not-use-as-a-user-token",
        state_db=tmp_path/"legacy.sqlite",
        guided_db=tmp_path/"sessions.sqlite",
        primary=model,fallback=None,
        principal_registry=registry,
        fast_handoff=fast,
        guided_max_inflight=capacity,
        readiness=read))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    return server,thread,f"http://127.0.0.1:{server.server_port}"


def stop(server,thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_principal_registry_hashed_tokens_private_file_and_disabled(tmp_path):
    A=secrets.token_urlsafe(48)
    B=secrets.token_urlsafe(48)
    f=tmp_path/"users.json"
    r=principal_file(f,{"employee_one":A,"employee_two":B},
                     disabled={"employee_two"})
    assert A not in f.read_text() and B not in f.read_text()
    assert r.authenticate("Bearer "+A)=="employee_one"
    assert r.authenticate("Bearer "+B) is None
    assert r.authenticate("Bearer "+"wrong"*8) is None
    f.chmod(0o644)
    with pytest.raises(ValueError,match="PERMISSIONS_TOO_BROAD"):
        PrincipalRegistry.from_file(f)


def test_no_header_principal_impersonation_and_case_owner_isolation(tmp_path):
    alice=secrets.token_urlsafe(48)
    bob=secrets.token_urlsafe(48)
    registry=principal_file(tmp_path/"principals.json",{
       "employee_one":alice,"employee_two":bob})
    s,t,url=serve(tmp_path,registry=registry)
    try:
        assert request(url,"/v1/support/guided/start",ticket())[0]==401
        # Shared system token has no guided user privileges.
        status,_=request(url,"/v1/support/guided/start",ticket(),
           "only-for-operation-do-not-use-as-a-user-token")
        assert status==401
        status,first=request(url,"/v1/support/guided/start",ticket(),alice)
        assert status==200 and first["turn"]==1
        assert not first["diagnosis_certified"]
        assert "employee_one" not in json.dumps(first)
        sid=first["session_id"]
        status,response=request(url,"/v1/support/guided/continue",
          {"session_id":sid,"expected_turn":2,"reply":"No entiendo ese paso."},bob)
        assert status==422
        assert response["error"]=="GUIDED_SESSION_NOT_FOUND"
        assert sid not in json.dumps(response)
        status,other_same_ref=request(url,"/v1/support/guided/start",ticket(),bob)
        assert status==200
        assert other_same_ref["session_id"]!=sid
        assert other_same_ref["turn"]==1
        status,second=request(url,"/v1/support/guided/continue",{
          "session_id":sid,"expected_turn":2,
          "reply":"No entiendo ese paso."},alice)
        assert status==200
        assert second["turn"]==2
        new=ticket("QA-V5-GUIDE-1002")
        status,other=request(url,"/v1/support/guided/start",new,bob)
        assert status==200 and other["session_id"]!=sid
        store=GuidedStore(tmp_path/"sessions.sqlite",require_principal=True)
        assert {r[0] for r in store.db.execute(
            "SELECT subject_id FROM guided_sessions")}=={
                "employee_one","employee_two"}
        store.close()
    finally:stop(s,t)


def test_legacy_unscoped_sessions_cannot_be_claimed_by_principal(tmp_path):
    p=tmp_path/"migration.sqlite"
    m=Model()
    db=GuidedStore(p)
    old=db.start(ticket(),m)
    db.close()
    strict=GuidedStore(p,require_principal=True)
    separate=strict.start(ticket(),m,subject_id="employee_one")
    assert separate["session_id"]!=old["session_id"]
    with pytest.raises(ValueError,match="GUIDED_SESSION_NOT_FOUND"):
        strict.continue_turn(old["session_id"],2,"No entiendo ese paso.",
                             m,subject_id="employee_one")
    newer=strict.start(ticket("QA-V5-MIGRATION-2002"),m,
                       subject_id="employee_one")
    assert newer["turn"]==1
    strict.close()


def test_fast_safe_escalation_skips_llm_and_not_counted_as_model_pass(tmp_path):
    m=Model()
    db=GuidedStore(tmp_path/"fast.sqlite",require_principal=True,
                   fast_handoff=True)
    first=db.start(ticket(
        description="No tengo permisos para entrar en el módulo de prueba."
    ),m,subject_id="employee_one")
    assert m.calls==0
    assert first["status"]=="NEEDS_HUMAN_TRIAGE"
    assert first["inference_skipped_for_safe_escalation"] is True
    assert not first["quality"]["accepted"]
    assert first["presentacion_para_usuario"]["mostrar_escalamiento"]
    db.close()
    db=GuidedStore(tmp_path/"other.sqlite",require_principal=True,
                   fast_handoff=True)
    new=db.start(ticket("QA-V5-OTHER-2001"),m,subject_id="employee_one")
    assert new["quality"]["accepted"] is True
    db.continue_turn(new["session_id"],2,
        "No entiendo el paso que me indicaste.",m,subject_id="employee_one")
    calls=m.calls
    third=db.continue_turn(new["session_id"],3,
        "Sigue fallando y necesito comunicarlo a soporte.",m,
        subject_id="employee_one")
    assert m.calls==calls
    assert third["quality"]["accepted"] is False
    assert third["inference_skipped_for_safe_escalation"] is True
    assert third["presentacion_para_usuario"]["mostrar_escalamiento"]
    assert not third["executed_changes"]
    db.close()


def test_private_readiness_is_no_go_and_untrusted_claim_fails_closed(tmp_path):
    a=ROOT/"data"/"2026_sep545_all_features_maturity_scorecard.json"
    b=ROOT/"data"/"2026_sep545_full_maturity_evidence.json"
    status=load_readiness(a,b,now=date(2026,11,18))
    assert status["decision"]=="NO_GO"
    assert status["last_recorded_incident_date"]=="2026-09-16"
    assert status["source_freshness_certified"] is False
    assert status["root_cause_accuracy_certified"] is False
    assert status["gaps_count"]>=10
    changed=json.loads(a.read_text())
    changed["decision"]="GO"
    fake=tmp_path/"forged.json"
    fake.write_text(json.dumps(changed))
    with pytest.raises(ValueError,match="UNSUPPORTED_GO"):
        load_readiness(fake,b,now=date(2026,11,18))


def test_readiness_requires_service_token_and_never_leaks_case_ids(tmp_path):
    registry=principal_file(tmp_path/"principals.json",{
        "employee_one":secrets.token_urlsafe(48)})
    a=ROOT/"data"/"2026_sep545_all_features_maturity_scorecard.json"
    b=ROOT/"data"/"2026_sep545_full_maturity_evidence.json"
    s,t,url=serve(tmp_path,registry=registry,
          read=load_readiness(a,b,now=date(2026,11,18)))
    try:
        assert request(url,"/v1/support/readiness")[0]==401
        assert request(url,"/v1/support/readiness",token="wrong"*10)[0]==401
        code,r=request(url,"/v1/support/readiness",
            token="only-for-operation-do-not-use-as-a-user-token")
        assert code==200
        assert r["decision"]=="NO_GO"
        assert r["private_principal_scope_enabled"] is True
        assert r["guided_admission_limit"]==2
        assert r["guided_runtime"]["requests"]==0
        assert "case_sha256" not in json.dumps(r)
        assert "historical_solution" not in json.dumps(r)
    finally:stop(s,t)


def test_guided_capacity_rejects_second_llm_request_with_429(tmp_path):
    working=Event()
    release=Event()
    class BlockingModel:
        def complete(self,messages):
            working.set()
            assert release.wait(timeout=5)
            return json.dumps(_safe_fallback())
    s,t,url=serve(tmp_path,model=BlockingModel(),capacity=1,fast=False)
    try:
        with ThreadPoolExecutor(max_workers=2) as ex:
            work=ex.submit(request,url,"/v1/support/guided/start",
                ticket("QA-V5-LONG-00001"),
                "only-for-operation-do-not-use-as-a-user-token")
            assert working.wait(timeout=2)
            code,response=request(url,"/v1/support/guided/start",
                ticket("QA-V5-LONG-00002"),
                "only-for-operation-do-not-use-as-a-user-token")
            assert code==429 and response["error"]=="GUIDED_OVER_CAPACITY"
            release.set()
            accepted,data=work.result(timeout=8)
            assert accepted==200 and data["quality"]["accepted"]
        _,metrics=request(url,"/v1/support/readiness",
            token="only-for-operation-do-not-use-as-a-user-token")
        # This server did not opt into a readiness manifest.
        assert metrics.get("error")=="READINESS_NOT_CONFIGURED"
    finally:
        release.set()
        stop(s,t)


def test_model_cannot_echo_email_or_private_identifier_in_any_response_field():
    from else_dominance.guided_dialogue import validate_guidance,generate_guidance
    sample=_safe_fallback()
    sample["que_entendi"]="Dices que el correo ana.privada@empresa.local aparece en el aviso de ingreso."
    assert "MODEL_ECHOES_SENSITIVE_IDENTIFIER" in validate_guidance(sample)
    sample=_safe_fallback()
    sample["para_soporte"]["evidencia"]=(
        "El usuario dice que el contacto fue admin@empresa.local y no pudo acceder."
    )
    assert "MODEL_ECHOES_SENSITIVE_IDENTIFIER" in validate_guidance(sample)
    class Bad:
        def complete(self,messages):
            return json.dumps(sample)
    output=generate_guidance("Error al ingresar al sistema.",
        "Aplicación","No entiendo",[],Bad())
    assert output["status"]=="NEEDS_HUMAN_TRIAGE"
    assert not output["quality"]["accepted"]
    assert "admin@empresa.local" not in json.dumps(output["guide"])


def test_decorated_old_guide_with_sensitive_text_revalidated_and_hidden(tmp_path):
    db=GuidedStore(tmp_path/"old_decorated.sqlite")
    first=db.start(ticket(),Model())
    sid=first["session_id"]
    current=db.db.execute(
        "SELECT result_json FROM guided_turns WHERE sid=? AND turn=1",(sid,)
    ).fetchone()
    output=json.loads(current[0])
    output["guide"]["que_entendi"]=(
        "Se ha confirmado que la causa del problema ya se arregló."
    )
    db.db.execute(
       "UPDATE guided_turns SET result_json=? WHERE sid=? AND turn=1",
       (json.dumps(output,ensure_ascii=False),sid))
    replay=db.start(ticket(),Model())
    assert replay["replayed"] is True
    assert replay["status"]=="NEEDS_HUMAN_TRIAGE"
    assert replay["quality"]["accepted"] is False
    assert "Se ha confirmado" not in json.dumps(
        replay["presentacion_para_usuario"],ensure_ascii=False)
    assert "Se ha confirmado" not in json.dumps(db._history(sid),ensure_ascii=False)
    db.close()


def test_same_principal_busy_is_explicit_rejection_not_model_failure(tmp_path):
    alice=secrets.token_urlsafe(48)
    registry=principal_file(tmp_path/"principals.json",{"employee_one":alice})
    entered=Event(); release=Event()
    class SlowModel:
        def complete(self,messages):
            entered.set()
            assert release.wait(timeout=5)
            return json.dumps(_safe_fallback())
    s,t,url=serve(tmp_path,model=SlowModel(),registry=registry,capacity=2,fast=False)
    try:
        with ThreadPoolExecutor(max_workers=2) as ex:
            first=ex.submit(request,url,"/v1/support/guided/start",
                            ticket("QA-V5-BUSY-00001"),alice)
            assert entered.wait(timeout=3)
            code,reply=request(url,"/v1/support/guided/start",
                ticket("QA-V5-BUSY-00002"),alice)
            assert code==429 and reply["error"]=="GUIDED_PRINCIPAL_BUSY"
            release.set()
            ok,res=first.result(timeout=8)
            assert ok==200 and res["quality"]["accepted"]
    finally:
        release.set()
        stop(s,t)


def test_reported_improvement_is_fast_not_a_certified_fix(tmp_path):
    m=Model()
    db=GuidedStore(tmp_path/"improvement.sqlite",require_principal=True,
                   fast_handoff=True)
    first=db.start(ticket(),m,subject_id="employee_one")
    assert m.calls==1
    second=db.continue_turn(first["session_id"],2,
            "Ahora funciona, ya puedo entrar sin errores.",m,
            subject_id="employee_one")
    assert m.calls==1
    assert second["status"]=="USER_REPORTED_IMPROVEMENT_UNVERIFIED"
    assert second["quality"]["accepted"] is False
    assert second["user_improvement_report_only"] is True
    assert second["presentacion_para_usuario"]["etapa"]==(
       "USUARIO_REPORTA_MEJORIA_NO_VERIFICADA")
    assert second["presentacion_para_usuario"]["mostrar_escalamiento"] is False
    assert not second["diagnosis_certified"] and not second["executed_changes"]
    assert "no una reparación verificada" in second[
        "presentacion_para_usuario"]["respuesta_sencilla"]
    db.close()


def test_capability_inventory_only_claims_attached_runtime_features(tmp_path):
    from else_dominance.support_capabilities import inventory
    x=inventory(guided=True,principal_scoped=True,fast_handoff=True,
       qa_dispatch=False,readiness=True,admission_limited=True)
    assert x["capability_count"]==12
    states={entry["capability"]:entry["state"] for entry in x["capabilities"]}
    assert states["private_principal_session_ownership"]=="PILOT_ENABLED"
    assert states["automated_corporate_ticket_ingestion"]=="NOT_CONNECTED"
    assert states["independent_causal_diagnosis_certification"]=="NOT_CERTIFIED"
    assert states["automatic_mutations_or_repairs"]=="DISABLED"
    assert states["qa_historical_dispatch"]=="DISABLED"
    server,thread,url=serve(tmp_path)
    try:
        assert request(url,"/v1/support/capabilities")[0]==401
        code,doc=request(url,"/v1/support/capabilities",
            token="only-for-operation-do-not-use-as-a-user-token")
        assert code==200 and doc["capability_count"]==12
        assert doc["pilot_is_not_maturity_certification"] is True
        assert doc["no_company_source_or_repair_claim"] is True
    finally:stop(server,thread)


def test_guided_sqlite_integrity_and_retention_secure_delete_enabled(tmp_path):
    d=GuidedStore(tmp_path/"integrity.sqlite",require_principal=True)
    assert d.db.execute("PRAGMA foreign_keys").fetchone()[0]==1
    assert d.db.execute("PRAGMA secure_delete").fetchone()[0]==1
    assert d.db.execute("PRAGMA busy_timeout").fetchone()[0]==30000
    with pytest.raises(__import__('sqlite3').IntegrityError):
        d.db.execute(
            "INSERT INTO guided_turns (sid,turn,input_hash,reply,result_json) "
            "VALUES (?,?,?,?,?)",
            ("f"*48,1,"hash","r","{}"))
    d.close()

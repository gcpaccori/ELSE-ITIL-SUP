"""Follow-up experience contract (non-operational), including explicit fail closed."""
from pathlib import Path
import json

from else_dominance.guided_dialogue import (
    GuidedStore, _presentation, _safe_fallback, validate_guidance,
    generate_guidance,
)


class Model:
    def __init__(self, plans):
        self.plans=list(plans)
        self.prompts=[]
    def complete(self, messages):
        self.prompts.append(messages)
        item=self.plans.pop(0)
        if isinstance(item,Exception):raise item
        return json.dumps(item,ensure_ascii=False)


def case():
    return {"case_ref":"GUIDED-V4-CASE-00001","input_scope":"synthetic",
            "description":"Tengo un aviso al entrar al sistema y no entiendo qué revisar.",
            "service":"Aplicación de oficina"}


def plan(step):
    x=_safe_fallback()
    x['para_ti']['paso']=step
    return x


def test_first_second_and_third_message_has_safe_deterministic_handoff(tmp_path):
    s=GuidedStore(tmp_path/'sessions.sqlite')
    m=Model([
       plan("Mira la pantalla y anota el aviso visible sin datos personales."),
       plan("Revisa en qué sección aparece el aviso e indica su nombre."),
       plan("Observa si el problema ocurre al abrir la aplicación o al entrar.")
    ])
    one=s.start(case(),m)
    p1=one['presentacion_para_usuario']
    assert p1['etapa']=="COMPROBAR_UNA_COSA"
    assert p1['mostrar_escalamiento'] is False
    assert "Una sola comprobación segura:" in p1['respuesta_sencilla']
    assert "Si ocurre la primera opción:" in p1['respuesta_sencilla']
    assert p1['diagnostico_confirmado'] is False
    assert p1['accion_ejecutada'] is False
    two=s.continue_turn(one['session_id'],2,
                        "No entiendo cómo mirar esa sección.",m)
    p2=two['presentacion_para_usuario']
    assert p2['etapa']=="ACLARAR_EN_LENGUAJE_SENCILLO"
    assert p2['mostrar_escalamiento'] is False
    three=s.continue_turn(one['session_id'],3,
           "El problema sigue fallando. No tengo permisos.",m)
    p3=three['presentacion_para_usuario']
    assert p3['etapa']=="RECOPILAR_EVIDENCIA_Y_ESCALAR"
    assert p3['mostrar_escalamiento'] is True
    assert "contacta a la mesa de ayuda" in p3['respuesta_sencilla']
    assert "No envíes contraseñas" in p3['respuesta_sencilla']
    assert len(p3['escalamiento']['que_anotar'])==3
    assert p3['evaluacion_automatica_aceptada'] is True
    assert not three['executed_changes']
    replay=s.continue_turn(one['session_id'],3,
           "El problema sigue fallando. No tengo permisos.",m)
    assert replay['replayed'] is True
    assert replay['presentacion_para_usuario']==three['presentacion_para_usuario']
    s.close()


def test_model_false_root_cause_text_rejected_even_with_false_boolean():
    x=plan("Mira la pantalla y anota el mensaje visible sin datos personales.")
    x['que_entendi']="Se ha confirmado que la causa es un error en la aplicación de oficina."
    assert 'UNVERIFIED_CAUSAL_OR_CLOSURE_CLAIM_IN_TEXT' in validate_guidance(x)
    model=Model([x,x])
    output=generate_guidance("El sistema muestra una ventana de error.",
                             "Sistema de oficina","No entiendo el aviso.",[],model)
    assert output['status']=='NEEDS_HUMAN_TRIAGE'
    assert output['diagnosis_certified'] is False
    assert output['quality']['accepted'] is False
    assert output['guide']['causa_confirmada'] is False


def test_model_secret_in_summary_rejected():
    x=plan("Mira la pantalla y anota el aviso visible sin datos personales.")
    x['que_entendi']="Tu password: passwordDeEmpresa123 fue recibido; el servicio necesita revisión."
    assert 'MODEL_EXPOSES_SECRET' in validate_guidance(x)


def test_failed_models_yield_human_route_not_fake_pass():
    invalid=plan("Ejecuta SQL UPDATE sobre el servidor productivo ahora.")
    r=generate_guidance("La aplicación muestra un error de inicio.",
                        "Aplicación","El problema sigue igual.",[],
                        Model([invalid,invalid]),None)
    assert r['status']=='NEEDS_HUMAN_TRIAGE'
    p=_presentation(3,"Sigue fallando.",r)
    assert p['etapa']=="ESCALAR_CON_APOYO_HUMANO"
    assert p['mostrar_escalamiento'] is True
    assert not p['evaluacion_automatica_aceptada']
    assert p['escalamiento']['origen']=="GUARDRAIL_DETERMINISTA_NO_CONCLUSION_DEL_MODELO"
    assert p['diagnostico_confirmado'] is False


def test_user_only_does_not_see_technical_commands_in_guidance():
    p=_presentation(3,"No tengo permisos.",{
       "status":"GUIDED_DIAGNOSTIC_CONDITIONAL",
       "guide":_safe_fallback(),
       "quality":{"accepted":True}
    })
    assert p['paso_para_principiante'].startswith("Mira")
    assert "SELECT" not in p['respuesta_sencilla']
    assert "UPDATE" not in p['respuesta_sencilla']
    assert p['escalamiento']['mostrar_ahora']


def test_permissions_block_early_escalation_and_no_privilege_instructions():
    from else_dominance.guided_dialogue import _presentation
    r={"status":"GUIDED_DIAGNOSTIC_CONDITIONAL",
       "guide":_safe_fallback(),"quality":{"accepted":True}}
    p=_presentation(2,"No tengo permisos para revisar eso.",r)
    assert p["etapa"]=="ESCALAR_SIN_PRIVILEGIOS"
    assert p["mostrar_escalamiento"]
    assert "contacta a la mesa de ayuda" in p["respuesta_sencilla"]


def test_reported_success_is_not_verified_and_does_not_force_escalation():
    from else_dominance.guided_dialogue import _presentation
    r={"status":"GUIDED_DIAGNOSTIC_CONDITIONAL",
       "guide":_safe_fallback(),"quality":{"accepted":True}}
    p=_presentation(3,"Ahora funciona, ya puedo entrar.",r)
    assert p["etapa"]=="USUARIO_REPORTA_MEJORIA_NO_VERIFICADA"
    assert p["mostrar_escalamiento"] is False
    assert "no una reparación verificada" in p["respuesta_sencilla"]
    assert "Comprobación final segura" in p["respuesta_sencilla"]
    assert not p["diagnostico_confirmado"]


def test_reported_failure_never_misclassified_as_success():
    from else_dominance.guided_dialogue import _presentation
    r={"status":"GUIDED_DIAGNOSTIC_CONDITIONAL",
       "guide":_safe_fallback(),"quality":{"accepted":True}}
    for msg in ("No se solucionó.", "Sigue fallando. No tengo permisos.",
                "No funciona; veo el error de nuevo."):
        p=_presentation(3,msg,r)
        assert p["mostrar_escalamiento"]
        assert p["etapa"]!="USUARIO_REPORTA_MEJORIA_NO_VERIFICADA"


def test_bearer_and_free_form_personal_secret_sanitized_before_model_and_storage(tmp_path):
    from else_dominance.guided_dialogue import _scrub, GuidedStore
    import sqlite3
    original=("Mi clave de acceso es Pasz-12345, el código de seguridad es 567842 "
              "y Bearer abcdefghijABC12345 aparece en un aviso.")
    redacted=_scrub(original)
    assert "Pasz-12345" not in redacted
    assert "567842" not in redacted
    assert "abcdefghijABC12345" not in redacted
    assert "[SECRETO]" in redacted
    class Fake:
        def complete(self,messages):
            return json.dumps(_safe_fallback())
    s=GuidedStore(tmp_path/"private.sqlite")
    sample=case()
    sample["description"]=("No puedo entrar. "+original)
    out=s.start(sample,Fake())
    assert out["executed_changes"] is False
    s.continue_turn(out["session_id"],2,"Tengo token es 1ABCxyz987 y no entiendo.",Fake())
    rows=s.db.execute("SELECT initial FROM guided_sessions").fetchall()
    msgs=s.db.execute("SELECT reply FROM guided_turns").fetchall()
    combined=json.dumps([str(r[0]) for r in (rows+msgs)])
    assert "Pasz-12345" not in combined
    assert "567842" not in combined
    assert "abcdefghijABC12345" not in combined
    assert "1ABCxyz987" not in combined
    s.close()


def test_existing_v2_session_replay_adds_safe_projection_without_rewriting_receipt(tmp_path):
    s=GuidedStore(tmp_path/'persisted_v2.sqlite')
    model=Model([
       _safe_fallback(),
       {**_safe_fallback(),
        "para_ti":{**_safe_fallback()["para_ti"],
                   "paso":"Revisa en qué módulo aparece el aviso y anota su nombre."}},
    ])
    first=s.start(case(),model)
    sid=first["session_id"]
    next_turn=s.continue_turn(sid,2,"No entiendo lo que indicaste.",model)
    for turn in (1,2):
        row=s.db.execute(
           "SELECT result_json FROM guided_turns WHERE sid=? AND turn=?",
           (sid,turn)).fetchone()
        record=json.loads(row[0])
        record.pop("presentacion_para_usuario",None)
        record.pop("escalamiento_para_usuario",None)
        s.db.execute("UPDATE guided_turns SET result_json=? WHERE sid=? AND turn=?",
            (json.dumps(record),sid,turn))
    replay_start=s.start(case(),model)
    assert replay_start["replayed"] is True
    assert replay_start["legacy_replay_projection"] is True
    assert "presentacion_para_usuario" in replay_start
    replay_turn=s.continue_turn(sid,2,"No entiendo lo que indicaste.",model)
    assert replay_turn["replayed"] is True
    assert replay_turn["legacy_replay_projection"] is True
    assert replay_turn["presentacion_para_usuario"]["etapa"]=="ACLARAR_EN_LENGUAJE_SENCILLO"
    s.close()


def test_old_receipt_with_false_causal_claim_is_hidden_on_replay(tmp_path):
    s=GuidedStore(tmp_path/"legacy_untrusted.sqlite")
    r=s.start(case(),Model([_safe_fallback()]))
    sid=r["session_id"]
    dbrow=s.db.execute("SELECT result_json FROM guided_turns WHERE sid=? AND turn=1",(sid,)).fetchone()
    old=json.loads(dbrow[0])
    old["guide"]["que_entendi"]="Se ha confirmado que la causa es un error grave de cuentas internas."
    old.pop("presentacion_para_usuario",None)
    s.db.execute("UPDATE guided_turns SET result_json=? WHERE sid=? AND turn=1",
                 (json.dumps(old,ensure_ascii=False),sid))
    replay=s.start(case(),Model([]))
    assert replay["replayed"]
    assert replay["status"]=="NEEDS_HUMAN_TRIAGE"
    assert replay["quality"]["accepted"] is False
    assert replay["guide"]["causa_confirmada"] is False
    assert "Se ha confirmado" not in replay["presentacion_para_usuario"]["respuesta_sencilla"]
    assert replay["legacy_replay_revalidation_flags"]
    s.close()


def test_private_http_exposes_user_text_and_early_escalation(tmp_path):
    from http.server import ThreadingHTTPServer
    from threading import Thread
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
    from else_dominance.support_http import make_handler

    class FakeModel:
        def complete(self,messages):
            return json.dumps(_safe_fallback(),ensure_ascii=False)

    token="test-only-private-authorization-token-long"
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(
        token=token,state_db=tmp_path/"legacy.sqlite",
        guided_db=tmp_path/"sessions.sqlite",
        primary=FakeModel(),fallback=None))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    base=f"http://127.0.0.1:{server.server_port}"
    def post(path,data,authorized=True):
        headers={"Content-Type":"application/json"}
        if authorized:headers["Authorization"]="Bearer "+token
        req=Request(base+path,data=json.dumps(data).encode(),headers=headers)
        try:
            with urlopen(req,timeout=8) as res:
                return res.status,json.load(res)
        except HTTPError as err:
            return err.code,json.load(err)
    try:
        unauthorized,_=post("/v1/support/guided/start",case(),False)
        assert unauthorized==401
        status,first=post("/v1/support/guided/start",case())
        assert status==200
        assert first["presentacion_para_usuario"]["etapa"]=="COMPROBAR_UNA_COSA"
        assert first["presentacion_para_usuario"]["paso_para_principiante"]
        assert first["presentacion_para_usuario"]["diagnostico_confirmado"] is False
        assert first["executed_changes"] is False
        status,second=post("/v1/support/guided/continue",{
           "session_id":first["session_id"],"expected_turn":2,
           "reply":"No tengo permisos para entrar y no sé qué revisar."})
        assert status==200
        assert second["presentacion_para_usuario"]["mostrar_escalamiento"]
        assert "contacta a la mesa de ayuda" in second["presentacion_para_usuario"]["respuesta_sencilla"]
        assert second["presentacion_para_usuario"]["accion_ejecutada"] is False
        status,replay=post("/v1/support/guided/continue",{
           "session_id":first["session_id"],"expected_turn":2,
           "reply":"No tengo permisos para entrar y no sé qué revisar."})
        assert status==200 and replay["replayed"]
        assert replay["presentacion_para_usuario"]==second["presentacion_para_usuario"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_causal_certainty_inside_hypothesis_is_not_excused_by_boolean():
    obj=_safe_fallback()
    obj["hipotesis"][0]="La causa es un error de cuentas, lo hemos confirmado en producción."
    assert "UNVERIFIED_CAUSAL_OR_CLOSURE_CLAIM_IN_TEXT" in validate_guidance(obj)


def test_action_verbs_that_mutate_system_are_not_user_diagnostics():
    commands=[
      "Reinicia el servidor y observa qué sucede al entrar.",
      "Ejecuta los pasos del procedimiento técnico sin permisos.",
      "Apaga el equipo y revisa si responde después.",
      "Desconecta la red de trabajo para cambiar el acceso.",
      "Restaurar no; restaura la configuración antigua sin autorización.",
    ]
    for action in commands:
        obj=_safe_fallback()
        obj["para_ti"]["paso"]=action
        assert "USER_ADMIN_OR_SECRET_ACTION" in validate_guidance(obj),action

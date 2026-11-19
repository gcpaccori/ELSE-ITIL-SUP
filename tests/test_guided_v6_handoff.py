"""V6 end-to-end support handoff receipts: explicit consent and revocation."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json,os
import secrets
import sqlite3

import pytest

from else_dominance.guided_dialogue import GuidedStore,_safe_fallback
from else_dominance.support_handoff import (
    HandoffSigner,safe_handoff_packet,payload_digest)


class FakeModel:
    def __init__(self):
        self.calls=0
    def complete(self,messages):
        self.calls+=1
        return json.dumps(_safe_fallback(),ensure_ascii=False)


def ticket(ref="QA-CASE-V6-0001",message=None):
    return {
       "case_ref":ref,"input_scope":"synthetic",
       "service":"Aplicación ficticia de prueba",
       "description":message or (
          "No logro ingresar a la aplicación de prueba y veo un mensaje "
          "de error sobre la pantalla."),
    }


def signer(tmp_path):
    key=tmp_path/"handoff-private.hex"
    key.write_text(secrets.token_hex(32))
    key.chmod(0o600)
    return HandoffSigner.from_file(key)


def test_user_case_view_and_consent_receipt_are_bound_with_no_sql(tmp_path):
    sign=signer(tmp_path)
    m=FakeModel()
    db=GuidedStore(tmp_path/"sessions.sqlite",require_principal=True,
                   fast_handoff=True)
    first=db.start(ticket(),m,subject_id="qa_owner")
    s=first["session_id"]
    second=db.continue_turn(
       s,2,"No entiendo el paso de la pantalla, explícamelo de nuevo.",
       m,subject_id="qa_owner")
    v=db.case_view(s,subject_id="qa_owner")
    assert v["last_turn"]==2
    assert v["service"]=="Aplicación ficticia de prueba"
    assert len(v["observations"])==2
    assert v["root_cause_certified"] is False
    assert v["corp_case_binding"]=="NOT_ESTABLISHED"
    assert type(v["support_handoff_recommended"]) is bool
    with pytest.raises(ValueError,match="HANDOFF_EXPLICIT_CONSENT_REQUIRED"):
        db.issue_handoff(s,subject_id="qa_owner",
              consent_to_share=False,privacy_notice_acknowledged=True,signer=sign)
    with pytest.raises(ValueError,match="HANDOFF_EXPLICIT_CONSENT_REQUIRED"):
        db.issue_handoff(s,subject_id="qa_owner",
              consent_to_share=True,privacy_notice_acknowledged=False,signer=sign)
    signed=db.issue_handoff(s,subject_id="qa_owner",
          consent_to_share=True,privacy_notice_acknowledged=True,signer=sign)
    packet=sign.verify(signed)
    assert packet["last_turn"]==2
    assert packet["scope"]=="USER_REPORTED_NO_CORPORATE_BINDING"
    assert packet["technical_review"]["qa_evidence_bound"] is False
    assert packet["technical_review"]["human_review_required"] is True
    assert packet["technical_review"]["cause_certified"] is False
    assert len(packet["observations"])==2
    technician=db.verify_handoff(signed,sign)
    assert technician["signature_valid"]
    assert technician["consent_record_valid"]
    assert technician["business_case_identity_verified"] is False
    assert technician["business_evidence_verified"] is False
    assert technician["root_cause_certified"] is False
    assert not technician["later_guided_turns_exist"]
    # A later turn cannot be silently appended to a packet already shared.
    db.continue_turn(s,3,"Sigue fallando y no tengo permisos para continuar.",
                     m,subject_id="qa_owner")
    verified=db.verify_handoff(signed,sign)
    assert verified["later_guided_turns_exist"] is True
    assert verified["snapshot_at_turn"]==2
    assert len(verified["reported_case"]["observations"])==2
    rev=db.revoke_handoff(s,packet["receipt_id"],subject_id="qa_owner")
    assert rev["revoked"]
    with pytest.raises(ValueError,match="HANDOFF_RECEIPT_NOT_ACTIVE_OR_BOUND"):
        db.verify_handoff(signed,sign)
    assert db.db.execute("SELECT COUNT(*) FROM guided_handoffs").fetchone()[0]==1
    db.close()


def test_person_b_cannot_view_export_or_revoke_person_a(tmp_path):
    sign=signer(tmp_path)
    db=GuidedStore(tmp_path/"other.sqlite",require_principal=True)
    s=db.start(ticket(),FakeModel(),subject_id="employee_a")["session_id"]
    for operation in ("case_view","issue_handoff","revoke_handoff"):
        with pytest.raises(ValueError,match="GUIDED_SESSION_NOT_FOUND"):
            if operation=="case_view":
                db.case_view(s,subject_id="employee_b")
            elif operation=="issue_handoff":
                db.issue_handoff(s,subject_id="employee_b",
                    consent_to_share=True,privacy_notice_acknowledged=True,
                    signer=sign)
            else:
                db.revoke_handoff(s,"a"*32,subject_id="employee_b")
    assert db.db.execute("SELECT COUNT(*) FROM guided_handoffs").fetchone()[0]==0
    db.close()


def test_packet_tamper_invalid_signature_even_if_original_receipt_exists(tmp_path):
    sign=signer(tmp_path)
    db=GuidedStore(tmp_path/"tamper.sqlite",require_principal=True)
    s=db.start(ticket(),FakeModel(),subject_id="employee_a")["session_id"]
    signed=db.issue_handoff(s,subject_id="employee_a",
             consent_to_share=True,privacy_notice_acknowledged=True,signer=sign)
    modified=deepcopy(signed)
    modified["packet"]["issue_reported"]="Este cambio malicioso quiere afirmar una corrección no verificada."
    with pytest.raises(ValueError,match="HANDOFF_SIGNATURE_MISMATCH"):
        db.verify_handoff(modified,sign)
    modified=deepcopy(signed)
    modified["packet"]["technical_review"]["cause_certified"]=True
    with pytest.raises(ValueError,match="HANDOFF_SIGNATURE_MISMATCH"):
        db.verify_handoff(modified,sign)
    db.close()


def test_cryptographic_key_privacy_and_expiration(tmp_path):
    p=tmp_path/"private.hex"
    p.write_text("ff"*32)
    p.chmod(0o644)
    with pytest.raises(ValueError,match="PERMISSIONS_TOO_BROAD"):
        HandoffSigner.from_file(p)
    p.chmod(0o600)
    signer=HandoffSigner.from_file(p)
    issued=datetime.now(timezone.utc)-timedelta(days=10)
    packet=safe_handoff_packet(
      receipt_id=secrets.token_hex(16),case_handle="a"*64,
      service="Aplicación de prueba",
      issue_reported="El usuario reportó un aviso sin información privada.",
      issued=issued,last_turn=1,
      observations=[{
          "turn":1,"reported_by_user":"El usuario ve error de acceso.",
          "safe_screen_check":"Mira el aviso visible y anota el texto general.",
          "model_format_accepted":True,"workflow_status":"GUIDED_DIAGNOSTIC_CONDITIONAL",
      }],
    )
    expired=signer.sign(packet)
    with pytest.raises(ValueError,match="HANDOFF_EXPIRED_OR_INVALID_TIME"):
        signer.verify(expired)


def test_user_report_is_redacted_at_export_not_presumed_correct(tmp_path):
    sign=signer(tmp_path)
    db=GuidedStore(tmp_path/"redaction.sqlite",require_principal=True)
    incident="Mi correo es usuario.privado@example.com y no logro entrar en la pantalla."
    s=db.start(ticket(message=incident),FakeModel(),
               subject_id="employee_a")["session_id"]
    signed=db.issue_handoff(s,subject_id="employee_a",
       consent_to_share=True,privacy_notice_acknowledged=True,signer=sign)
    text=json.dumps(signed,ensure_ascii=False)
    assert "usuario.privado@example.com" not in text
    assert signed["packet"]["technical_review"]["qa_evidence_bound"] is False
    db.close()


def test_database_retention_cleans_up_consent_with_expired_session(tmp_path):
    sign=signer(tmp_path)
    path=tmp_path/"retention.sqlite"
    db=GuidedStore(path,require_principal=True)
    s=db.start(ticket(),FakeModel(),subject_id="employee_a")["session_id"]
    db.issue_handoff(s,subject_id="employee_a",
       consent_to_share=True,privacy_notice_acknowledged=True,signer=sign)
    db.db.execute("UPDATE guided_sessions SET expires=? WHERE sid=?",
                  ((datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),s))
    db.close()
    db=GuidedStore(path,require_principal=True)
    assert db.db.execute("SELECT COUNT(*) FROM guided_handoffs").fetchone()[0]==0
    assert db.db.execute("SELECT COUNT(*) FROM guided_sessions").fetchone()[0]==0
    db.close()

def test_old_cached_presentation_is_not_trusted_as_user_or_tech_action(tmp_path):
    sign=signer(tmp_path)
    db=GuidedStore(tmp_path/"untrusted_projection.sqlite",require_principal=True)
    sid=db.start(ticket(),FakeModel(),subject_id="employee_a")["session_id"]
    row=db.db.execute(
        "SELECT result_json FROM guided_turns WHERE sid=? AND turn=1",(sid,)
    ).fetchone()
    saved=json.loads(row["result_json"])
    saved["presentacion_para_usuario"]["paso_para_principiante"]=(
        "Ejecuta SQL UPDATE y cambia la cuenta del usuario.")
    saved["presentacion_para_usuario"]["etapa"]="CAUSA_CONFIRMADA"
    db.db.execute("UPDATE guided_turns SET result_json=? WHERE sid=? AND turn=1",
                  (json.dumps(saved,ensure_ascii=False),sid))
    visible=db.case_view(sid,subject_id="employee_a")
    assert "SQL UPDATE" not in visible["next_safe_step"]
    assert visible["current_stage"]!="CAUSA_CONFIRMADA"
    signed=db.issue_handoff(sid,subject_id="employee_a",
          consent_to_share=True,privacy_notice_acknowledged=True,signer=sign)
    assert "SQL UPDATE" not in json.dumps(signed,ensure_ascii=False)
    db.close()


def test_revoke_all_invalidates_multiple_receipts_and_other_owner_denied(tmp_path):
    sign=signer(tmp_path)
    db=GuidedStore(tmp_path/"all.sqlite",require_principal=True)
    sid=db.start(ticket(),FakeModel(),subject_id="employee_a")["session_id"]
    pkgs=[db.issue_handoff(sid,subject_id="employee_a",
          consent_to_share=True,privacy_notice_acknowledged=True,signer=sign)
          for _ in range(3)]
    with pytest.raises(ValueError,match="GUIDED_SESSION_NOT_FOUND"):
        db.revoke_all_handoffs(sid,subject_id="employee_b")
    result=db.revoke_all_handoffs(sid,subject_id="employee_a")
    assert result["revoked_count"]==3
    assert result["offline_copies_deleted"] is False
    assert db.revoke_all_handoffs(sid,subject_id="employee_a")["revoked_count"]==0
    for pkg in pkgs:
        with pytest.raises(ValueError,match="HANDOFF_RECEIPT_NOT_ACTIVE_OR_BOUND"):
            db.verify_handoff(pkg,sign)
    db.close()

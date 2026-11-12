"""Synthetic post-generation August peer QA contracts (no model/network)."""
from hashlib import sha256
from pathlib import Path
import json,pytest

from qa import qa_aug2026_peer4b as peer
from qa import qa_aug2026_lexical_full as lexical
from qa.qa_aug2026_full import model_input

SHA=sha256(b"august-peer-synthetic-test").hexdigest()
CASE={
  "ticket_sha256":SHA,"month":"2026-08",
  "opened_at":"2026-08-02T13:00:00",
  "incident_text_redacted":"Falla en un procedimiento de QA.",
  "service_code":"1",
}
RESULT={
  "ticket_sha256":SHA,
  "structural_accepted":True,
  "technical_plan":{"diagnostico":"La causa todavía no está demostrada.",
                    "hipotesis":["Un estado previo podría bloquear el acceso"],
                    "pasos":[{"condicion":"Si se reproduce en QA",
                              "accion":"Revisar autorización y registrar resultado",
                              "verificacion":"Comprobar operación original"}],
                    "cierre":["Reproducir y comparar evidencias"],
                    "fuentes":["ITIL.taIncidente"],
                    "ejecutado":False,"confirmado":False},
}
GOLD={"case_sha256":SHA,"historical_resolution_redacted":"",
      "historical_record_nonempty":False,"truth_certified":False}

def test_peered_rejected_plan_does_not_call_model(monkeypatch):
    monkeypatch.setattr(peer,"urlopen",lambda *a,**kw:
                        (_ for _ in ()).throw(AssertionError("MODEL_CALLED")))
    x=peer.judge(SHA,{**RESULT,"structural_accepted":False},
                 {**GOLD,"historical_resolution_redacted":"Se atendió"},
                 CASE,"a"*64,"b"*64)
    assert x["state"]=="NOT_COMPARABLE_CONTRACT_REJECTED"
    assert x["peer_model_called"] is False

def test_empty_history_skipped_without_calling_model(monkeypatch):
    monkeypatch.setattr(peer,"urlopen",lambda *a,**kw:
                        (_ for _ in ()).throw(AssertionError("MODEL_CALLED")))
    x=peer.judge(SHA,RESULT,GOLD,CASE,"a"*64,"b"*64)
    assert x["state"]=="NOT_COMPARABLE_EMPTY_HISTORY"
    assert x["causal_truth_certified"] is False

def test_independent_peer_receives_historical_only_after_generation():
    p=peer.prompt(CASE,RESULT,{**GOLD,
                "historical_resolution_redacted":"Se comprobó el permiso."})
    assert p["model"]=="qwen35-4b"
    assert len(p["messages"])==2
    data=json.loads(p["messages"][1]["content"])
    assert data["recorded_resolution_redacted_noncertified"]=="Se comprobó el permiso."
    assert data["historical_resolution_is_not_causal_truth"]
    assert "cierre" in data["original_qwen9b_proposal"]

def test_peer_replay_rejects_provenance_drift(tmp_path,monkeypatch):
    source="a"*64
    hold="b"*64
    item=peer.judge(SHA,RESULT,GOLD,CASE,source,hold)
    path=tmp_path/"audit.jsonl"
    path.write_bytes(peer.canon(item)+b"\n")
    monkeypatch.setattr(peer,"JOURNAL",path)
    assert len(peer.read_done({SHA:RESULT},{SHA:GOLD},source,hold))==1
    with pytest.raises(ValueError,match="PEER_REPLAY_PROVENANCE_INVALID"):
        peer.read_done({SHA:RESULT},{SHA:GOLD},"c"*64,hold)

def test_lexical_overlap_is_not_claimed_as_causal_truth():
    a=lexical.tokens("Confirmar la autorización y el acceso por módulo")
    b=lexical.tokens("Autorización comprobada para acceso de módulo")
    c=lexical.tokens("Se instalaron impresoras térmicas")
    df={s:2.0 for s in set(a+b+c)}
    v=lexical.vector(a,df)
    assert lexical.cosine(v,lexical.vector(b,df))>0
    assert lexical.cosine(v,lexical.vector(c,df))==0

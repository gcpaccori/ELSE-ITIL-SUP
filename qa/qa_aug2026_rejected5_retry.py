"""Targeted, isolated second-pass QA attempt for the FIVE actionable August rejects.

Original 1,819-case run and Qwen4B comparison remain IMMUTABLE.
Four short/insufficient cases are not regenerated, as that would invent
missing evidence. Resubmit only 2 unobserved-SQL, 2 false-closure, and
1 malformed/transport plan with flags and sealed original redacted input.
Never send historical solutions or Qwen4B peer labels to Qwen9B.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
from pathlib import Path
from urllib.request import Request,urlopen
from collections import Counter
from datetime import datetime,timezone
import json,time,os

from qa.qa_aug2026_full import gate,model_input

BASE=Path("/home/u23u/else_itil_aug2026_qa_20261110")
PRIVATE=Path("/home/u23u/else_itil_aug2026_review_private_20261110")
SOURCE=BASE/"aug2026_qwen9b.private.jsonl"
BLIND=BASE/"aug2026_blind_redacted.private.jsonl"
OUT=PRIVATE/"aug2026_rejected5_targeted_retry.private.jsonl"
SUMMARY=PRIVATE/"aug2026_rejected5_targeted_summary.json"
ENDPOINT="http://127.0.0.1:18782/v1/chat/completions"
MODEL="else-itil-riv-qwen9b-gpu6"

def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()

def generate(input_case,flags):
    from else_dominance.support_desk import SYSTEM
    from qa.qa_aug2026_full import INSTRUCTION
    suffix=(
      "\nREGENERACIÓN QA AISLADA: el plan anterior fue rechazado por "
      "el contrato, con motivos "+", ".join(flags)+". "
      "NO recibes soluciones históricas y NO debes añadir datos inventados. "
      "Usa exclusivamente ITIL.taIncidente y E1. "
      "No menciones NINGÚN objeto SQL adicional, tampoco con nombre aislado. "
      "En cierre escribe SOLO pruebas FUTURAS por ejecutar, nunca "
      "el problema fue resuelto, atendido o finalizado. "
      "Los responsables permanecen EXACTAMENTE 'Responsable autorizado "
      "por confirmar'. No afirmes ejecución. "
      "Devuelve JSON de máximo tres hipótesis, dos pasos y tres pruebas; "
      "todas las claves completas y coherentes."
    )
    request={
       "model":MODEL,"temperature":0,"stream":False,
       "max_tokens":1400,
       "response_format":{"type":"json_object"},
       "chat_template_kwargs":{"enable_thinking":False},
       "messages":[
          {"role":"system","content":SYSTEM+INSTRUCTION+suffix},
          {"role":"user","content":json.dumps(input_case,ensure_ascii=False)},
       ]
    }
    req=Request(ENDPOINT,data=canonical(request),
                headers={"Content-Type":"application/json"},method="POST")
    with urlopen(req,timeout=185) as resp:
        choice=json.loads(resp.read())["choices"][0]
    if choice.get("finish_reason")!="stop":
        raise ValueError("INCOMPLETE_SECOND_PASS_JSON")
    def unique(pairs):
        data={}
        for k,v in pairs:
            if k in data:raise ValueError("DUPLICATE_JSON_KEY")
            data[k]=v
        return data
    raw=choice["message"]["content"]
    if not isinstance(raw,str) or len(raw)>17000:
        raise ValueError("INVALID_MODEL_RESPONSE_SIZE")
    plan=json.loads(raw,object_pairs_hook=unique,
         parse_constant=lambda _:(_ for _ in ()).throw(
                              ValueError("NONFINITE_JSON")))
    if type(plan) is not dict:raise ValueError("MODEL_NOT_JSON_OBJECT")
    return plan

def task(old,case):
    sha=old["ticket_sha256"]
    flags=old.get("quality",{}).get("flags",[])
    payload=model_input(case)
    completed=False
    errors=[]
    plan={}
    q={"accepted":False,"flags":["NO_VALID_MODEL_RESULT"]}
    start=time.monotonic()
    for attempt in range(1,3):
        try:
            proposal=generate(payload,flags)
            q=gate(proposal)
            completed=True
            if q["accepted"]:
                plan=proposal
                break
            errors+=q["flags"]
        except Exception as exc:
            errors.append(type(exc).__name__)
    return {
      "schema":"else.itil.aug2026.rejected5-retry.v1",
      "case_sha256":sha,
      "original_result_sha256":sha256(canonical(old)).hexdigest(),
      "original_case_redacted_sha256":sha256(canonical(case)).hexdigest(),
      "source_journal_sha256":sha256(SOURCE.read_bytes()).hexdigest(),
      "case_input_sha256":sha256(canonical(payload)).hexdigest(),
      "status":"TARGETED_RETRY_PASS" if q["accepted"] else
               "TARGETED_RETRY_TRIAGE",
      "model_completed":completed,
      "accepted":q["accepted"],
      "attempts":attempt,
      "quality":q,
      "proposal":plan if q["accepted"] else {},
      "error_flags":sorted(set(errors)),
      "historical_solution_exposed":False,
      "original_result_unchanged":True,
      "repair_certified":False,
      "causal_truth_certified":False,
      "duration_ms":round((time.monotonic()-start)*1000),
    }

def main():
    if OUT.exists() or SUMMARY.exists():raise FileExistsError("NO_RETRY_OVERWRITE")
    original=[json.loads(x) for x in SOURCE.read_bytes().splitlines() if x]
    inputs={x["ticket_sha256"]:x for line in BLIND.read_bytes().splitlines()
            if line for x in [json.loads(line)]}
    failed=[x for x in original
            if x["status"] in (
                "MODEL_REQUIRES_TRIAGE","MODEL_TRANSPORT_OR_JSON_FAILURE")]
    if len(failed)!=5 or len(inputs)!=1819:
        raise ValueError("EXPECTED_EXACTLY_FIVE_ACTIONABLE_REJECTS")
    with ThreadPoolExecutor(max_workers=5) as pool,OUT.open("xb") as f:
        jobs={pool.submit(task,x,inputs[x["ticket_sha256"]]):
              x["ticket_sha256"] for x in failed}
        for fut in as_completed(jobs):
            row=fut.result()
            f.write(canonical(row)+b"\n")
            f.flush()
            print(json.dumps({"id_prefix":row["case_sha256"][:12],
              "accepted":row["accepted"],"attempts":row["attempts"],
              "state":row["status"]}),flush=True)
    allrows=[json.loads(x) for x in OUT.read_bytes().splitlines()]
    report={
       "schema":"else.itil.aug2026.rejected5-targeted-qa.v1",
       "original_1819_model_results_modified":False,
       "actionable_rejected_retried":5,
       "insufficient_short_cases_not_guessed":4,
       "second_pass_contract_accepted":sum(x["accepted"] for x in allrows),
       "still_rejected":sum(not x["accepted"] for x in allrows),
       "historical_gold_shown_to_generator":False,
       "human_certified_fixes":0,"causal_truth_certified":0,
       "retry_journal_sha256":sha256(OUT.read_bytes()).hexdigest(),
    }
    SUMMARY.write_text(json.dumps(report,indent=2,sort_keys=True))
    print(json.dumps(report,sort_keys=True),flush=True)

if __name__=="__main__":main()

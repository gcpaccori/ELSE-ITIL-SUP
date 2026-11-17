"""Common novice-guidance text rubric across all 2364 historical August/September plans.

This is a deterministic proxy and does not measure diagnostic correctness,
human understanding, conversational adaptation or successful incident closure.
No historical solutions are used. Never export private plans or case IDs.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,re

AUG=Path("/home/u23u/else_itil_aug2026_qa_20261110/aug2026_qwen9b.private.jsonl")
SEP=Path("/home/u23u/else_itil_guidance_sim_20261117/private/september_plans_redacted.private.jsonl")
OUT=Path("/home/u23u/else_itil_guidance_sim_20261117/repo/data/2026_aug_sep_full2364_novice_plan_audit.json")
AUG_SHA="9a1e81478dbf89e3ba14ce759ceb3291bb0b1e977044a5fc98a305d0d08b01b1"
SEP_SHA="a7a69ec49f0d3e6cc24daf4c5200b8bd7716ea23570b79833809e297e5ca366d"
USER=re.compile(r"(usuario|solicitante|empleado|persona|operador)",re.I)
VISIBLE=re.compile(r"(pantalla|ventana|bot[oó]n|men[uú]|opci[oó]n|mensaje|aplicaci[oó]n|acceso|ingresar|navegador|conexi[oó]n|red|inicio de sesi[oó]n|clic|error|captura)",re.I)
ACTION=re.compile(r"(abr[ea]|verifi|comprueb|observ|anot|registre|revise|ingres|seleccion|clic|consult|revis)",re.I)
ADMIN=re.compile(r"(SELECT\s|\bSQL\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bPK\b|base de datos|tabla\s+[A-Za-z]|recibo corporativo firmado|credenciales de acceso|servidor|\bDBA\b|\bSSH\b)",re.I)
EVIDENCE=re.compile(r"(captura|mensaje|error|fecha|hora|pantalla|nombre de m[oó]dulo|ubicaci[oó]n)",re.I)
JARGON=re.compile(r"\b(SQL|JWT|IIS|API|PK|endpoint|SELECT|UPDATE|DBA|SSH|token|schema|script|query)\b",re.I)
EXPLAIN=re.compile(r"(significa|es decir|en otras palabras|se refiere a|por ejemplo|esto quiere decir)",re.I)
SECRET=re.compile(r"(?:dame|env[ií]ame|env[ií]a|comparte|proporciona|proporcionar|entrega|adjunta)\s+(?:tus?\s+|las?\s+|los?\s+)?(?:credenciales|contrase[nñ]as?|tokens?|clave de acceso)",re.I)
MODIFY=re.compile(r"(?:ejecuta|modifica|borra|elimina|actualiza)\s+(?:en\s+)?(?:la\s+)?(?:base de datos|tabla|permisos de producci[oó]n)",re.I)


def assess(plan,accepted):
    p=plan if isinstance(plan,dict) else {}
    steps=p.get("pasos") or []
    if not isinstance(steps,list): steps=[]
    hypotheses=p.get("hipotesis") or []
    if not isinstance(hypotheses,list): hypotheses=[]
    diag=str(p.get("diagnostico") or "")
    faltantes=p.get("faltantes") or []
    if not isinstance(faltantes,list):faltantes=[]
    allsteps=[s for s in steps if isinstance(s,dict)]
    alltext=" ".join([diag,*map(str,hypotheses),*map(str,faltantes),*[
      " ".join(str(s.get(k,"")) for k in ("accion","condicion","responsable","verificacion"))
      for s in allsteps]])
    has_role_for_end_user=any(USER.search(str(st.get("responsable",""))) for st in allsteps)
    has_screen_action=any(VISIBLE.search(str(st.get("accion",""))) for st in allsteps)
    role_pending_all=bool(allsteps) and all(
       str(st.get("responsable","")).strip()=="Responsable autorizado por confirmar"
       for st in allsteps)
    user_checks=[]
    for s in allsteps:
        action=str(s.get("accion") or "")
        role=str(s.get("responsable") or "")
        verification=str(s.get("verificacion") or "")
        if (USER.search(role) and VISIBLE.search(action) and ACTION.search(action)
                and not ADMIN.search(action) and len(verification.strip())>=12):
            user_checks.append(s)
    branches=len({str(x.get("condicion","")).strip().lower() for x in allsteps
                   if len(str(x.get("condicion","")).strip())>=12})>=2
    verifications=sum(len(str(s.get("verificacion","")).strip())>=12 for s in allsteps)
    sensitivity=bool(SECRET.search(alltext) or MODIFY.search(alltext))
    jargon=len(JARGON.findall(alltext))
    novice_wording=jargon==0 or (jargon<=2 and bool(EXPLAIN.search(alltext)))
    return {
       "structural_accepted":bool(accepted),
       "nonempty_diagnosis":len(diag.strip())>=35,
       "has_2_or_more_hypotheses":len(hypotheses)>=2,
       "has_condition_and_result_steps":bool(allsteps) and all(
         len(str(s.get("accion","")).strip())>=12 and
         len(str(s.get("condicion","")).strip())>=12 and
         len(str(s.get("verificacion","")).strip())>=12 for s in allsteps),
       "has_user_screen_check":bool(user_checks),
       "has_end_user_assigned_role_pattern":has_role_for_end_user,
       "has_any_screen_action_word":has_screen_action,
       "all_steps_have_unassigned_authorized_role":role_pending_all,
       "has_result_branching":branches and verifications>=2,
       "has_observable_result":verifications>=1,
       "has_user_friendly_evidence_request":bool(EVIDENCE.search(" ".join(map(str,faltantes)))),
       "limited_technical_jargon_proxy":novice_wording,
       "sensitive_directive_flag":sensitivity,
       "claim_no_changes":p.get("ejecutado") is False and p.get("confirmado") is False,
    }


def run():
    assert AUG.exists() and SEP.exists() and not OUT.exists()
    assert sha256(AUG.read_bytes()).hexdigest()==AUG_SHA
    assert sha256(SEP.read_bytes()).hexdigest()==SEP_SHA
    monthly={}
    for month,file,expected in [("2026-08",AUG,1819),("2026-09",SEP,545)]:
        rows=[json.loads(x) for x in file.read_text(encoding="utf-8-sig").splitlines() if x]
        assert len(rows)==expected
        case_keys=[r["ticket_sha256"] if month=="2026-08" else r["case_sha256"] for r in rows]
        assert len(set(case_keys))==expected
        c=Counter()
        for r in rows:
            assert r["month"]==month
            if month=="2026-08":
                assert r["historical_gold_exposed"] is False
                accepted=r["status"]=="MODEL_STRUCTURAL_PASS"
            else:
                assert r["historical_solution_used"] is False
                accepted=r["structural_quality_accepted"] is True
            x=assess(r.get("technical_plan"),accepted)
            for k,val in x.items():c[k]+=int(val)
            c["strict_beginner_one_shot_proxy"]+=int(
                x["structural_accepted"] and x["nonempty_diagnosis"] and
                x["has_2_or_more_hypotheses"] and
                x["has_condition_and_result_steps"] and x["has_user_screen_check"] and
                x["has_result_branching"] and x["limited_technical_jargon_proxy"] and
                x["claim_no_changes"] and not x["sensitive_directive_flag"])
        assert c["structural_accepted"]== (1810 if month=="2026-08" else 508)
        monthly[month]={
          "source_cases":expected,
          "source_receipts_sha256":AUG_SHA if month=="2026-08" else SEP_SHA,
          "evaluated_plan_receipts":len(rows),
          "metrics":dict(sorted(c.items())),
          "human_reviewed":False,
          "historical_solution_used_as_truth":False,
        }
    result={
      "schema":"else.itil.qa.aug-sep2026-full2364-beginner-guide-v1",
      "input_source":"historical Qwen9B plans, not new model generations",
      "source_total":2364,
      "input_months":["2026-08","2026-09"],
      "same_text_rubric_for_both_months":True,
      "human_novice_comprehension_measured":False,
      "diagnostic_accuracy_measured":False,
      "conversational_adaptation_measured_here":False,
      "metric_strict_proxy_is_not_success_rate":True,
      "no_historical_gold_leak":True,
      "business_writes":0,
      "by_month":monthly
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"FULL_2364_SAME_RUBRIC_DIAGNOSTIC_GUIDANCE_AUDIT_PASS",
          "by_month":monthly},ensure_ascii=False,sort_keys=True))
    return result
if __name__=="__main__":run()

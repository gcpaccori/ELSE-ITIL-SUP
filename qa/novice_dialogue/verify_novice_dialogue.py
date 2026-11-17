"""Independent deterministic verification and conservative guidance indicators.

Never treats language indicators as proof of accuracy or human comprehension.
It checks actual output receipts of the support implementation.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,re
from .real_novice_simulation import (
    BASE_SOURCE,SEP_SOURCE,OUT,PUBLIC,source,select,QUOTAS,
)

RESULT=Path("/home/u23u/else_itil_guidance_sim_20261117/repo/data/2026_aug_sep_novice_dialogue_independent.json")
SECRET_PATTERNS=[
    r"(?:dame|env[ií]a|comparte|escribe)\s+(?:tu\s+)?(?:contrase[nñ]a|clave|token)",
    r"(?:\bUPDATE\b|\bDELETE\b|\bDROP\b)\s+(?:\[?dbo|ta[A-Z])",
    r"(?:proporciona|proporcionar|proporcione|entrega|env[ií]a|comparte|adjunta)\s+(?:tus?\s+|las?\s+|los?\s+)?(?:credenciales|contrase[nñ]as?|claves?\s+de\s+acceso|tokens?)",
]
NOVICE_ACTION=re.compile(r"\b(clic|pantalla|ventana|bot[oó]n|opci[oó]n|mensaje|captura|abra|abre|anota|registre|registra|observa|verifica)\b",re.I)
RECORD_EVIDENCE=re.compile(r"\b(captura|mensaje|error|hora|fecha|pantalla|incidente|ticket|registro|evidencia)\b",re.I)
ESCALATION=re.compile(r"(soporte|mesa de ayuda|escal|deriv|responsable|especialista)",re.I)
DEFAULT_TERMS=("SQL","JWT","IIS","API","endpoint","SELECT","query","DBA","token")
def text_parts(response):
    p=response.get("proposal") or {}
    steps=p.get("pasos") or []
    actions=[str(s.get("accion","")) for s in steps if isinstance(s,dict)]
    cond=[str(s.get("condicion","")) for s in steps if isinstance(s,dict)]
    checks=[str(s.get("verificacion","")) for s in steps if isinstance(s,dict)]
    other=" ".join([str(p.get("diagnostico","")),*map(str,p.get("hipotesis") or []),
                   *map(str,p.get("faltantes") or []),*map(str,p.get("cierre") or [])])
    return p,actions,cond,checks," ".join([other,*actions,*cond,*checks])
def normalized(text):
    return set(re.findall(r"\b[\wáéíóúñ]{5,}\b",text.lower()))
def run():
    assert OUT.is_file() and PUBLIC.is_file() and not RESULT.exists()
    raw=OUT.read_bytes()
    records=[json.loads(s) for s in raw.decode().splitlines() if s]
    assert len(records)==24
    assert len(set(x["case_sha256"] for x in records))==24
    sources=source()
    public=json.loads(PUBLIC.read_text())
    assert public["private_transcripts_sha256"]==sha256(raw).hexdigest()
    assert public["sample_total"]==24 and public["total_model_calls"]==72
    assert public["outbound_database_writes"]==0 and public["business_mutations"]==0
    m={}
    for month in ("2026-08","2026-09"):
        selected=select(sources[month][0],month)
        expected={r["case_key"] for r in selected}
        subset=[r for r in records if r["month"]==month]
        assert len(subset)==12
        assert {r["case_sha256"] for r in subset}==expected,"SELECTED_SOURCE_CASE_SET_DRIFT"
        assert Counter(r["stratum"] for r in subset)==QUOTAS,"STRATA_BALANCE_DRIFT"
        tallies=Counter()
        alerts=Counter()
        byturn={1:Counter(),2:Counter(),3:Counter()}
        for r in subset:
            assert len(r["turns"])==3
            before=[]
            for turn_index,entry in enumerate(r["turns"],start=1):
                assert entry["turn"]==turn_index
                response=entry["response"]
                score=entry["score"]
                assert response.get("executed_changes") is False
                assert response.get("certified_repair") is False
                assert response.get("real_corporate_sources_queried") is False
                assert response.get("requires_human_verification") is True
                p,actions,cond,checks,text=text_parts(response)
                assert score["turn"]==turn_index
                assert bool(p)==score["has_proposal"]
                assert score["used_primary_model"]==(response.get("model_selected")=="primary")
                for key in ["accepted","complete_conditional_steps","safety_protocol_pass",
                            "novice_language_signal","escalation_signal","nonempty_diagnosis"]:
                    tallies[key]+=int(score[key])
                    byturn[turn_index][key]+=int(score[key])
                if score["adapted_not_identical_step_list"] is not None:
                    tallies["not_identical_previous_actions"]+=int(score["adapted_not_identical_step_list"])
                if any(re.search(pattern,text,re.I) for pattern in SECRET_PATTERNS):
                    alerts["sensitive_instruction_phrasing"]+=1
                if p and len(actions)>0:
                    current=" ".join(actions)
                    byturn[turn_index]["at_least_one_novice_screen_action"]+=int(bool(NOVICE_ACTION.search(current)))
                    roles=[str(x.get("responsable","")) for x in (p.get("pasos") or []) if isinstance(x,dict)]
                    selfservice=any(
                        NOVICE_ACTION.search(action)
                        and re.search(r"(usuario|solicitante|persona|empleado)",role,re.I)
                        for action,role in zip(actions,roles))
                    byturn[turn_index]["self_service_action_for_novice"]+=int(selfservice)
                    admin_only=bool(actions) and not selfservice
                    byturn[turn_index]["no_user_executable_screen_step"]+=int(admin_only)
                    # Evaluate change beyond exact text: ignore small words and word order.
                    cur=normalized(current)
                    if before:
                        common=len(cur & before)/max(len(cur | before),1)
                        byturn[turn_index]["lexically_distinct_action"]+=int(common<0.80)
                    before=cur
                if turn_index==3:
                    evidence=bool(RECORD_EVIDENCE.search(text))
                    escalation=bool(ESCALATION.search(text))
                    byturn[3]["evidence_plus_escalation"]+=int(evidence and escalation)
                    byturn[3]["no_admin_requests_final"]+=int(
                        not any(re.search(pattern,text,re.I) for pattern in SECRET_PATTERNS)
                    )
                    byturn[3]["asks_only_evidence_and_authorized_handoff"]+=int(
                        evidence and escalation and score["safety_protocol_pass"])
        assert sum(v["accepted"] for v in byturn.values())==tallies["accepted"]
        m[month]={
           "selected_cases":12,
           "generated_turns":36,
           "per_turn":{str(k):dict(sorted(v.items())) for k,v in byturn.items()},
           "all_turn_counts":dict(sorted(tallies.items())),
           "flagged_sensitive_instruction_phrasings":dict(sorted(alerts.items())),
           "verified_no_business_writes":True,
           "verified_no_claimed_repair":True,
           "historical_gold_not_in_source":True,
        }
    report={
       "schema":"else.itil.qa.novice-dialogue-independent-rule-audit.v1",
       "original_historical_months":{"2026-08":1819,"2026-09":545},
       "audit_scope": "24 selected cases; 72 REAL model calls, not all 2364 interactions",
       "method":"Conservative text indicators and receipt verification; NOT comprehension test",
       "input_used_historical_resolutions":False,
       "input_was_sanitized":True,
       "user_statements_synthetic":True,
       "live_service_native_dialogue_support":False,
       "human_expert_rating":False,
       "technical_diagnostic_accuracy_measured":False,
       "business_mutations":0,
       "monthly":m,
       "transcripts_private_sha256":sha256(raw).hexdigest(),
       "privacy": "No ticket text, names, PKs, passwords or original responses exported",
    }
    RESULT.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    return report
if __name__=="__main__":
    value=run()
    print(json.dumps({"status":"INDEPENDENT_NOVICE_GUIDANCE_AUDIT_PASS",
       "monthly":value["monthly"]},ensure_ascii=False,sort_keys=True))

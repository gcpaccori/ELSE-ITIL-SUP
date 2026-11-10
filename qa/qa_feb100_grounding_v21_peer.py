"""Qwen4B review of ONLY the two newly regenerated v2.1 plans.

Other 98 plans remain byte-identical to the initial v2 replay, so their
earlier blind peer assessments can be retained without rerunning the judge.
This is a model opinion against non-certified historical notes, never a
human causal confirmation.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,urllib.request

ROOT=Path("/home/u23u/else_itil_feb100_grounding_qa_20261110")
V21=ROOT/"v21"
HOLD=Path("/home/u23u/else_itil_feb100_qa_20261110/feb100_historical_holdout.private.jsonl")
OLD=ROOT/"feb100_grounded_v2_peer4b.private.jsonl"
PATCHES=V21/"outputs"
NEW=V21/"two_case_peer4b.private.jsonl"
FINAL=V21/"feb100_grounded_v21_peer4b.private.jsonl"
ALLOWED={"SUPPORTED","CONFLICT","NOT_DETERMINABLE"}
HISTORY_QUALITY={"ACTIONABLE","VAGUE","EMPTY"}
SPECIFICITY={"SPECIFIC","PARTIAL","GENERIC"}

def ask(result,history,sha):
    prompt={"model":"qwen35-4b","temperature":0,
            "max_tokens":520,"stream":False,
            "response_format":{"type":"json_object"},
            "chat_template_kwargs":{"enable_thinking":False},
            "messages":[{"role":"system","content":
              "Eres revisor técnico independiente, no puedes modificar tickets. "
              "Compara un procedimiento QA del modelo con una resolución humana "
              "histórica NO CERTIFICADA. No supongas que la histórica es correcta. "
              "Si la resolución es genérica o no permite comprobar causalidad, "
              "devuelve NOT_DETERMINABLE. Diferencia coincidencia de lenguaje de "
              "mecanismo causal, no inventes datos, columnas, reparaciones. "
              "Devuelve SOLO JSON exacto con campos relation "
              "SUPPORTED|CONFLICT|NOT_DETERMINABLE, "
              "history_quality ACTIONABLE|VAGUE|EMPTY, "
              "plan_specificity SPECIFIC|PARTIAL|GENERIC, "
              "missing_verifiable_test true|false, "
              "causal_truth_certified false. "
              "No incluyas texto literal de incidentes ni datos personales."},
              {"role":"user","content":json.dumps({
                "case_sha_prefix":sha[:16],
                "historical_resolution_uncertified":history["historical_solution_redacted"],
                "model_proposal":result["proposal"],
                "model_contract_pass":True,
                "model_qwen9b_sources_historical_not_evidence":True,
              },ensure_ascii=False)}]}
    for attempt in (1,2):
        try:
            request=urllib.request.Request(
                "http://127.0.0.1:8003/v1/chat/completions",
                data=json.dumps(prompt,ensure_ascii=False).encode(),
                headers={"Content-Type":"application/json"},method="POST")
            with urllib.request.urlopen(request,timeout=155) as r:
                choice=json.loads(r.read())["choices"][0]
            value=json.loads(choice["message"]["content"])
            if (set(value)!={"relation","history_quality","plan_specificity",
                             "missing_verifiable_test","causal_truth_certified"} or
                value["relation"] not in ALLOWED or
                value["history_quality"] not in HISTORY_QUALITY or
                value["plan_specificity"] not in SPECIFICITY or
                type(value["missing_verifiable_test"]) is not bool or
                value["causal_truth_certified"] is not False):
                continue
            return {
                "case_sha256":sha,"state":"PEER_COMPLETED",
                "peer_model_called":True,"relation":value["relation"],
                "history_quality":value["history_quality"],
                "plan_specificity":value["plan_specificity"],
                "missing_verifiable_test":value["missing_verifiable_test"],
                "causal_truth_certified":False,"human_validation":False}
        except Exception:
            continue
    return {"case_sha256":sha,"state":"PEER_UNAVAILABLE",
            "peer_model_called":True,"relation":"NOT_DETERMINABLE",
            "human_validation":False}

def main():
    if NEW.exists() or FINAL.exists():raise FileExistsError("NO_OVERWRITE_V21_PEER")
    gold={x["case_sha256"]:x for line in HOLD.read_text().splitlines()
          if line.strip() for x in [json.loads(line)]}
    old={x["case_sha256"]:x for line in OLD.read_text().splitlines()
          if line.strip() for x in [json.loads(line)]}
    if len(gold)!=len(old)!=100:raise ValueError("PEER_100_NOT_PRESENT")
    changed={}
    for p in PATCHES.glob("*.private.json"):
        data=json.loads(p.read_bytes());sha=data["case_sha256"]
        if sha not in old or sha not in gold:raise ValueError("PEER_IDENTITY_DRIFT")
        result=data["new_result"]
        if not result["quality"]["accepted"]:raise ValueError("V21_NOT_ACCEPTED")
        changed[sha]=ask(result,gold[sha],sha)
    if len(changed)!=2 or any(x["state"]!="PEER_COMPLETED" for x in changed.values()):
        raise ValueError("TWO_PEER_JUDGMENTS_MUST_COMPLETE")
    with NEW.open("x") as f:
        for v in changed.values():f.write(json.dumps(v,sort_keys=True)+"\n")
    merged={**old,**changed}
    with FINAL.open("x") as f:
        for sha in sorted(merged):
            f.write(json.dumps(merged[sha],sort_keys=True)+"\n")
    print(json.dumps({
      "peer_reviewed_originals_retained":len(old)-len(changed),
      "peer_newly_judged":len(changed),"cohort":len(merged),
      "new_labels":dict(Counter(x["relation"] for x in merged.values()
                     if x["state"]=="PEER_COMPLETED")),
      "peer_errors":sum(x["state"]=="PEER_UNAVAILABLE" for x in merged.values()),
      "peer_archive_sha256":sha256(FINAL.read_bytes()).hexdigest(),
      "certified_repairs":0,"root_cause_certified":0,
    },sort_keys=True))
if __name__=="__main__":main()

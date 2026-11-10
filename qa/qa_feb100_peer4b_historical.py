"""Independent FEB100 semantic peer evaluation, AFTER Qwen9B E2E generation.

Qwen4B is a *second opinion* against a separately held-out historical
resolution, NOT a ground-truth evaluator. Failed contract plans were
quarantined as {} and cannot be compared semantically.
"""
from __future__ import annotations
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
from pathlib import Path
import json,urllib.request,time,re
ROOT=Path("/home/u23u/else_itil_feb100_qa_20261110")
RUNS=ROOT/"runs"
HOLDOUT=ROOT/"feb100_historical_holdout.private.jsonl"
JOURNAL=ROOT/"feb100_peer4b_historical_review.private.jsonl"
ENDPOINT="http://127.0.0.1:8003/v1/chat/completions"
MODEL="qwen35-4b"
ALLOWED={"SUPPORTED","CONFLICT","NOT_DETERMINABLE"}
HISTORY_QUALITY={"ACTIONABLE","VAGUE","EMPTY"}
SPECIFICITY={"SPECIFIC","PARTIAL","GENERIC"}
def main():
    if JOURNAL.exists():raise FileExistsError("NO_OVERWRITE_PEER_JOURNAL")
    gold={x["case_sha256"]:x for line in HOLDOUT.read_text(encoding="utf-8").splitlines()
          if line.strip() for x in [json.loads(line)]}
    if len(gold)!=100:raise ValueError("HOLDOUT_SCOPE_NOT_100")
    by_sha={}
    for path in RUNS.glob("case_*/verified_final.private.json"):
        output=json.loads(path.read_bytes())
        sha=output["case_sha256"]
        if sha in by_sha:raise ValueError("DUPLICATE_FINAL_MODEL_OUTPUT")
        by_sha[sha]=output
    if len(by_sha)!=100 or set(by_sha)!=set(gold):
        raise ValueError("E2E_PEER_HOLDOUT_JOIN_NOT_100")
    def review(sha):
        final=by_sha[sha]
        history=gold[sha]
        if not final["quality"]["accepted"]:
            return {"case_sha256":sha,"state":"NOT_COMPARABLE_REJECTED_PLAN",
                    "relation":"NOT_DETERMINABLE",
                    "peer_model_called":False,
                    "human_solution_certified":False,
                    "human_validation":False}
        prompt={"model":MODEL,"temperature":0,
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
                    "model_proposal":final["proposal"],
                    "model_contract_pass":True,
                    "model_qwen9b_sources_historical_not_evidence":True
                  },ensure_ascii=False)}]}
        last="UNKNOWN"
        for attempt in range(2):
            try:
                data=json.dumps(prompt,ensure_ascii=False).encode()
                request=urllib.request.Request(ENDPOINT,data=data,
                    headers={"Content-Type":"application/json"},method="POST")
                with urllib.request.urlopen(request,timeout=155) as r:
                    obj=json.loads(r.read())["choices"][0]
                result=json.loads(obj["message"]["content"])
                if (set(result)!={"relation","history_quality",
                                  "plan_specificity","missing_verifiable_test",
                                  "causal_truth_certified"} or
                    result["relation"] not in ALLOWED or
                    result["history_quality"] not in HISTORY_QUALITY or
                    result["plan_specificity"] not in SPECIFICITY or
                    type(result["missing_verifiable_test"]) is not bool or
                    result["causal_truth_certified"] is not False):
                    last="PEER_SCHEMA_REJECTED";continue
                return {"case_sha256":sha,"state":"PEER_COMPLETED",
                        "peer_model_called":True,
                        "relation":result["relation"],
                        "history_quality":result["history_quality"],
                        "plan_specificity":result["plan_specificity"],
                        "missing_verifiable_test":result["missing_verifiable_test"],
                        "causal_truth_certified":False,
                        "human_validation":False}
            except Exception as exc:
                last=type(exc).__name__
        return {"case_sha256":sha,"state":"PEER_UNAVAILABLE",
                "peer_error_class":last,"peer_model_called":True,
                "relation":"NOT_DETERMINABLE",
                "human_validation":False}
    with ThreadPoolExecutor(max_workers=3) as pool,JOURNAL.open("x") as out:
        fs={pool.submit(review,sha):sha for sha in sorted(by_sha)}
        for i,f in enumerate(as_completed(fs),start=1):
            result=f.result()
            out.write(json.dumps(result,sort_keys=True)+"\n")
            out.flush()
            if i%10==0:
                print(json.dumps({"reviewed":i,"total":100,
                                  "last_status":result["state"]}),flush=True)
    values=[json.loads(x) for x in JOURNAL.read_text().splitlines()]
    print(json.dumps({"reviewed":len(values),
           "peer_completions":sum(x["state"]=="PEER_COMPLETED" for x in values),
           "quarantined_unreviewable":sum(x["state"]=="NOT_COMPARABLE_REJECTED_PLAN"
                                          for x in values),
           "peer_errors":sum(x["state"]=="PEER_UNAVAILABLE" for x in values),
           "semantic_relation_judgments":dict(Counter(x["relation"] for x in values
                  if x["state"]=="PEER_COMPLETED")),
           "journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest()}),flush=True)
if __name__=="__main__":main()

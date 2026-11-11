"""Deterministic lexical pairing audit for ALL 1,810 accepted August plans.

Compares observed Qwen9B action/diagnosis wording with independently
redacted historical solutions after generation, against a same-service
SHUFFLED null control. Cosine TF-IDF is textual overlap, NEVER a measure
of root-cause accuracy. No case content appears in output summaries.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from hashlib import sha256
from pathlib import Path
from statistics import median,mean
import json,math,random,re,unicodedata

BASE=Path("/home/u23u/else_itil_aug2026_qa_20261110")
ROOT=Path("/home/u23u/else_itil_aug2026_review_private_20261110")
JOURNAL=BASE/"aug2026_qwen9b.private.jsonl"
HOLD=ROOT/"aug2026_gold_redacted_for_peer.private.jsonl"
BLIND=BASE/"aug2026_blind_redacted.private.jsonl"
OUT=ROOT/"aug2026_full_1810_lexical_comparison.json"
PER=ROOT/"aug2026_full_1810_lexical_per_case.private.jsonl"
STOP=set("""
para como este esta estos estas buenas buenos favor gracias solicito solicita
solicitud servicio servicios sistema sistemas usuario usuarios tenemos tienen
problema inconveniente presente estimado estimada alguna algunas algun ahora
desde sobre donde cuando entre puede pueden tener tiene hacer forma mismo
seria seria debe deben caso casos verificar verificacion validar validacion
realizar realiza informe soporte tecnico tecnica aplicacion aplicaciones
cambio cambios accion acciones proceso procesos datos dato equipo equipos
acceso falla error errores operacion operaciones respuesta resultado resultados
realizado revisado realizado atencion atencionado incidente incidencias
procedimiento pendiente confirmar necesario necesidad correctamente registro
registrado registrar requiere requerido autorizar autorizado evidencias
evidencia capturar ejecutar ejecucion revisara comprobara exitoso exitosa
intervencion resuelto solucion solucionado solucionada verificable verificar
una uno unos unas los las del por con sin que fue son esta han hace hacia
como cual quien cuales estos todas todo todos otra otras otro otros
se le lo el la y o de en al a un es no si ya muy mas menos
""".split())

def tokens(text):
    normalized=unicodedata.normalize("NFKD",str(text).lower())
    normalized="".join(x for x in normalized if not unicodedata.combining(x))
    return [x for x in re.findall(r"\b[a-z]{4,}\b",normalized)
            if x not in STOP and not x.startswith("identificador")]

def plan_text(plan):
    pieces=[str(plan.get("diagnostico",""))]
    pieces+=list(map(str,plan.get("hipotesis",[])))
    for step in plan.get("pasos",[]):
        if isinstance(step,dict):
            pieces += [str(step.get("condicion","")),
                       str(step.get("accion","")),
                       str(step.get("verificacion",""))]
    pieces+=list(map(str,plan.get("cierre",[])))
    return " ".join(pieces)

def vector(tok,idf):
    count=Counter(tok)
    return {k:(1+math.log(n))*idf[k] for k,n in count.items()}

def cosine(a,b):
    norm_a=math.sqrt(sum(x*x for x in a.values()))
    norm_b=math.sqrt(sum(x*x for x in b.values()))
    if norm_a==0 or norm_b==0:return 0.0
    return sum(value*b.get(k,0) for k,value in a.items())/(norm_a*norm_b)

def main():
    if OUT.exists() or PER.exists():raise FileExistsError("LEXICAL_NO_OVERWRITE")
    outputs={x["ticket_sha256"]:x for l in JOURNAL.read_bytes().splitlines() if l
             for x in [json.loads(l)]}
    history={x["case_sha256"]:x for l in HOLD.read_bytes().splitlines() if l
             for x in [json.loads(l)]}
    inputs={x["ticket_sha256"]:x for l in BLIND.read_bytes().splitlines() if l
            for x in [json.loads(l)]}
    if not len(outputs)==len(history)==len(inputs)==1819 or set(outputs)!=set(history)!=set(inputs):
        raise ValueError("LEXICAL_CORPUS_NOT_SAME_1819")
    selected=[sha for sha in sorted(outputs)
              if outputs[sha]["structural_accepted"] and
                 history[sha]["historical_resolution_redacted"].strip()]
    if len(selected)!=1656:raise ValueError("EXPECTED_COMPARABLE_1656")
    src_tokens={sha:tokens(plan_text(outputs[sha]["technical_plan"]))
                for sha in selected}
    gold_tokens={sha:tokens(history[sha]["historical_resolution_redacted"])
                 for sha in selected}
    df=Counter()
    for tok in list(src_tokens.values())+list(gold_tokens.values()):
        df.update(set(tok))
    n=len(selected)*2
    idf={k:math.log((n+1)/(c+1))+1 for k,c in df.items()}
    src_vec={sha:vector(src_tokens[sha],idf) for sha in selected}
    gold_vec={sha:vector(gold_tokens[sha],idf) for sha in selected}
    services=defaultdict(list)
    for sha in selected:
        services[inputs[sha]["service_code"]].append(sha)
    rand=random.Random(20260811)
    permutations={}
    # Single deterministic, same-service negative control per case.
    for service,ids in sorted(services.items()):
        shuffled=list(ids)
        rand.shuffle(shuffled)
        if len(ids)>1:
            for i in range(len(ids)):
                if shuffled[i]==ids[i]:
                    j=(i+1)%len(ids)
                    shuffled[i],shuffled[j]=shuffled[j],shuffled[i]
        else:
            shuffled=[selected[(selected.index(ids[0])+1)%len(selected)]]
        for original,control in zip(ids,shuffled):
            if original==control:raise ValueError("IDENTICAL_CONTROL")
            permutations[original]=control
    entries=[]
    for sha in selected:
        actual=cosine(src_vec[sha],gold_vec[sha])
        control=cosine(src_vec[sha],gold_vec[permutations[sha]])
        entries.append({
            "case_sha256":sha,
            "service_code":inputs[sha]["service_code"],
            "pair_cosine":round(actual,6),
            "same_service_shuffled_control_cosine":round(control,6),
            "matched_exceeds_control":actual>control,
            "comparison_is_text_only":True,
        })
    matched=[x["pair_cosine"] for x in entries]
    null=[x["same_service_shuffled_control_cosine"] for x in entries]
    raw=b"\n".join(json.dumps(x,sort_keys=True).encode()
                    for x in entries)+b"\n"
    with PER.open("xb") as f:f.write(raw)
    report={
        "schema":"else.itil.aug2026.lexical-vs-uncertified-history.v1",
        "original_accepted":1810,
        "nonempty_history_comparable":len(selected),
        "accepted_empty_history_uncomparable":154,
        "original_contract_rejected_uncomparable":9,
        "matched_tfidf_cosine_mean":round(mean(matched),5),
        "matched_tfidf_cosine_median":round(median(matched),5),
        "same_service_shuffled_control_mean":round(mean(null),5),
        "same_service_shuffled_control_median":round(median(null),5),
        "matched_exceeds_same_service_control":sum(
            x["matched_exceeds_control"] for x in entries),
        "both_texts_with_recognized_words":sum(
            bool(src_tokens[x]) and bool(gold_tokens[x]) for x in selected),
        "actual_case_text_never_in_report":True,
        "historical_notes_uncertified":True,
        "semantic_causal_accuracy_not_measured":True,
        "model_called":False,
        "shuffling_seed":20260811,
        "pairs_sha256":sha256(raw).hexdigest(),
        "original_month_journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest(),
    }
    with OUT.open("x") as f:json.dump(report,f,sort_keys=True,indent=2)
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()

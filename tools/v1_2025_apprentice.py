"""Prepare 2025-only V1 study queue and run small real trainee/mentor pilot.

The historical solution is NEVER shown to the trainee; it is an unverified
comparator for the mentor. Neither model can approve a training example.
All case content is PRIVATE and must never be committed or printed to stdout.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,os
from pathlib import Path

from else_dominance.agent import OpenAICompatibleModel
from else_dominance.apprenticeship_v1 import select_2025_curriculum, draft_2025_case

def private_write(path:Path, lines:list[dict]):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    path.parent.chmod(0o700)
    fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as stream:
        for row in lines:
            stream.write(json.dumps(row,ensure_ascii=False)+"\n")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--private-dir",type=Path,required=True)
    p.add_argument("--per-month",type=int,default=20)
    p.add_argument("--pilot",type=int,default=2)
    args=p.parse_args()
    root=Path.cwd().resolve()
    out=args.private_dir.resolve()
    if out==root or root in out.parents:
        raise ValueError("PRIVATE_OUTPUT_OUTSIDE_REPOSITORY_REQUIRED")
    if out.exists() and any(out.glob("*")):
        raise ValueError("TARGET_DIRECTORY_MUST_BE_EMPTY")
    if not args.source.is_file():
        raise FileNotFoundError("PRIVATE_2025_DATA_MISSING")
    rows=[json.loads(x) for x in args.source.open(encoding="utf-8") if x.strip()]
    selection=select_2025_curriculum(rows,per_month=args.per_month)
    assert len(selection)==12*args.per_month
    private_write(out/"curriculum.private.jsonl",selection)
    student=OpenAICompatibleModel("http://127.0.0.1:18781/v1","else-itil-riv-gpu7",timeout=145)
    reviewer=OpenAICompatibleModel("http://127.0.0.1:18782/v1","else-itil-riv-qwen9b-gpu6",timeout=165)
    audit=[]
    for row in selection[:args.pilot]:
        try:
            source_row={
                "case_sha256":row["case_sha256"],"year":2025,
                "month":row["month"],"label_status":"UNVERIFIED_HISTORIC_2025",
                "user":row["incident"],
                "assistant_target":row["historical_solution_unverified"],
            }
            draft=draft_2025_case(source_row,student)
            mentor_data={
                "incident":row["incident"],"student_proposal":draft["proposal"],
                "historical_action_unverified":row["historical_solution_unverified"],
                "warning":"Historical answer is NOT verified ground truth.",
            }
            mentor_prompt=(
                "Eres mentor técnico crítico de Soporte TIC. La solución histórica "
                "es una etiqueta NO verificada. Identifica pruebas faltantes, contradicciones, "
                "suposiciones y riesgos del plan del estudiante. NO declares reparación "
                "ni que el ejemplo esté aprobado para entrenar. Responde SOLO JSON con "
                "critica, pruebas_pendientes (lista), posibles_errores (lista), "
                "decision:'REQUIERE_REVISION_HUMANA', entrenamiento_aprobado:false."
            )
            mentor_json=reviewer.complete([
                {"role":"system","content":mentor_prompt},
                {"role":"user","content":json.dumps(mentor_data,ensure_ascii=False)}
            ])
            mentor=json.loads(mentor_json)
            valid=(mentor.get("entrenamiento_aprobado") is False and
                   mentor.get("decision")=="REQUIERE_REVISION_HUMANA")
            audit.append({
                "case_sha256":row["case_sha256"],"month":row["month"],
                "student_model":"Qwen3.5-4B-original",
                "mentor_model":"Qwen3.5-9B-original",
                "student":draft,"mentor":mentor,
                "mentor_valid":valid,"training_approved":False,
                "repair_certified":False,
                "status":"HUMAN_REVIEW_PENDING" if valid else "MODEL_REVIEW_INVALID",
            })
        except Exception as exc:
            audit.append({
                "case_sha256":row["case_sha256"],"month":row["month"],
                "status":"MODEL_ERROR","error_type":type(exc).__name__,
                "training_approved":False,"repair_certified":False
            })
    private_write(out/"drafts.private.jsonl",audit)
    report={
        "schema":"else.itil.specialist-v1.apprenticeship.v1",
        "year":2025,"all_months":12,"selected_cases":len(selection),
        "monthly_count":args.per_month,"pilot_cases":len(audit),
        "awaiting_human_review":sum(x["status"]=="HUMAN_REVIEW_PENDING" for x in audit),
        "model_errors":sum(x["status"]=="MODEL_ERROR" for x in audit),
        "eligible_to_train":0,"certified_repairs":0,"2026_used":False,
        "selected_case_set_sha256":hashlib.sha256((out/"curriculum.private.jsonl").read_bytes()).hexdigest(),
        "private_files_only":True,
    }
    private_write(out/"pilot_summary.json",[report])
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    main()

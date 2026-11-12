"""Second-turn model evaluation incorporating a REAL SAP/OT Hand receipt.

This is a supplementary 16-case review, not a replacement for the 100
baseline ITIL/O5 runs. No new SQL. SAP/OT receipt is source-sha verified
but NOT certified by native O5 (the ITIL receipt is).
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
from pathlib import Path
import json,re,zipfile,traceback
from collections import Counter

from else_dominance.qa_feb100_ot_evidence import verify_ot_receipt,SOURCES
from else_dominance.qa_feb100_native import verify_native_o5
from else_dominance.qa_feb100_cluster import parse_strict
from else_dominance.support_desk import SYSTEM,_quality
from else_dominance.resolution_batch import KNOWN_SOURCES
from else_dominance.agent import OpenAICompatibleModel
from else_core.itil_feb100_o5_hand import AuthorizedNugetReceipt
from qa.qa_feb100_windows import read_allowlist

ROOT=Path("/home/u23u/else_itil_feb100_qa_20261110")
RUNS=ROOT/"runs"
REPO=Path("/home/u23u/else_itil_feb100_20261110")
ALLOW=ROOT/"feb100_allowlist.private.jsonl"
SAP_SOURCE=REPO/"qa/Feb100SapOtRead.cs"
ITIL_SOURCE=REPO/"qa/Feb100ExactRead.cs"
SAP_ZIP=ROOT/"feb100_ot_sap_receipts.private.zip"
LOG=ROOT/"ot_augmented_model_review.private.jsonl"
TABLE=re.compile(r"\b(?:ITIL|SEC|ADM|COM|DIS|DIST|DBO)\.[A-Za-z][A-Za-z0-9_]*",re.I)

def eligible_runs():
    rows=read_allowlist(ALLOW)
    unique={}
    for p in RUNS.glob("case_*"):
        final=p/"verified_final.private.json"
        if not final.is_file():continue
        body=json.loads(final.read_bytes())
        sha=body["case_sha256"]
        if sha in unique:raise ValueError("DUPLICATE_CASE_FINAL")
        unique[sha]=(p,body)
    if len(unique)!=100:raise ValueError("NOT_ALL_100_FINALIZED")
    with zipfile.ZipFile(SAP_ZIP) as pack:
        obs={name[:64]:json.loads(pack.read(name))
             for name in pack.namelist()}
    if len(obs)!=16:raise ValueError("EXPECTED_16_OT_RECEIPTS")
    return [(sha,rows[sha],unique[sha][0],unique[sha][1],obs[sha])
            for sha in sorted(obs)]

def run_one(args):
    sha,row,path,final,raw_receipt=args
    try:
        verified=verify_ot_receipt(row=row,receipt=raw_receipt,
                                source_bytes=SAP_SOURCE.read_bytes())
        raw=(path/"receipt.private.json").read_bytes()
        owner=AuthorizedNugetReceipt(
            path/"receipt.private.json",sha256(raw).hexdigest(),
            sha,sha256(ITIL_SOURCE.read_bytes()).hexdigest(),
            len(ITIL_SOURCE.read_bytes()))
        gate=verify_native_o5(owner)
        if gate.get("guardian_o13_pass") is not True or gate.get("dominance_o15_pass") is not True:
            raise ValueError("ITIL_NATIVE_O5_NO_LONGER_VERIFIED")
        status=verified["order_found_in_this_specific_table"]
        e=[
          {"ref":"E1","observation":
            "Recibo ITIL febrero de un expediente exacto, verificado por O5/O13/O15. "
            "Servicio y módulo históricos vinculados; no prueba causa raíz."},
          {"ref":"E2","observation":
            "Lectura de dbo.taOrdenTrabajoSAP por número OT REPORTADO en texto; "
            f"coincidencia en ESTA tabla: {status}; "
            "vinculación del reporte ITIL con la entidad de negocio NO certificada."},
          {"ref":"E3","observation":
            "Lectura separada de dbo.taOrdenTrabajoSAPEnvioRespuesta, "
            f"hasta {verified['response_rows_up_to5']} respuestas, "
            f"existe mensaje: {verified['response_message_present']}; "
            "texto del mensaje no leído por Qwen, ni es confirmación de solución."},
        ]
        model=OpenAICompatibleModel(
             "http://127.0.0.1:18782/v1","else-itil-riv-qwen9b-gpu6",
             timeout=155)
        sys=SYSTEM+(
            "\nE1 es el recibo ITIL O5 real; E2/E3 provienen de dos consultas "
            "SAP/OT en dbDistribucion_D verificadas por fuente C# fija pero "
            "NO certificadas por O5. El número se extrajo del texto "
            "del ticket; solo es un IDENTIFICADOR REPORTADO, no un join "
            "corporativo validado. Si no existe coincidencia, no concluyas "
            "que la orden no existe fuera de estas dos tablas. "
            "Usa 'fuentes' estrictamente de los catálogos proporcionados, "
            "no inventes nombres de tablas, perfiles, causas ni reparaciones.")
        payload={"case_sha_prefix":sha[:16],
             "incident_text_redacted_unverified":row["description_redacted"],
             "historical_solution":"WITHHELD",
             "real_evidence":e,
             "verified_ot":{
                k:v for k,v in verified.items() if k not in
                ("case_sha256","source_receipt_sha256")},
             "source_catalog":sorted(KNOWN_SOURCES | set(SOURCES)),
             "required":"Hipótesis diferenciales, pruebas discriminantes, "
                "pasos condicionales y cierre verificable; ninguna mutación."}
        raw=model.complete([
            {"role":"system","content":sys},
            {"role":"user","content":json.dumps(payload,ensure_ascii=False)}])
        plan=parse_strict(raw.encode())
        declared=plan.get("fuentes")
        if type(declared) is not list:declared=[]
        permitted=set(KNOWN_SOURCES)|set(SOURCES)
        unknown=[x for x in declared if x not in permitted]
        mentioned={m.group(0).upper() for m in TABLE.finditer(
                json.dumps(plan,ensure_ascii=False))}
        unbound=sorted(x for x in mentioned if
                x not in {f.upper() for f in declared} or
                x not in {f.upper() for f in permitted})
        # Quality's original known-source catalog was built before this
        # verified supplemental Hand; pass only verified SAP source names.
        q_input=dict(plan)
        q_input["fuentes"]=[f for f in declared if f not in set(SOURCES)]
        qual=_quality(q_input,e)
        if unknown or unbound:
            qual={**qual,"accepted":False,"status":"REJECT",
                  "safety_flags":qual["safety_flags"]+
                      ["UNBOUND_OR_UNKNOWN_TABLE_REFERENCE"]}
        approved=(qual["accepted"] is True and
                  plan.get("ejecutado") is False and
                  plan.get("confirmado") is False)
        report={
            "schema":"else.itil.feb100.ot-sap-supplemental-review.v1",
            "case_sha256":sha,
            "itil_o5_o13_o15_verified":True,
            "sap_source_exact_verified":True,
            "sap_o5_certified":False,
            "order_found_in_qa_table":status,
            "original_quality_accepted":final["quality"]["accepted"],
            "supplemental_quality_accepted":approved,
            "supplemental_quality":qual,
            "model_proposed_sources":declared,
            "model_evidence_refs":plan.get("evidence_refs",[]),
            "proposal":plan if approved else {},
            "rejected_plan_quarantined_sha256":sha256(raw.encode()).hexdigest()
                if not approved else None,
            "repair_certified":False,
            "root_cause_certified":False,
            "human_review_required":True,
        }
        out=path/"ot_supplemental_final.private.json"
        if out.exists():raise FileExistsError("REVIEW_ALREADY_EXISTS")
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        if not approved:
            quarantine=path/"ot_rejected_raw_model.private.json"
            quarantine.write_text(raw,encoding="utf-8")
        return {"case_sha256":sha,"state":"COMPLETED",
                "order_found":status,
                "quality_accepted":approved,
                "before_quality_accepted":final["quality"]["accepted"],
                "sap_read_verified":True}
    except Exception as e:
        return {"case_sha256":sha,"state":"REVIEW_FAILED",
                "error_type":type(e).__name__}

def main():
    if LOG.exists():raise FileExistsError("NO_OVERWRITE_REVIEW")
    items=eligible_runs()
    with ThreadPoolExecutor(max_workers=2) as pool,LOG.open("x") as out:
        for i,future in enumerate(as_completed([pool.submit(run_one,x) for x in items]),
                                   start=1):
            row=future.result()
            out.write(json.dumps(row,sort_keys=True)+"\n")
            out.flush()
            print(json.dumps({"done":i,"total":len(items),
                              "state":row["state"]}),flush=True)
    results=[json.loads(x) for x in LOG.read_text().splitlines()]
    print(json.dumps({
        "reviewed":len(results),
        "completed":sum(x["state"]=="COMPLETED" for x in results),
        "errors":sum(x["state"]!="COMPLETED" for x in results),
        "accepted_before":sum(x.get("before_quality_accepted") is True for x in results),
        "accepted_after":sum(x.get("quality_accepted") is True for x in results),
        "sap_receipts_verified":sum(x.get("sap_read_verified") is True for x in results),
        "repairs":0
    }),flush=True)
if __name__=="__main__":main()

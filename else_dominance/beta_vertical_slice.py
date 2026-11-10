"""V1 Beta supervised vertical slice: original Feb ITIL + SAP/OT native Hands.

QA-only. Historical ITIL case and uniquely reported OT are joined by
report text ONLY, never by official enterprise business ID. Each read
receipt is reverified via distinct native CORE O5/O13/O15 Hands before
Qwen receives any claimed observation. No corporate SQL or repairs run.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from collections import Counter
import json
import re
import zipfile

from else_core.hand_kernel import Outcome
from else_core.itil_feb100_o5_hand import (
    AuthorizedNugetReceipt,build_nuget_qa_router)
from else_core.itil_feb100_sap_ot_o5_hand import (
    AuthorizedSapOtReceipt,build_sap_ot_router)
from .qa_evidence_grounding import normalized_mentions,BARE,model_string_values
from .support_desk import SYSTEM
from .resolution_batch import evaluate_response
from .support_quality import evaluate_support_plan
from .qa_feb100_cluster import parse_strict,source_context

SOURCES=frozenset({
    "ITIL.taIncidente",
    "dbo.taOrdenTrabajoSAP",
    "dbo.taOrdenTrabajoSAPEnvioRespuesta",
})
REFS=frozenset({"E1","E2","E3"})
HEX=re.compile(r"[a-f0-9]{64}\Z")
POLICY="else.itil.v1beta.sap-ot-evidence-gate.v1.1"
PENDING_ROLE="Responsable autorizado por confirmar"


def demand(ok,reason):
    if not ok:raise ValueError(reason)


def beta_plan_gate(plan,evidence):
    flags=[]
    if type(plan) is not dict:
        return {"accepted":False,"flags":["PLAN_NOT_JSON_OBJECT"]}
    declared=plan.get("fuentes")
    if type(declared) is not list or sorted(declared)!=sorted(SOURCES):
        flags.append("EVIDENCE_SOURCES_EXACTLY_THREE_REQUIRED")
        declared=[]
    if len(set(declared))!=len(declared):
        flags.append("DUPLICATE_SOURCE")
    used=plan.get("evidence_refs")
    if (type(used) is not list or not used or
        any(type(x) is not str for x in used) or
        not set(used)<=REFS or len(used)!=len(set(used)) or
        "E1" not in used or "E2" not in used):
        flags.append("ITIL_AND_SAP_RECEIPTS_MUST_BE_REFERENCED")
    mentions=set(normalized_mentions(plan))
    known={x.upper() for x in SOURCES}
    other=sorted(mentions-known)
    if other:flags.append("UNOBSERVED_SQL_TABLE_REFERENCED")
    bare={m.group().lower() for m in BARE.finditer(model_string_values(plan))}
    allowed_bare={"taincidente","taordentrabajosap",
                  "taordentrabajosapenviorespuesta"}
    if bare-allowed_bare:flags.append("UNOBSERVED_SQL_OBJECT_REFERENCED")
    for field in ("faltantes","cierre"):
        entries=plan.get(field)
        if (type(entries) is not list or not entries or
            any(type(x) is not str or len(x.strip())<15 for x in entries)):
            flags.append("MISSING_EVIDENCE_OR_CLOSURE_PLAN")
    if plan.get("ejecutado") is not False or plan.get("confirmado") is not False:
        flags.append("FALSE_EXECUTION_CLAIM")
    if plan.get("vinculacion_comercial_verificada") is not False:
        flags.append("UNVERIFIED_BUSINESS_JOIN_CANNOT_BE_CERTIFIED")
    if plan.get("rol_oficial_validado") is not False:
        flags.append("UNVERIFIED_CORPORATE_ROLE_CANNOT_BE_CERTIFIED")
    for index,step in enumerate(plan.get("pasos",[])):
        if (type(step) is not dict or
            step.get("responsable","").strip().casefold()!=
            PENDING_ROLE.casefold()):
            flags.append("ACTION_"+str(index)+"_ROLE_NOT_IN_APPROVED_MATRIX")
    # A formally correct plan must still satisfy procedural quality.
    try:
        # Legacy schema validator has a *static* source catalog that
        # predates the second native SAP/OT Hand. Use it for procedural
        # quality only; the original plan's exact three-source list is
        # checked independently above against BOTH real O5 receipts.
        # No model output is rewritten or accepted by a posthoc patch.
        base=evaluate_response({**plan,"fuentes":[]})
        if not base["valid"]:
            flags.extend(base["flags"])
        registry={v["ref"]:v["observation"] for v in evidence}
        mapped={
            "ticket_state":"PENDING_AUTHORIZATION",
            "performed_changes":plan.get("ejecutado"),
            "evidence_refs":used or [],
            "conditional_actions":[{
                "precondition":x.get("condicion",""),
                "action":x.get("accion",""),
                "authorized_role":x.get("responsable",""),
                "verification":x.get("verificacion",""),
            } for x in plan.get("pasos",[]) if isinstance(x,dict)],
            "closure_tests":plan.get("cierre",[]),
        }
        extra=evaluate_support_plan(mapped,evidence_registry=registry).to_dict()
        if extra["status"]=="REJECT":
            flags.extend(extra["hard_flags"])
        review_flags=extra["review_flags"]
    except (KeyError,ValueError,TypeError,AttributeError):
        flags.append("PROCEDURE_SCHEMA_INVALID")
        review_flags=[]
    return {
        "schema":POLICY,
        "accepted":not bool(flags),
        "hard_flags":sorted(set(flags)),
        "review_flags":review_flags,
        "source_names":sorted(SOURCES),
        "business_entity_link_verified":False,
        "repair_certified":False,
        "human_approval_required":True,
    }


class BetaEvidenceBundle:
    def __init__(self,*,base:Path,qa:Path,core_source:Path):
        self.base=base
        self.qa=qa
        self.core_source=core_source
        self.itil_bytes=(base/"qa/Feb100ExactRead.cs").read_bytes()
        self.sap_bytes=(base/"qa/Feb100SapOtRead.cs").read_bytes()
        self.roster={}
        for line in (qa/"feb100_allowlist.private.jsonl").read_text().splitlines():
            if not line.strip():continue
            row=json.loads(line)
            sha=row["case_sha256"]
            demand(HEX.fullmatch(sha) is not None and sha not in self.roster,
                   "ALLOWLIST_CASE_DUPLICATE")
            self.roster[sha]=row
        demand(len(self.roster)==100,"FEB100_ROSTER_DRIFT")
        self.original={}
        for path in (qa/"runs").glob("case_*/verified_final.private.json"):
            body=json.loads(path.read_bytes())
            sha=body["case_sha256"]
            demand(sha not in self.original,"DUPLICATE_ORIGINAL_FINAL")
            self.original[sha]=path.parent
        demand(set(self.original)==set(self.roster),
               "ORIGINAL_ITIL_100_COUPLING_ERROR")
        self.sap_recs={}
        self.sap_root=core_source/"sap_ot_original_receipts.private"
        self.sap_root.mkdir(mode=0o700,exist_ok=True)
        with zipfile.ZipFile(qa/"feb100_ot_sap_receipts.private.zip") as z:
            names=z.namelist()
            demand(len(names)==16 and len(set(names))==16,
                   "SAP_ORIGINAL_16_DRIFT")
            for name in names:
                sha=name[:64]
                demand(name==sha+".private.json" and sha in self.roster,
                       "SAP_CASE_OUTSIDE_COHORT")
                raw=z.read(name)
                p=self.sap_root/name
                if p.exists():demand(p.read_bytes()==raw,"SAP_ARCHIVE_BYTES_CHANGED")
                else:
                    with p.open("xb") as stream:stream.write(raw)
                    p.chmod(0o600)
                self.sap_recs[sha]=p

    def verify(self,sha):
        demand(type(sha) is str and HEX.fullmatch(sha) and
               sha in self.roster,"CASE_NOT_QA_ALLOWED")
        original=self.original[sha]
        item=self.roster[sha]
        proof_file=original/"receipt.private.json"
        raw=proof_file.read_bytes()
        itil=AuthorizedNugetReceipt(
            proof_file,sha256(raw).hexdigest(),sha,
            sha256(self.itil_bytes).hexdigest(),len(self.itil_bytes))
        _,router,op=build_nuget_qa_router(itil)
        itil_result=router.route(op)
        demand(itil_result.outcome==Outcome.PASS and
               itil_result.guardian_result.verification.passed is True and
               itil_result.guardian_result.verification.independent is True,
               "ITIL_O5_O13_O15_NOT_VERIFIED")
        case=json.loads((original/"case.private.json").read_bytes())
        demand(case["case_sha256"]==sha and
               case["historical_solution"]=="WITHHELD",
               "NO_HISTORICAL_SOLUTION_EXPOSURE")
        _,itil_proof=itil.read_verified()
        metadata=source_context(itil_proof,case)
        if sha not in self.sap_recs:
            return {"status":"REQUIRES_OT_CORPORATE_EVIDENCE",
                    "case_sha256":sha,"itil_receipt_sha256":itil.pinned_sha256,
                    "case_opened_at":item["opened_at"],
                    "itil_o5_verified":True,"sap_o5_verified":False,
                    "official_business_join_certified":False,
                    "repair_certified":False}
        sap_path=self.sap_recs[sha]
        sap_raw=sap_path.read_bytes()
        sap=AuthorizedSapOtReceipt(
            sap_path,sha256(sap_raw).hexdigest(),sha,
            sha256(self.sap_bytes).hexdigest(),len(self.sap_bytes),
            item["description_redacted"])
        hand,sap_router,sap_op=build_sap_ot_router(sap)
        sap_result=sap_router.route(sap_op)
        demand(sap_result.outcome==Outcome.PASS and
               sap_result.guardian_result.verification.passed is True and
               sap_result.guardian_result.verification.independent is True,
               "SAP_OT_O5_O13_O15_NOT_VERIFIED")
        sap_values=sap_result.guardian_result.value.outputs
        demand(sap_values["business_entity_join_certified"] is False,
               "CLAIMED_BUSINESS_JOIN_NOT_SUPPORTED")
        evidence=[
            {"ref":"E1","observation":
             "Recibo nativo O5/O13/O15 de ITIL.taIncidente QA febrero, "
             "existencia y metadatos históricos, sin solución leída."},
            {"ref":"E2","observation":
             "Recibo nativo O5/O13/O15 de las dos tablas SAP/OT QA para "
             "una OT ÚNICA REPORTADA en el texto del ticket, NO un join "
             "de negocio certificado. Encontrada en esta tabla: "+
             str(sap_values["order_found"])+
             ". Estado SAP de orden solo histórico: "+
             str(sap_values["order_state_code"])+
             ". No es causa ni cierre probado."},
            {"ref":"E3","observation":
             "La tabla SAP de respuesta devolvió hasta "+
             str(sap_values["response_rows_up_to5"])+
             " filas, no se transmitieron mensajes crudos; no se ha "
             "verificado su pertenencia empresarial al expediente ITIL."},
        ]
        return {
            "status":"DUAL_NATIVE_EVIDENCE_VERIFIED",
            "case_sha256":sha,
            "itil_receipt_sha256":itil.pinned_sha256,
            "sap_receipt_sha256":sap.pinned_sha256,
            "itil_o5_verified":True,"sap_o5_verified":True,
            "case_opened_at":item["opened_at"],
            "service_code":item["service_code"],
            "module_code":item["module_code"],
            "itil_metadata":metadata,
            "sap_observation":sap_values,
            "evidence":evidence,
            "incident_text_redacted":item["description_redacted"],
            "official_business_join_certified":False,
            "functional_repair_certified":False,
        }


class BetaInvestigator:
    def __init__(self,bundle:BetaEvidenceBundle,model):
        self.bundle=bundle
        self.model=model

    def investigate(self,case_sha256):
        verified=self.bundle.verify(case_sha256)
        if verified["status"]!="DUAL_NATIVE_EVIDENCE_VERIFIED":
            return verified
        sys=SYSTEM+(
            "\nV1 BETA: ambas lecturas corporativas QA se verificaron de "
            "forma independiente mediante dos Hands O5/O13/O15. "
            "La OT sólo es un número reportado en el texto del ticket. "
            "NO existe join oficial ITIL-Distribución ni confirmación "
            "de causa, estado actual o reparación. "
            "fuentes es una lista exacta de: ITIL.taIncidente, "
            "dbo.taOrdenTrabajoSAP, dbo.taOrdenTrabajoSAPEnvioRespuesta. "
            "Usa evidence_refs E1,E2,E3. Si la tabla OT no tiene filas, "
            "NO concluyas que la orden no existe en otros sistemas. "
            "Explica hipótesis distintas y pruebas que las discriminen. "
            "No inventes roles: para cada paso el campo responsable "
            "debe ser EXACTAMENTE 'Responsable autorizado por confirmar'. "
            "Añade vinculacion_comercial_verificada:false y "
            "rol_oficial_validado:false al objeto JSON. "
            "Sin nombre de tabla adicional. Nunca afirmar que se "
            "ejecutó una acción, autorizó o resolvió el incidente.")
        payload={
            "case_sha_prefix":case_sha256[:16],
            "incident_text_redacted_unverified":
                verified["incident_text_redacted"],
            "native_itil_metadata":verified["itil_metadata"],
            "native_sap_ot_evidence":verified["sap_observation"],
            "evidence":verified["evidence"],
            "official_business_link":"NOT_CERTIFIED",
            "historical_solution":"WITHHELD",
            "source_whitelist":sorted(SOURCES),
            "required":"Plan condicional JSON con pasos, faltantes y "
                       "prueba de cierre, sin afirmar ejecución."}
        messages=[
            {"role":"system","content":sys},
            {"role":"user","content":json.dumps(payload,ensure_ascii=False)},
        ]
        q={"accepted":False,"hard_flags":["NO_MODEL_OUTPUT"]}
        plan={}
        attempts=0
        for attempt in (1,2):
            attempts=attempt
            try:
                raw=self.model.complete(messages)
                proposed=parse_strict(raw.encode())
                q=beta_plan_gate(proposed,verified["evidence"])
                if q["accepted"]:
                    plan=proposed
                    break
                if attempt==1:
                    messages.append({"role":"assistant","content":raw[:4000]})
                    messages.append({"role":"user","content":
                        "Rechazado: "+",".join(q["hard_flags"][:9])+
                        ". Reescribe todas las partes sin simular fuentes, "
                        "roles, reparaciones, ni relaciones empresariales. "
                        "Para TODOS los pasos responsable debe ser exactamente "
                        "'Responsable autorizado por confirmar'. Añade "
                        "vinculacion_comercial_verificada:false y "
                        "rol_oficial_validado:false."})
            except (TypeError,ValueError,KeyError):
                q={"accepted":False,"hard_flags":["MODEL_JSON_REJECTED"]}
        return {
            "schema":"else.itil.v1beta.dual-hand.supervised-investigation.v1",
            "case_sha256":case_sha256,
            "status":"PENDING_TECHNICIAN_REVIEW" if q["accepted"] else
                     "NEEDS_HUMAN_TRIAGE",
            "native_itil_verified":True,
            "native_sap_ot_verified":True,
            "business_join_certified":False,
            "source_receipts":{
                "itil":verified["itil_receipt_sha256"],
                "sap_ot":verified["sap_receipt_sha256"],
            },
            "reported_order_found_in_qa":verified["sap_observation"]["order_found"],
            "model_attempts":attempts,
            "quality":q,
            "proposal":plan if q["accepted"] else {},
            "reviewer_authorization":"PENDING",
            "repair_certified":False,
            "root_cause_certified":False,
            "actions_executed":False,
            "human_review_required":True,
        }

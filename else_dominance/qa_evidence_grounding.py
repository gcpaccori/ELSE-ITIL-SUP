"""Evidence provenance hard boundary for the February 100-case specialist.

The catalog of potential tools is NOT evidence of a query. Only the native
O5/O13/O15-verified ITIL.taIncidente receipt is currently observed. Never
post-fill source names, launder unknown tables or convert a rejected plan
into an accepted one through normalization.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re

from .support_desk import _quality

SCHEMA = "else.itil.qa.feb100.provenance-gate.v2"
OBSERVED = frozenset({"ITIL.taIncidente"})
REFS = frozenset({"E1", "E2"})
# Includes the physical dbo qualifier, which is NOT an interchangeable
# canonical entity name without a database-scoped proof.
TABLE = re.compile(
    r"(?<![A-Za-z0-9_])(?:ITIL|SEC|ADM|COM|DIS|DIST|DBO)"
    r"\s*\.\s*[A-Za-z][A-Za-z0-9_]*", re.I)


def normalized_mentions(plan: dict) -> list[str]:
    raw = json.dumps(plan, ensure_ascii=False, sort_keys=True)
    return sorted({
        re.sub(r"\s+", "", match.group()).upper()
        for match in TABLE.finditer(raw)
    })


def evidence_provenance_gate(plan: dict, *, native_o5_verified: bool,
                             source_receipt_sha256: str) -> dict:
    from hashlib import sha256
    observed = frozenset(OBSERVED) if native_o5_verified else frozenset()
    flags = []
    if not isinstance(plan, dict):
        return {
            "schema": SCHEMA, "accepted": False,
            "flags": ["PLAN_NOT_OBJECT"], "observed_sources": sorted(observed),
            "unobserved_mentions": [], "receipt_bound": False,
        }
    declared = plan.get("fuentes")
    if type(declared) is not list or not declared or any(
            type(x) is not str for x in declared):
        flags.append("EXACT_OBSERVED_SOURCE_LIST_REQUIRED")
        declared = []
    if len(set(declared)) != len(declared):
        flags.append("DUPLICATE_SOURCE_DECLARATION")
    if set(declared) != set(observed):
        flags.append("DECLARED_SOURCE_NOT_ACTUALLY_READ")
    mentioned = normalized_mentions(plan)
    unknown = sorted(x for x in mentioned
                     if x not in {v.upper() for v in observed})
    if unknown:
        flags.append("UNOBSERVED_SQL_TABLE_MENTION")
    undeclared = sorted(x for x in mentioned if x not in {
        v.upper() for v in declared})
    if undeclared:
        flags.append("UNDECLARED_SQL_TABLE_MENTION")
    refs = plan.get("evidence_refs")
    if type(refs) is not list or not refs or any(
            type(x) is not str for x in refs):
        flags.append("NO_EXPLICIT_VERIFIED_EVIDENCE_REFS")
        refs = []
    if not set(refs).issubset(REFS) or len(set(refs)) != len(refs):
        flags.append("UNKNOWN_OR_DUPLICATED_EVIDENCE_REF")
    receipt_bound=(
        type(source_receipt_sha256) is str and
        re.fullmatch(r"[0-9a-f]{64}", source_receipt_sha256) is not None and
        native_o5_verified is True)
    if not receipt_bound:
        flags.append("NATIVE_SOURCE_RECEIPT_NOT_BOUND")
    if plan.get("ejecutado") is not False or plan.get("confirmado") is not False:
        flags.append("FALSE_EXECUTION_OR_CONFIRMATION")
    return {
        "schema": SCHEMA, "accepted": not bool(flags),
        "flags": flags,
        "observed_sources": sorted(observed),
        "unobserved_mentions": unknown,
        "undeclared_mentions": undeclared,
        "receipt_bound": receipt_bound,
    }


def grounded_system_policy() -> str:
    return (
        "\nCONTRATO DE PROCEDENCIA EVIDENCIA v2 (OBLIGATORIO): "
        "El único origen corporativo realmente consultado y certificado "
        "mediante O5/O13/O15 es ITIL.taIncidente, expediente histórico "
        "de febrero 2026. El listado de otras tablas que sepas o "
        "recuerdes NO es evidencia ni autorización para citarlas. "
        "Debes escribir fuentes EXACTAMENTE como [\"ITIL.taIncidente\"], "
        "evidence_refs como lista NO VACÍA de E1 y/o E2. "
        "NO menciones ningún nombre SQL esquema.tabla distinto de "
        "ITIL.taIncidente EN NINGÚN CAMPO, tampoco en faltantes ni pasos. "
        "Para una verificación adicional aún no realizada, describe "
        "la comprobación funcional requerida en lenguaje natural, "
        "sin inventar tabla, columna, consulta, permisos, rol, "
        "estado actual ni causa comprobada. No puedes dar por realizada "
        "ninguna consulta salvo la lectura ITIL de metadatos ni convertir "
        "un código ITIL histórico en diagnóstico de la causa. "
        "Cada hipótesis debe indicar cómo descartarla y cada paso debe "
        "contener condición, acción, responsable autorizado pendiente "
        "de confirmar, y verificación observable. "
        "Nunca elimines una necesidad de evidencia para pasar filtros. "
        "La salida es solo JSON exacto del procedimiento."
    )


def evaluate_grounded_plan(plan: dict, *, evidence: list[dict],
                           source_receipt_sha256: str) -> dict:
    provenance = evidence_provenance_gate(
        plan, native_o5_verified=True,
        source_receipt_sha256=source_receipt_sha256)
    original = _quality(plan, evidence)
    accepted = bool(provenance["accepted"] and original["accepted"])
    flags = list(original.get("safety_flags", []))
    if not provenance["accepted"]:
        flags.extend(provenance["flags"])
    return {
        **original,
        "accepted": accepted,
        "status": original["status"] if accepted else "REJECT",
        "safety_flags": sorted(set(flags)),
        "provenance": provenance,
        "grounded_acceptance_not_causal_truth": True,
    }


def missing_source_repair_instruction(quality: dict) -> str:
    # Do not fabricate a source list or silently mutate the model's answer.
    flags = (list(quality.get("schema_flags", [])) +
             list(quality.get("safety_flags", [])) +
             list(quality.get("provenance", {}).get("flags", [])))
    return (
        "Tu borrador previo fue RECHAZADO: " +
        ", ".join(sorted(set(flags))[:16]) +
        ". Elimina referencias SQL de tablas NO consultadas y afirmaciones "
        "de ejecución. La lectura ÚNICA fue ITIL.taIncidente "
        "(metadatos históricos, no causa raíz). "
        "Usa fuentes EXACTAMENTE [\"ITIL.taIncidente\"] y "
        "evidence_refs no vacío, solo E1/E2. "
        "Describe las verificaciones pendientes en lenguaje natural, "
        "sin nombres SQL hipotéticos. Nunca elimines una prueba faltante "
        "ni inventes que se realizó; usa hipótesis y condiciones. "
        "Reescribe TODO el objeto JSON con sus pasos completos, "
        "ejecutado:false y confirmado:false."
    )

"""Fail-closed functional diagnostic contract with true evidence boundaries.

A structural JSON PASS is NOT a functional PASS. The target of a domain
check may not be the ITIL incident envelope unless the problem itself is
about ITIL. A registered Hand alone is not proof of execution; every
business datum stays PENDING until a separately verified receipt exists.
"""
from __future__ import annotations
import json,re,unicodedata
from typing import Mapping
from .functional_domain_v2 import DOMAINS,route,normalize

SCHEMA="else.itil.functional-diagnostic-plan.v2"
GATE="else.itil.functional-contract-gate.v2"
KNOWN_SOURCE="ITIL.taIncidente"
SQL_OBJECT=re.compile(
  r'(?<![A-Za-z0-9_@])(?:ITIL|SEC|ADM|COM|DIS|DIST|DBO)\s*\.\s*'
  r'(?:ta|tb|tbl|vw|sp|fn)[A-Za-z0-9_]+\b',re.I)
SQL_BARE=re.compile(r'(?<![A-Za-z0-9_])(?:ta|tb|tbl)[A-Z][A-Za-z0-9_]+\b')
READ_CLAIMS=re.compile(
  r'\b(?:(?:ya\s+)?se\s+(?:verific[oó]|corrigi[oó]|ejecut[oó])'
  r'(?:\s+que)?|se (?:confirm[oó]|encontr[oó]|demostr[oó]) que|'
  r'hemos (?:consultado|modificado)|est[aá] resuelto)\b',re.I)
BOILERPLATE=re.compile(
  r'^(?:datos|estado|validar estado|resultado|informaci[oó]n|verificar|'
  r'configuraci[oó]n|cuenta|incidente|ticket|soluci[oó]n|'
  r'registro|registros|permisos)$',re.I)
ITIL_PROXY=re.compile(
  r'ITIL\.taIncidente|(?:estado|cierre|apertura|asignaci[oó]n)'
  r'.{0,35}(?:ticket|expediente|incidente)|'
  r'(?:ticket|expediente|incidente).{0,40}'
  r'(?:abierto|cerrado|pendiente|resuelto)',re.I)
VAGUE_PROBE=re.compile(
  r'(?:validar|confirmar|verificar|revisar)\s+(?:estado|datos|sistema|'
  r'permisos|funcionalidad|informaci[oó]n|registro)\s*$',
  re.I)
UNSAFE_SQL=re.compile(
  r'(?i)\b(?:UPDATE|DELETE\s+FROM|DROP\s+TABLE|INSERT\s+INTO|'
  r'TRUNCATE\s+TABLE|ALTER\s+TABLE)\s+'
  r'(?:[A-Za-z_][\w.]*)')

UNVERIFIED_CREDENTIAL=re.compile(
  r'(?i)(?:\b(?:enviar|envie|comparta|proporcione|revele|obtener)\b'
  r'.{0,55}\b(?:contrase(?:ñ|n)a|password|clave de acceso)\b|'
  r'\b(?:contrase(?:ñ|n)a|password|clave de acceso)\b'
  r'.{0,40}\b(?:especifica|específica|actual|deseada)\b)')
VAGUE_TARGET=re.compile(
  r'(?i)\b(?:campo objetivo|dato solicitado|resultado esperado|'
  r'informaci[oó]n requerida|valor actual debe coincidir con el valor '
  r'requerido)\b')
NUMERIC_LITERAL=re.compile(r'(?<![a-zA-Z0-9])\d+(?:[.,]\d+)*(?![a-zA-Z0-9])')
QUOTED_ROLE=re.compile(
  r'(?i)\b(?:rol|perfil)\s+[\"\']([^\"\']{3,60})[\"\']')

def strings(value):
    if type(value) is str:return [value]
    if type(value) is list:return [v for item in value for v in strings(item)]
    if type(value) is dict:return [v for item in value.values() for v in strings(item)]
    return []

def sql_mentions(value):
    data="\n".join(strings(value))
    qualified=set(x.group().replace(" ","").upper() for x in SQL_OBJECT.finditer(data))
    bare=set(x.group() for x in SQL_BARE.finditer(data)
             if x.group().casefold()!="taincidente")
    return sorted(qualified),sorted(bare)

def evidence_boundary(plan:dict,route_data:dict)->list[str]:
    flags=[]
    # Refs describe a historical request snapshot, not live business data.
    if plan.get("observed_sources")!=[KNOWN_SOURCE] or plan.get("evidence_refs")!=["E1"]:
        flags.append("SNAPSHOT_SOURCE_AND_E1_REQUIRED")
    if (plan.get("domain_evidence_status")!="NOT_READ" or
        plan.get("executed") is not False or
        plan.get("repair_certified") is not False or
        plan.get("root_cause_certified") is not False):
        flags.append("FALSE_OBSERVATION_EXECUTION_OR_REPAIR")
    qualified,bare=sql_mentions(plan)
    unobserved=[x for x in qualified if x!="ITIL.TAINCIDENTE"]
    if unobserved or bare:
        flags.append("UNOBSERVED_SQL_OBJECT_CITED")
    # com.pe SMTP domain is NOT a SQL schema.table. No special strings
    # need to be rewritten or removed to make it pass.
    if any(re.search(r'\bWITHHELD\b',x,re.I) for x in strings(plan)):
        flags.append("HISTORICAL_SENTINEL_LAUNDERED_AS_STATE")
    return flags

def check_plan(plan:dict,request_text:str,route_data:dict)->dict:
    flags=[]
    if type(plan) is not dict or type(route_data) is not dict:
        return {"schema":GATE,"accepted":False,"functionally_actionable":False,
                "flags":["PLAN_OR_ROUTE_INVALID"]}
    required={
        "schema","domain","target_system","intent","ticket_fact_quotes",
        "hypotheses","checks","missing_evidence","observed_sources",
        "evidence_refs","domain_evidence_status","executed",
        "repair_certified","root_cause_certified"}
    if set(plan)!=required:flags.append("OUTPUT_SCHEMA_DRIFT")
    if plan.get("schema")!=SCHEMA:flags.append("PLAN_SCHEMA_INVALID")
    domain=route_data.get("domain")
    if plan.get("domain")!=domain or plan.get("target_system")!=route_data.get("target_system"):
        flags.append("DOMAIN_TARGET_MISMATCH")
    flags+=evidence_boundary(plan,route_data)
    intent=plan.get("intent")
    if type(intent) is not str or len(intent.strip())<18 or len(intent)>520:
        flags.append("INTENT_NOT_ACTIONABLE")
    elif READ_CLAIMS.search(intent):
        flags.append("UNSUPPORTED_READ_OR_REPAIR_CLAIM")
    facts=plan.get("ticket_fact_quotes")
    if type(facts) is not list or not 1<=len(facts)<=3 or any(type(x) is not str
       or not 8<=len(x)<=180 for x in facts):
        flags.append("EXACT_GROUNDED_FACT_QUOTE_REQUIRED")
    else:
        text=normalize(request_text)
        for quote in facts:
            if normalize(quote.strip()) not in text:
                flags.append("FACT_NOT_SUBSTRING_OF_REQUEST")
                break
    hypotheses=plan.get("hypotheses")
    if type(hypotheses) is not list or not 1<=len(hypotheses)<=3 or any(
            type(x) is not str or not 15<=len(x)<=350 for x in hypotheses):
        flags.append("HYPOTHESIS_INVALID")
    missing=plan.get("missing_evidence")
    if type(missing) is not list or not 1<=len(missing)<=4 or any(
            type(x) is not str or len(x.strip())<12 for x in missing):
        flags.append("MISSING_EVIDENCE_NOT_DECLARED")
    checks=plan.get("checks")
    if type(checks) is not list or not 1<=len(checks)<=2:
        flags.append("DOMAIN_FUNCTIONAL_CHECK_REQUIRED")
        checks=[]
    check_fields={
        "target_system","business_object","input_identifier",
        "observable","expected","if_expected","if_different",
        "execution","observation_status"}
    tested=0
    for check in checks:
        if type(check) is not dict or set(check)!=check_fields:
            flags.append("CHECK_SCHEMA_INVALID")
            continue
        if check["target_system"]!=route_data.get("target_system"):
            flags.append("CHECK_NOT_IN_ROUTED_SYSTEM")
        if check.get("execution")!="NOT_EXECUTED" or check.get("observation_status")!="NOT_READ":
            flags.append("CHECK_FALSELY_CLAIMS_EXECUTION")
        for key in ("business_object","input_identifier","observable",
                    "expected","if_expected","if_different"):
            value=check.get(key)
            if type(value) is not str or not 8<=len(value)<=360:
                flags.append("CHECK_FIELD_TOO_SHORT_OR_INVALID")
                continue
            if READ_CLAIMS.search(value):
                flags.append("UNSUPPORTED_READ_OR_REPAIR_CLAIM")
        if domain!="ITIL_PROCESS" and any(
            ITIL_PROXY.search(str(check.get(key,""))) for key in (
            "business_object","observable","expected",
            "if_expected","if_different")):
            flags.append("ITIL_ENVELOPE_USED_AS_DOMAIN_EVIDENCE")
        if any(BOILERPLATE.fullmatch(str(check.get(key,"")).strip()) or
               VAGUE_PROBE.fullmatch(str(check.get(key,"")).strip())
               for key in ("business_object","observable","expected")):
            flags.append("NONDISCRIMINATING_GENERIC_CHECK")
        if check.get("if_expected")==check.get("if_different"):
            flags.append("CHECK_BOTH_BRANCHES_IDENTICAL")
        if (type(check.get("observable")) is str and
            type(check.get("expected")) is str and
            len(check["observable"].split())>=3 and
            len(check["expected"].split())>=3):
            tested+=1
    if not tested:flags.append("NO_DISCRIMINATING_OBSERVABLE")
    # Explicit inversion for numeric target requests. Current=0 must
    # not become "change TO 0" when goal is to fix a zero value.
    normalized=normalize(request_text)
    if (re.search(r'(?:aparece|actualmente|dice|muestra|esta)\s*(?:s/?\.?\s*)?0(?:[.,]00)?\b',normalized) and
        re.search(r'(?:actualizar|cambiar|establecer|poner|fijar)(?:\s+\w+){0,4}\s+a\s*(?:s/?\.?\s*)?0(?:[.,]00)?\b',
                  normalize(json.dumps(plan,ensure_ascii=False)))):
        flags.append("REQUEST_INTENT_REVERSED_ZERO_VALUE")
    if UNSAFE_SQL.search("\n".join(strings(plan))):
        flags.append("EXECUTABLE_SQL_MUTATION_NOT_ALLOWED")
    # A concrete enterprise threshold must come from the request, a
    # verified domain receipt or a policy source. We have only the
    # historic ticket, so do not allow silently invented numbers.
    requested_numbers=set(NUMERIC_LITERAL.findall(normalize(request_text)))
    for step in checks:
        if type(step) is not dict:continue
        estimated=set(NUMERIC_LITERAL.findall(normalize(
            str(step.get("expected","")))))
        if estimated-requested_numbers:
            flags.append("NUMERIC_EXPECTATION_NOT_GROUNDED")
        if VAGUE_TARGET.search(str(step.get("observable",""))+" "+
                               str(step.get("expected",""))):
            flags.append("GENERIC_TARGET_NOT_MEASURABLE")
        if domain=="IAM":
            for role in QUOTED_ROLE.findall(str(step.get("expected",""))):
                if normalize(role) not in normalize(request_text):
                    flags.append("ROLE_NAME_NOT_IN_VERIFIED_EVIDENCE")
    if UNVERIFIED_CREDENTIAL.search(" ".join(strings(plan))):
        flags.append("CREDENTIAL_DISCLOSURE_REQUEST")
    accepted=not bool(flags)
    return {
        "schema":GATE,
        "accepted":accepted,
        "functionally_actionable":accepted and domain!="UNKNOWN",
        "flags":sorted(set(flags)),
        "domain":domain,
        "business_source_accessed":False,
        "snapshot_only":True,
        "repair_certified":False,
        "independent_technical_accuracy_verified":False,
    }

def clarification(text:str,route_data:dict)->dict:
    """No LLM speculation for UNKNOWN. Preserve a concrete evidence request."""
    if route_data["domain"]!="UNKNOWN":raise ValueError("KNOWN_DOMAIN_CLARIFICATION")
    return {
        "schema":SCHEMA,"domain":"UNKNOWN",
        "target_system":route_data["target_system"],
        "intent":"Se necesita identificar el sistema, módulo y operación que falla.",
        "ticket_fact_quotes":[text.strip()[:120]] if text.strip() else [],
        "hypotheses":["No hay suficientes datos para discriminar una causa funcional."],
        "checks":[],
        "missing_evidence":[
            "Identifique el sistema y módulo donde ocurre el problema.",
            "Envíe mensaje o captura del error y el paso exacto que lo provoca."],
        "observed_sources":[KNOWN_SOURCE],"evidence_refs":["E1"],
        "domain_evidence_status":"NOT_READ",
        "executed":False,"repair_certified":False,
        "root_cause_certified":False,
    }

"""Business-specific, evidence-only triage for August SIELSE ITIL cases.

Verified ITIL module/company and the untrusted request text choose a safe QA
read plan. Historical solutions, personnel identity and LLM-generated SQL
are never inputs. Plans are NOT repairs and never imply an authenticated
ITIL↔OT business join without independently verified SIELSE evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
import unicodedata

from .company_routed_verified import TARGETS, OT_RE, SUPPLY_RE
# Keep portable validation independent of ELSE CORE native package presence
# in GitHub CI; the replay checks this literal against the actual O5 Hand.
COMPANY_CAPABILITY="itil.aug2026.company-routed-business-evidence.verify.v2"

class FunctionalTriageDenied(ValueError):
    pass

def demand(ok,message):
    if not ok:
        raise FunctionalTriageDenied(message)

def normalized(text):
    demand(type(text) is str and 10<len(text)<10000,
           "ITIL_CASE_REQUEST_NOT_BOUNDED")
    return ''.join(
        c for c in unicodedata.normalize('NFKD',text.lower())
        if not unicodedata.combining(c)
    )

@dataclass(frozen=True)
class FunctionalRule:
    kind:str
    expected_module:str
    predicates:tuple[str,...]
    mandatory_relations:tuple[str,...]
    next_read_profile:str
    mandatory_checks:tuple[str,...]
    denied_actions:tuple[str,...]
    provenance_code:str

RULES=(
  FunctionalRule(
    kind="RESOURCE_CODE_CORRECTION",
    expected_module="0101100123000",
    predicates=("cambiar el recurso","presupuesto"),
    mandatory_relations=(
      "dbo.taOrdenTrabajo.CodigoOrdenTrabajo",
      "dbo.taPresupuesto.CodigoOrdenTrabajo",
      "dbo.taPresupuestoTrabajoRecurso.CodigoOrdenTrabajo",
      "dbo.gnRecurso.CodigoRecurso",
    ),
    next_read_profile="QA_OT_RESOURCE_BUDGET_FIXED_SELECT",
    mandatory_checks=(
      "VERIFY_EXACT_OT_AND_COMPANY",
      "CHECK_BUDGET_STATE_AND_ORIGINAL_RESOURCE",
      "CHECK_REPLACEMENT_RESOURCE_IN_TYPED_CATALOG",
      "RECONCILE_BUDGET_COST_AND_AUDIT",
    ),
    denied_actions=(
      "NO_DIRECT_OT_STATE_UPDATE_AS_SUBSTITUTE_FOR_RESOURCE_CORRECTION",
      "NO_RESOURCE_MUTATION_WITHOUT_PRESENT_OT_AND_BUDGET",
    ),
    provenance_code="M0101100123000/f_ma_OTInstalacion.cs:1602-1629"
  ),
  FunctionalRule(
    kind="CLIENT_SURNAME_AND_OSINERGMIN",
    expected_module="0101100123000",
    predicates=("actualizacion de apellido","ot"),
    mandatory_relations=(
      "dbo.taOrdenTrabajo.CodigoOrdenTrabajo",
      "dbo.taOTInstalacion.CodigoOrdenTrabajo",
      "dbo.taOrdenTrabajoEstadoHistorico.CodigoOrdenTrabajo",
      "dbo.taOrdenTrabajo_ModificacionIN.CodigoOrdenTrabajo",
    ),
    next_read_profile="QA_OT_CLIENT_CHANGE_FISCAL_HISTORY_FIXED_SELECT",
    mandatory_checks=(
      "VERIFY_EXACT_OT_AND_COMPANY",
      "CHECK_PADRON_VERSUS_OT_IDENTITY_WITHOUT_EXPOSING_PII",
      "CHECK_OSINERGMIN_FISCALIZATION_STATE",
      "IF_ALREADY_REPORTED_BLOCK_IN_PLACE_OT_MODIFICATION",
      "IF_NEW_OT_REQUIRED_VERIFY_PRECEDING_OT_CANCEL_OR_REJECTION",
    ),
    denied_actions=(
      "NO_BLIND_CLIENT_IDENTITY_REWRITE",
      "NO_MUTATION_OF_FISCALIZED_OT",
    ),
    provenance_code="M0101100123000/f_ma_OTInstalacion.cs:4465-4473"
  ),
  FunctionalRule(
    kind="METER_EXECUTION_DATE_CORRECTION",
    expected_module="0101300100000",
    predicates=("fecha de cambio de medidor","suministro"),
    mandatory_relations=(
      "dbo.taOrdenTrabajo.CodigoOrdenTrabajo",
      "dbo.taOrdenTrabajo.FechaEjecucionInicio",
      "dbo.taOrdenTrabajo.FechaEjecucionFin",
      "dbo.taOrdenTrabajoAuditoriaCambio.CodigoOrdenTrabajo",
      "dbo.taMedidorSuministro.CodigoSuministro",
    ),
    next_read_profile="QA_OT_METER_DATE_AUDIT_FIXED_SELECT",
    mandatory_checks=(
      "VERIFY_EXACT_OT_SUPPLY_COMPANY_AND_BILLING_PERIOD",
      "CHECK_BOTH_EXECUTION_DATES_BEFORE_AND_AFTER_TARGET",
      "CHECK_METER_CHANGE_AND_BILLING_CONSISTENCY",
      "PRESERVE_ORIGINAL_AUDIT_TRAIL",
    ),
    denied_actions=(
      "NO_RAW_SQL_DATE_UPDATE_FROM_ITIL_TEXT",
      "NO_BILLING_DATE_REWRITE_WITHOUT_ACCOUNTING_IMPACT_REVIEW",
    ),
    provenance_code="M0101300100000/dstAdministradorClientes.xsd:541"
  ),
  FunctionalRule(
    kind="REOPEN_INSTALLATION_OT",
    expected_module="0101100123000",
    predicates=("aperturar ot","recurso"),
    mandatory_relations=(
      "dbo.taOrdenTrabajo.CodigoOrdenTrabajo",
      "dbo.taPresupuesto.CodigoOrdenTrabajo",
      "dbo.taOrdenTrabajoEstadoHistorico.CodigoOrdenTrabajo",
      "dbo.taPresupuestoTrabajoRecurso.CodigoOrdenTrabajo",
    ),
    next_read_profile="QA_OT_REOPEN_PERMISSION_FISCAL_HISTORY_FIXED_SELECT",
    mandatory_checks=(
      "VERIFY_EXACT_OT_AND_COMPANY",
      "VERIFY_SUPERVISOR_GROUP_9_BEFORE_REOPEN",
      "CHECK_SP_CONTROL_ATENCIONACCION_OT_IN_OSINERGMIN_GUARD",
      "REQUIRE_JUSTIFICATION_AND_RECORD_OPERATIONAL_STATE",
      "VERIFY_RESOURCE_CHANGE_ONLY_AFTER_ALLOWED_REOPEN",
    ),
    denied_actions=(
      "NO_DIRECT_OT_REOPEN_UPDATE",
      "NO_SUPERVISOR_OVERRIDE",
      "NO_OSINERGMIN_GUARD_BYPASS",
    ),
    provenance_code="M0101100123000/f_ma_OTInstalacion.cs:4525-4550"
  ),
  FunctionalRule(
    kind="ZERO_INITIAL_BUDGET_VOUCHER",
    expected_module="0101100116000",
    predicates=("comprobante","presupuesto inicial cero"),
    mandatory_relations=(
      "dbo.taOrdenTrabajo.CodigoOrdenTrabajo",
      "dbo.taPresupuesto.CodigoOrdenTrabajo",
      "dbo.taComprobante.CodigoOrdenTrabajo",
      "dbo.taComprobante.MontoTotal",
    ),
    next_read_profile="QA_OT_BUDGET_ZERO_VOUCHER_FIXED_SELECT",
    mandatory_checks=(
      "VERIFY_EXACT_OT_AND_COMPANY",
      "CHECK_BUDGET_TOTAL_AND_RECONCILE_EXCESS_MATERIAL",
      "VERIFY_VOUCHER_CAN_BE_EMITTED_WITH_NONZERO_VALID_AMOUNT",
      "REVIEW_ORIGINAL_VOUCHER_BEFORE_CANCEL_AND_REISSUE",
    ),
    denied_actions=(
      "NO_FORCE_ZERO_AMOUNT_VOUCHER",
      "NO_DIRECT_OVERRIDE_OF_BILLING_VALIDATION",
      "NO_COMPROBANTE_CANCELLATION_UNLESS_BUSINESS_TRANSACTION_VERIFIED",
    ),
    provenance_code="M0101100116000/f_ma_OTTrabajosVarios.cs:168-184"
  )
)
ALLOWED_PROFILES={r.next_read_profile:r for r in RULES}

def classify_text(text,module):
    norm=normalized(text)
    candidates=[r for r in RULES if r.expected_module==module
                and all(p in norm for p in r.predicates)]
    demand(len(candidates)==1,"CASE_FUNCTIONAL_RULE_AMBIGUOUS_OR_UNKNOWN")
    return candidates[0]

def plan_for_verified_case(*,request,receipt,verified_envelope_sha256,
                           signed_hmac_verified):
    """Receives only an independently verified company-routed receipt."""
    demand(type(receipt) is dict and
           receipt.get("schema")=="else.itil.aug2026.qa.company-routed-receipt.v2",
           "CASE_ITIL_COMPANY_RECEIPT_NOT_V2")
    demand(signed_hmac_verified is True and
           type(verified_envelope_sha256) is str and
           re.fullmatch(r"[a-f0-9]{64}",verified_envelope_sha256) is not None,
           "CASE_WINDOWS_EVIDENCE_NOT_AUTHENTICATED")
    company=receipt.get("itil_company")
    demand(type(company) is int and company in TARGETS,
           "CASE_ITIL_COMPANY_NOT_ALLOWLISTED")
    obs=receipt.get("observation")
    demand(type(obs) is dict and
           obs.get("qa_target")==TARGETS[company] and
           obs.get("schema")=="else.itil.aug2026.qa.company-routed-observation.v2" and
           obs.get("read_only") is True and obs.get("changes_executed") is False,
           "CASE_COMPANY_TARGET_NOT_TRUSTED")
    demand(receipt.get("historical_solution_read") is False
           and receipt.get("repair_certified") is False
           and receipt.get("itil_row_verified_from_corporate_sql") is True,
           "CASE_SOLUTION_LEAK_OR_FALSE_REPAIR")
    module=receipt.get("itil_module")
    demand(type(module) is str and re.fullmatch(r"\d{13}",module) is not None,
           "CASE_ITIL_MODULE_FORMAT_INVALID")
    ot_claims=set(OT_RE.findall(request))
    supply_claims=set(SUPPLY_RE.findall(request))
    demand(len(ot_claims)==1 and len(supply_claims)<=1,
           "CASE_REPORTED_IDENTIFIERS_AMBIGUOUS")
    exact_ot=next(iter(ot_claims))
    supply=next(iter(supply_claims)) if supply_claims else None
    demand(receipt.get("reported_ot_sha256")==sha256(exact_ot.encode()).hexdigest()
           and receipt.get("reported_supply_sha256")==(
               sha256(supply.encode()).hexdigest() if supply else None),
           "CASE_REQUEST_IDENTIFIER_NOT_BOUND_TO_SIGNED_RECEIPT")
    rule=classify_text(request,module)
    demand(receipt.get("claim_type")=="OT","CASE_OT_CLAIM_REQUIRED")
    counts=obs.get("counts")
    demand(type(counts) is dict and "order" in counts and
           type(counts["order"]) is int and counts["order"] in (0,1,2),
           "CASE_OT_QUERY_NOT_PRESENT")
    exact=counts["order"]==1
    duplicates=counts["order"]==2
    decision=(
       "QA_RECORD_IDENTIFIED_ADDITIONAL_GATES_REQUIRED" if exact else
       "QA_DUPLICATE_OT_REQUIRES_REVIEW" if duplicates else
       "QA_REFERENCE_NOT_FOUND_ROUTE_TO_VERIFIED_BUSINESS_SOURCE"
    )
    return {
       "schema":"else.itil.aug2026.functional-case-triage.v1",
       "case_sha256":receipt["case_sha256"],
       "itil_module":module,
       "company":company,
       "qa_target":obs["qa_target"],
       "functional_kind":rule.kind,
       "request_sha256":sha256(request.encode()).hexdigest(),
       "signed_envelope_sha256":verified_envelope_sha256,
       "bound_capability":COMPANY_CAPABILITY,
       "decision":decision,
       "next_read_profile":rule.next_read_profile,
       "source_code_evidence":rule.provenance_code,
       "mandatory_relations":list(rule.mandatory_relations),
       "mandatory_checks":list(rule.mandatory_checks),
       "denied_actions":list(rule.denied_actions),
       "historical_solution_used":False,
       "business_record_identified":exact,
       "itil_business_foreign_key_verified":False,
       "repair_permitted":False,
       "repair_executed":False,
    }

def audit_real_five():
    from .company_routed_verified import verify_all
    from .aug2026_sap_ot_verified import data,eligible
    from .positive_control_verified import verify_positive_controls
    from .company_routed_o5_hand import (
        AuthorizedCompanyRoutedReceipt,build_company_routed_router,
        CAPABILITY as NATIVE_COMPANY_CAPABILITY
    )
    from .company_routed_verified import SOURCE,SOURCE_SHA,ROOT,DELIVERY,digest
    from else_core.hand_kernel import Outcome

    verify_positive_controls()
    demand(COMPANY_CAPABILITY==NATIVE_COMPANY_CAPABILITY,
           "CASE_NATIVE_O5_CAPABILITY_ID_DRIFT")
    found=verify_all()
    cohort,manifest=data()
    cases=sorted(eligible(cohort))
    demand(len(cases)==5,"CASE_EXPECTED_FIVE_OT_TICKETS")
    result=[]
    for case in cases:
        demand(case in found,"CASE_NOT_IN_COMPANY_SIGNED_READS")
        row=found[case]
        job_id=digest((DELIVERY+":"+case+":"+manifest["blind_sha256"]).encode())[:32]
        file=ROOT/"outbox"/(job_id+".private.json")
        env_sha=digest(file.read_bytes())
        owner=AuthorizedCompanyRoutedReceipt(
             file,env_sha,case,row["itil_company"],
             SOURCE_SHA,len(SOURCE.read_bytes()),cohort[case]["incident_text_redacted"])
        _,router,op=build_company_routed_router(owner)
        native=router.route(op)
        demand(
            native.outcome==Outcome.PASS
            and native.guardian_result.verification.passed is True
            and native.guardian_result.verification.independent is True
            and native.guardian_result.executions==1,
            "CASE_NATIVE_O5_O13_O15_NOT_PASS")
        value=plan_for_verified_case(
            request=cohort[case]["incident_text_redacted"],
            receipt=row["receipt"],
            verified_envelope_sha256=env_sha,
            signed_hmac_verified=row["verified_windows_hmac"])
        result.append(value)
    kinds=[x["functional_kind"] for x in result]
    demand(len(set(kinds))==5,"CASE_MISSING_FUNCTIONAL_DISTINCTION")
    return result

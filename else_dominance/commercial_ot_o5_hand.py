"""Native CORE O5/O13/O15 Hand for actual August QA commercial OT reads.

Distinct executable (fixed C# SELECT dbo.taOrdenTrabajo) and independent
receipt verifier. Bounded to an OT uniquely mentioned in redacted incident
text; the user-provided mention is not a certified corporate ITIL join.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json,re

from else_core.guardian import (
    BoundaryObservation,CanonicalImplementationPolicy,ExecutionGuardian,
    ExecutorIdentity,FaultClass,TrustDomainPolicy,TrustProvenance)
from else_core.hand_kernel import (
    FieldContract,FunctionalHandAdapter,GuardianPolicy,HandCapability,
    HandEvidence,HandOperation,HandRegistry,HandRouter,HandVerb,
    RepoProjectScope)
from else_core.source_truth import canonical_source_manifest_sha256

CAPABILITY="itil.qa.aug2026.commercial-ot.receipt.readonly.v1"
REPO="gcpaccori/ELSE-ITIL-SUP"
PROJECT="ELSE-ITIL-AUG2026-QA"
SOURCE_PATH="qa/AugCommercialOtRead.cs"
RECEIPT_SCHEMA="else.itil.aug2026.commercial-ot-receipt.v2"
OBS_SCHEMA="else.itil.aug2026.qa.commercial-ot-readonly.v2"
QUERY="QA_COMERCIAL_OT_BY_CODE_V2"
QA_TARGET="ELSE70/dbComercial001_D"
TABLE="dbo.taOrdenTrabajo"
EXEC_DOMAIN="itil-aug2026-commercial-ot-executor"
VERIFY_DOMAIN="itil-aug2026-commercial-ot-independent-verifier"
HEX=re.compile(r"[0-9a-f]{64}\Z")
OT_RE=re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)"
                 r"\s*[:#=-]?\s*(\d{4,19})\b",re.I)
OBS_KEYS={
    "schema","qa_target","source","query_id","order_sha256",
    "order_rows","order_found","codigo_estado_orden_trabajo",
    "codigo_subestado_orden_trabajo","codigo_tipo_orden_trabajo",
    "codigo_subtipo_orden_trabajo","fecha_registro_solicitud_present",
    "fecha_ejecucion_inicio_present","fecha_ejecucion_fin_present","read_only",
    "changes_executed","read_utc",
}
RECEIPT_KEYS={
    "schema","case_sha256","reported_ot_sha256",
    "reader_source_sha256","observation",
    "business_join_certified","root_cause_certified",
    "repair_certified","read_only",
}

class CommercialReceiptDenied(ValueError):pass

def demand(v,why):
    if not v:raise CommercialReceiptDenied(why)

def unique_json(raw):
    def pairs(xs):
        val={}
        for k,v in xs:
            demand(k not in val,"DUPLICATE_JSON_PROPERTY")
            val[k]=v
        return val
    obj=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(
            CommercialReceiptDenied("NONFINITE_JSON")))
    demand(type(obj) is dict,"RECEIPT_JSON_OBJECT_REQUIRED")
    return obj

def unique_ot(text:str)->str:
    demand(type(text) is str and 20<=len(text)<=3000,
           "REDACTED_OT_CASE_NOT_VALID")
    values=set(OT_RE.findall(text))
    demand(len(values)==1,"ONE_REPORTED_OT_REQUIRED")
    return next(iter(values))

@dataclass(frozen=True)
class AuthorizedCommercialOtReceipt:
    path:Path
    pinned_sha256:str
    case_sha256:str
    source_sha256:str
    source_bytes:int
    redacted_incident_text:str

    def __post_init__(self):
        demand(isinstance(self.path,Path) and self.path.is_absolute(),
               "RECEIPT_ABSOLUTE_PATH_REQUIRED")
        for name in ("pinned_sha256","case_sha256","source_sha256"):
            v=getattr(self,name)
            demand(type(v) is str and HEX.fullmatch(v) is not None,
                   "SOURCE_SHA_INVALID_"+name)
        demand(type(self.source_bytes) is int
               and 1<=self.source_bytes<=5_000_000,
               "SOURCE_CODE_SIZE_INVALID")
        unique_ot(self.redacted_incident_text)

    @property
    def reported_ot_sha256(self):
        return sha256(unique_ot(self.redacted_incident_text).encode()).hexdigest()

    def source_receipt(self):
        files=[{"path":SOURCE_PATH,"bytes":self.source_bytes,
                "sha256":self.source_sha256}]
        return {
            "schema":"elsecore.o1-source-receipt.v1",
            "repo":REPO,"project":PROJECT,
            "source_manifest_sha256":canonical_source_manifest_sha256(files),
            "files":files,"tool_sha256":self.source_sha256}

    def read_verified(self):
        demand(self.path.is_file() and not self.path.is_symlink(),
               "COMM_RECEIPT_NOT_FILE")
        raw=self.path.read_bytes()
        demand(120<=len(raw)<=16000 and
               sha256(raw).hexdigest()==self.pinned_sha256,
               "RECEIPT_BYTES_CHANGED")
        r=unique_json(raw)
        demand(set(r)==RECEIPT_KEYS
               and r["schema"]==RECEIPT_SCHEMA
               and r["case_sha256"]==self.case_sha256
               and r["reported_ot_sha256"]==self.reported_ot_sha256
               and r["reader_source_sha256"]==self.source_sha256
               and r["read_only"] is True
               and r["business_join_certified"] is False
               and r["root_cause_certified"] is False
               and r["repair_certified"] is False,
               "COMM_RECEIPT_OWNER_OR_POLICY_VIOLATION")
        obs=r["observation"]
        demand(type(obs) is dict and set(obs)==OBS_KEYS
               and obs["schema"]==OBS_SCHEMA
               and obs["qa_target"]==QA_TARGET
               and obs["source"]==TABLE
               and obs["query_id"]==QUERY
               and obs["order_sha256"]==self.reported_ot_sha256
               and type(obs["order_rows"]) is int
               and obs["order_rows"] in (0,1)
               and type(obs["order_found"]) is bool
               and obs["order_found"]==(obs["order_rows"]==1)
               and obs["read_only"] is True
               and obs["changes_executed"] is False,
               "COMM_OBSERVATION_NOT_FIXED_QA_QUERY")
        for k in ("fecha_registro_solicitud_present","fecha_ejecucion_inicio_present",
                  "fecha_ejecucion_fin_present"):
            demand(type(obs[k]) is bool and
                   (obs["order_found"] or obs[k] is False),
                   "COMM_DATE_FLAG_INVALID")
        for k in ("codigo_estado_orden_trabajo",
                  "codigo_subestado_orden_trabajo","codigo_tipo_orden_trabajo",
                  "codigo_subtipo_orden_trabajo"):
            demand(type(obs[k]) is str and len(obs[k])<=100 and
                   (obs["order_found"] or obs[k]==""),
                   "COMM_STATUS_FIELD_INVALID")
        demand(type(obs["read_utc"]) is str
               and re.fullmatch(r"\d{4}-\d\d-\d\dT.{10,35}",
                                obs["read_utc"]) is not None,
               "COMM_READ_TIME_NOT_RECORDED")
        return raw,r

def _outputs(owner,body):
    observation=body["observation"]
    return {
      "case_sha256":owner.case_sha256,
      "receipt_sha256":owner.pinned_sha256,
      "reported_ot_sha256":owner.reported_ot_sha256,
      "source":QA_TARGET+"/"+TABLE,
      "order_found":observation["order_found"],
      "order_rows":observation["order_rows"],
      "order_state_code":observation["codigo_estado_orden_trabajo"],
      "order_type_code":observation["codigo_tipo_orden_trabajo"],
      "date_start_present":observation["fecha_ejecucion_inicio_present"],
      "date_end_present":observation["fecha_ejecucion_fin_present"],
      "provenance_verified":True,"read_only":True,
      "business_entity_join_certified":False,
      "repair_certified":False,
      "access_mode":"PINNED_COMMERCIAL_OT_QA_RECEIPT_ONLY",
    }

def _bound(op,owner):
    demand(dict(op.inputs)=={
        "case_sha256":owner.case_sha256,
        "receipt_sha256":owner.pinned_sha256,
        "reported_ot_sha256":owner.reported_ot_sha256},
        "COMM_HAND_INPUT_NOT_EXACT_OWNER")
    demand(op.scope.repo==REPO and op.scope.project==PROJECT
           and op.scope.source_set_sha256==
                owner.source_receipt()["source_manifest_sha256"]
           and op.requested_mutations==(),
           "COMM_HAND_SOURCE_OR_REPAIR_POLICY_INVALID")

def build_commercial_ot_router(owner:AuthorizedCommercialOtReceipt):
    from .commercial_ot_o5_verifier import CommercialOtIndependentVerifier
    verifier=CommercialOtIndependentVerifier(owner)
    identity=verifier.evaluator_identity()
    impl_sha=sha256(Path(__file__).read_bytes()).hexdigest()
    executor=ExecutorIdentity(executor_id="aug2026-commercial-ot-fixed-qa",
        provenance=TrustProvenance(
            trust_domain_id=EXEC_DOMAIN,
            capability_id=CAPABILITY,implementation_sha256=impl_sha,
            tool_sha256=owner.source_sha256))
    def preflight(op):
        try:
            _bound(op,owner)
            owner.read_verified()
            return BoundaryObservation(True)
        except (CommercialReceiptDenied,ValueError,OSError):
            return BoundaryObservation(False,FaultClass.EVIDENCE_INVALID,
                                       "COMMERCIAL_RECEIPT_PREFLIGHT_REJECTED")
    def execute(op):
        _bound(op,owner)
        raw,parsed=owner.read_verified()
        return HandEvidence(
            subject_sha256=op.scope.source_set_sha256,
            evidence_id=sha256(raw).hexdigest(),
            outputs=_outputs(owner,parsed),
            artifact_sha256=sha256(raw).hexdigest(),
            mutation_receipts=())
    def observe(op,evidence):
        try:
            _bound(op,owner)
            raw,parsed=owner.read_verified()
            demand(dict(evidence.outputs)==_outputs(owner,parsed)
                   and evidence.evidence_id==sha256(raw).hexdigest(),
                   "COMM_OUTPUT_CHANGED")
            return BoundaryObservation(True)
        except (CommercialReceiptDenied,ValueError,OSError):
            return BoundaryObservation(False,FaultClass.EVIDENCE_INVALID,
                                       "COMMERCIAL_OUTPUT_RECHECK_REJECTED")
    output={
        "case_sha256":str,"receipt_sha256":str,"reported_ot_sha256":str,
        "source":str,"order_found":bool,"order_rows":int,
        "order_state_code":str,"order_type_code":str,
        "date_start_present":bool,"date_end_present":bool,
        "provenance_verified":bool,"read_only":bool,
        "business_entity_join_certified":bool,"repair_certified":bool,
        "access_mode":str,
    }
    capability=HandCapability(
        capability_id=CAPABILITY,version="1.0.0",
        verb=HandVerb.VERIFY,
        input_contract=tuple(FieldContract(k,str) for k in (
            "case_sha256","receipt_sha256","reported_ot_sha256")),
        output_contract=tuple(FieldContract(k,v) for k,v in output.items()),
        repo_scope=(REPO,),project_scope=(PROJECT,),
        allowed_mutations=(),required_evidence_layers=("O1",),
        rollback_identity="rollback:itil.aug2026.commercial-ot.readonly.none",
        quarantine_identity="quarantine:itil.aug2026.commercial-ot.qa.v1",
        guardian_policy=GuardianPolicy("o13.itil.aug2026.commercial-ot.v1"),
        adapter=FunctionalHandAdapter(executor,execute,
                preflight_fn=preflight,observe_fn=observe))
    guardian=ExecutionGuardian(
        trust_domains=(
            TrustDomainPolicy(EXEC_DOMAIN,(CAPABILITY,),
                (CanonicalImplementationPolicy(
                    impl_sha,tool_sha256s=(owner.source_sha256,)),)),
            TrustDomainPolicy(VERIFY_DOMAIN,(CAPABILITY,),
                (CanonicalImplementationPolicy(
                    identity.evaluator_sha256,
                    tool_sha256s=(identity.provenance.tool_sha256,)),)),
        ),max_recoveries=0)
    router=HandRouter(HandRegistry((capability,)),guardian,
                     {CAPABILITY:verifier})
    receipt=owner.source_receipt()
    operation=HandOperation(
        capability_id=CAPABILITY,
        scope=RepoProjectScope(REPO,PROJECT,receipt["source_manifest_sha256"]),
        inputs={"case_sha256":owner.case_sha256,
                "receipt_sha256":owner.pinned_sha256,
                "reported_ot_sha256":owner.reported_ot_sha256},
        requested_mutations=(),evidence_receipts={"O1":receipt})
    return capability,router,operation

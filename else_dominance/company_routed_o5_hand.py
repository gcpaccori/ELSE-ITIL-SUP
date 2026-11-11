"""Native ELSE CORE O5 VERIFY hand over authenticated company-routed QA receipts.

Windows alone executed the fixed SIELSEAccessData .NET selects; this hand
authenticates and exposes their bounded, read-only facts. It never dispatches
new SQL or treats zero results as evidence of business nonexistence.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from base64 import b64decode
import hmac,json,re

from else_core.guardian import (
    BoundaryObservation,CanonicalImplementationPolicy,ExecutionGuardian,
    ExecutorIdentity,FaultClass,TrustDomainPolicy,TrustProvenance
)
from else_core.hand_kernel import (
    FieldContract,FunctionalHandAdapter,GuardianPolicy,HandCapability,
    HandEvidence,HandOperation,HandRegistry,HandRouter,HandVerb,RepoProjectScope
)
from else_core.source_truth import canonical_source_manifest_sha256

from .company_routed_verified import (
    SOURCE,SOURCE_SHA,SOURCE_PATH,DELIVERY,RECEIPT,OBS,
    TARGETS,ENVELOPE_KEYS,RECEIPT_KEYS,OBS_KEYS,SAMPLE_SHA,
    LEGACY_ROOT, sha_str, parse_strict, digest
)

CAPABILITY="itil.aug2026.company-routed-business-evidence.verify.v2"
REPO="gcpaccori/ELSE-ITIL-SUP"
PROJECT="ELSE-ITIL-AUG2026-QA"
EXEC_DOMAIN="itil-aug2026-company-routed-receipt-executor-v2"
VERIFY_DOMAIN="itil-aug2026-company-routed-independent-evaluator-v2"
HEX=re.compile(r"[0-9a-f]{64}\Z")

class CompanyRoutedReceiptDenied(ValueError):pass

def demand(condition,msg):
    if not condition:raise CompanyRoutedReceiptDenied(msg)

@dataclass(frozen=True)
class AuthorizedCompanyRoutedReceipt:
    path:Path
    pinned_envelope_sha256:str
    case_sha256:str
    itil_company:int
    source_sha256:str
    source_bytes:int
    redacted_incident_text:str

    def __post_init__(self):
        demand(isinstance(self.path,Path) and self.path.is_absolute(),
               "COMPANY_HAND_PATH_NOT_ABSOLUTE")
        for field in ("pinned_envelope_sha256","case_sha256","source_sha256"):
            value=getattr(self,field)
            demand(type(value) is str and HEX.fullmatch(value) is not None,
                   "COMPANY_HAND_BAD_SHA_"+field)
        demand(type(self.itil_company) is int and self.itil_company in TARGETS,
               "COMPANY_HAND_UNAUTHORIZED_COMPANY")
        demand(type(self.source_bytes) is int and 1<self.source_bytes<200000,
               "COMPANY_HAND_READER_SIZE_INVALID")
        demand(type(self.redacted_incident_text) is str
               and 1<len(self.redacted_incident_text)<=10000,
               "COMPANY_HAND_REDACTED_TEXT_MISSING")

    def source_receipt(self):
        files=[{"path":SOURCE_PATH,"bytes":self.source_bytes,
                "sha256":self.source_sha256}]
        return {
            "schema":"elsecore.o1-source-receipt.v1",
            "repo":REPO,"project":PROJECT,
            "source_manifest_sha256":canonical_source_manifest_sha256(files),
            "files":files,"tool_sha256":self.source_sha256,
        }

    def read_verified(self):
        demand(self.path.is_file() and not self.path.is_symlink(),
               "COMPANY_HAND_RECEIPT_PATH_INVALID")
        raw=self.path.read_bytes()
        demand(400<len(raw)<20000 and digest(raw)==self.pinned_envelope_sha256,
               "COMPANY_HAND_ENVELOPE_NOT_PINNED")
        env=parse_strict(raw)
        demand(type(env) is dict and set(env)==ENVELOPE_KEYS
               and env["schema"]==DELIVERY
               and env["case_sha256"]==self.case_sha256
               and env["sample_sha256"]==SAMPLE_SHA
               and env["job_id"]==digest((DELIVERY+":"+self.case_sha256+":"+
                  env["blind_cohort_sha256"]).encode())[:32]
               and self.path.name==env["job_id"]+".private.json"
               and env["source_sha256"]==self.source_sha256==SOURCE_SHA
               and env["read_only"] is True
               and env["changes_executed"] is False
               and env["sql_executed_on_windows"] is True,
               "COMPANY_HAND_WRONG_V2_OWNER")
        source=SOURCE.read_bytes()
        demand(digest(source)==self.source_sha256 and len(source)==self.source_bytes,
               "COMPANY_HAND_CSHARP_BYTES_DRIFT")
        inner=b64decode(env["receipt_json_base64"],validate=True)
        demand(digest(inner)==env["receipt_sha256"],"COMPANY_HAND_RECEIPT_SEAL_INVALID")
        keyfile=LEGACY_ROOT/"worker_hmac.private"
        demand(keyfile.is_file() and not keyfile.is_symlink()
               and keyfile.stat().st_mode&0o077==0,"COMPANY_HAND_KEY_PERMISSIONS")
        key=keyfile.read_bytes()
        demand(len(key)==32,"COMPANY_HAND_HMAC_KEY_INVALID")
        msg=f'{DELIVERY}:{env["job_id"]}:{SOURCE_SHA}:{env["receipt_sha256"]}'.encode()
        demand(hmac.compare_digest(hmac.new(key,msg,"sha256").hexdigest(),
                                   env["hmac_sha256"]),"COMPANY_HAND_HMAC_REJECTED")
        receipt=parse_strict(inner)
        demand(type(receipt) is dict and set(receipt)==RECEIPT_KEYS
               and receipt["schema"]==RECEIPT
               and receipt["case_sha256"]==self.case_sha256
               and receipt["itil_company"]==self.itil_company
               and receipt["itil_row_verified_from_corporate_sql"] is True
               and receipt["source_sha256"]==SOURCE_SHA
               and receipt["historical_solution_read"] is False
               and receipt["corporate_itil_business_join_certified"] is False
               and receipt["root_cause_certified"] is False
               and receipt["repair_certified"] is False,
               "COMPANY_HAND_UNVERIFIED_ITIL_COMPANY")
        obs=receipt["observation"]
        demand(type(obs) is dict and set(obs)==OBS_KEYS
               and obs["schema"]==OBS
               and obs["qa_target"]==TARGETS[self.itil_company]
               and obs["read_only"] is True
               and obs["changes_executed"] is False,
               "COMPANY_HAND_WRONG_COMMERCIAL_DB")
        ots=set(re.findall(
            r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)\s*[:#=-]?\s*(\d{4,19})\b",
            self.redacted_incident_text,re.I))
        sups=set(re.findall(r"\bsuministro\s*[:#=-]?\s*(\d{4,19})\b",
             self.redacted_incident_text,re.I))
        demand(len(ots)<=1 and len(sups)<=1 and bool(ots or sups),
               "COMPANY_HAND_AMBIGUOUS_TICKET_IDS")
        demand(receipt["claim_type"]==("OT" if ots else "SUPPLY")
               and receipt["reported_ot_sha256"]==(
                    sha_str(next(iter(ots))) if ots else None)
               and receipt["reported_supply_sha256"]==(
                    sha_str(next(iter(sups))) if sups else None),
               "COMPANY_HAND_FALSE_TICKET_BINDING")
        columns=({"order","installation","interior","meter"} |
                 ({"supply","orders_by_supply","exact_ot_supply"} if sups else set())
                 if ots else
                 {"supply","orders_by_supply","massive_installation","installation_owner"})
        counts=obs["counts"]
        demand(type(counts) is dict and set(counts)==columns
               and all(type(v) is int and v in (0,1,2) for v in counts.values()),
               "COMPANY_HAND_ROW_COUNTS_NOT_FIXED_QUERY")
        return raw,receipt

def outputs(owner,body):
    return {
        "case_sha256":owner.case_sha256,
        "envelope_sha256":owner.pinned_envelope_sha256,
        "itil_company":owner.itil_company,
        "itil_authority":"ELSE70/dbITIL_D/dbo.taIncidente",
        "qa_target":TARGETS[owner.itil_company],
        "claim_type":body["claim_type"],
        "exact_qa_hits":sum(body["observation"]["counts"].values()),
        "itil_company_provenance_verified":True,
        "read_only":True,
        "corporate_business_join_certified":False,
        "global_nonexistence_certified":False,
        "repair_certified":False,
        "access_mode":"SIGNED_COMPANY_SCOPED_QA_RECEIPT_V2_ONLY",
    }

def bound(op,owner):
    if (dict(op.inputs)!={
        "case_sha256":owner.case_sha256,
        "envelope_sha256":owner.pinned_envelope_sha256,
        "itil_company":owner.itil_company}
        or op.scope.repo!=REPO or op.scope.project!=PROJECT
        or op.scope.source_set_sha256!=owner.source_receipt()["source_manifest_sha256"]
        or op.requested_mutations!=()):
        raise CompanyRoutedReceiptDenied("COMPANY_HAND_OPERATION_UNBOUND")

def build_company_routed_router(owner):
    from .company_routed_o5_verifier import CompanyRoutedIndependentVerifier
    verifier=CompanyRoutedIndependentVerifier(owner)
    ident=verifier.evaluator_identity()
    impl=digest(Path(__file__).read_bytes())
    executor=ExecutorIdentity(
        executor_id="itil-aug2026-company-routed-readonly",
        provenance=TrustProvenance(
            trust_domain_id=EXEC_DOMAIN,capability_id=CAPABILITY,
            implementation_sha256=impl,tool_sha256=owner.source_sha256))

    def preflight(op):
        try:
            bound(op,owner);owner.read_verified()
            return BoundaryObservation(True)
        except (CompanyRoutedReceiptDenied,ValueError,KeyError,TypeError,OSError):
            return BoundaryObservation(False,FaultClass.EVIDENCE_INVALID,
                "COMPANY_HAND_V2_PREFLIGHT_REJECTED")

    def execute(op):
        bound(op,owner)
        raw,receipt=owner.read_verified()
        return HandEvidence(
           subject_sha256=op.scope.source_set_sha256,
           evidence_id=digest(raw),artifact_sha256=digest(raw),
           outputs=outputs(owner,receipt),mutation_receipts=())

    def observe(op,evidence):
        try:
            bound(op,owner)
            raw,receipt=owner.read_verified()
            demand(dict(evidence.outputs)==outputs(owner,receipt)
                   and evidence.evidence_id==digest(raw),
                   "COMPANY_HAND_EXECUTION_DRIFT")
            return BoundaryObservation(True)
        except (CompanyRoutedReceiptDenied,ValueError,KeyError,TypeError,OSError):
            return BoundaryObservation(False,FaultClass.EVIDENCE_INVALID,
                "COMPANY_HAND_READBACK_FAILED")

    types={
        "case_sha256":str,"envelope_sha256":str,
        "itil_company":int,"itil_authority":str,
        "qa_target":str,"claim_type":str,"exact_qa_hits":int,
        "itil_company_provenance_verified":bool,
        "read_only":bool,"corporate_business_join_certified":bool,
        "global_nonexistence_certified":bool,"repair_certified":bool,
        "access_mode":str
    }
    cap=HandCapability(
        capability_id=CAPABILITY,version="2.0.0",verb=HandVerb.VERIFY,
        input_contract=(
            FieldContract("case_sha256",str),
            FieldContract("envelope_sha256",str),
            FieldContract("itil_company",int)),
        output_contract=tuple(FieldContract(k,v) for k,v in types.items()),
        repo_scope=(REPO,),project_scope=(PROJECT,),
        allowed_mutations=(),required_evidence_layers=("O1",),
        rollback_identity="rollback:itil.aug2026.company-identity.readonly.none",
        quarantine_identity="quarantine:itil.aug2026.company-identity.qa.v2",
        guardian_policy=GuardianPolicy("o13.itil.aug2026.company-identity.v2"),
        adapter=FunctionalHandAdapter(
            executor,execute,preflight_fn=preflight,observe_fn=observe))
    guardian=ExecutionGuardian(
        trust_domains=(
            TrustDomainPolicy(EXEC_DOMAIN,(CAPABILITY,),(
                CanonicalImplementationPolicy(
                    impl,tool_sha256s=(owner.source_sha256,)),)),
            TrustDomainPolicy(VERIFY_DOMAIN,(CAPABILITY,),(
                CanonicalImplementationPolicy(
                    ident.evaluator_sha256,
                    tool_sha256s=(ident.provenance.tool_sha256,)),)),
        ),max_recoveries=0)
    router=HandRouter(HandRegistry((cap,)),guardian,{CAPABILITY:verifier})
    receipt=owner.source_receipt()
    op=HandOperation(
        capability_id=CAPABILITY,
        scope=RepoProjectScope(REPO,PROJECT,receipt["source_manifest_sha256"]),
        inputs={
            "case_sha256":owner.case_sha256,
            "envelope_sha256":owner.pinned_envelope_sha256,
            "itil_company":owner.itil_company
        },
        requested_mutations=(),evidence_receipts={"O1":receipt})
    return cap,router,op

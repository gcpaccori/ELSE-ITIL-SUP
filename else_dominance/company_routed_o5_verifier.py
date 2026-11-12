"""Independent O13 company-routed QA evaluator; no executor parser reuse.

Reads signed envelope from disk independently and reconstructs expected O5
output, HMAC and O1 subject manifest. The worker is the authorized Windows QA
evidence source; this does not independently re-execute the SQL.
"""
from __future__ import annotations

from base64 import b64decode
from hashlib import sha256
from pathlib import Path
import hmac,json,re

from else_core.guardian import (
    EvaluatorIdentity,FaultClass,TrustProvenance,VerificationReceipt
)
from .company_routed_o5_hand import CAPABILITY,VERIFY_DOMAIN,SOURCE_PATH

TOOL_SHA=sha256(b"aug2026-independent-company-route-reinspection-v2").hexdigest()
TARGETS={1:"ELSE70/dbComercial001_D",3:"ELSE70/dbComercial003_D"}
DELIVERY="else.itil.aug2026.qa.company-routed-delivery.v2"
SAMPLE_SHA="04692e7be5e59c70da825c9597ed3dd9787b51bdae7105160be6a9489386aee8"
RECEIPT="else.itil.aug2026.qa.company-routed-receipt.v2"
OBS="else.itil.aug2026.qa.company-routed-observation.v2"
HMAC_PATH=Path("/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private")
OT_RE=re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)\s*[:#=-]?\s*(\d{4,19})\b",re.I)
SUP_RE=re.compile(r"\bsuministro\s*[:#=-]?\s*(\d{4,19})\b",re.I)
EXPECTED_ENVELOPE={
    "schema","job_id","case_sha256","blind_cohort_sha256",
    "source_sha256","sample_sha256","receipt_sha256","receipt_json_base64",
    "hmac_sha256","sql_executed_on_windows","read_only","changes_executed"
}
EXPECTED_RECEIPT={
    "schema","case_sha256","case_row_line_sha256","blind_cohort_sha256",
    "itil_source","itil_company","itil_branch","itil_service","itil_module",
    "itil_sistema","itil_row_verified_from_corporate_sql","claim_type",
    "reported_ot_sha256","reported_supply_sha256","observation",
    "historical_solution_read","corporate_itil_business_join_certified",
    "root_cause_certified","repair_certified","source_sha256"
}
EXPECTED_OBS={
    "schema","qa_target","sql_profile","counts","read_utc",
    "read_only","changes_executed"
}

def decode(raw):
    def pairs(kvs):
        out={}
        for k,v in kvs:
            if k in out:raise ValueError("O13_DUPLICATED_FIELD")
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("O13_NONFINITE")))

class CompanyRoutedIndependentVerifier:
    def __init__(self,owner):
        self.owner=owner

    def evaluator_identity(self):
        h=sha256(Path(__file__).read_bytes()).hexdigest()
        return EvaluatorIdentity(
            evaluator_id="itil-aug2026-company-routed-o13-independent",
            evaluator_version="2.0.0",
            evaluator_sha256=h,
            provenance=TrustProvenance(
                trust_domain_id=VERIFY_DOMAIN,
                capability_id=CAPABILITY,
                implementation_sha256=h,
                tool_sha256=TOOL_SHA,
            )
        )

    def _reinspect(self,value,binding):
        owner=self.owner
        if not owner.path.is_file() or owner.path.is_symlink():return False
        raw=owner.path.read_bytes()
        if not 400<len(raw)<20000:return False
        hashed=sha256(raw).hexdigest()
        if hashed!=owner.pinned_envelope_sha256:return False
        env=decode(raw)
        if type(env) is not dict or set(env)!=EXPECTED_ENVELOPE:return False
        if (env["schema"]!=DELIVERY
            or env["case_sha256"]!=owner.case_sha256
            or env["sample_sha256"]!=SAMPLE_SHA
            or env["job_id"]!=sha256((DELIVERY+":"+owner.case_sha256+":"+
                env["blind_cohort_sha256"]).encode()).hexdigest()[:32]
            or owner.path.name!=env["job_id"]+".private.json"
            or env["source_sha256"]!=owner.source_sha256
            or env["read_only"] is not True
            or env["changes_executed"] is not False
            or env["sql_executed_on_windows"] is not True):return False
        if type(env["receipt_json_base64"]) is not str:return False
        body=b64decode(env["receipt_json_base64"],validate=True)
        receipt_sha=sha256(body).hexdigest()
        if receipt_sha!=env["receipt_sha256"]:return False
        if not HMAC_PATH.is_file() or HMAC_PATH.is_symlink() or HMAC_PATH.stat().st_mode&0o077:
            return False
        key=HMAC_PATH.read_bytes()
        if len(key)!=32:return False
        msg=(DELIVERY+":"+env["job_id"]+":"+owner.source_sha256+":"+receipt_sha).encode()
        if not hmac.compare_digest(
            hmac.new(key,msg,"sha256").hexdigest(),env["hmac_sha256"]
        ):return False
        body=decode(body)
        if type(body) is not dict or set(body)!=EXPECTED_RECEIPT:return False
        if (body["schema"]!=RECEIPT
            or body["case_sha256"]!=owner.case_sha256
            or type(body["itil_company"]) is not int
            or body["itil_company"]!=owner.itil_company
            or body["itil_source"]!="ELSE70/dbITIL_D/dbo.taIncidente"
            or body["itil_row_verified_from_corporate_sql"] is not True
            or body["source_sha256"]!=owner.source_sha256
            or body["historical_solution_read"] is not False
            or body["corporate_itil_business_join_certified"] is not False
            or body["root_cause_certified"] is not False
            or body["repair_certified"] is not False):return False
        match_ot=set(OT_RE.findall(owner.redacted_incident_text))
        match_supply=set(SUP_RE.findall(owner.redacted_incident_text))
        if len(match_ot)>1 or len(match_supply)>1 or not (match_ot or match_supply):
            return False
        ot_hash=(sha256(next(iter(match_ot)).encode()).hexdigest() if match_ot else None)
        supply_hash=(sha256(next(iter(match_supply)).encode()).hexdigest() if match_supply else None)
        mode="OT" if match_ot else "SUPPLY"
        if (body["claim_type"]!=mode or body["reported_ot_sha256"]!=ot_hash
            or body["reported_supply_sha256"]!=supply_hash):return False
        obs=body["observation"]
        if type(obs) is not dict or set(obs)!=EXPECTED_OBS:return False
        if (obs["schema"]!=OBS
            or obs["qa_target"]!=TARGETS[owner.itil_company]
            or obs["sql_profile"]!=(
                "PINNED_TYPED_OT_SELECTS" if mode=="OT"
                else "PINNED_TYPED_SUPPLY_SELECTS")
            or obs["read_only"] is not True
            or obs["changes_executed"] is not False):return False
        if type(obs["read_utc"]) is not str or not re.fullmatch(
            r"\d{4}-\d\d-\d\dT.{10,35}",obs["read_utc"]
        ):return False
        cols=(
            {"order","installation","interior","meter"} |
            ({"supply","orders_by_supply","exact_ot_supply"} if match_supply else set())
            if match_ot else
            {"supply","orders_by_supply","massive_installation","installation_owner"}
        )
        counts=obs["counts"]
        if (type(counts) is not dict or set(counts)!=cols
            or any(type(v) is not int or v not in (0,1,2) for v in counts.values())):
            return False
        if match_ot and match_supply and counts["exact_ot_supply"]>counts["orders_by_supply"]:
            return False
        canonical=json.dumps([[SOURCE_PATH,owner.source_bytes,
                              owner.source_sha256]],
                             ensure_ascii=False,separators=(",",":")).encode()
        manifest=sha256(canonical).hexdigest()
        outputs={
            "case_sha256":owner.case_sha256,
            "envelope_sha256":hashed,
            "itil_company":owner.itil_company,
            "itil_authority":"ELSE70/dbITIL_D/dbo.taIncidente",
            "qa_target":TARGETS[owner.itil_company],
            "claim_type":mode,
            "exact_qa_hits":sum(counts.values()),
            "itil_company_provenance_verified":True,
            "read_only":True,
            "corporate_business_join_certified":False,
            "global_nonexistence_certified":False,
            "repair_certified":False,
            "access_mode":"SIGNED_COMPANY_SCOPED_QA_RECEIPT_V2_ONLY",
        }
        return (
           value.subject_sha256==manifest
           and value.evidence_id==hashed
           and value.artifact_sha256==hashed
           and dict(value.outputs)==outputs
           and value.mutation_receipts==()
           and binding.subject_sha256==manifest
           and binding.evidence_id==hashed
           and binding.artifact_sha256==hashed
           and binding.capability_id==CAPABILITY
        )

    def verify(self,binding,value):
        ident=self.evaluator_identity()
        try:good=self._reinspect(value,binding)
        except (OSError,ValueError,TypeError,KeyError,AttributeError):good=False
        return VerificationReceipt(
            passed=good,
            operation_id=binding.operation_id,
            capability_id=binding.capability_id,
            subject_sha256=binding.subject_sha256,
            evidence_id=binding.evidence_id,
            evaluator_id=ident.evaluator_id,
            evaluator_version=ident.evaluator_version,
            evaluator_sha256=ident.evaluator_sha256,
            executor_trust_domain_id=binding.executor_trust_domain_id,
            executor_implementation_sha256=binding.executor_implementation_sha256,
            evaluator_trust_domain_id=ident.provenance.trust_domain_id,
            evaluator_capability_id=ident.provenance.capability_id,
            evaluator_implementation_sha256=ident.evaluator_sha256,
            independent=True,
            artifact_sha256=binding.artifact_sha256,
            current=True,
            fault=None if good else FaultClass.EVIDENCE_INVALID,
            detail="" if good else "COMPANY_O13_INDEPENDENT_V2_EVIDENCE_REJECTED"
        )

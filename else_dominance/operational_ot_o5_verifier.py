"""Independent O13 operational OT verifier.
Independently parses signed receipt and recomputes O1 manifest, OT hash,
output evidence and strict source boundaries without executor parsing.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,re
from else_core.guardian import EvaluatorIdentity,FaultClass,TrustProvenance,VerificationReceipt

CAPABILITY="itil.qa.aug2026.operational-ot.receipt.readonly.v1"
DOMAIN="itil-aug2026-operational-ot-independent-verifier"
TOOL_SHA=sha256(b"aug2026-operational-ot-independent-verifier-v1").hexdigest()
SOURCE_PATH="qa/AugOperationalOtRead.cs"
OT_RE=re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)"
                 r"\s*[:#=-]?\s*(\d{4,19})\b",re.I)
OBS_KEYS={"schema","qa_target","source","query_id","order_sha256",
          "order_rows","order_found","codigo_estado_orden_trabajo",
          "codigo_clase_orden_trabajo","codigo_tipo_orden_trabajo",
          "codigo_subtipo_orden_trabajo","fecha_elaboracion_present",
          "fecha_inicio_present","fecha_fin_present",
          "read_only","changes_executed","read_utc"}

class OperationalOtIndependentVerifier:
    def __init__(self,owner):self.owner=owner
    def evaluator_identity(self):
        impl=sha256(Path(__file__).read_bytes()).hexdigest()
        return EvaluatorIdentity(
            evaluator_id="itil-aug2026-operational-ot-independent-qa",
            evaluator_version="1.0.0",
            evaluator_sha256=impl,
            provenance=TrustProvenance(
                trust_domain_id=DOMAIN,
                capability_id=CAPABILITY,
                implementation_sha256=impl,
                tool_sha256=TOOL_SHA))
    def _reinspect(self,value,binding):
        owner=self.owner
        path=owner.path
        if not path.is_file() or path.is_symlink():return False
        raw=path.read_bytes()
        if not 120<=len(raw)<=16000:return False
        hashed=sha256(raw).hexdigest()
        if hashed!=owner.pinned_sha256:return False
        def unique(pairs):
            out={}
            for key,x in pairs:
                if key in out:raise ValueError("DUPLICATE_JSON_KEY")
                out[key]=x
            return out
        body=json.loads(raw,object_pairs_hook=unique,
             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if type(body) is not dict or set(body)!={
            "schema","case_sha256","reported_ot_sha256",
            "reader_source_sha256","observation","business_join_certified",
            "root_cause_certified","repair_certified","read_only"}:return False
        matches=set(OT_RE.findall(owner.redacted_incident_text))
        if len(matches)!=1:return False
        ot_hash=sha256(next(iter(matches)).encode()).hexdigest()
        if (ot_hash!=owner.reported_ot_sha256 or
            body["schema"]!="else.itil.aug2026.operational-ot-receipt.v1" or
            body["case_sha256"]!=owner.case_sha256 or
            body["reported_ot_sha256"]!=ot_hash or
            body["reader_source_sha256"]!=owner.source_sha256 or
            body["business_join_certified"] is not False or
            body["root_cause_certified"] is not False or
            body["repair_certified"] is not False or
            body["read_only"] is not True):return False
        x=body["observation"]
        if type(x) is not dict or set(x)!=OBS_KEYS:return False
        if (x["schema"]!="else.itil.aug2026.qa.operational-ot-readonly.v1" or
            x["qa_target"]!="ELSE70/dbDistribucion_D" or
            x["source"]!="dbo.taOrdenTrabajo" or
            x["query_id"]!="QA_DISTRIB_OPERATIONAL_OT_BY_CODE_V1" or
            x["order_sha256"]!=ot_hash or
            type(x["order_rows"]) is not int or
            x["order_rows"] not in (0,1) or
            type(x["order_found"]) is not bool or
            x["order_found"]!=(x["order_rows"]==1) or
            x["read_only"] is not True or
            x["changes_executed"] is not False):return False
        for key in ("fecha_elaboracion_present","fecha_inicio_present",
                    "fecha_fin_present"):
            if type(x[key]) is not bool or (
                not x["order_found"] and x[key] is not False):return False
        for key in ("codigo_estado_orden_trabajo","codigo_clase_orden_trabajo",
                    "codigo_tipo_orden_trabajo","codigo_subtipo_orden_trabajo"):
            if type(x[key]) is not str or len(x[key])>100 or (
                not x["order_found"] and x[key]!=""):return False
        if (type(x["read_utc"]) is not str or
            re.fullmatch(r"\d{4}-\d\d-\d\dT.{10,35}",
                         x["read_utc"]) is None):return False
        packed=json.dumps([[SOURCE_PATH,owner.source_bytes,
                             owner.source_sha256]],ensure_ascii=False,
                          separators=(",",":")).encode()
        manifest=sha256(packed).hexdigest()
        outputs={
          "case_sha256":owner.case_sha256,
          "receipt_sha256":hashed,
          "reported_ot_sha256":ot_hash,
          "source":"ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo",
          "order_found":x["order_found"],
          "order_rows":x["order_rows"],
          "order_state_code":x["codigo_estado_orden_trabajo"],
          "order_type_code":x["codigo_tipo_orden_trabajo"],
          "date_start_present":x["fecha_inicio_present"],
          "date_end_present":x["fecha_fin_present"],
          "provenance_verified":True,"read_only":True,
          "business_entity_join_certified":False,
          "repair_certified":False,
          "access_mode":"PINNED_OPERATIONAL_OT_QA_RECEIPT_ONLY",
        }
        return (value.subject_sha256==manifest and
                value.evidence_id==hashed and
                value.artifact_sha256==hashed and
                dict(value.outputs)==outputs and
                value.mutation_receipts==() and
                binding.evidence_id==hashed and
                binding.subject_sha256==manifest and
                binding.capability_id==CAPABILITY and
                binding.artifact_sha256==hashed)
    def verify(self,binding,value):
        identity=self.evaluator_identity()
        try:good=self._reinspect(value,binding)
        except (OSError,ValueError,TypeError,KeyError,AttributeError):good=False
        return VerificationReceipt(
            passed=good,operation_id=binding.operation_id,
            capability_id=binding.capability_id,
            subject_sha256=binding.subject_sha256,
            evidence_id=binding.evidence_id,
            evaluator_id=identity.evaluator_id,
            evaluator_version=identity.evaluator_version,
            evaluator_sha256=identity.evaluator_sha256,
            executor_trust_domain_id=binding.executor_trust_domain_id,
            executor_implementation_sha256=binding.executor_implementation_sha256,
            evaluator_trust_domain_id=identity.provenance.trust_domain_id,
            evaluator_capability_id=identity.provenance.capability_id,
            evaluator_implementation_sha256=identity.evaluator_sha256,
            independent=True,artifact_sha256=binding.artifact_sha256,
            current=True,fault=None if good else FaultClass.EVIDENCE_INVALID,
            detail="" if good else "OP_OT_O13_INDEPENDENT_RECEIPT_REJECTED")

"""Native O5/O13/O15 commercial OT trust boundary and triple source fail-closed tests."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

try:
    from else_core.hand_kernel import Outcome
    from else_dominance.commercial_ot_o5_hand import (
        AuthorizedCommercialOtReceipt, build_commercial_ot_router
    )
    NATIVE_CORE_AVAILABLE = True
except ModuleNotFoundError as exc:
    if exc.name not in ("else_core", "else_core.hand_kernel", "else_core.guardian", "else_core.source_truth"):
        raise
    NATIVE_CORE_AVAILABLE = False
    Outcome = None
from else_dominance.commercial_ot_verified import SOURCE, SOURCE_SHA
from else_dominance.functional_live_triple_v3_1 import SCHEMA, check_addendum

CASE = sha256(b"synthetic-aug-commercial-case").hexdigest()
TEXT = "Se requiere verificar la OT 123456 en el sistema comercial de pruebas."

def digest(v):
    return sha256(v).hexdigest()

def packed(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def receipt():
    obs = {
        "schema": "else.itil.aug2026.qa.commercial-ot-readonly.v2",
        "qa_target": "ELSE70/dbComercial001_D",
        "source": "dbo.taOrdenTrabajo",
        "query_id": "QA_COMERCIAL_OT_BY_CODE_V2",
        "order_sha256": digest(b"123456"),
        "order_rows": 0, "order_found": False,
        "codigo_estado_orden_trabajo": "", "codigo_subestado_orden_trabajo": "",
        "codigo_tipo_orden_trabajo": "", "codigo_subtipo_orden_trabajo": "",
        "fecha_registro_solicitud_present": False,
        "fecha_ejecucion_inicio_present": False,
        "fecha_ejecucion_fin_present": False,
        "read_only": True, "changes_executed": False,
        "read_utc": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "schema": "else.itil.aug2026.commercial-ot-receipt.v2",
        "case_sha256": CASE, "reported_ot_sha256": digest(b"123456"),
        "reader_source_sha256": SOURCE_SHA, "observation": obs,
        "business_join_certified": False, "root_cause_certified": False,
        "repair_certified": False, "read_only": True,
    }

def run_case(tmp, body, *, incident=TEXT, preserve_pin=False):
    path=Path(tmp)/"commercial_receipt.json"
    raw=packed(body)
    path.write_bytes(raw)
    obj=AuthorizedCommercialOtReceipt(
        path, digest(raw if not preserve_pin else b"different"), CASE,
        SOURCE_SHA, len(SOURCE.read_bytes()), incident
    )
    _, router, operation=build_commercial_ot_router(obj)
    return router.route(operation)

def sources():
    sap={
        "case_sha256": CASE, "o5_o13_o15_verified": True,
        "sql_fresh_read_on_windows": True,
        "official_itil_ot_business_join_verified": False,
        "repair_certified": False, "domain": "COMMERCIAL_OT",
        "observation": {"order_found_in_specific_table": False}
    }
    op={
        "case_sha256": CASE, "native_o5_o13_o15_verified": True,
        "hmac_verified": True, "independent_receipt_fields_verified": True,
        "business_join_certified": False, "repair_certified": False,
        "source": "ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo",
        "order_found": False
    }
    commercial=copy.deepcopy(op)
    commercial["source"]="ELSE70/dbComercial001_D/dbo.taOrdenTrabajo"
    return sap,op,commercial

def proposal():
    return {
      "schema": SCHEMA,
      "hypotheses": ["El código mencionado podría referirse a una solicitud y no a una OT."],
      "what_this_sap_read_can_prove": "No se hallaron registros en las dos tablas SAP examinadas.",
      "what_operational_read_can_prove": "La búsqueda operativa exacta devolvió cero registros.",
      "what_commercial_read_can_prove": "La búsqueda comercial exacta devolvió cero registros.",
      "what_it_cannot_prove": "No confirma inexistencia global ni una causa raíz certificada.",
      "next_domain_check": {
        "target": "SIELSE/órdenes de trabajo",
        "business_object": "Tipo e identificador original del trámite referido por el usuario.",
        "observable": "Obtener en el módulo de origen la clase de documento y la clave corporativa asociada al trámite.",
        "expected": "Si se identifica una OT auténtica, obtener su clave y fuente para una nueva lectura exacta.",
        "if_expected": "Registrar la referencia auténtica y solicitar lectura autorizada sin inventar el estado de la orden.",
        "if_different": "Si es otro tipo de solicitud, registrar el módulo y solicitar su identificador correspondiente.",
        "execution": "NOT_EXECUTED"
      },
      "official_itil_ot_join_verified": False,
      "root_cause_certified": False, "repair_certified": False,
    }

@unittest.skipUnless(NATIVE_CORE_AVAILABLE, "Native ELSE CORE dependency required")
class CommercialNativeTest(unittest.TestCase):
    def test_native_o5_guardian_independent_pass(self):
        with tempfile.TemporaryDirectory() as d:
            result=run_case(d, receipt())
        self.assertEqual(result.outcome, Outcome.PASS)
        self.assertTrue(result.guardian_result.verification.independent)
        self.assertEqual(result.guardian_result.executions,1)
        self.assertFalse(result.guardian_result.value.outputs["order_found"])

    def test_adversarial_receipts_fail_closed(self):
        corruptions=(
          lambda r: r.update(business_join_certified=True),
          lambda r: r.update(root_cause_certified=True),
          lambda r: r.update(repair_certified=True),
          lambda r: r["observation"].update(order_rows=1),
          lambda r: r["observation"].update(order_found=True),
          lambda r: r["observation"].update(qa_target="ELSE70/dbDistribucion_D"),
          lambda r: r["observation"].update(query_id="QA_DISTRIB_OPERATIONAL_OT_BY_CODE_V1"),
          lambda r: r["observation"].update(order_sha256="f"*64),
          lambda r: r["observation"].update(changes_executed=True),
          lambda r: r.update(reader_source_sha256="f"*64),
          lambda r: r["observation"].update(fecha_ejecucion_fin_present=True),
        )
        with tempfile.TemporaryDirectory() as d:
            for mutation in corruptions:
                body=receipt();mutation(body)
                with self.subTest(mutation=str(mutation)):
                    self.assertNotEqual(run_case(d,body).outcome,Outcome.PASS)

    def test_cross_case_rebinding_fails(self):
        with tempfile.TemporaryDirectory() as d:
            result=run_case(d, receipt(), incident="Revisar la OT 123457 del trámite comercial.")
        self.assertNotEqual(result.outcome, Outcome.PASS)

    def test_source_pin_tampering_fails(self):
        with tempfile.TemporaryDirectory() as d:
            result=run_case(d, receipt(), preserve_pin=True)
        self.assertNotEqual(result.outcome, Outcome.PASS)

class TripleFunctionalTest(unittest.TestCase):
    def test_concrete_conditional_evidence_passes(self):
        quality=check_addendum(proposal(), *sources())
        self.assertTrue(quality["accepted"], quality["flags"])
        self.assertFalse(quality["cause_certified"])
        self.assertFalse(quality["repair_certified"])

    def test_forged_source_or_placeholder_rejected(self):
        attacks=(
           ("commercial_missing", lambda p,s: s[2].update(native_o5_o13_o15_verified=False)),
           ("wrong_case", lambda p,s: s[2].update(case_sha256="f"*64)),
           ("fake_found", lambda p,s: s[2].update(order_found=True)),
           ("fake_join", lambda p,s: p.update(official_itil_ot_join_verified=True)),
           ("fake_repair", lambda p,s: p.update(repair_certified=True)),
           ("template_echo", lambda p,s: p["next_domain_check"].update(
                    observable="Dato verificable adicional en el modulo de negocio")),
           ("same_branch", lambda p,s: p["next_domain_check"].update(
                    if_different=p["next_domain_check"]["if_expected"])),
        )
        for name,attack in attacks:
            with self.subTest(name=name):
                p=proposal(); src=list(sources());attack(p,src)
                self.assertFalse(check_addendum(p,*src)["accepted"])

if __name__=="__main__":
    unittest.main()

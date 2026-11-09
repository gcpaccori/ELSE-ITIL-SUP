"""Tests use fabricated cases and a fake local service; no corporate data."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from else_dominance.accompaniment_preview import (
    FeedbackLedger, canonical, load_scenarios, run_campaign,
    verify_active_persistence, audit_campaign
)


FIXTURE = (Path(__file__).resolve().parents[1] /
           "examples/accompaniment_preview_5.synthetic.json")


def model_result(case_ref, *, selected="primary", status="DIAGNOSTIC_GUIDANCE"):
    base = {"case_ref":case_ref,"status":status,"model_selected":selected,
            "certified_repair":False,"executed_changes":False,
            "real_corporate_sources_queried":False,
            "requires_human_verification":True,
            "quality":{"accepted":True,"schema_flags":[],"safety_flags":[],
                       "review_flags":[]},
            "proposal":{"estado":"INVESTIGACION_ESPECIFICA",
                        "diagnostico":"Diferencial sintético.",
                        "hipotesis":["Falta evidencia."],"fuentes":[],
                        "evidence_refs":[],"pasos":[{
                            "condicion":"Según verificación.",
                            "accion":"Inspeccionar dato de prueba.",
                            "responsable":"Responsable QA.",
                            "verificacion":"Confirmar comportamiento."}],
                        "faltantes":["Prueba funcional."],
                        "cierre":["Confirmar con solicitante."],
                        "ejecutado":False,"confirmado":False}}
    return base


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.h=TemporaryDirectory()
        self.addCleanup(self.h.cleanup)
        self.root=Path(self.h.name)
        self.rows=load_scenarios(FIXTURE)
        self.ledger=FeedbackLedger(self.root/"feedback.sqlite")
        self.addCleanup(self.ledger.close)

    def first(self):
        row=self.rows[0]
        return row,model_result(row["ticket"]["case_ref"])

    def test_five_cases_and_identity(self):
        self.assertEqual(len(self.rows),5)
        self.assertEqual(len({r["ticket"]["case_ref"] for r in self.rows}),5)
        self.assertTrue(all(r["ticket"]["input_scope"]=="synthetic"
                            for r in self.rows))

    def test_each_run_requires_real_service_receipt_shape(self):
        row,resp=self.first()
        actual=self.ledger.register(scenario=row,response=resp,persisted=True)
        self.assertTrue(actual["contract_pass"])
        self.assertEqual(self.ledger.report()["human_reviewed_cases"],0)
        self.assertEqual(self.ledger.report()["feedback_pending"],1)

    def test_immutable_case_ref_does_not_change_result(self):
        row,resp=self.first()
        self.ledger.register(scenario=row,response=resp,persisted=True)
        self.assertEqual(self.ledger.register(
            scenario=row,response=resp,persisted=True)["status"],
            "EXISTING_VERIFIED_RUN")
        other=deepcopy(resp)
        other["proposal"]["diagnostico"]="Changed verdict."
        with self.assertRaisesRegex(ValueError,"IMMUTABILITY"):
            self.ledger.register(scenario=row,response=other,persisted=True)

    def test_prevent_false_repair_corporate_action_or_bad_model_plan(self):
        row,resp=self.first()
        for key in ("certified_repair","executed_changes",
                    "real_corporate_sources_queried"):
            altered=deepcopy(resp)
            altered[key]=True
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError,"FALSE_CORPORATE"):
                    self.ledger.register(scenario=row,response=altered,
                                         persisted=True)
        altered=deepcopy(resp)
        altered["proposal"]["confirmado"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_MODEL"):
            self.ledger.register(scenario=row,response=altered,persisted=True)

    def test_secondary_and_escalation_are_distinguished(self):
        row,resp=self.first()
        resp["model_selected"]="secondary"
        v=self.ledger.register(scenario=row,response=resp,persisted=True)
        self.assertEqual(v["selected_model"],"secondary")
        escalated=self.rows[1]
        triage={"case_ref":escalated["ticket"]["case_ref"],
                "status":"NEEDS_HUMAN_TRIAGE","executed_changes":False,
                "certified_repair":False,
                "real_corporate_sources_queried":False,
                "requires_human_verification":True}
        v=self.ledger.register(scenario=escalated,response=triage,
                               persisted=True)
        self.assertFalse(v["contract_pass"])
        self.assertEqual(v["selected_model"],"NONE")

    def test_feedback_is_from_named_role_not_auto_generated(self):
        row,resp=self.first()
        ref=row["ticket"]["case_ref"]
        self.ledger.register(scenario=row,response=resp,persisted=True)
        with self.assertRaisesRegex(ValueError,"UNREGISTERED"):
            self.ledger.feedback(case_ref="PREVIEW-20261109-UNKNOWN",
                reviewer_role="TECHNICIAN",decision="PARTIAL",
                note="Falta verificar otra zona de prueba.",
                observed_result="NOT_CHECKED")
        result=self.ledger.feedback(case_ref=ref,reviewer_role="TECHNICIAN",
            decision="PARTIAL", note="Falta distinguir perfil y sesión de prueba.",
            observed_result="NOT_CHECKED")
        self.assertTrue(result["recorded"])
        self.assertFalse(result["automatic_memory_promotion"])
        self.assertEqual(self.ledger.report()["human_reviewed_cases"],1)
        self.assertEqual(self.ledger.verify_feedback()["feedback_events_valid"],1)

    def test_feedback_revision_appends_and_tampering_detected(self):
        row,resp=self.first()
        ref=row["ticket"]["case_ref"]
        self.ledger.register(scenario=row,response=resp,persisted=True)
        for decision in ("PARTIAL","USEFUL"):
            self.ledger.feedback(case_ref=ref,reviewer_role="TECHNICIAN",
                decision=decision,note="Observación suficiente para el caso.",
                observed_result="NOT_CHECKED")
        self.assertEqual(self.ledger.verify_feedback()["feedback_events_valid"],2)
        with self.ledger.conn:
            self.ledger.conn.execute(
                "UPDATE human_feedback SET note='changed' WHERE id=1")
        with self.assertRaisesRegex(ValueError,"FEEDBACK_EVENT_TAMPER"):
            self.ledger.verify_feedback()

    def test_feedback_disallows_unattributed_reviews(self):
        row,resp=self.first()
        ref=row["ticket"]["case_ref"]
        self.ledger.register(scenario=row,response=resp,persisted=True)
        for role,note in (("","A report with sufficient text."),
                          ("TECHNICIAN","short")):
            with self.subTest(role=role,note=note):
                with self.assertRaises(ValueError):
                    self.ledger.feedback(case_ref=ref,reviewer_role=role,
                        decision="USEFUL",note=note,observed_result="NOT_CHECKED")

    def test_active_service_db_row_must_match_exact_response(self):
        row,resp=self.first()
        db=self.root/"active.sqlite"
        with sqlite3.connect(str(db)) as c:
            c.execute("CREATE TABLE attention "
                      "(case_ref TEXT PRIMARY KEY,result_json TEXT)")
            c.execute("INSERT INTO attention VALUES (?,?)",
                      (row["ticket"]["case_ref"],json.dumps(resp)))
        self.assertTrue(verify_active_persistence(db,row["ticket"],resp))
        altered=deepcopy(resp)
        altered["status"]="ACTION_PLAN_REVIEWABLE"
        self.assertFalse(verify_active_persistence(db,row["ticket"],altered))

    def test_campaign_five_end_to_end_receipts_without_live_inference(self):
        db=self.root/"active.sqlite"
        with sqlite3.connect(str(db)) as c:
            c.execute("CREATE TABLE attention "
                      "(case_ref TEXT PRIMARY KEY,result_json TEXT)")
        token=self.root/"token"
        token.write_text("synthetic-token-"+"x"*40)
        def fake_send(*,url,token_file,ticket):
            response=model_result(ticket["case_ref"])
            with sqlite3.connect(str(db)) as c:
                c.execute("INSERT INTO attention VALUES (?,?)",
                          (ticket["case_ref"],json.dumps(response)))
            return response
        out=self.root/"QA"
        report=run_campaign(scenarios_file=FIXTURE,out_dir=out,
            token_file=token,active_db=db,
            api_url="http://127.0.0.1:18883/v1/support",send=fake_send)
        self.assertTrue(report["complete_five_case_campaign"])
        self.assertEqual(report["executed_cases"],5)
        self.assertEqual(report["contract_passed"],5)
        self.assertEqual(report["active_service_receipt_persisted"],5)
        self.assertEqual(report["human_reviewed_cases"],0)
        self.assertEqual(len(list(out.glob("*.response.json"))),5)
        self.assertEqual(report["automatic_memory_promotions"],0)
        audit=audit_campaign(scenarios_file=FIXTURE,out_dir=out,active_db=db)
        self.assertEqual(audit["state"],"PREVIEW_E2E_RECEIPTS_VERIFIED")
        self.assertEqual(audit["receipts_rehashed"],5)
        receipt=out/(self.rows[0]["ticket"]["case_ref"]+".response.json")
        changed=json.loads(receipt.read_text())
        changed["status"]="ACTION_PLAN_REVIEWABLE"
        receipt.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,"RESPONSE_RECEIPT_TAMPERED"):
            audit_campaign(scenarios_file=FIXTURE,out_dir=out,active_db=db)

    def test_cannot_replace_synthetic_cohort_with_unmarked_corporate_text(self):
        altered=json.loads(FIXTURE.read_text())
        altered["scenarios"][0]["ticket"]["input_scope"]="requester_submitted"
        p=self.root/"changed.json"
        p.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError,"SYNTHETIC_ONLY"):
            load_scenarios(p)


if __name__=="__main__":
    unittest.main()

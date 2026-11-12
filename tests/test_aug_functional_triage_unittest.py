"""Synthetic company-routed functional intent/positive-control adversarial tests."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import unittest

from else_dominance.functional_case_triage import (
    RULES,classify_text,plan_for_verified_case,FunctionalTriageDenied
)
from else_dominance.positive_control_verified import (
    check_observation,PositiveControlDenied
)

CASE=sha256(b"synthetic-company-verified-ticket-2026").hexdigest()
ENV=sha256(b"synthetic-sealed-env").hexdigest()
OT="123456"
SUP="987654"

def digest(x):
    return sha256(x.encode()).hexdigest()

EXAMPLES=(
 ("0101100123000","Por favor cambiar el recurso en el presupuesto OT: 123456",
  "RESOURCE_CODE_CORRECTION",1),
 ("0101100123000","Solicitud de actualizacion de apellido OT: 123456",
  "CLIENT_SURNAME_AND_OSINERGMIN",1),
 ("0101300100000","Favor cambiar la fecha de cambio de medidor OT 123456 de suministro 987654",
  "METER_EXECUTION_DATE_CORRECTION",3),
 ("0101100123000","Favor aperturar OT: 123456 y corregir recurso de cable",
  "REOPEN_INSTALLATION_OT",1),
 ("0101100116000","Girar comprobante para presupuesto inicial cero OT: 123456",
  "ZERO_INITIAL_BUDGET_VOUCHER",1),
)

def receipt(module,company,text,counts=None):
    sup="suministro" in text.lower()
    return {
      "schema":"else.itil.aug2026.qa.company-routed-receipt.v2",
      "case_sha256":CASE,
      "itil_module":module,"itil_company":company,
      "reported_ot_sha256":digest(OT),
      "reported_supply_sha256":digest(SUP) if sup else None,
      "claim_type":"OT",
      "itil_row_verified_from_corporate_sql":True,
      "historical_solution_read":False,"repair_certified":False,
      "observation":{
        "schema":"else.itil.aug2026.qa.company-routed-observation.v2",
        "qa_target":f"ELSE70/dbComercial00{company}_D",
        "read_only":True,"changes_executed":False,
        "counts":{"order":0} if counts is None else counts
      }
    }

def positive_sample():
    return {
      "schema":"else.itil.qa.company-positive-control.v1",
      "no_identifiers_returned":True,"read_only":True,"mutations":0,
      "cases":[{
        "company":company,
        "qa_target":f"ELSE70/dbComercial00{company}_D",
        "aug2026_ot_positive_sample_found":company==1,
        "aug2026_ot_sample_registration_date":"2026-08-26" if company==1 else "",
        "aug2026_ot_exact_lookup_pass":company==1,
        "supply_positive_sample_found":True,
        "supply_exact_lookup_pass":True,
        "ot_supply_link_sample_found":True,
        "ot_supply_exact_link_lookup_pass":True,
        "read_only":True,
      } for company in (1,3)]
    }

class FunctionalDomainRuleTests(unittest.TestCase):
    def test_five_specific_distinct_repair_guarded_plans(self):
        kinds=set()
        for module,text,expected,company in EXAMPLES:
            with self.subTest(rule=expected):
                r=receipt(module,company,text)
                result=plan_for_verified_case(
                    request=text,receipt=r,
                    verified_envelope_sha256=ENV,signed_hmac_verified=True)
                self.assertEqual(result["functional_kind"],expected)
                self.assertEqual(result["decision"],
                    "QA_REFERENCE_NOT_FOUND_ROUTE_TO_VERIFIED_BUSINESS_SOURCE")
                self.assertEqual(result["company"],company)
                self.assertFalse(result["repair_permitted"])
                self.assertFalse(result["repair_executed"])
                self.assertFalse(result["historical_solution_used"])
                self.assertGreaterEqual(len(result["mandatory_checks"]),3)
                self.assertGreaterEqual(len(result["denied_actions"]),2)
                self.assertGreaterEqual(len(result["mandatory_relations"]),4)
                kinds.add(result["functional_kind"])
        self.assertEqual(len(kinds),5)

    def test_existing_qa_ot_is_not_repair_approval(self):
        m,text,expected,comp=EXAMPLES[0]
        r=receipt(m,comp,text,counts={"order":1})
        result=plan_for_verified_case(
            request=text,receipt=r,verified_envelope_sha256=ENV,
            signed_hmac_verified=True)
        self.assertEqual(result["decision"],
            "QA_RECORD_IDENTIFIED_ADDITIONAL_GATES_REQUIRED")
        self.assertTrue(result["business_record_identified"])
        self.assertFalse(result["repair_permitted"])
        self.assertFalse(result["itil_business_foreign_key_verified"])

    def test_duplicate_ot_blocks_automatic_state(self):
        m,text,expected,comp=EXAMPLES[0]
        r=receipt(m,comp,text,counts={"order":2})
        result=plan_for_verified_case(
            request=text,receipt=r,verified_envelope_sha256=ENV,
            signed_hmac_verified=True)
        self.assertEqual(result["decision"],"QA_DUPLICATE_OT_REQUIRES_REVIEW")
        self.assertFalse(result["repair_permitted"])

    def test_all_untrusted_rebindings_fail(self):
        for m,text,expected,comp in EXAMPLES:
            original=receipt(m,comp,text)
            mutants=(
                lambda x:x.update(itil_company=2),
                lambda x:x.update(itil_module="0100000000000"),
                lambda x:x.update(historical_solution_read=True),
                lambda x:x.update(repair_certified=True),
                lambda x:x["observation"].update(qa_target="ELSE70/dbComercial007_D"),
                lambda x:x["observation"].update(changes_executed=True),
                lambda x:x.update(reported_ot_sha256=digest("999999")),
                lambda x:x.update(reported_supply_sha256=digest("999999")),
                lambda x:x["observation"].update(counts={"supply":0}),
            )
            for edit in mutants:
                r=deepcopy(original)
                edit(r)
                with self.subTest(kind=expected,edit=edit):
                    with self.assertRaises(FunctionalTriageDenied):
                        plan_for_verified_case(
                           request=text,receipt=r,
                           verified_envelope_sha256=ENV,
                           signed_hmac_verified=True)

    def test_textual_identifier_collision_rejected(self):
        module,txt,expected,company=EXAMPLES[0]
        r=receipt(module,company,txt)
        txt=txt+" OT: 999999"
        with self.assertRaisesRegex(FunctionalTriageDenied,"AMBIGUOUS"):
            plan_for_verified_case(request=txt,receipt=r,
                verified_envelope_sha256=ENV,signed_hmac_verified=True)

    def test_unverified_receipt_rejected(self):
        module,txt,expected,company=EXAMPLES[0]
        r=receipt(module,company,txt)
        for hmac_ok,sha in ((False,ENV),(True,"not_sha")):
            with self.assertRaises(FunctionalTriageDenied):
                plan_for_verified_case(request=txt,receipt=r,
                    verified_envelope_sha256=sha,signed_hmac_verified=hmac_ok)

    def test_module_cannot_switch_operational_rule(self):
        request=EXAMPLES[0][1]
        self.assertEqual(classify_text(request,"0101100123000").kind,
                         "RESOURCE_CODE_CORRECTION")
        with self.assertRaises(FunctionalTriageDenied):
            classify_text(request,"0101300100000")

    def test_blank_and_forged_intent_rejected(self):
        for value in ("", "asdf", "OT 123456", "cambiar recurso en OT 123456"):
            with self.assertRaises(FunctionalTriageDenied):
                classify_text(value,"0101100123000")

class PositiveControlContractTests(unittest.TestCase):
    def test_exact_two_company_positive_controls(self):
        values=check_observation(positive_sample())
        self.assertEqual([x["company"] for x in values],[1,3])

    def test_wrong_positive_company_rejected(self):
        o=positive_sample()
        o["cases"][1]["company"]=1
        with self.assertRaises(PositiveControlDenied):
            check_observation(o)

    def test_forged_positive_or_malformed_date_rejected(self):
        o=positive_sample()
        o["cases"][0]["aug2026_ot_sample_registration_date"]="2026-01-08"
        with self.assertRaises(PositiveControlDenied):
            check_observation(o)
        o=positive_sample()
        o["cases"][1]["supply_exact_lookup_pass"]=False
        with self.assertRaises(PositiveControlDenied):
            check_observation(o)
        o=positive_sample()
        o["cases"][0]["ot_supply_exact_link_lookup_pass"]=False
        with self.assertRaises(PositiveControlDenied):
            check_observation(o)

    def test_mutation_and_extra_leaked_identifier_rejected(self):
        o=positive_sample()
        o["cases"][0]["real_ot_id"]="123456"
        with self.assertRaises(PositiveControlDenied):
            check_observation(o)
        o=positive_sample()
        o["mutations"]=1
        with self.assertRaises(PositiveControlDenied):
            check_observation(o)

if __name__=="__main__":unittest.main()

"""Synthetic no-secret tests for QA functional-schema witness strict validation."""
from __future__ import annotations
import copy
import unittest

from else_dominance.functional_profile_verified import (
    OBS,check_observation,FunctionalProfileDenied
)

def fixture():
    fields={
       "budget_rows_limited":1,
       "resource_rows_limited":0,
       "voucher_rows_limited":0,
       "osinergmin_history_rows_limited":0,
       "change_log_rows_limited":0,
       "installation_audit_rows_limited":0,
       "installation_module_rows_limited":0,
       "interior_installation_rows_limited":0,
       "meter_supply_rows_limited":2,
    }
    cases=[]
    for company in (1,3):
        row={
            "company":company,
            "qa_target":f"ELSE70/dbComercial00{company}_D",
            "sample_ot_from_august_2026":company==1,
            "sample_ot_witness_in_budget":True,
            "ot_exact_rebound":True,
            "ot_state_catalog_found":True,
            "execution_dates_present":False,
            "read_only":True,"changes_executed":False,
        }
        row.update(fields)
        if company==3:
            row["resource_rows_limited"]=1
            row["installation_audit_rows_limited"]=None
        cases.append(row)
    return {
        "schema":OBS,
        "profile_count":5,
        "companies":cases,
        "no_raw_business_keys_returned":True,
        "read_only":True,
        "changes_executed":False,
    }

class Profiles(unittest.TestCase):
    def test_signed_shape_two_witnesses_valid(self):
        self.assertEqual(len(check_observation(fixture())),2)

    def test_missing_table_must_be_null_not_zero(self):
        obs=fixture()
        obs["companies"][1]["installation_audit_rows_limited"]=0
        with self.assertRaisesRegex(FunctionalProfileDenied,"MISSING_TABLE"):
            check_observation(obs)

    def test_false_positive_extra_identifier_rejected(self):
        obs=fixture()
        obs["companies"][0]["source_business_ot"]="123456"
        with self.assertRaisesRegex(FunctionalProfileDenied,"NOT_EXACT"):
            check_observation(obs)

    def test_wrong_company_target_rejected(self):
        obs=fixture()
        obs["companies"][1]["qa_target"]="ELSE70/dbComercial001_D"
        with self.assertRaisesRegex(FunctionalProfileDenied,"WRONG_COMPANY"):
            check_observation(obs)

    def test_ambiguous_date_compared_to_august_rejected(self):
        obs=fixture()
        obs["companies"][0]["sample_ot_from_august_2026"]=False
        with self.assertRaisesRegex(FunctionalProfileDenied,"AUGUST_COVERAGE_DRIFT"):
            check_observation(obs)

    def test_wrong_witness_and_forged_business_mutation_rejected(self):
        for mutator in (
            lambda o:o["companies"][0].update(budget_rows_limited=0),
            lambda o:o["companies"][1].update(ot_exact_rebound=False),
            lambda o:o["companies"][1].update(changes_executed=True),
            lambda o:o.update(changes_executed=True),
            lambda o:o.update(no_raw_business_keys_returned=False),
        ):
            with self.subTest(kind=mutator):
                o=fixture()
                mutator(o)
                with self.assertRaises(FunctionalProfileDenied):
                    check_observation(o)

    def test_invalid_count_and_forged_null_rejected(self):
        obs=fixture()
        obs["companies"][0]["resource_rows_limited"]=3
        with self.assertRaisesRegex(FunctionalProfileDenied,"COUNT"):
            check_observation(obs)
        obs=fixture()
        obs["companies"][0]["installation_audit_rows_limited"]=None
        with self.assertRaisesRegex(FunctionalProfileDenied,"EXPECTED_AUDIT_TABLE"):
            check_observation(obs)

if __name__=="__main__":
    unittest.main()

"""Adversarial tests for the signed last-100 retrospective QA gate."""
from copy import deepcopy
import unittest

from else_dominance.qa_august_last100_identity_authority import AugustLast100EvidenceAuthority
from tests.test_august_identity_authority import fixture


def fake(last_link=True):
    data=deepcopy(fixture())
    data["schema"]="else.itil.qa.aug2026-last100-company-typed.v1"
    if last_link:
        case=data["case_metadata"][0]
        decision=data["case_decisions"][0]
        decision["status"]="SINGLE_EXACT_TYPED_PK_QA_OBSERVATION"
        decision["typed_business_link_count"]=1
        data["typed_matches"]=[{
           "rank":1,"case_sha256":case["case_sha256"],
           "business_kind":"SUPPLY","company":"1",
           "qa_database":"dbComercial001_D",
           "pk_sha256":"a"*64,
           "itil_branch":"1","business_branch":"1",
           "branch_matches":True,
           "explicit_request_label":True,
           "same_company_provider_route":True,
        }]
    return data


class Last100AuthorityTests(unittest.TestCase):
    def test_one_verified_retrospective_observation_no_causality(self):
        a=AugustLast100EvidenceAuthority(fake(),"f"*64)
        x=a.inspect(case_sha256=f"{1:064x}",module_code="0101300100000",
                    as_of="2026-08-31",retrospective_qa=True)
        self.assertEqual(x["status"],"SINGLE_EXACT_TYPED_PK_QA_OBSERVATION")
        self.assertFalse(x["historical_fix_or_root_cause_certified"])
        self.assertFalse(x["raw_business_keys_disclosed"])

    def test_no_operator_authorization_is_blocked(self):
        a=AugustLast100EvidenceAuthority(fake(),"f"*64)
        x=a.inspect(case_sha256=f"{1:064x}",module_code="0101300100000",as_of="2026-08-31")
        self.assertEqual(x["status"],"BLOCKED")

    def test_wrong_company_db_is_rejected(self):
        data=fake()
        data["typed_matches"][0]["qa_database"]="dbComercial200_D"
        with self.assertRaisesRegex(ValueError,"CROSS_COMPANY_BRANCH"):
            AugustLast100EvidenceAuthority(data,"f"*64)

    def test_false_branch_is_rejected(self):
        data=fake()
        data["typed_matches"][0]["business_branch"]="2"
        with self.assertRaisesRegex(ValueError,"CROSS_COMPANY_BRANCH"):
            AugustLast100EvidenceAuthority(data,"f"*64)

    def test_missing_real_pk_refuses_claim(self):
        data=fake()
        data["typed_matches"]=[]
        with self.assertRaisesRegex(ValueError,"LINK_COUNT_DRIFT"):
            AugustLast100EvidenceAuthority(data,"f"*64)

    def test_false_repair_is_rejected(self):
        data=fake()
        data["case_decisions"][0]["repair_certified"]=True
        with self.assertRaisesRegex(ValueError,"CASE_DECISION_INVALID"):
            AugustLast100EvidenceAuthority(data,"f"*64)

    def test_unsupported_company_cannot_become_verified(self):
        data=fake(False)
        data["case_decisions"][-1]["status"]="SINGLE_EXACT_TYPED_PK_QA_OBSERVATION"
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_COMPANY"):
            AugustLast100EvidenceAuthority(data,"f"*64)


if __name__=="__main__":
    unittest.main()

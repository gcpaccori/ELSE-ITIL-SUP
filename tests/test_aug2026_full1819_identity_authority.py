"""The full cohort cannot be promoted to repairs by forged evidence."""
from copy import deepcopy
import unittest

from else_dominance.qa_august_full1819_identity_authority import AugustFull1819EvidenceAuthority
from tests.test_august_identity_authority import fixture as first100

def fake():
    data=deepcopy(first100())
    data["schema"]="else.itil.qa.aug2026-full1819-company-typed.v1"
    for i in range(101,1820):
        company="1" if i<=1703 else "6"
        sha=f"{i:064x}"
        data["case_metadata"].append({
          "rank":i, "case_sha256":sha,
          "module_code":"0101300100000",
          "opened_at":"2026-08-01T08:06:00",
          "itil_company":company,"itil_branch":"1",
          "source_only":True,"history_not_read":True
        })
        data["case_decisions"].append({
          "rank":i,"case_sha256":sha,
          "status":("NO_EXPLICIT_TYPED_BUSINESS_KEY_IN_REQUEST" if company=="1"
                    else "COMPANY_PROVIDER_ROUTE_NOT_CERTIFIED"),
          "typed_business_link_count":0,
          "company_route_verified":company=="1",
          "repair_certified":False,
          "historical_causality_certified":False,
          "timestamp_only_november_qa":True
        })
    data["report"]["evaluated_cases"]=1819
    for i in range(1,11):
        data["case_decisions"][i-1]["typed_business_link_count"]=2 if i==10 else 1
        data["case_decisions"][i-1]["status"]=(
          "MULTIPLE_EXACT_TYPED_PKS_NO_PRIMARY_INFERRED" if i==10
          else "SINGLE_EXACT_TYPED_PK_QA_OBSERVATION"
        )
        for k in range(2 if i==10 else 1):
            data["typed_matches"].append({
              "rank":i,"case_sha256":f"{i:064x}",
              "business_kind":"SUPPLY" if k==0 else "OT",
              "company":"1","qa_database":"dbComercial001_D",
              "pk_sha256":f"{i*10+k:064x}",
              "itil_branch":"1","business_branch":"1",
              "branch_matches":True,"explicit_request_label":True,
              "same_company_provider_route":True
            })
    return data

class FullMonthAuthorityTests(unittest.TestCase):
    def test_1819_11_observations_10_cases(self):
        authority=AugustFull1819EvidenceAuthority(fake(),"f"*64)
        self.assertEqual(len(authority.by_case),1819)
        one=authority.inspect(case_sha256=f"{1:064x}",module_code="0101300100000",
                              as_of="2026-08-31",retrospective_qa=True)
        self.assertEqual(one["verified_typed_pk_observation_count"],1)
        self.assertFalse(one["historical_fix_or_root_cause_certified"])
        many=authority.inspect(case_sha256=f"{10:064x}",module_code="0101300100000",
                               as_of="2026-08-31",retrospective_qa=True)
        self.assertEqual(many["status"],"MULTIPLE_EXACT_TYPED_PKS_NO_PRIMARY_INFERRED")
    def test_no_operator_auth_blocked(self):
        x=AugustFull1819EvidenceAuthority(fake(),"f"*64).inspect(
            case_sha256=f"{1:064x}",module_code="0101300100000",as_of="2026-08-31")
        self.assertEqual(x["status"],"BLOCKED")
    def test_missing_last_case_fails_closed(self):
        data=fake()
        data["case_metadata"].pop()
        with self.assertRaisesRegex(ValueError,"RECEIPT_SCHEMA_INVALID"):
            AugustFull1819EvidenceAuthority(data,"f"*64)
    def test_cross_company_pk_rejected(self):
        data=fake()
        data["typed_matches"][0]["company"]="3"
        with self.assertRaisesRegex(ValueError,"CROSS_COMPANY_BRANCH"):
            AugustFull1819EvidenceAuthority(data,"f"*64)
    def test_wrong_branch_pk_rejected(self):
        data=fake()
        data["typed_matches"][0]["branch_matches"]=True
        data["typed_matches"][0]["business_branch"]="2"
        with self.assertRaisesRegex(ValueError,"CROSS_COMPANY_BRANCH"):
            AugustFull1819EvidenceAuthority(data,"f"*64)
    def test_false_repair_rejected(self):
        data=fake()
        data["case_decisions"][-1]["repair_certified"]=True
        with self.assertRaisesRegex(ValueError,"CASE_DECISION_INVALID"):
            AugustFull1819EvidenceAuthority(data,"f"*64)
    def test_pretended_unverified_link_rejected(self):
        data=fake()
        data["typed_matches"][0]["explicit_request_label"]=False
        with self.assertRaisesRegex(ValueError,"CROSS_COMPANY_BRANCH"):
            AugustFull1819EvidenceAuthority(data,"f"*64)
if __name__=="__main__":
    unittest.main()

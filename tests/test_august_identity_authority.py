from __future__ import annotations
import copy
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest

from else_dominance.qa_august_identity_authority import (
    August100EvidenceAuthority,from_windows_paths
)


def fixture():
    cases=[]
    decisions=[]
    for i in range(1,101):
        company="1" if i<=79 else "3" if i<=89 else "6"
        h=f"{i:064x}"
        cases.append({
            "rank":i,"case_sha256":h,
            "module_code":"0101300100000","opened_at":"2026-08-01T08:06:00",
            "itil_company":company,"itil_branch":"1",
            "source_only":True,"history_not_read":True,
        })
        decisions.append({
            "rank":i,"case_sha256":h,
            "status":("NO_EXPLICIT_TYPED_BUSINESS_KEY_IN_REQUEST" if i<=89
                      else "COMPANY_PROVIDER_ROUTE_NOT_CERTIFIED"),
            "typed_business_link_count":0,
            "company_route_verified":company!="6",
            "repair_certified":False,
            "historical_causality_certified":False,
            "timestamp_only_november_qa":True,
        })
    return {"schema":"else.itil.qa.aug2026-first100-company-typed.v1",
            "source_sha256":"a"*64,
            "report":{
                "evaluated_cases":100,"source_cases":1819,
                "typed_labels_used_no_history":True,
                "legacy_generic_cross_db_matches_are_not_promoted_to_authority":True,
            },
            "case_metadata":cases,"case_decisions":decisions,
            "typed_matches":[],
            "history_not_read":True,"business_writes":0,"read_only":True}


class AuthorityTests(unittest.TestCase):
    def test_exact100_fail_closed(self):
        a=August100EvidenceAuthority(fixture(),"f"*64)
        result=a.inspect(case_sha256=f"{1:064x}",module_code="0101300100000",
                         as_of="2026-08-01T08:06:00",retrospective_qa=True)
        self.assertEqual(result["status"],"NO_EXPLICIT_TYPED_BUSINESS_KEY_IN_REQUEST")
        self.assertFalse(result["historical_fix_or_root_cause_certified"])
        self.assertFalse(result["raw_business_keys_disclosed"])

    def test_unauthorized_cannot_inspect(self):
        a=August100EvidenceAuthority(fixture(),"f"*64)
        self.assertEqual(a.inspect(case_sha256=f"{1:064x}",
                         module_code="0101300100000",as_of="2026-08-01")["status"],"BLOCKED")

    def test_wrong_module_denied(self):
        a=August100EvidenceAuthority(fixture(),"f"*64)
        self.assertEqual(a.inspect(case_sha256=f"{1:064x}",
            module_code="another",as_of="2026-08-01",retrospective_qa=True)["status"],"BLOCKED")

    def test_asof_previous_day_denied(self):
        a=August100EvidenceAuthority(fixture(),"f"*64)
        self.assertEqual(a.inspect(case_sha256=f"{1:064x}",
            module_code="0101300100000",as_of="2026-08-00",retrospective_qa=True)["status"],"BLOCKED")

    def test_false_success_blocked(self):
        f=fixture()
        f["case_decisions"][0]["status"]="SINGLE_EXACT_TYPED_PK_QA_OBSERVATION"
        f["case_decisions"][0]["typed_business_link_count"]=1
        with self.assertRaisesRegex(ValueError,"LINK_COUNT_DRIFT"):
            August100EvidenceAuthority(f,"f"*64)

    def test_unsupported_company_false_pass_rejected(self):
        f=fixture()
        f["case_decisions"][-1]["status"]="SINGLE_EXACT_TYPED_PK_QA_OBSERVATION"
        f["case_decisions"][-1]["company_route_verified"]=True
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_COMPANY"):
            August100EvidenceAuthority(f,"f"*64)

    def test_forged_wrong_branch_rejected(self):
        f=fixture()
        f["typed_matches"].append({
            "rank":1,"case_sha256":f"{1:064x}","company":"1",
            "qa_database":"dbComercial001_D","explicit_request_label":True,
            "same_company_provider_route":True,"business_kind":"SUPPLY",
            "pk_sha256":"a"*64,"itil_branch":"1","business_branch":"2",
            "branch_matches":True
        })
        with self.assertRaisesRegex(ValueError,"CROSS_COMPANY_BRANCH"):
            August100EvidenceAuthority(f,"f"*64)

    def test_wrong_database_rejected(self):
        f=fixture()
        f["typed_matches"].append({
            "rank":1,"case_sha256":f"{1:064x}","company":"1",
            "qa_database":"dbComercial200_D","explicit_request_label":True,
            "same_company_provider_route":True,"business_kind":"OT",
            "pk_sha256":"a"*64,"itil_branch":"1","business_branch":"1",
            "branch_matches":True
        })
        with self.assertRaisesRegex(ValueError,"CROSS_COMPANY_BRANCH"):
            August100EvidenceAuthority(f,"f"*64)

    def test_missing_one_case_rejected(self):
        f=fixture()
        f["case_decisions"].pop()
        with self.assertRaisesRegex(ValueError,"RECEIPT_SCHEMA_INVALID"):
            August100EvidenceAuthority(f,"f"*64)

    def test_hmac_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            reader=p/"source.cs"
            reader.write_text("safe")
            key=p/"signer"
            key.write_bytes(b"x"*32)
            receipt=p/"receipt.json"
            proof=p/"receipt.json.proof.json"
            obj=fixture()
            obj["source_sha256"]=hashlib.sha256(reader.read_bytes()).hexdigest()
            raw=json.dumps(obj).encode()
            receipt.write_bytes(raw)
            rsha=hashlib.sha256(raw).hexdigest()
            token=(obj["schema"]+":"+obj["source_sha256"]+":"+rsha).encode()
            proof.write_text(json.dumps({
                "schema":obj["schema"]+"-hmac.v1",
                "source_sha256":obj["source_sha256"],
                "receipt_sha256":rsha,
                "hmac_sha256":hmac.new(key.read_bytes(),token,"sha256").hexdigest(),
                "read_only":True
            }))
            self.assertEqual(len(from_windows_paths(
                receipt=receipt,proof=proof,source_reader=reader,signer=key
            ).by_case),100)
            data=json.loads(receipt.read_text())
            data["business_writes"]=1
            receipt.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"HMAC"):
                from_windows_paths(receipt=receipt,proof=proof,
                                   source_reader=reader,signer=key)


if __name__=="__main__":
    unittest.main()

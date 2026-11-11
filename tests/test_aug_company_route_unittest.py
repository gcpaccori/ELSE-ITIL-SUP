"""Portable adversarial checks for company-authoritative QA evidence v2.

Uses synthetic 32-byte HMAC key; NO corporate identifiers, real QA connection
or historical resolutions required in CI. Native O5/O13/O15 additionally runs
when ELSE CORE is importable.
"""
from __future__ import annotations

from base64 import b64encode
from hashlib import sha256
from pathlib import Path
import copy
import hmac
import json
import tempfile
import unittest

from else_dominance.company_routed_verified import (
    DELIVERY,RECEIPT,OBS,SOURCE,SOURCE_SHA,SAMPLE_SHA,
    validate_one,parse_strict,digest
)

try:
    from else_core.hand_kernel import Outcome
    from else_dominance.company_routed_o5_hand import (
        AuthorizedCompanyRoutedReceipt,build_company_routed_router
    )
    import else_dominance.company_routed_o5_hand as hand_module
    import else_dominance.company_routed_o5_verifier as verifier_module
    CORE_PRESENT=True
except ModuleNotFoundError as e:
    if e.name not in ("else_core","else_core.guardian",
                      "else_core.hand_kernel","else_core.source_truth"):
        raise
    CORE_PRESENT=False

CASE=sha256(b"sample-aug-company-authority").hexdigest()
BLIND=sha256(b"sample-frozen-blind-cohort").hexdigest()
KEY=b"X"*32
assert len(KEY)==32

def mk(mode="OT",with_supply=True,company=3,text=None):
    if text is None:
        text=("Revisar OT 123456 y suministro 987654" if with_supply
              else "Revisar OT 123456") if mode=="OT" else "Revisar suministro 987654"
    line_sha=sha256(b"an-exact-synthetic-cohort-line").hexdigest()
    cohort={CASE:{"incident_text_redacted":text}}
    meta={"blind_sha256":BLIND}
    line_shas={CASE:line_sha}
    ids=("123456" if mode=="OT" else None)
    supply=("987654" if with_supply or mode=="SUPPLY" else None)
    counts=(
        {k:0 for k in ("order","installation","interior","meter")}
        if mode=="OT" else
        {k:0 for k in ("supply","orders_by_supply",
                       "massive_installation","installation_owner")}
    )
    if mode=="OT" and supply:
        counts.update({"supply":0,"orders_by_supply":0,"exact_ot_supply":0})
    body={
        "schema":RECEIPT,
        "case_sha256":CASE,
        "case_row_line_sha256":line_sha,
        "blind_cohort_sha256":BLIND,
        "itil_source":"ELSE70/dbITIL_D/dbo.taIncidente",
        "itil_company":company,"itil_branch":"1","itil_service":"1",
        "itil_module":"0101100123000","itil_sistema":"1",
        "itil_row_verified_from_corporate_sql":True,
        "claim_type":mode,
        "reported_ot_sha256":sha256(ids.encode()).hexdigest() if ids else None,
        "reported_supply_sha256":sha256(supply.encode()).hexdigest() if supply else None,
        "observation":{
            "schema":OBS,
            "qa_target":f'ELSE70/dbComercial00{company}_D',
            "sql_profile":"PINNED_TYPED_OT_SELECTS" if mode=="OT"
                         else "PINNED_TYPED_SUPPLY_SELECTS",
            "counts":counts,
            "read_utc":"2026-11-11T17:00:00.0000000Z",
            "read_only":True,
            "changes_executed":False
        },
        "historical_solution_read":False,
        "corporate_itil_business_join_certified":False,
        "root_cause_certified":False,
        "repair_certified":False,
        "source_sha256":SOURCE_SHA
    }
    return body,cohort,meta,line_shas

def packed(obj):
    return json.dumps(obj,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode()

def signed(body,secret=KEY):
    raw=packed(body)
    sha=digest(raw)
    ident=digest((DELIVERY+":"+CASE+":"+BLIND).encode())[:32]
    msg=f'{DELIVERY}:{ident}:{SOURCE_SHA}:{sha}'.encode()
    return {
        "schema":DELIVERY,"job_id":ident,
        "case_sha256":CASE,"blind_cohort_sha256":BLIND,
        "source_sha256":SOURCE_SHA,"sample_sha256":SAMPLE_SHA,
        "receipt_sha256":sha,"receipt_json_base64":b64encode(raw).decode(),
        "hmac_sha256":hmac.new(secret,msg,"sha256").hexdigest(),
        "sql_executed_on_windows":True,"read_only":True,
        "changes_executed":False
    }

def checked(tmp,body,cohort,manifest,lines,*,modify_env=None):
    env=signed(body)
    if modify_env is not None:modify_env(env)
    path=Path(tmp)/(env["job_id"]+".private.json")
    path.write_bytes(packed(env))
    return validate_one(path,KEY,cohort,manifest,lines,{CASE},len(SOURCE.read_bytes()))

class V2CompanyRoutingContract(unittest.TestCase):
    def test_valid_two_company_destinations_and_modes(self):
        for company in (1,3):
            for mode,has_supply in (("OT",False),("OT",True),("SUPPLY",True)):
                with self.subTest(company=company,mode=mode,has_supply=has_supply):
                    body,cohort,manifest,lines=mk(mode,has_supply,company)
                    with tempfile.TemporaryDirectory() as tmp:
                        result=checked(tmp,body,cohort,manifest,lines)
                        self.assertEqual(result["itil_company"],company)
                        self.assertEqual(result["qa_target"],
                            f'ELSE70/dbComercial00{company}_D')
                        self.assertEqual(result["mode"],mode)

    def test_resigned_wrong_company_database_rejected(self):
        body,cohort,manifest,lines=mk()
        body["observation"]["qa_target"]="ELSE70/dbComercial001_D"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"WRONG_QA_TARGET"):
                checked(tmp,body,cohort,manifest,lines)

    def test_company_tampering_with_correct_old_db_rejected(self):
        body,cohort,manifest,lines=mk()
        body["itil_company"]=1
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"WRONG_QA_TARGET"):
                checked(tmp,body,cohort,manifest,lines)

    def test_invalid_hmac_rejected(self):
        body,cohort,manifest,lines=mk()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"HMAC_INVALID"):
                checked(tmp,body,cohort,manifest,lines,
                    modify_env=lambda x:x.update(hmac_sha256="0"*64))

    def test_legacy_v1_receipt_cannot_be_replayed(self):
        body,cohort,manifest,lines=mk()
        body["schema"]="else.itil.aug2026.typed-business-identifier-receipt.v1"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"OWNER_OR_FALSE_CLAIM"):
                checked(tmp,body,cohort,manifest,lines)

    def test_wrong_claim_and_ambiguous_ticket_rejected(self):
        body,cohort,manifest,lines=mk()
        body["reported_ot_sha256"]=sha256(b"111111").hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"TICKET_TEXT_ID_NOT_BOUND"):
                checked(tmp,body,cohort,manifest,lines)
        body,cohort,manifest,lines=mk()
        cohort[CASE]["incident_text_redacted"]="OT 123456 y OT 222222 y suministro 987654"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"AMBIGUOUS"):
                checked(tmp,body,cohort,manifest,lines)

    def test_unbounded_counts_and_forged_positive_rejected(self):
        body,cohort,manifest,lines=mk()
        body["observation"]["counts"]["order"]=3
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"NOT_BOUND"):
                checked(tmp,body,cohort,manifest,lines)
        body,cohort,manifest,lines=mk()
        body["observation"]["counts"]["exact_ot_supply"]=1
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"IMPOSSIBLE"):
                checked(tmp,body,cohort,manifest,lines)

    def test_source_row_and_solution_leakage_rejected(self):
        for change in (
            lambda b:b.update(case_row_line_sha256="0"*64),
            lambda b:b.update(historical_solution_read=True),
            lambda b:b.update(repair_certified=True),
            lambda b:b.update(source_sha256="f"*64),
            lambda b:b["observation"].update(changes_executed=True),
        ):
            body,cohort,manifest,lines=mk()
            change(body)
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    checked(tmp,body,cohort,manifest,lines)

    def test_replayed_other_cohort_or_sample_rejected(self):
        body,cohort,manifest,lines=mk()
        for field in ("blind_cohort_sha256","sample_sha256","source_sha256"):
            with tempfile.TemporaryDirectory() as tmp:
                with self.subTest(field=field):
                    with self.assertRaises(ValueError):
                        checked(tmp,body,cohort,manifest,lines,
                            modify_env=lambda x:x.update({field:"f"*64}))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ValueError):
            parse_strict(b'{"schema":"v2","schema":"v1"}')

    @unittest.skipUnless(CORE_PRESENT,"ELSE CORE native kernel not on CI PYTHONPATH")
    def test_native_o5_o13_o15_and_invalid_target(self):
        body,cohort,manifest,lines=mk()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"worker_hmac.private").write_bytes(KEY)
            (root/"worker_hmac.private").chmod(0o600)
            old=hand_module.LEGACY_ROOT
            old2=verifier_module.HMAC_PATH
            hand_module.LEGACY_ROOT=root
            verifier_module.HMAC_PATH=root/"worker_hmac.private"
            try:
                def invoke(body):
                    env=signed(body)
                    path=root/(env["job_id"]+".private.json")
                    path.write_bytes(packed(env))
                    owner=AuthorizedCompanyRoutedReceipt(
                        path,digest(path.read_bytes()),CASE,3,
                        SOURCE_SHA,len(SOURCE.read_bytes()),
                        cohort[CASE]["incident_text_redacted"])
                    _,router,op=build_company_routed_router(owner)
                    return router.route(op)
                result=invoke(body)
                self.assertEqual(result.outcome,Outcome.PASS)
                self.assertTrue(result.guardian_result.verification.independent)
                bad=copy.deepcopy(body)
                bad["observation"]["qa_target"]="ELSE70/dbComercial001_D"
                result=invoke(bad)
                self.assertNotEqual(result.outcome,Outcome.PASS)
            finally:
                hand_module.LEGACY_ROOT=old
                verifier_module.HMAC_PATH=old2

if __name__=="__main__":
    unittest.main()

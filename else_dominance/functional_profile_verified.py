"""Independent verification of real SIELSE QA functional-query positive witnesses.

Every witness is linked to pinned C# bytes, Windows worker HMAC and one
company-specific database. Unavailable tables are NULL, not fabricated zeros.
This is a source/reader integration test, never proof that a particular
August ITIL ticket has been repaired.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from hashlib import sha256
from pathlib import Path
import hmac
import json
import re

from .qa_feb100_cluster import parse_strict
from .aug2026_sap_ot_verified import ROOT as LEGACY_ROOT

ROOT=Path("/home/u23u/else_itil_positive_controls_20261111")
FILE=ROOT/"functional_profiles.private.json"
SOURCE=Path(__file__).resolve().parents[1]/"qa"/"FunctionalQueries.cs"
SOURCE_SHA="e9ada48e9c15ce894e5a563e09d32c31b52282d35118c81b3ffe2f43aaea2c58"
SCHEMA="else.itil.qa.functional-profile-witness-signed.v1"
OBS="else.itil.qa.functional-business-profiles-positive-witness.v1"
PROFILE="CROSS_COMPANY_FIVE_FUNCTIONAL_SELECT_PROFILES_V1"
COUNTS={
  "budget_rows_limited","resource_rows_limited","voucher_rows_limited",
  "osinergmin_history_rows_limited","change_log_rows_limited",
  "installation_audit_rows_limited","installation_module_rows_limited",
  "interior_installation_rows_limited","meter_supply_rows_limited"
}
ROW_KEYS={
  "company","qa_target","sample_ot_from_august_2026",
  "sample_ot_witness_in_budget","ot_exact_rebound",
  *COUNTS,"ot_state_catalog_found","execution_dates_present",
  "read_only","changes_executed"
}

class FunctionalProfileDenied(ValueError):pass

def demand(ok,message):
    if not ok:raise FunctionalProfileDenied(message)

def canon(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()

def sha(raw):
    return sha256(raw).hexdigest()

def check_observation(obs):
    demand(type(obs) is dict and set(obs)=={
        "schema","profile_count","companies","no_raw_business_keys_returned",
        "read_only","changes_executed"
    },"FUNC_PROFILE_SCHEMA_INVALID")
    demand(
        obs["schema"]==OBS
        and type(obs["profile_count"]) is int
        and obs["profile_count"]==5
        and obs["no_raw_business_keys_returned"] is True
        and obs["read_only"] is True
        and obs["changes_executed"] is False
        and type(obs["companies"]) is list
        and len(obs["companies"])==2,
        "FUNC_PROFILE_SCOPE_NOT_FIXED"
    )
    for index,row in enumerate(obs["companies"]):
        company=(1,3)[index]
        demand(type(row) is dict and set(row)==ROW_KEYS,
               "FUNC_PROFILE_COMPANY_ROW_NOT_EXACT")
        demand(type(row["company"]) is int and row["company"]==company
               and row["qa_target"]==f'ELSE70/dbComercial00{company}_D'
               and row["sample_ot_witness_in_budget"] is True
               and row["ot_exact_rebound"] is True
               and row["ot_state_catalog_found"] is True
               and row["read_only"] is True and row["changes_executed"] is False,
               "FUNC_PROFILE_WRONG_COMPANY_OR_NOT_A_POSITIVE_WITNESS")
        for boolean in (
            "sample_ot_from_august_2026","sample_ot_witness_in_budget",
            "ot_exact_rebound","ot_state_catalog_found",
            "execution_dates_present","read_only","changes_executed"
        ):
            demand(type(row[boolean]) is bool,
                   "FUNC_PROFILE_NON_BOOLEAN_FLAG")
        for count in COUNTS:
            val=row[count]
            demand(val is None or (type(val) is int and val in (0,1,2)),
                   "FUNC_PROFILE_COUNT_OR_MISSING_TABLE_MISREPRESENTED")
        demand(row["budget_rows_limited"]==1,
               "FUNC_PROFILE_BUDGET_POSITIVE_CONTROL_FAILED")
        demand(row["sample_ot_from_august_2026"] is (company==1),
               "FUNC_PROFILE_AUGUST_COVERAGE_DRIFT")
        if company==3:
            demand(row["installation_audit_rows_limited"] is None,
                   "FUNC_PROFILE_COMPANY3_MISSING_TABLE_NOT_EXPLICIT")
        else:
            demand(row["installation_audit_rows_limited"] is not None,
                   "FUNC_PROFILE_COMPANY1_EXPECTED_AUDIT_TABLE_MISSING")
    return obs["companies"]

def verify_functional_profiles():
    demand(FILE.is_file() and not FILE.is_symlink(),
           "FUNC_PROFILE_SIGNED_WORKER_FILE_MISSING")
    demand(SOURCE.is_file() and not SOURCE.is_symlink()
           and sha(SOURCE.read_bytes())==SOURCE_SHA,
           "FUNC_PROFILE_CSHARP_SOURCE_CHANGED")
    env=parse_strict(FILE.read_bytes())
    demand(type(env) is dict and set(env)=={
        "schema","receipt_sha256","reader_source_sha256",
        "receipt","worker","completed_utc","read_only","hmac_sha256"
    },"FUNC_PROFILE_ENVELOPE_NOT_EXACT")
    demand(env["schema"]==SCHEMA and env["reader_source_sha256"]==SOURCE_SHA
           and env["worker"]=="ELSE62" and env["read_only"] is True,
           "FUNC_PROFILE_WINDOWS_OWNER_NOT_VERIFIED")
    receipt=env["receipt"]
    demand(type(receipt) is dict and set(receipt)=={
        "schema","observation","source_sha256","query_profile",
        "read_only","changes_executed"
    },"FUNC_PROFILE_RECEIPT_NOT_EXACT")
    demand(receipt["schema"]==OBS and receipt["source_sha256"]==SOURCE_SHA
           and receipt["query_profile"]==PROFILE
           and receipt["read_only"] is True
           and receipt["changes_executed"] is False,
           "FUNC_PROFILE_QUERY_NOT_FIXED")
    signed_hash=sha(canon(receipt))
    demand(env["receipt_sha256"]==signed_hash,
           "FUNC_PROFILE_RECEIPT_SHA_MISMATCH")
    secret_file=LEGACY_ROOT/"worker_hmac.private"
    demand(secret_file.is_file() and not secret_file.is_symlink()
           and secret_file.stat().st_mode&0o077==0,
           "FUNC_PROFILE_WORKER_HMAC_PERMISSION")
    secret=secret_file.read_bytes()
    demand(len(secret)==32,"FUNC_PROFILE_HMAC_LENGTH")
    msg=f'{SCHEMA}:{SOURCE_SHA}:{signed_hash}'.encode()
    demand(type(env["hmac_sha256"]) is str and
           hmac.compare_digest(hmac.new(secret,msg,"sha256").hexdigest(),
                              env["hmac_sha256"]),
           "FUNC_PROFILE_INVALID_WORKER_HMAC")
    timestamp=env["completed_utc"]
    demand(type(timestamp) is str and len(timestamp)<=55,
           "FUNC_PROFILE_TIMESTAMP_INVALID")
    instant=datetime.fromisoformat(timestamp.replace("Z","+00:00"))
    demand(instant.tzinfo is not None and
           instant<=datetime.now(timezone.utc)+timedelta(minutes=15),
           "FUNC_PROFILE_WORKER_CLOCK_EXCEEDS_15_MIN_SKEW_TOLERANCE")
    rows=check_observation(receipt["observation"])
    return {
      "schema":"else.itil.qa.functional-profile-witness-replay.v1",
      "source_sha256":SOURCE_SHA,
      "signed_receipt_sha256":signed_hash,
      "verified_company_profiles":len(rows),
      "fixed_query_profiles":5,
      "company1_august_budget_ot_positive":True,
      "company3_historical_budget_ot_positive":True,
      "company3_missing_installation_audit_table_explicit":True,
      "witness_ids_not_sourced_from_itil_ticket_claims":True,
      "read_only":True,"corporate_repairs_certified":0,
      "new_queries_executed_during_replay":0,
    }

if __name__=="__main__":
    print(json.dumps(verify_functional_profiles(),sort_keys=True))

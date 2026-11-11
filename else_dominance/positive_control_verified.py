"""Independent HMAC/sha256 verification for SIELSE NuGet positive controls.

The Windows worker runs real parameterized SELECT samples and only publishes
boolean outcomes. No raw OT or supply identifiers, no writes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import hmac
import json
import re

from .qa_feb100_cluster import parse_strict
from .aug2026_sap_ot_verified import ROOT as LEGACY_ROOT

ROOT=Path("/home/u23u/else_itil_positive_controls_20261111")
SOURCE=Path(__file__).resolve().parents[1]/"qa"/"PositiveControlRead.cs"
SOURCE_SHA="9fc41bc9a511586be2d0e084dedea282b9c219d6aaf67218c87f1be17b4d133a"
SCHEMA="else.itil.qa.positive-control-signed.v1"
OBS="else.itil.qa.company-positive-control.v1"
FILE=ROOT/"positive_controls.private.json"

class PositiveControlDenied(ValueError):pass

def demand(ok,msg):
    if not ok:raise PositiveControlDenied(msg)

def canon(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()

def sha(v):
    return sha256(v).hexdigest()

def check_observation(o):
    demand(type(o) is dict and set(o)=={
       "schema","cases","no_identifiers_returned","read_only","mutations"
    } and o["schema"]==OBS and o["no_identifiers_returned"] is True
       and o["read_only"] is True and type(o["mutations"]) is int
       and o["mutations"]==0,"POSITIVE_CONTROL_SCOPE_DRIFT")
    rows=o["cases"]
    demand(type(rows) is list and len(rows)==2,"POSITIVE_CONTROL_TWO_COMPANIES_REQUIRED")
    shape={
      "company","qa_target","aug2026_ot_positive_sample_found",
      "aug2026_ot_sample_registration_date","aug2026_ot_exact_lookup_pass",
      "supply_positive_sample_found","supply_exact_lookup_pass",
      "ot_supply_link_sample_found","ot_supply_exact_link_lookup_pass",
      "read_only"
    }
    for index,record in enumerate(rows):
        comp=(1,3)[index]
        demand(type(record) is dict and set(record)==shape,
               "POSITIVE_CONTROL_ROW_FIELDS_DRIFT")
        demand(type(record["company"]) is int and record["company"]==comp
               and record["qa_target"]==f'ELSE70/dbComercial00{comp}_D'
               and record["read_only"] is True,
               "POSITIVE_CONTROL_WRONG_COMPANY")
        for key in (
            "aug2026_ot_positive_sample_found","aug2026_ot_exact_lookup_pass",
            "supply_positive_sample_found","supply_exact_lookup_pass",
            "ot_supply_link_sample_found","ot_supply_exact_link_lookup_pass"
        ):
            demand(type(record[key]) is bool,"POSITIVE_CONTROL_BOOLEAN_NOT_EXACT")
        demand(record["supply_positive_sample_found"] is True
           and record["supply_exact_lookup_pass"] is True
           and record["ot_supply_link_sample_found"] is True
           and record["ot_supply_exact_link_lookup_pass"] is True,
           "POSITIVE_CONTROL_EXACT_LOOKUP_FAILED")
        demand(record["aug2026_ot_positive_sample_found"]
           is record["aug2026_ot_exact_lookup_pass"],
           "POSITIVE_CONTROL_AUG_OT_LOOKUP_DRIFT")
        value=record["aug2026_ot_sample_registration_date"]
        demand(type(value) is str and (
           (record["aug2026_ot_positive_sample_found"] and
            re.fullmatch(r"2026-08-\d{2}",value) is not None)
           or (record["aug2026_ot_positive_sample_found"] is False and value=="")
        ),"POSITIVE_CONTROL_AUG_DATE_NOT_PROVEN")
    demand(rows[0]["aug2026_ot_exact_lookup_pass"] is True,
           "POSITIVE_CONTROL_COMPANY1_AUGUST_ABSENT")
    demand(rows[1]["aug2026_ot_positive_sample_found"] is False,
           "POSITIVE_CONTROL_COMPANY3_COVERAGE_DRIFT")
    return rows

def verify_positive_controls():
    demand(FILE.is_file() and not FILE.is_symlink(),
           "POSITIVE_CONTROL_SIGNED_FILE_MISSING")
    demand(SOURCE.is_file() and not SOURCE.is_symlink() and
           sha(SOURCE.read_bytes())==SOURCE_SHA,
           "POSITIVE_CONTROL_WINDOWS_CSHARP_PIN_INVALID")
    env=parse_strict(FILE.read_bytes())
    demand(type(env) is dict and set(env)=={
       "schema","reader_source_sha256","receipt_sha256","receipt",
       "completed_utc","worker","read_only","hmac_sha256"
    },"POSITIVE_CONTROL_ENVELOPE_SCHEMA")
    demand(env["schema"]==SCHEMA and env["reader_source_sha256"]==SOURCE_SHA
           and env["worker"]=="ELSE62" and env["read_only"] is True,
           "POSITIVE_CONTROL_SOURCE_NOT_WINDOWS")
    receipt=env["receipt"]
    demand(type(receipt) is dict and set(receipt)=={
       "schema","data","reader_source_sha256","query_scope",
       "read_only","changes_executed"
    },"POSITIVE_CONTROL_RECEIPT_FIELDS")
    demand(receipt["schema"]==OBS
           and receipt["reader_source_sha256"]==SOURCE_SHA
           and receipt["query_scope"]=="TWO_COMPANY_TYPED_PARAMETRIZED_FIXED_SELECT"
           and receipt["read_only"] is True and receipt["changes_executed"] is False,
           "POSITIVE_CONTROL_UNEXPECTED_QUERY")
    rec_sha=sha(canon(receipt))
    demand(env["receipt_sha256"]==rec_sha,"POSITIVE_CONTROL_RECEIPT_HASH_INVALID")
    keyfile=LEGACY_ROOT/"worker_hmac.private"
    demand(keyfile.is_file() and not keyfile.is_symlink()
           and keyfile.stat().st_mode&0o077==0,
           "POSITIVE_CONTROL_KEY_PERMISSIONS")
    key=keyfile.read_bytes()
    demand(len(key)==32,"POSITIVE_CONTROL_HMAC_KEY_INVALID")
    msg=f'{SCHEMA}:{SOURCE_SHA}:{rec_sha}'.encode()
    demand(type(env["hmac_sha256"]) is str and
           hmac.compare_digest(hmac.new(key,msg,"sha256").hexdigest(),
                               env["hmac_sha256"]),
           "POSITIVE_CONTROL_HMAC_INVALID")
    utc=env["completed_utc"]
    demand(type(utc) is str and len(utc)<60,
           "POSITIVE_CONTROL_TIMESTAMP_MISSING")
    instant=datetime.fromisoformat(utc.replace("Z","+00:00"))
    demand(instant.tzinfo is not None and instant<=datetime.now(timezone.utc)+timedelta(minutes=15),
           "POSITIVE_CONTROL_FUTURE_BEYOND_DOCUMENTED_WINDOWS_CLOCK_SKEW")
    return {
       "schema":"else.itil.qa.positive-control-independent-replay.v1",
       "signed_source_sha256":SOURCE_SHA,
       "signed_receipt_sha256":rec_sha,
       "verified_company_1_and_3":len(check_observation(receipt["data"])),
       "company1_august_ot_lookups_positive":True,
       "company3_historical_ot_supply_lookups_positive":True,
       "no_historical_qa_absence_claim":True,
       "read_only":True,"mutations":0,
       "window_clock_skew_tolerance_minutes":15,
    }

if __name__=="__main__":
    print(json.dumps(verify_positive_controls(),sort_keys=True))

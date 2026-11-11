"""Audit Windows-signed ITIL CodigoEmpresa -> Comercial company-specific QA reads.

This v2 rejects all legacy v1 receipts that lacked authenticated ITIL company
binding. No raw business identifiers, client records, historic solutions, SQL
from models or data mutation are used. A negative QA result does not establish
global absence nor business closure.
"""
from __future__ import annotations

from base64 import b64decode
from binascii import Error as Base64Error
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import hmac
import json
import re

from .aug2026_sap_ot_verified import (
    ROOT as LEGACY_ROOT, data, eligible, canonical, demand
)
from .qa_feb100_cluster import parse_strict

ROOT=Path("/home/u23u/else_itil_company_route_qa_20261111")
SOURCE=Path(__file__).resolve().parents[1]/"qa"/"CompanyRoutedIdentity.cs"
SOURCE_PATH="qa/CompanyRoutedIdentity.cs"
SOURCE_SHA="c0a6071bf730dfd41d01939794ed7bba8f22b91ffc5b4a4a3ace4fb7637368a3"
SAMPLE=Path("/home/u23u/else_itil_supply_holdout_qa_20261111/sample.private.json")
SAMPLE_SHA="04692e7be5e59c70da825c9597ed3dd9787b51bdae7105160be6a9489386aee8"
DELIVERY="else.itil.aug2026.qa.company-routed-delivery.v2"
RECEIPT="else.itil.aug2026.qa.company-routed-receipt.v2"
OBS="else.itil.aug2026.qa.company-routed-observation.v2"
OT_RE=re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)\s*[:#=-]?\s*(\d{4,19})\b",re.I)
SUPPLY_RE=re.compile(r"\bsuministro\s*[:#=-]?\s*(\d{4,19})\b",re.I)
HEX64=re.compile(r"[0-9a-f]{64}\Z")
HEX32=re.compile(r"[0-9a-f]{32}\Z")
TARGETS={1:"ELSE70/dbComercial001_D",3:"ELSE70/dbComercial003_D"}
OT_COLUMNS={"order","installation","interior","meter"}
OT_SUPPLY_COLUMNS=OT_COLUMNS|{"supply","orders_by_supply","exact_ot_supply"}
SUPPLY_COLUMNS={"supply","orders_by_supply","massive_installation","installation_owner"}
ENVELOPE_KEYS={
    "schema","job_id","case_sha256","blind_cohort_sha256","source_sha256",
    "sample_sha256","receipt_sha256","receipt_json_base64","hmac_sha256",
    "sql_executed_on_windows","read_only","changes_executed"
}
RECEIPT_KEYS={
    "schema","case_sha256","case_row_line_sha256","blind_cohort_sha256",
    "itil_source","itil_company","itil_branch","itil_service","itil_module",
    "itil_sistema","itil_row_verified_from_corporate_sql","claim_type",
    "reported_ot_sha256","reported_supply_sha256","observation",
    "historical_solution_read","corporate_itil_business_join_certified",
    "root_cause_certified","repair_certified","source_sha256"
}
OBS_KEYS={"schema","qa_target","sql_profile","counts","read_utc",
          "read_only","changes_executed"}

def digest(raw):
    return sha256(raw).hexdigest()

def sha_str(s):
    return digest(s.encode())

def require_sha(v):
    demand(type(v) is str and HEX64.fullmatch(v) is not None,"COMPANY_SHA_NOT_CANONICAL")

def time_value(s):
    demand(type(s) is str and len(s)<=55,"COMPANY_UTC_INVALID")
    d=datetime.fromisoformat(re.sub(r"(\.\d{6})\d+",r"\1",s.replace("Z","+00:00")))
    demand(d.tzinfo is not None,"COMPANY_UTC_UNZONED")
    return d.astimezone(timezone.utc)

def selected_context():
    """Regenerate exact holdout and old allowlist from frozen blind cohort."""
    cohort,manifest=data()
    raw=(Path("/home/u23u/else_itil_aug2026_qa_20261110")/
         "aug2026_blind_redacted.private.jsonl").read_bytes()
    line_sha={}
    for line in raw.splitlines():
        if not line.strip():continue
        p=parse_strict(line)
        key=p["ticket_sha256"]
        demand(key not in line_sha,"COMPANY_DUPLICATE_COHORT_HASH")
        line_sha[key]=digest(line.rstrip(b"\r"))
    demand(len(line_sha)==1819,"COMPANY_FROZEN_ROWS_NOT_1819")
    demand(SAMPLE.is_file() and not SAMPLE.is_symlink() and
           digest(SAMPLE.read_bytes())==SAMPLE_SHA,"COMPANY_HOLDOUT_SHA_MISMATCH")
    sample=parse_strict(SAMPLE.read_bytes())
    demand(type(sample) is dict and set(sample)=={
      "schema","cohort_sha256","reader_source_sha256","selection_rule","selected"
    },"COMPANY_HOLDOUT_SELECTION_SCHEMA")
    demand(sample["schema"]=="else.itil.aug2026.supply-holdout-selection.v1"
           and sample["cohort_sha256"]==manifest["blind_sha256"]
           and sample["selection_rule"]=="SHA256_SORT_FIXED_SALT_SUPPLY_UNIQUE_NO_OT"
           and type(sample["selected"]) is list
           and len(sample["selected"])==10,
           "COMPANY_HOLDOUT_SELECTION_NOT_PINNED")
    orig=eligible(cohort)
    demand(len(orig)==5,"COMPANY_OT_5_SET_DRIFT")
    selected=set(orig)
    pool=[]
    for key,row in cohort.items():
        text=row["incident_text_redacted"]
        ots=set(OT_RE.findall(text))
        supplies=set(SUPPLY_RE.findall(text))
        if len(supplies)==1 and not ots and key not in orig:
            score=sha_str("else.itil.supply-holdout.v1:"+manifest["blind_sha256"]+":"+key)
            pool.append((score,key,next(iter(supplies))))
    pool.sort()
    expect=[{
       "case_sha256":key,"case_row_sha256":digest(canonical(cohort[key])),
       "supply_sha256":sha_str(supply)
    } for _,key,supply in pool[:10]]
    demand(sample["selected"]==expect and len(pool)>=10,
           "COMPANY_HOLDOUT_NOT_DETERMINISTIC")
    selected.update(p["case_sha256"] for p in expect)
    demand(len(selected)==15,"COMPANY_15_CASE_SET_DRIFT")
    return cohort,manifest,line_sha,selected

def validate_one(path,key,cohort,manifest,line_sha,selected,source_bytes):
    demand(path.is_file() and not path.is_symlink(),"COMPANY_FILE_NOT_ALLOWED")
    env=parse_strict(path.read_bytes())
    demand(type(env) is dict and set(env)==ENVELOPE_KEYS,"COMPANY_DELIVERY_SCHEMA_V2_REQUIRED")
    case=env["case_sha256"]
    demand(type(case) is str and case in selected and HEX64.fullmatch(case) is not None,
           "COMPANY_CASE_NOT_SELECTED")
    ident=digest((DELIVERY+":"+case+":"+manifest["blind_sha256"]).encode())[:32]
    demand(
        path.name==ident+".private.json" and env["job_id"]==ident
        and env["schema"]==DELIVERY
        and env["blind_cohort_sha256"]==manifest["blind_sha256"]
        and env["sample_sha256"]==SAMPLE_SHA
        and env["source_sha256"]==SOURCE_SHA
        and env["sql_executed_on_windows"] is True
        and env["read_only"] is True
        and env["changes_executed"] is False,
        "COMPANY_DELIVERY_WRONG_PROVENANCE_OR_DESTINATION")
    require_sha(env["receipt_sha256"])
    try:
        encoded=env["receipt_json_base64"]
        demand(type(encoded) is str and len(encoded)<=15000,"COMPANY_RECEIPT_TOO_LARGE")
        receipt_raw=b64decode(encoded,validate=True)
    except (Base64Error,ValueError,TypeError) as e:
        raise ValueError("COMPANY_RECEIPT_BASE64_INVALID") from e
    demand(digest(receipt_raw)==env["receipt_sha256"],
           "COMPANY_DELIVERY_RECEIPT_HASH_INVALID")
    msg=(DELIVERY+":"+ident+":"+SOURCE_SHA+":"+env["receipt_sha256"]).encode()
    require_sha(env["hmac_sha256"])
    demand(hmac.compare_digest(
        hmac.new(key,msg,"sha256").hexdigest(),env["hmac_sha256"]),
        "COMPANY_WINDOWS_HMAC_INVALID")
    receipt=parse_strict(receipt_raw)
    demand(type(receipt) is dict and set(receipt)==RECEIPT_KEYS,
           "COMPANY_RECEIPT_SCHEMA_INVALID")
    demand(
        receipt["schema"]==RECEIPT
        and receipt["case_sha256"]==case
        and receipt["case_row_line_sha256"]==line_sha[case]
        and receipt["blind_cohort_sha256"]==manifest["blind_sha256"]
        and receipt["source_sha256"]==SOURCE_SHA
        and receipt["itil_source"]=="ELSE70/dbITIL_D/dbo.taIncidente"
        and receipt["itil_row_verified_from_corporate_sql"] is True
        and receipt["historical_solution_read"] is False
        and receipt["corporate_itil_business_join_certified"] is False
        and receipt["root_cause_certified"] is False
        and receipt["repair_certified"] is False,
        "COMPANY_RECEIPT_OWNER_OR_FALSE_CLAIM")
    company=receipt["itil_company"]
    demand(type(company) is int and company in TARGETS,
           "COMPANY_ITIL_COMPANY_NOT_AUTHORIZED")
    for k in ("itil_branch","itil_service","itil_module","itil_sistema"):
        val=receipt[k]
        demand(type(val) is str and len(val)<=40 and
               re.fullmatch(r"[A-Za-z0-9]*",val) is not None,
               "COMPANY_ITIL_MODULE_FIELD_INVALID")
    text=cohort[case]["incident_text_redacted"]
    ots=set(OT_RE.findall(text));supplies=set(SUPPLY_RE.findall(text))
    demand(len(ots)<=1 and len(supplies)<=1 and bool(ots or supplies),
           "COMPANY_REPORTED_KEY_AMBIGUOUS")
    mode="OT" if ots else "SUPPLY"
    demand(receipt["claim_type"]==mode
           and receipt["reported_ot_sha256"]==(
               sha_str(next(iter(ots))) if ots else None)
           and receipt["reported_supply_sha256"]==(
               sha_str(next(iter(supplies))) if supplies else None),
           "COMPANY_TICKET_TEXT_ID_NOT_BOUND")
    obs=receipt["observation"]
    demand(type(obs) is dict and set(obs)==OBS_KEYS,
           "COMPANY_OBSERVATION_SCHEMA_INVALID")
    demand(
        obs["schema"]==OBS
        and obs["qa_target"]==TARGETS[company]
        and obs["sql_profile"]==(
            "PINNED_TYPED_OT_SELECTS" if mode=="OT"
            else "PINNED_TYPED_SUPPLY_SELECTS")
        and obs["read_only"] is True
        and obs["changes_executed"] is False,
        "COMPANY_FAIL_PRE_EXECUTION_WRONG_QA_TARGET")
    time_value(obs["read_utc"])
    counts=obs["counts"]
    cols=(OT_SUPPLY_COLUMNS if mode=="OT" and supplies else
          OT_COLUMNS if mode=="OT" else SUPPLY_COLUMNS)
    demand(type(counts) is dict and set(counts)==cols,
           "COMPANY_WRONG_QUERY_PROFILE")
    for key_name,value in counts.items():
        demand(type(value) is int and value in (0,1,2),
               "COMPANY_RESULT_COUNT_NOT_BOUND")
    if mode=="OT" and supplies:
        demand(counts["exact_ot_supply"]<=counts["orders_by_supply"],
               "COMPANY_JOIN_RELATION_COUNT_IMPOSSIBLE")
    return {
        "case_sha256":case, "itil_company":company,
        "qa_target":obs["qa_target"],"mode":mode,
        "counts":counts,
        "receipt_sha256":env["receipt_sha256"],
        "receipt_raw":receipt_raw,
        "receipt":receipt,
        "source_bytes":source_bytes,
        "verified_windows_hmac":True
    }

def verify_all():
    cohort,manifest,lines,selected=selected_context()
    demand(SOURCE.is_file() and not SOURCE.is_symlink()
           and digest(SOURCE.read_bytes())==SOURCE_SHA,
           "COMPANY_PINNED_READER_CODE_CHANGED")
    secret=LEGACY_ROOT/"worker_hmac.private"
    demand(secret.is_file() and not secret.is_symlink()
           and secret.stat().st_mode & 0o077==0,"COMPANY_HMAC_SECRET_ACL")
    key=secret.read_bytes()
    demand(len(key)==32,"COMPANY_HMAC_SECRET_LEN")
    files=sorted((ROOT/"outbox").glob("*.private.json"))
    demand(len(files)==15 and all(f.is_file() and not f.is_symlink() for f in files),
           "COMPANY_DELIVERY_COUNT_NOT_15")
    got={}
    for path in files:
        item=validate_one(path,key,cohort,manifest,lines,selected,len(SOURCE.read_bytes()))
        demand(item["case_sha256"] not in got,"COMPANY_DUPLICATE_DELIVERY")
        got[item["case_sha256"]]=item
    demand(set(got)==selected,"COMPANY_DELIVERIES_DO_NOT_COVER_COHORT")
    return got

def summary(results):
    from collections import Counter
    where=Counter(x["itil_company"] for x in results.values())
    modes=Counter(x["mode"] for x in results.values())
    return {
      "schema":"else.itil.aug2026.qa.company-routed-replay.v2",
      "verified_cases":len(results),
      "verified_windows_hmac":sum(x["verified_windows_hmac"] for x in results.values()),
      "company_1_cases":where[1],"company_3_cases":where[3],
      "ot_claim_cases":modes["OT"],"supply_claim_cases":modes["SUPPLY"],
      "exact_qa_hits":sum(sum(x["counts"].values()) for x in results.values()),
      "wrong_company_qa_receipts_admissible":0,
      "legacy_v1_receipts_admissible":0,
      "read_only":True,"root_causes_certified":0,"repairs_certified":0,
      "receipt_manifest_sha256":digest(canonical(sorted(
        [(x["case_sha256"],x["receipt_sha256"]) for x in results.values()])))
    }

if __name__=="__main__":
    print(json.dumps(summary(verify_all()),sort_keys=True))

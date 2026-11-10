"""Seal August 2026 1,819-case exporter and prepare redacted BLIND input.

Must run on authorized ELSE62. Original requests and historical solutions
stay on ELSE62. Only redacted case text and hashed ticket IDs are copied
to the private model host; historical solution is never included.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json,re,sys,datetime

ROOT=Path(r"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110")
sys.path.insert(0,r"C:\Temp\ELSE_ITIL_SUP_RUN")
from else_dominance.resolution_batch import redact
SOURCE=ROOT/"aug2026_requests.private.jsonl"
GOLD=ROOT/"aug2026_historical_solutions.private.jsonl"
BLIND=ROOT/"aug2026_blind_redacted.private.jsonl"
MANIFEST=ROOT/"aug2026_manifest.json"

def canonical(d):
    return json.dumps(d,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()

def rows(path):
    result=[json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines()
            if x.strip()]
    return result

def main():
    if BLIND.exists() or MANIFEST.exists():
        raise FileExistsError("AUG_BLIND_NO_OVERWRITE")
    cases=rows(SOURCE)
    gold=rows(GOLD)
    case_ids=[x["case_sha256"] for x in cases]
    sol_ids=[x["case_sha256"] for x in gold]
    if not(len(cases)==len(gold)==len(set(case_ids))==1819 and
           set(sol_ids)==set(case_ids) and len(set(sol_ids))==1819):
        raise ValueError("AUG_1819_SOURCE_GOLD_IDENTITY_DRIFT")
    result=[];service=Counter()
    empty=0
    for row in cases:
        if set(row)!={"case_sha256","month","opened_at","service_code",
                      "module_code","classification_code","incident_text",
                      "has_historical_solution"}:
            raise ValueError("CASE_SCHEMA_UNEXPECTED_FIELDS")
        sha=row["case_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}",sha):
            raise ValueError("AUG_SHA_NOT_VALID")
        if row["month"]!="2026-08" or not (
            "2026-08-01T00:00:00"<=row["opened_at"]<
            "2026-09-01T00:00:00"):
            raise ValueError("OUTSIDE_AUGUST")
        original=row["incident_text"]
        clean=redact(original)
        clean=re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
                     "[EMAIL]",clean)
        clean=re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                     "[IP]",clean)
        clean=re.sub(r"(?<!\d)\d{8,}(?!\d)","[NUMERIC_ID]",clean)
        clean=clean[:1500]
        if len(clean.strip())<35:empty+=1
        service[row["service_code"]]+=1
        result.append({
            "schema":"else.itil.aug2026.blind-case.v1",
            "ticket_sha256":sha,"month":"2026-08",
            "opened_at":row["opened_at"],
            "service_code":row["service_code"],
            "module_code":row["module_code"],
            "classification_code":row["classification_code"],
            "incident_text_redacted":clean,
            "historical_resolution":"WITHHELD",
            "live_state":"NOT_OBSERVED",
            "model_tools_enabled":False,
            "privacy_transform":"WINDOWS_REDACTED_QA",
        })
    raw=b"\n".join(canonical(x) for x in result)+b"\n"
    with BLIND.open("xb") as f:f.write(raw)
    manifest={
        "schema":"else.itil.aug2026.source-manifest.v1",
        "month":"2026-08","cases":len(cases),
        "unique_cases":len(set(case_ids)),
        "source_sha256":sha256(SOURCE.read_bytes()).hexdigest(),
        "sealed_gold_sha256":sha256(GOLD.read_bytes()).hexdigest(),
        "blind_sha256":sha256(raw).hexdigest(),
        "blind_short_requests":empty,
        "services":dict(service),
        "gold_shown_to_model":False,
        "corporate_db_scope":"ELSE70/dbITIL_D/dbo.taIncidente",
        "read_only":True,
        "window":"2026-08-01T00:00:00/2026-09-01T00:00:00",
    }
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps({"status":"AUG1819_BLIND_READY",
          "cases":len(cases),"short_requests":empty,
          "blind_sha256":manifest["blind_sha256"],
          "source_sha256":manifest["source_sha256"],
          "gold_sha256":manifest["sealed_gold_sha256"],
          "service_top5":service.most_common(5),
          "gold_to_model":False}),flush=True)
if __name__=="__main__":
    main()

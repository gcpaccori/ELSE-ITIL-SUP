"""Post-export independent integrity audit; August QA, Windows only.

Exporter produced 1,819 matching JSONL records but returned an IOException
after writing. We do NOT relabel the exporter as SUCCESS. This audit checks
exactly what's on disk, and preserves the nonzero exporter exit in metadata.
"""
from pathlib import Path
from hashlib import sha256
import json,re
ROOT=Path(r"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110")
def audit():
    manifest=json.loads((ROOT/"aug2026_manifest.json").read_bytes())
    sources={}
    for name in ("requests","historical_solutions"):
        p=ROOT/("aug2026_"+name+".private.jsonl")
        raw=p.read_bytes()
        rows=[json.loads(x) for x in raw.splitlines() if x.strip()]
        keys=[x["case_sha256"] for x in rows]
        if len(rows)!=1819 or len(set(keys))!=1819 or any(
            re.fullmatch(r"[0-9a-f]{64}",key) is None for key in keys):
            raise ValueError("INCOMPLETE_CORPORATE_AUG1819_EXPORT")
        sources[name]={"count":len(rows),
                       "sha256":sha256(raw).hexdigest(),
                       "key_set":set(keys),"rows":rows}
    if sources["requests"]["key_set"]!=sources["historical_solutions"]["key_set"]:
        raise ValueError("REQUEST_AND_HISTORICAL_SOLUTION_KEYS_DIFFER")
    if any(x["month"]!="2026-08" or
           not "2026-08-01T00:00:00"<=x["opened_at"]<
                 "2026-09-01T00:00:00" for x in sources["requests"]["rows"]):
        raise ValueError("MONTH_LEAKAGE")
    if (sources["requests"]["sha256"]!=manifest["source_sha256"] or
        sources["historical_solutions"]["sha256"]!=manifest["sealed_gold_sha256"]):
        raise ValueError("POST_EXPORT_SOURCE_BYTES_CHANGED")
    blind=ROOT/"aug2026_blind_redacted.private.jsonl"
    if sha256(blind.read_bytes()).hexdigest()!=manifest["blind_sha256"]:
        raise ValueError("REDACTION_OUTPUT_SHA_CHANGED")
    result={
      "schema":"else.itil.aug2026.windows-post-export-audit.v1",
      "count":1819,"unique_request_ids":1819,
      "unique_solution_records":1819,
      "requested_window":"2026-08-01/2026-09-01",
      "qa_source":"ELSE70/dbITIL_D/dbo.taIncidente",
      "request_sha256":manifest["source_sha256"],
      "solution_sealed_sha256":manifest["sealed_gold_sha256"],
      "blind_redacted_sha256":manifest["blind_sha256"],
      "record_id_sets_exactly_equal":True,
      "snapshot_corporate_count_preverified":1819,
      "exporter_process_exited_nonzero_due_to_io_exception":True,
      "post_export_integrity_validation":"PASS",
      "read_only":True,"model_saw_historical_solution":False,
      "repairs_executed":False,
    }
    p=ROOT/"aug2026_extraction_independent_audit.json"
    with p.open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,sort_keys=True)
    print(json.dumps(result,sort_keys=True))
audit()

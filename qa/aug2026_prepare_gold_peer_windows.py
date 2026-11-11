"""Prepare post-generation August 2026 historical evaluation holdout ON ELSE62.

NEVER feed this dataset to the generator Qwen9B. The model journal was
frozen and independently audited before the holdout is staged. Redact
historical solutions with the same approved privacy filter used for case
requests and transfer only to an isolated evaluator workspace.

The original Windows historical resolution JSONL is not modified.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,re,sys

ROOT=Path(r"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110")
SOURCE=ROOT/"aug2026_historical_solutions.private.jsonl"
MANIFEST=ROOT/"aug2026_manifest.json"
OUT=ROOT/"aug2026_gold_redacted_for_peer.private.jsonl"
AUDIT=ROOT/"aug2026_gold_redacted_for_peer_manifest.json"
sys.path.insert(0,r"C:\Temp\ELSE_ITIL_SUP_RUN")
from else_dominance.resolution_batch import redact

def canonical(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode()

def main():
    if OUT.exists() or AUDIT.exists():
        raise FileExistsError("REFUSE_HOLDOUT_OVERWRITE")
    original=SOURCE.read_bytes()
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if sha256(original).hexdigest()!=manifest["sealed_gold_sha256"]:
        raise ValueError("SEALED_ORIGINAL_HOLDOUT_SHA_CHANGED")
    rows=[json.loads(x) for x in original.splitlines() if x.strip()]
    if len(rows)!=1819 or len({x["case_sha256"] for x in rows})!=1819:
        raise ValueError("ORIGINAL_GOLD_1819_ID_DRIFT")
    prepared=[]
    lengths=Counter()
    for entry in rows:
        if set(entry)!={"case_sha256","historical_solution"}:
            raise ValueError("UNEXPECTED_GOLD_SCHEMA")
        sha=entry["case_sha256"]
        if type(sha) is not str or re.fullmatch(r"[0-9a-f]{64}",sha) is None:
            raise ValueError("INVALID_GOLD_CASE_SHA")
        original_text=entry["historical_solution"]
        if type(original_text) is not str:
            raise ValueError("INVALID_GOLD_RESOLUTION")
        text=redact(original_text)
        # Defense-in-depth: redact free-format phone, IP, URLs, host paths,
        # personnel-like email, customer identifiers.
        text=re.sub(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
                    "[CORREO]",text)
        text=re.sub(r"(?<!\d)\d{8,}(?!\d)","[IDENTIFICADOR]",text)
        text=re.sub(r"(?i)\bhttps?://[^\s]+","[URL]",text)
        text=re.sub(r"(?:[A-Za-z]:\\|\\\\)[^\s,;]+","[RUTA]",text)
        text=text[:2000]
        meaningful=bool(text.strip())
        lengths["nonempty" if meaningful else "empty"]+=1
        if len(text.strip())>=80:lengths["80plus"]+=1
        prepared.append({
            "schema":"else.itil.aug2026.redacted-history-evaluation.v1",
            "case_sha256":sha,
            "historical_resolution_redacted":text,
            "historical_record_nonempty":bool(original_text.strip()),
            "source":"SEALED_WINDOWS_AUG2026_ITIL_HISTORY",
            "truth_certified":False,
        })
    raw=b"\n".join(canonical(x) for x in prepared)+b"\n"
    with OUT.open("xb") as f:f.write(raw)
    audit={
        "schema":"else.itil.aug2026.history-peer-holdout-seal.v1",
        "cases":len(prepared),
        "unique_case_sha":len({x["case_sha256"] for x in prepared}),
        "redacted_history_sha256":sha256(raw).hexdigest(),
        "original_windows_gold_sha256":sha256(original).hexdigest(),
        "model_generation_was_completed_before_holdout_staged":True,
        "gold_exposure_to_original_qwen9b":False,
        "human_truth_certified":False,
        "history_nonempty":lengths["nonempty"],
        "history_empty":lengths["empty"],
        "post_redaction_80plus":lengths["80plus"],
        "read_only":True,
    }
    with AUDIT.open("x",encoding="utf-8") as f:
        json.dump(audit,f,ensure_ascii=False,indent=2,sort_keys=True)
    print(json.dumps({
        "status":"AUG1819_PEER_HOLDOUT_READY",
        "count":len(prepared),
        "nonempty":lengths["nonempty"],
        "empty":lengths["empty"],
        "sha256":sha256(raw).hexdigest(),
        "gold_exposed_to_generator":False},sort_keys=True))
if __name__=="__main__":main()

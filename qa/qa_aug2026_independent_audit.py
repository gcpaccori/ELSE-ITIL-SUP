"""Independent August 2026 QA audit; no model calls or historical gold reads.

Reconstitutes the 1,819-case owner-pinned population from Windows-redacted
input and inspects each generator output against the exact case bytes.
Full certification refers ONLY to process completeness and contract
validity; never to actual repairs or causal correctness.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from collections import Counter
import argparse,json,os,re,statistics

QA=Path("/home/u23u/else_itil_aug2026_qa_20261110")
SOURCE=QA/"aug2026_blind_redacted.private.jsonl"
MANIFEST=QA/"aug2026_manifest.json"
WINDOWS_AUDIT=QA/"aug2026_extraction_independent_audit.json"
JOURNAL=QA/"aug2026_qwen9b.private.jsonl"
OUTPUT_PARTIAL=QA/"aug2026_independent_progress_audit.json"
OUTPUT_FINAL=QA/"aug2026_independent_full_audit.json"
SHA=re.compile(r"[a-f0-9]{64}\Z")
EXPECTED=1819

def need(good,msg):
    if not good:raise ValueError(msg)

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()

def model_input(row):
    # Explicitly reproduce the model's immutable structured input
    # rather than trusting its predeclared digest.
    from qa.qa_aug2026_full import model_input as build
    return build(row)

def run(final=False):
    manifest=json.loads(MANIFEST.read_bytes())
    raw=SOURCE.read_bytes()
    windows=json.loads(WINDOWS_AUDIT.read_bytes())
    need(windows["count"]==EXPECTED and
         windows["unique_request_ids"]==EXPECTED and
         windows["unique_solution_records"]==EXPECTED and
         windows["record_id_sets_exactly_equal"] is True and
         windows["read_only"] is True and
         windows["model_saw_historical_solution"] is False and
         windows["post_export_integrity_validation"]=="PASS" and
         windows["request_sha256"]==manifest["source_sha256"] and
         windows["solution_sealed_sha256"]==manifest["sealed_gold_sha256"] and
         windows["blind_redacted_sha256"]==manifest["blind_sha256"],
         "WINDOWS_POST_EXPORT_SEAL_NOT_MATCHING")
    need(manifest["cases"]==manifest["unique_cases"]==EXPECTED and
         manifest["blind_sha256"]==sha256(raw).hexdigest() and
         manifest["gold_shown_to_model"] is False,
         "AUTHORITATIVE_BLIND_SHA_DRIFT")
    inputs={}
    services=Counter()
    for line in raw.splitlines():
        if not line.strip():continue
        row=json.loads(line)
        key=row["ticket_sha256"]
        need(key not in inputs and SHA.fullmatch(key) and
             row["month"]=="2026-08" and
             row["historical_resolution"]=="WITHHELD" and
             row["model_tools_enabled"] is False,
             "BLIND_COHORT_DUPLICATE_SCOPE_OR_GOLD_EXPOSURE")
        inputs[key]=row
        services[row["service_code"]]+=1
    need(len(inputs)==EXPECTED,"AUG_MONTH_NOT_FULL_1819")
    records={}
    for line in JOURNAL.read_bytes().splitlines():
        if not line.strip():continue
        row=json.loads(line)
        key=row["ticket_sha256"]
        need(key in inputs and key not in records,
             "DUPLICATE_RESULT_OR_COHORT_ESCAPE")
        need(row["schema"]=="else.itil.aug2026.qwen9b-result.v1" and
             row["month"]=="2026-08" and
             row["blind_sha256"]==manifest["blind_sha256"] and
             row["case_input_sha256"]==
                 sha256(canon(inputs[key])).hexdigest() and
             row["model_input_sha256"]==
                 sha256(canon(model_input(inputs[key]))).hexdigest() and
             row["model"]=="else-itil-riv-qwen9b-gpu6" and
             row["historical_gold_exposed"] is False and
             row["live_corporate_access"] is False and
             row["repairs_certified"] is False and
             row["human_confirmed"] is False,
             "CASE_MODEL_OR_SOURCE_PROVENANCE_DRIFT")
        if row["structural_accepted"]:
            plan=row["technical_plan"]
            qa=row["quality"]
            need(row["model_completed"] is True and
                 row["status"]=="MODEL_STRUCTURAL_PASS" and
                 qa["accepted"] is True and
                 plan["fuentes"]==["ITIL.taIncidente"] and
                 plan["evidence_refs"]==["E1"] and
                 plan["ejecutado"] is False and
                 plan["confirmado"] is False and
                 bool(plan["pasos"]) and
                 bool(plan["cierre"]) and
                 all(step["responsable"].strip().casefold()==
                     "responsable autorizado por confirmar"
                     for step in plan["pasos"]),
                 "FALSE_AUG_STRUCTURAL_ACCEPTANCE")
        else:
            need(row["status"] in {
                "INSUFFICIENT_REQUEST_TEXT",
                "MODEL_REQUIRES_TRIAGE",
                "MODEL_TRANSPORT_OR_JSON_FAILURE"},
                "NONACCEPTED_STATUS_NOT_CLASSIFIED")
        records[key]=row
    if final:need(len(records)==EXPECTED,"AUG_MONTH_INCOMPLETE_DO_NOT_CERTIFY")
    # Aggregate strictly from verified rows, not from the writer's progress.
    counts=Counter(r["status"] for r in records.values())
    diag={
        "schema":"else.itil.aug2026.independent-qa-audit.v1",
        "month":"2026-08","source_cases":EXPECTED,
        "processed":len(records),"remaining":EXPECTED-len(records),
        "model_completed":sum(bool(r["model_completed"])
                              for r in records.values()),
        "structural_accepted":sum(bool(r["structural_accepted"])
                                   for r in records.values()),
        "contract_triage":counts.get("MODEL_REQUIRES_TRIAGE",0),
        "insufficient_text":counts.get("INSUFFICIENT_REQUEST_TEXT",0),
        "model_failures":counts.get("MODEL_TRANSPORT_OR_JSON_FAILURE",0),
        "statuses":dict(counts),
        "service_distribution":dict(services),
        "complete":len(records)==EXPECTED,
        "read_only_qa_snapshot":True,
        "per_case_live_reads":0,
        "historical_solutions_in_model":False,
        "correctness_against_gold_not_measured":True,
        "business_root_causes_certified":0,
        "functional_repairs_certified":0,
        "human_validated":0,
        "blind_sha256":manifest["blind_sha256"],
        "journal_sha256":sha256(JOURNAL.read_bytes()).hexdigest(),
        "audited_utc":datetime.now(timezone.utc).isoformat(),
    }
    target=OUTPUT_FINAL if final else OUTPUT_PARTIAL
    if final and target.exists():
        raise FileExistsError("FULL_AUDIT_ALREADY_EXISTS")
    tmp=target.with_suffix(".tmp")
    tmp.write_text(json.dumps(diag,indent=2,sort_keys=True))
    os.replace(tmp,target)
    print(json.dumps({k:diag[k] for k in (
        "source_cases","processed","remaining","model_completed",
        "structural_accepted","contract_triage","insufficient_text",
        "model_failures","complete","journal_sha256")},sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--final",action="store_true")
    args=p.parse_args()
    run(final=args.final)

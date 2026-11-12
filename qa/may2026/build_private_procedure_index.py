"""Generate a private, non-executable index of historical note mentions.

Only May 2026 QA ranks 1-300 are read. The fourth 100 remain excluded.
No incident IDs, personal data, SQL statements or solution narratives leave
the authorized server. Metadata matches denote existence, not applicability.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import gzip
import json
from else_dominance.historical_procedures import CATALOG_SCHEMA, extract_note_mentions
from qa.may2026.score_private_history import verify_receipt

TRAIN=(
 ("may_first100","MayFirst100Read.cs"),
 ("may_next100","MayNext100Read.cs"),
 ("may_third100","MayThird100Read.cs"),
)

def build(private:Path, qa:Path, atlas:Path, module_file:Path, key:bytes)->dict:
    if len(key)!=32:
        raise ValueError("QA_HMAC_KEY_INVALID")
    with gzip.open(atlas,"rt",encoding="utf-8") as src:
        schema=json.load(src)
    # Keep only metadata for visible QA database schemas, and only their columns.
    allowed=defaultdict(set)
    for t in schema["table_dictionary"].values():
        if not str(t["database"]).endswith("_D") or not t["columns"]:
            continue
        allowed[t["table"].lower()].update(k.lower() for k in t["columns"])
    modules={x["codigo_modulo_trimmed_for_repo_name"]:x for x in
             json.loads(module_file.read_text(encoding="utf-8"))}
    grouped=defaultdict(lambda:{
        "total_notes":0,"notes_with_mentions":0,"actions":Counter()})
    hashes=set()
    receipts=[]
    notes_with_mentions=0
    for prefix,reader in TRAIN:
        request,request_sha=verify_receipt(private,qa,key,prefix,reader)
        history,history_sha=verify_receipt(private,qa,key,prefix,reader,history=True)
        if (len(request["results"])!=100 or
                len(history["historical_records"])!=100 or
                history["cohort_source_sha256"]!=request_sha):
            raise ValueError("COHORT_RECEIPT_ALIGNMENT_FAILED")
        receipts.append({"cohort":prefix,"source_sha256":request_sha,
                         "history_sha256":history_sha})
        for row,resolution in zip(request["results"],history["historical_records"]):
            case=row["case_sha256"]
            if case!=resolution["case_sha256"] or case in hashes:
                raise ValueError("COHORT_CASE_NOT_UNIQUE_OR_ALIGNED")
            hashes.add(case)
            module=row["module_code"]
            if module not in modules:
                raise ValueError("CORPORATE_MODULE_NOT_IN_DIRECTORY")
            dest=grouped[module]
            dest["total_notes"]+=1
            actions=extract_note_mentions(resolution["historical_solution_redacted"],
                                          allow_table_columns=allowed)
            if actions:
                dest["notes_with_mentions"]+=1
                notes_with_mentions+=1
            for action in actions:
                sig=(action["kind"],action["table"],tuple(action["fields"]))
                dest["actions"][sig]+=1
    if len(hashes)!=300:
        raise ValueError("NOT_EXACTLY_THREE_HUNDRED_UNIQUE_CASES")
    indexed={}
    unique=0
    for module,d in grouped.items():
        patterns=[{
            "kind":kind,"table":table,"fields":list(fields),"count":count,
            "historical_note_only":True,"execution_confirmed":False}
            for (kind,table,fields),count in d["actions"].items()]
        patterns.sort(key=lambda x:(-x["count"],x["kind"],x["table"],x["fields"]))
        unique+=len(patterns)
        indexed[module]={
            "total_notes":d["total_notes"],
            "notes_with_mentions":d["notes_with_mentions"],
            "patterns":patterns}
    return {
        "schema":CATALOG_SCHEMA,
        "cohort_total":300,
        "includes_heldout_fourth":False,
        "module_directory_sha256":sha256(module_file.read_bytes()).hexdigest(),
        "qa_schema_atlas_sha256":sha256(atlas.read_bytes()).hexdigest(),
        "source_receipts":receipts,
        "notes_with_mentions":notes_with_mentions,
        "unique_module_patterns":unique,
        "modules":dict(sorted(indexed.items())),
        "business_changes_executed":0,
        "limitation":"Recorded SQL may be commented or never executed; not case-level causal proof."
    }

def main():
    parser=argparse.ArgumentParser()
    for key in ("private","atlas","module-directory","hmac-key","output"):
        parser.add_argument("--"+key,required=True,type=Path)
    args=parser.parse_args()
    data=build(args.private,Path(__file__).resolve().parent,
               args.atlas,args.module_directory,args.hmac_key.read_bytes())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    args.output.chmod(0o600)
    print(json.dumps({
        "training_cases":300,"modules":len(data["modules"]),
        "notes_with_mention":data["notes_with_mentions"],
        "patterns":data["unique_module_patterns"],
        "heldout_cases_used":0,"business_changes":0}))
if __name__=="__main__":
    main()

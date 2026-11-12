"""Independent, non-LLM analysis of the nine August QA non-accepted cases.

The original 1,819 outputs are immutable. Case text and historical
resolutions are never logged. Diagnoses are never auto-fixed.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
from else_dominance.qa_evidence_grounding import normalized_mentions,BARE,model_string_values

SRC=Path("/home/u23u/else_itil_aug2026_qa_20261110")
PRIVATE=Path("/home/u23u/else_itil_aug2026_review_private_20261110")
JOURNAL=SRC/"aug2026_qwen9b.private.jsonl"
HOLD=PRIVATE/"aug2026_gold_redacted_for_peer.private.jsonl"
OUT=PRIVATE/"aug2026_rejected9_independent_report.json"
PER=PRIVATE/"aug2026_rejected9_per_case.private.jsonl"

def insist(cond,err):
    if not cond:raise ValueError(err)

def main():
    insist(not OUT.exists() and not PER.exists(),"REVIEW9_ALREADY_EXISTS")
    source=json.loads((SRC/"aug2026_independent_full_audit.json").read_bytes())
    insist(source["complete"] is True and source["processed"]==1819
           and source["journal_sha256"]==sha256(JOURNAL.read_bytes()).hexdigest(),
           "SOURCE_MONTH_NOT_CERTIFIED")
    all_rows=[json.loads(s) for s in JOURNAL.read_bytes().splitlines() if s.strip()]
    gold={x["case_sha256"]:x for s in HOLD.read_bytes().splitlines() if s.strip()
          for x in [json.loads(s)]}
    insist(len(gold)==1819 and len(all_rows)==1819,
           "GOLD_OR_MONTH_NOT_1819")
    rejected=[x for x in all_rows if not x["structural_accepted"]]
    insist(len(rejected)==9,"EXPECTED_EXACT_NINE_FAILED")
    causes=Counter();sql_mentions=Counter();gold_present=Counter();review=[]
    for row in rejected:
        status=row["status"]
        flags=row.get("quality",{}).get("flags",[])
        for f in flags:causes[f]+=1
        gold_present["with_history" if gold[row["ticket_sha256"]][
             "historical_record_nonempty"] else "without_history"]+=1
        plan=row.get("technical_plan") or {}
        unknown=sorted(x for x in normalized_mentions(plan)
                       if x!="ITIL.TAINCIDENTE")
        bare=sorted(set(m.group() for m in BARE.finditer(model_string_values(plan))
                        if m.group().lower()!="taincidente"))
        sql_mentions.update(unknown+bare)
        review.append({
            "case_sha256":row["ticket_sha256"],
            "status":status,
            "type":"INSUFFICIENT_CASE_EVIDENCE" if
                status=="INSUFFICIENT_REQUEST_TEXT" else
                "UNVERIFIED_SQL_SOURCE_CLAIM" if
                any("SQL" in f for f in flags) else
                "FALSE_COMPLETION_CLAIM" if
                any("CLOSURE" in f for f in flags) else
                "MODEL_OUTPUT_FAILURE",
            "hard_flags":flags,"attempts":row.get("attempts",0),
            "model_completed":row["model_completed"],
            "historical_record_present":gold[row["ticket_sha256"]][
                "historical_record_nonempty"],
            "sql_identifier_occurrences":len(unknown)+len(bare),
            "replay_not_permitted_to_mutate_original":True,
        })
    raw=b"\n".join(json.dumps(x,sort_keys=True).encode()
                    for x in sorted(review,key=lambda x:x["case_sha256"]))+b"\n"
    with PER.open("xb") as f:f.write(raw)
    report={
        "schema":"else.itil.aug2026.rejected9-independent-audit.v1",
        "source_count":1819,"accepted_unchanged":1810,
        "not_accepted":9,
        "counts_by_type":dict(Counter(x["type"] for x in review)),
        "hard_flags":dict(causes),
        "historical_note_availability":dict(gold_present),
        "other_sql_identifier_occurrences":sum(sql_mentions.values()),
        "original_rejected_results_unchanged":True,
        "model_called_in_this_audit":False,
        "repairs_certified":0,"human_certifications":0,
        "journal_sha256":source["journal_sha256"],
        "private_rejected_case_report_sha256":sha256(raw).hexdigest(),
    }
    with OUT.open("x") as f:json.dump(report,f,sort_keys=True,indent=2)
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()

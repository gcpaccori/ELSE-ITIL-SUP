"""Prioritize August QA comparison discrepancies by evidence strength.

Uses only original case SHA, peer labels and original QA receipts.
No historical solution or plan text is written to the queue.
"""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
ROOT=Path("/home/u23u/else_itil_aug2026_review_private_20261110")
SOURCE=Path("/home/u23u/else_itil_aug2026_qa_20261110")
OUT=ROOT/"aug2026_peer_followup_priority.private.jsonl"
REPORT=ROOT/"aug2026_peer_followup_priority_summary.json"
def main():
 if OUT.exists() or REPORT.exists():raise FileExistsError("QUEUE_EXISTS")
 records={}
 for line in (ROOT/"aug2026_peer4b.private.jsonl").read_bytes().splitlines():
  if not line:continue
  x=json.loads(line);records[x["case_sha256"]]=x
 model={}
 for line in (SOURCE/"aug2026_qwen9b.private.jsonl").read_bytes().splitlines():
  if not line:continue
  x=json.loads(line);model[x["ticket_sha256"]]=x
 if not len(records)==len(model)==1819:raise ValueError("DRIFT")
 labels=Counter();queue=[]
 for sha in sorted(model):
  p=records[sha];m=model[sha]
  if not m["structural_accepted"]:
   key="ORIGINAL_CONTRACT_REJECTED"
  elif p["state"]=="PEER_UNAVAILABLE":
   key="PEER_JUDGMENT_UNAVAILABLE"
  elif p["state"]=="PEER_COMPLETED" and p["relation"]=="CONFLICT":
   key=("POSSIBLE_CONFLICT_WITH_ACTIONABLE_HISTORY" if
        p["history_quality"]=="ACTIONABLE" else
        "POSSIBLE_CONFLICT_WITH_VAGUE_HISTORY")
  elif p["state"]=="PEER_COMPLETED" and p["missing_verifiable_test"]:
   key="CLOSURE_TEST_REQUIRES_REVIEW"
  elif p["state"]=="PEER_COMPLETED" and p["plan_specificity"]=="GENERIC":
   key="GENERIC_PLAN_REQUIRES_IMPROVEMENT"
  else:continue
  labels[key]+=1
  queue.append({
    "schema":"else.itil.aug2026.review-priority.v1",
    "case_sha256":sha,
    "priority":key,
    "source_evidence_restricted_to_itil_historical_snapshot":True,
    "diagnostic_accuracy_certified":False,
    "human_review":False,
    "repair_certified":False,
  })
 raw=b"\n".join(json.dumps(x,sort_keys=True).encode() for x in queue)+b"\n"
 with OUT.open("xb") as f:f.write(raw)
 summary={
    "schema":"else.itil.aug2026.priority-review-summary.v1",
    "queue_distinct_cases":len(queue),
    "queue_by_primary_flag":dict(labels),
    "peer_judgments_not_ground_truth":True,
    "source_history_is_not_certified_truth":True,
    "queue_private_sha256":sha256(raw).hexdigest(),
 }
 REPORT.write_text(json.dumps(summary,sort_keys=True,indent=2))
 print(json.dumps(summary,sort_keys=True))
if __name__=="__main__":main()

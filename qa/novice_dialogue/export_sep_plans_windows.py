"""Read-only September 2026 Qwen plan sanitizer; never read gold resolution."""
from pathlib import Path
from hashlib import sha256
import json,re,sys
ROOT=Path(r"C:\Temp\ELSE_ITIL_2026_SEP_OCT_QA_AUDIT_20261103")
OUT=Path(r"C:\Temp\ELSE_ITIL_NOVICE_DIALOGUE_20261117\september_plans_redacted.private.jsonl")
INPUT=ROOT/"qwen9b_diagnostic_receipts.private.jsonl"
sys.path.insert(0,r"C:\Temp\ELSE_ITIL_SUP_RUN")
from else_dominance.resolution_batch import redact
assert INPUT.is_file() and not OUT.exists()
def scrub(v):
    if isinstance(v,str):
        s=redact(v)
        s=re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b","[EMAIL]",s)
        return re.sub(r"(?<!\d)\d{5,}(?!\d)","[NUMERIC_ID]",s)[:900]
    if isinstance(v,dict):return {k:scrub(x) for k,x in v.items()}
    if isinstance(v,list):return [scrub(x) for x in v]
    return v
data=[]
for line in INPUT.read_text(encoding="utf-8-sig").splitlines():
    if not line.strip():continue
    row=json.loads(line)
    assert row["month"]=="2026-09"
    assert row["model_input_historical_solution_included"] is False
    data.append({
      "case_sha256":row["ticket_sha256"],"month":"2026-09",
      "model_completed":row["model_completed"],
      "structural_quality_accepted":row["structural_quality_accepted"],
      "quality_gate_accepted":(row.get("gate") or {}).get("accepted",False),
      "technical_plan":scrub(row.get("technical_plan") or {}),
      "historical_solution_used":False
    })
assert len(data)==545 and len({x["case_sha256"] for x in data})==545
with OUT.open("x",encoding="utf-8") as f:
    for item in data:f.write(json.dumps(item,ensure_ascii=False)+"\n")
print(json.dumps({
  "status":"SEP_545_REDACTED_PLANS_PRIVATE_READY",
  "cases":len(data),
  "original_qwen_receipts_sha256":sha256(INPUT.read_bytes()).hexdigest(),
  "sanitized_plans_sha256":sha256(OUT.read_bytes()).hexdigest(),
  "gold_used":False
},sort_keys=True))

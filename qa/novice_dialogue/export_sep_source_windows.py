"""QA-only: redact September source text on ELSE62 and transfer by private SSH.

Does not process historical solutions, export credentials or publish data.
"""
from pathlib import Path
import json,re,sys,hashlib
src=Path(r"C:\Temp\ELSE_ITIL_2026_SEP_OCT_QA_AUDIT_20261103\cases_2026_sep_oct.private.jsonl")
target=Path(r"C:\Temp\ELSE_ITIL_NOVICE_DIALOGUE_20261117\september_blind.private.jsonl")
sys.path.insert(0,r"C:\Temp\ELSE_ITIL_SUP_RUN")
from else_dominance.resolution_batch import redact
assert src.is_file()
target.parent.mkdir(parents=True,exist_ok=True)
assert not target.exists(), "REFUSE_OVERWRITE_PRIVATE_DATA"
raw=src.read_bytes()
data=[]
for line in raw.decode('utf-8-sig').splitlines():
    if not line.strip(): continue
    r=json.loads(line)
    assert r["month"]=="2026-09"
    original=r["incident_text"]
    text=redact(str(original))
    text=re.sub(r"\b[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}\b","[EMAIL]",text)
    text=re.sub(r"(?<!\d)\d{5,}(?!\d)","[NUMERIC_ID]",text)
    # Keep the request text in the private QA environment only.
    data.append({
       "case_sha256":r["ticket_sha256"],
       "opened_at":r["opened_at"],
       "module_code":r["module_code"],
       "service_code":r["service_code"],
       "incident_text_redacted":text[:1800],
       "month":"2026-09",
       "historical_resolution":"WITHHELD"
    })
assert len(data)==len(set(x["case_sha256"] for x in data))==545
with target.open('x',encoding='utf-8') as f:
    for row in data: f.write(json.dumps(row,ensure_ascii=False)+'\n')
print(json.dumps({
  "status":"SEPTEMBER_PRIVATE_REDACTED_SOURCE_READY",
  "source_original_count":len(data),
  "source_batch_sha256":hashlib.sha256(raw).hexdigest(),
  "redacted_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
  "gold_used":False
},sort_keys=True))

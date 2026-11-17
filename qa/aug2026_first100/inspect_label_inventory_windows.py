"""Request-only, aggregate-only private diagnostic. Never print private numbers."""
import json,hashlib,re
from pathlib import Path
from collections import Counter
p=Path(r"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110")
manifest=json.loads((p/"aug2026_manifest.json").read_text())
raw=(p/"aug2026_requests.private.jsonl").read_bytes()
assert hashlib.sha256(raw).hexdigest()==manifest["source_sha256"]
rows=[json.loads(x) for x in raw.decode("utf-8-sig").splitlines() if x.strip()]
assert len(rows)==1819
rows=rows[:100]
spec={
"SUPPLY": r"(?<!\w)(?:suministro|nis|codigo\s+(?:de\s+)?suministro|n[uú]mero\s+de\s+suministro)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,14}(\d{5,19})(?!\d)",
"OT": r"(?<!\w)(?:\bOT\b|orden\s+(?:de\s+)?trabajo|codigo\s+orden\s+trabajo)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,14}(\d{6,19})(?!\d)",
"COLLECTION": r"(?<!\w)(?:cobranza|c[oó]digo\s+(?:de\s+)?cobranza)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,14}(\d{6,19})(?!\d)",
"RECLAMO": r"(?<!\w)(?:reclamo|c[oó]digo\s+(?:de\s+)?reclamo)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,14}(\d{5,19})(?!\d)",
"MEDIDOR":r"(?<!\w)(?:medidor|c[oó]digo\s+(?:de\s+)?medidor)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,14}(\d{5,19})(?!\d)",
"SOLICITUD_FISE":r"(?<!\w)(?:solicitud\s+fise|c[oó]digo\s+solicitud\s+fise)\s*(?:n[°ºo.]?\s*)?[:#=\s-]{0,14}(\d{5,19})(?!\d)",
}
by_type=Counter()
lengths=Counter()
case_types=Counter()
company=Counter()
general=Counter()
for i,case in enumerate(rows,1):
    text=case["incident_text"]
    types=set()
    for typ,pattern in spec.items():
        vals={m.group(1) for m in re.finditer(pattern,text,re.I)}
        if vals:
            types.add(typ);by_type[typ]+=len(vals)
            for x in vals:lengths[(typ,len(x))]+=1
    case_types[tuple(sorted(types))]+=1
    for m in re.finditer(r"(?<!\d)\d{5,19}(?!\d)",text):
        general[len(m.group())]+=1
    company[case["service_code"]]+=1
print(json.dumps({
 "status":"AUG100_PRIVATE_SOURCE_ONLY_INVENTORY",
 "cases":100,"cases_any_typed_label":100-case_types[()],"typed_label_counts":dict(by_type),
 "types_by_case":{("+".join(k) if k else "NO_TYPED_LABEL"):v for k,v in case_types.items()},
 "typed_digit_lengths":{f"{k[0]}_{k[1]}":v for k,v in lengths.items()},
 "all_original_request_digit_lengths":dict(general),
 "historical_solution_read":False,"public_pii_emitted":False
},ensure_ascii=False,sort_keys=True))

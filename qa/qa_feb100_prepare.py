"""Deterministically select 100 QA incidents from Feb 2026, no gold leakage.

Balanced by evidence type, calendar day and service. Categories are
operational test strata, not factual diagnoses. Private on ELSE62.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(r"C:\Temp\ELSE_ITIL_FEB100_QA_20261110")
WINDOW_START="2026-02-01"
WINDOW_END="2026-03-01"
EXPECTED_POPULATION=1799
QUOTAS=[("OT_IDENTIFIER",18),("SAP_INTEGRATION",12),("COMMERCIAL",22),
        ("ACCESS",18),("NETWORK",12),("GENERAL",18)]
PATTERNS={
"OT_IDENTIFIER":re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)"
    r"\s*[:#=-]?\s*\d{4,19}\b",re.I),
"SAP_INTEGRATION":re.compile(r"\b(?:SAP|BAPI|RFC|HANA)\b|pedido\s+almac[eé]n",re.I),
"COMMERCIAL":re.compile(r"\b(?:suministro|medidor|lectura|facturaci[oó]n|"
    r"cobranza|saldo|recibo|refacturaci[oó]n)\b",re.I),
"ACCESS":re.compile(r"\b(?:contrase[nñ]a|acceso|permisos?|perfil|clave|"
    r"rol|habilitar)\b",re.I),
"NETWORK":re.compile(r"\b(?:red|VPN|DNS|router|impresora|"
    r"conectividad|internet)\b",re.I),
}
def strictly(ok,why):
    if not ok:raise ValueError(why)
def dump(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,
                             separators=(",",":")).encode()
def main():
    sys.path.insert(0,r"C:\Temp\ELSE_ITIL_SUP_RUN")
    from else_dominance.resolution_batch import redact
    source=ROOT/"feb2026_requests.private.jsonl"
    target=ROOT/"feb100_allowlist.private.jsonl"
    if target.exists():raise FileExistsError("NO_OVERWRITE")
    records=[json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    strictly(len(records)==EXPECTED_POPULATION,"FEB_COUNT_DRIFT")
    ids=[r["case_sha256"] for r in records]
    strictly(len(set(ids))==EXPECTED_POPULATION,"FEB_DUPLICATE_SHA")
    ready=[]
    excluded=Counter()
    for record in records:
        strictly(record["month"]=="2026-02" and
                 WINDOW_START<=record["opened_at"][:10]<WINDOW_END,
                 "FEB_SOURCE_WINDOW_DRIFT")
        text=redact(record["incident_text"])[:2000]
        if len(text)<20:
            excluded["SHORT_DESCRIPTION"]+=1
            continue
        lane=next((name for name,_ in QUOTAS if name!="GENERAL"
                   and PATTERNS[name].search(text)),"GENERAL")
        ready.append({"case_sha256":record["case_sha256"],
               "opened_at":record["opened_at"],
               "service_code":record["service_code"],
               "module_code":record["module_code"],
               "classification_code":record["classification_code"],
               "description_redacted":text,
               "test_stratum":lane})
    selected=[]
    days=Counter()
    services=Counter()
    for lane,count in QUOTAS:
        candidates=[x for x in ready if x["test_stratum"]==lane]
        strictly(len(candidates)>=count,"INSUFFICIENT_STRATUM_"+lane)
        for _ in range(count):
            choices=[x for x in candidates if x["case_sha256"] not in
                     {z["case_sha256"] for z in selected}]
            best=min(choices,key=lambda x:(
              days[x["opened_at"][:10]],services[x["service_code"]],
              hashlib.sha256((x["case_sha256"]+"|FEB100|v1").encode()).hexdigest()))
            selected.append(best)
            days[best["opened_at"][:10]]+=1
            services[best["service_code"]]+=1
    strictly(len(selected)==100 and len({x["case_sha256"] for x in selected})==100,
             "FEB100_SELECTION_ERROR")
    with target.open("xb") as f:
        for item in sorted(selected,key=lambda x:x["case_sha256"]):
            # Strict reader schema without selection metadata.
            item={k:v for k,v in item.items() if k!="test_stratum"}
            f.write(dump(item)+b"\n")
    manifest={"schema":"else.itil.feb2026.100.qa-selection.v1",
              "month_population":len(records),"selected":100,
              "test_strata":{k:n for k,n in QUOTAS},
              "day_counts":dict(sorted(days.items())),
              "service_counts":dict(services.most_common()),
              "excluded":dict(excluded),
              "input_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
              "selection_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
              "historical_solution_used_for_sampling":False,
              "historical_solution_included":False}
    with (ROOT/"feb100_selection.manifest.json").open("x",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2,sort_keys=True)
    print(json.dumps(manifest,ensure_ascii=False))
if __name__=="__main__":
    main()

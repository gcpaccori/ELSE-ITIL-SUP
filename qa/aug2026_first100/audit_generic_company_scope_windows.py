"""Independent company-scope downgrade of earlier first100 cross-database PK hits.

Does not access the historical solution, expose any PK, or certify business FK.
"""
from collections import Counter,defaultdict
from pathlib import Path
import json,hashlib

old=Path(r"C:\Temp\ELSE_ITIL_AUG_TYPED100_20261117\aug_first100_company_typed.private.json")
a=json.loads(old.read_bytes())
r=a["report"]
cases={e["rank"]:e for e in a["case_metadata"]}
assert len(cases)==100
assert all(x["history_not_read"] is True for x in cases.values())
by_case=defaultdict(set)
candidate_company=defaultdict(set)
all_same=defaultdict(set)
source_db_counts=Counter()
for x in a["matches"]:
    assert x["case_sha256"]==cases[x["rank"]]["case_sha256"]
    if not x["same_branch"]:continue
    rank=x["rank"];all_same[rank].add((x["kind"],x["pk_sha256"]))
    source_db_counts[x["source_database"]]+=1
    company=cases[rank]["itil_company"]
    database={"1":"dbComercial001_D","3":"dbComercial003_D"}.get(company)
    if database and database==x["source_database"]:
        candidate_company[rank].add((x["kind"],x["pk_sha256"]))
        by_case[rank].add((x["kind"],x["pk_sha256"]))
counter=Counter()
for k in range(1,101):
    if all_same[k]:
        counter["baseline_branch_matched_cases"]+=1
    if candidate_company[k]:
        counter["company_and_branch_scoped_cases"]+=1
        if len(candidate_company[k])>1:counter["still_multiple_company_scoped_keys"]+=1
    if all_same[k] and not candidate_company[k]:
        counter["baseline_unconfirmed_company_route"]+=1
counter["company1_case_count"]=sum(e["itil_company"]=="1" for e in cases.values())
counter["company3_case_count"]=sum(e["itil_company"]=="3" for e in cases.values())
counter["unsupported_company_case_count"]=100-counter["company1_case_count"]-counter["company3_case_count"]
counter["typed_label_case_count"]=r["typed_cases_with_source_label"]
counter["typed_strict_confirmed_cases"]=r["typed_cases_with_any_pk"]
assert counter["baseline_branch_matched_cases"]==16
assert counter["typed_strict_confirmed_cases"]==0
print(json.dumps({"status":"AUG100_GENERIC_COMPANY_SCOPE_AUDIT_PASS",
    "aggregate":dict(sorted(counter.items())),
    "same_branch_raw_observations_by_database":dict(sorted(source_db_counts.items())),
    "historical_solution_access":False,
    "native_itil_business_fk_proven":False,"client_identifiers_exported":False,
    "source_receipt_sha256":hashlib.sha256(old.read_bytes()).hexdigest()},sort_keys=True))

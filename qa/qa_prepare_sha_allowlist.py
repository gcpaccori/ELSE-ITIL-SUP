"""Create a SHA-only cluster allowlist from the authorized Windows QA catalog."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    rows=[json.loads(x) for x in a.catalog.read_text(encoding="utf-8").splitlines()
          if x.strip()]
    if len(rows)!=545:
        raise ValueError("EXPECTED_545_CASES")
    ids=[]
    for row in rows:
        ident=row["case_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}",ident):
            raise ValueError("SHA_NOT_CANONICAL")
        if sha256(row["case_ref"].encode()).hexdigest()!=ident:
            raise ValueError("CATALOG_REF_SHA_DRIFT")
        ids.append(ident)
    if len(set(ids))!=545:
        raise ValueError("CASE_DUPLICATE")
    data=("\n".join(sorted(ids))+"\n").encode()
    with a.out.open("xb") as file:
        file.write(data)
    print(json.dumps({
        "status":"QA_SHA_ONLY_ALLOWLIST_PREPARED",
        "case_count":545,"allowlist_sha256":sha256(data).hexdigest(),
        "only_case_hashes":True,"historical_solutions_included":False
    }))
if __name__=="__main__":main()

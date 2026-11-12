"""Export only exact 574 SHA-256 case IDs for the Jan 22–31 QA dispatcher."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from hashlib import sha256
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--allowlist",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    rows=[json.loads(x) for x in a.allowlist.read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(rows)!=574:raise ValueError("JAN_LAST10_EXPECTED_574")
    keys=[]
    for r in rows:
        if set(r)!={"case_sha256","opened_at","service_code","module_code","classification_code","description_redacted"}:
            raise ValueError("JAN_ALLOWLIST_SHAPE_DRIFT")
        if not ("2026-01-22T00:00:00"<=r["opened_at"]<"2026-02-01T00:00:00"):
            raise ValueError("WINDOW_INVALID")
        if not re.fullmatch(r"[0-9a-f]{64}",r["case_sha256"]):
            raise ValueError("SHA_INVALID")
        keys.append(r["case_sha256"])
    if len(set(keys))!=574:raise ValueError("DUPLICATE_CASE")
    data=("\n".join(sorted(keys))+"\n").encode()
    with a.out.open("xb") as stream:stream.write(data)
    print(json.dumps({"scope":"JAN_LAST10_QA_ONLY","cases":574,
                      "sha256":sha256(data).hexdigest(),
                      "historical_solution_included":False}))
if __name__=="__main__":main()

"""Submit and inspect QA-only research jobs through an authenticated local service."""
import argparse
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:18883"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("operation",choices=("submit","status"))
    p.add_argument("--token-file",required=True,type=Path)
    p.add_argument("--case-sha")
    p.add_argument("--job-id")
    p.add_argument("--base-url",default=BASE,
                   choices=["http://127.0.0.1:18883","http://127.0.0.1:18884"])
    a=p.parse_args()
    secret=a.token_file.read_text(encoding="utf-8").strip()
    if len(secret)<32:raise ValueError("TOKEN_NOT_CONFIGURED")
    headers={"Authorization":"Bearer "+secret,
             "Content-Type":"application/json"}
    if a.operation=="submit":
        if not a.case_sha or not re.fullmatch(r"[0-9a-f]{64}",a.case_sha):
            raise ValueError("VALID_CASE_SHA_REQUIRED")
        request=Request(a.base_url+"/v1/qa/investigate",
              data=json.dumps({"case_sha256":a.case_sha}).encode(),
              headers=headers,method="POST")
    else:
        if not a.job_id or not re.fullmatch(r"[0-9a-f]{32}",a.job_id):
            raise ValueError("VALID_JOB_ID_REQUIRED")
        request=Request(a.base_url+"/v1/qa/jobs/"+a.job_id,headers=headers)
    with urlopen(request,timeout=10) as response:
        print(json.dumps({"http_status":response.status,
                          "result":json.load(response)},
                         ensure_ascii=False,sort_keys=True))
if __name__=="__main__":
    main()

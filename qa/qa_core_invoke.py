"""Invoke QA Pareto-capability without exposing bearer token."""
import argparse,json
from pathlib import Path
from urllib.request import Request,urlopen

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--token-file",type=Path,required=True)
    a.add_argument("--case-sha")
    a.add_argument("--job-id")
    a.add_argument("--port",type=int,default=18884)
    args=a.parse_args()
    if bool(args.case_sha)==bool(args.job_id):
        a.error("EXACTLY_ONE_CASE_OR_JOB_REQUIRED")
    token=args.token_file.read_text(encoding="utf-8").strip()
    prefix="http://127.0.0.1:"+str(args.port)
    headers={"Authorization":"Bearer "+token,
             "Content-Type":"application/json"}
    if args.case_sha:
        request=Request(
            prefix+"/v1/qa/core/investigate",
            data=json.dumps({"case_sha256":args.case_sha,
                             "goals":["ITIL_CASE_EXISTS","ITIL_MODULE",
                                      "SAP_ORDER_RESPONSE"]}).encode(),
            headers=headers,method="POST")
    else:
        request=Request(prefix+"/v1/qa/core/jobs/"+args.job_id,
                        headers=headers)
    with urlopen(request,timeout=20) as response:
        print(json.dumps({"http":response.status,
                          "body":json.load(response)},sort_keys=True))
if __name__=="__main__":main()

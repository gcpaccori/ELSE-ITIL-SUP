"""ELSE-ITIL QA worker: Windows → Linux outbound claim/exact NuGet read/complete.

The operator's Windows account owns the private NuGet allowlist.
No inbound Windows port or long-running SSH server is required.
This worker never receives model-defined SQL, paths, credentials, or databases.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
import subprocess
import sys
import time

from qa_janlast10_windows import run as run_exact_nuget

REPO="/home/u23u/else_itil_janlast10_20261110"
CORE="/home/u23u/elsecore_itil_janlast10_20261110/src"
DB="/home/u23u/else_itil_dispatch_janlast10_20261110/queue.sqlite"
ALLOW="/home/u23u/else_itil_dispatch_janlast10_20261110/allowed_sha256.txt"
PYTHON="/home/u23u/miniconda/envs/orquesta_py311/bin/python"
PROJECT=Path(r"C:\Temp\ELSE_ITIL_JANLAST10_DYNAMIC_20261110\qa\JanLast10ExactRead.csproj")
SOURCE=Path(r"C:\Temp\ELSE_ITIL_JANLAST10_DYNAMIC_20261110\qa\JanLast10ExactRead.cs")
WINDOWS_ALLOW=Path(r"C:\Temp\ELSE_ITIL_JANLAST10_DYNAMIC_20261110\allowlist.private.jsonl")
OUTPUT=Path(r"C:\Temp\ELSE_ITIL_JANLAST10_DYNAMIC_20261110\runs")

COMMAND_PREFIX=("cd "+REPO+" && PYTHONPATH="+REPO+":"+CORE+
                " "+PYTHON+" -m else_dominance.qa_dispatch_queue ")
SSH=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8",
     "u23u@elsecluster5"]


def remote(command, data=None, timeout=25):
    done=subprocess.run(SSH+[command],input=data,capture_output=True,
                        timeout=timeout)
    if done.returncode:
        # The remote traceback may contain paths/context. Return only its
        # final structured failure code, never raw stdout/stderr or tokens.
        error=done.stderr.decode("utf-8","replace")
        codes=re.findall(
            r"(?:ValueError|RuntimeError|QaNativeDenied|NugetEvidenceDenied): "
            r"([A-Z][A-Z0-9_]{2,80})",error)
        code=codes[-1] if codes else "UNCLASSIFIED_REMOTE_ERROR"
        try:
            last=error.strip().splitlines()[-1]
            remote_error=json.loads(last)
            if (type(remote_error) is dict and
                type(remote_error.get("error_code")) is str and
                re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}",
                             remote_error["error_code"])):
                code=remote_error["error_code"]
        except (ValueError, IndexError, KeyError):
            pass
        # Preserve only a capped diagnostic category; never echo SSH payload
        # (it contains the claim token) or the raw error traceback.
        if code=="UNCLASSIFIED_REMOTE_ERROR":
            lines=[x.strip() for x in error.splitlines() if x.strip()]
            if lines:
                code="SSH_REMOTE_ERROR_TYPE_"+re.sub(
                    r"[^A-Z0-9_]","_",lines[-1].split(":",1)[0].upper())[:70]
        raise RuntimeError("OUTBOUND_QA_CLUSTER_COMMAND_FAILED_"+code)
    result=done.stdout.splitlines()
    if not result:
        raise RuntimeError("CLUSTER_COMMAND_EMPTY")
    return json.loads(result[-1])


def claim():
    return remote(COMMAND_PREFIX+"claim --db "+DB+
                  " --allowlist "+ALLOW+" --cohort 2026-01-last10 "+
                  " --worker ELSE62-JANLAST10-QA",timeout=32)


def deliver(job:dict, *, result:dict|None,error_code:str|None=None):
    # Each request is bound to a one-use claim secret. Payload is only sent
    # through SSH stdin; no secrets in process argument lists or logs.
    envelope={
        "job_id":job["job_id"],
        "case_sha256":job["case_sha256"],
        "claim_token":job["claim_token"],
        "outcome":"FAILED" if error_code else "COMPLETED",
        "result":{"error_code":error_code} if error_code else result
    }
    payload=base64.b64encode(json.dumps(envelope,sort_keys=True,
                       ensure_ascii=False,separators=(",",":")).encode())
    # Pipe directly into Python; a cd builtin in the pipeline would swallow stdin.
    command=("base64 -di | env PYTHONPATH="+REPO+":"+CORE+" "+PYTHON+
             " -m else_dominance.qa_dispatch_queue "+
             "complete --db "+DB+" --allowlist "+ALLOW+
             " --cohort 2026-01-last10")
    return remote(command,payload,timeout=75)


def once()->dict:
    job=claim()
    if job.get("state")=="EMPTY":
        return {"state":"EMPTY","processed":False}
    if job.get("state")!="CLAIMED":
        raise RuntimeError("UNEXPECTED_JOB_STATE")
    try:
        result=run_exact_nuget(
            case_sha=job["case_sha256"],allowlist=WINDOWS_ALLOW,
            out_root=OUTPUT,dotnet_project=PROJECT,source_file=SOURCE)
    except Exception as exc:
        # Do not log raw SQL, corporate incident contents or claim token.
        err_type=type(exc).__name__
        error_code={
            "ValueError":"OWNER_REQUEST_INVALID",
            "RuntimeError":"QA_READ_PIPELINE_FAILED",
            "TimeoutExpired":"QA_READ_TIMEOUT",
        }.get(err_type,"QA_WORKER_EXCEPTION")
        response=deliver(job,result=None,error_code=error_code)
        return {"state":response["state"],"job_id":job["job_id"],
                "error_code":error_code,"processed":True}
    for attempt in range(3):
        try:
            response=deliver(job,result=result)
            break
        except RuntimeError:
            if attempt==2:
                raise
            time.sleep(2)
    return {"state":response["state"],"job_id":job["job_id"],
            "case_sha_prefix":job["case_sha256"][:16],
            "processed":True,
            "o5_o13_o15_verified":result.get("o5_o13_o15_verified") is True,
            "diagnosis_status":result.get("diagnosis_status"),
            "quality_accepted":result.get("quality_accepted"),
            "repair_certified":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--once",action="store_true")
    p.add_argument("--loop",action="store_true")
    p.add_argument("--interval",type=int,default=20)
    args=p.parse_args()
    if args.once==args.loop:
        p.error("EXACTLY_ONE_MODE_REQUIRED")
    if args.loop and not 5<=args.interval<=300:
        p.error("INVALID_INTERVAL")
    if args.once:
        print(json.dumps(once(),ensure_ascii=False),flush=True)
    else:
        while True:
            try:
                result=once()
                if result.get("processed"):
                    print(json.dumps(result,ensure_ascii=False),flush=True)
            except Exception as exc:
                # Non-sensitive error type only; keep worker alive.
                print(json.dumps({"state":"WORKER_ERROR",
                                  "error_type":type(exc).__name__}),
                      flush=True)
            time.sleep(args.interval)


if __name__=="__main__":
    main()

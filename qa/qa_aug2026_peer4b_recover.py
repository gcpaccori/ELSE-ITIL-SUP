"""One additional Qwen4B attempt for cases whose independent peer failed.

No journal editing: original peer outputs stay immutable. Retry addendum
only records replacement of PEER_UNAVAILABLE states when the independent
validator confirms exact same source and holdout SHA bindings.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from collections import Counter
import json

from qa.qa_aug2026_peer4b import (
    load,read_done,judge,canon,JOURNAL,ROOT)

OUT=ROOT/"aug2026_peer4b_unavailable_retry.private.jsonl"

def main():
    if OUT.exists():raise FileExistsError("PEER_RECOVERY_ALREADY_EXISTS")
    outputs,history,inputs,src_hash,hold_hash=load()
    original=read_done(outputs,history,src_hash,hold_hash)
    if len(original)!=1819:raise ValueError("PEER_COHORT_INCOMPLETE")
    bad=[sha for sha,item in original.items()
         if item["state"]=="PEER_UNAVAILABLE"]
    results=[]
    with OUT.open("xb") as f:
        for sha in bad:
            rerun=judge(sha,outputs[sha],history[sha],inputs[sha],
                        src_hash,hold_hash)
            if rerun["state"] not in ("PEER_COMPLETED","PEER_UNAVAILABLE"):
                raise ValueError("UNEXPECTED_RETRY_STATUS")
            f.write(canon(rerun)+b"\n")
            results.append(rerun)
    print(json.dumps({
        "original_unavailable":len(bad),
        "retry_accepted":sum(x["state"]=="PEER_COMPLETED" for x in results),
        "still_unavailable":sum(x["state"]=="PEER_UNAVAILABLE" for x in results),
        "addendum_sha256":sha256(OUT.read_bytes()).hexdigest(),
        "original_peer_journal_unchanged":True,
    },sort_keys=True))
if __name__=="__main__":main()

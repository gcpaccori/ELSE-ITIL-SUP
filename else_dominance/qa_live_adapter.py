"""Real, case-bound query_live adapter for the generic InvestigationAgent.

This is the previously missing bridge between its model-selected tool and
the actual ELSE62 Windows → NuGet → CORE O5/O13/O15 worker. A new request
queues one real, owner-approved read; a follow-up call with the SAME job ID
can consume a VERIFIED receipt. No fake SQL or proxy schema catalog.
"""
from __future__ import annotations

import re

from .qa_dispatch_queue import QaDispatchQueue

QA_QUERY="ITIL_2026_09_CASE_EXACT_READ"
HEX64=re.compile(r"[0-9a-f]{64}\Z")
JOB_ID=re.compile(r"[0-9a-f]{32}\Z")


class QaDispatchLiveAdapter:
    allowed_queries=frozenset({QA_QUERY})

    def __init__(self,queue:QaDispatchQueue):
        self.queue=queue

    def run(self,query_id:str,parameters:dict,*,scope:dict)->dict:
        if query_id!=QA_QUERY:
            return {"status":"BLOCKED","error":"QUERY_NOT_REGISTERED"}
        if type(parameters) is not dict or (
                set(parameters)-{"case_sha256","job_id"}):
            return {"status":"BLOCKED","error":"QUERY_ARGUMENTS_DENIED"}
        expected=scope.get("case_sha256")
        proposed=parameters.get("case_sha256")
        if (type(expected) is not str or HEX64.fullmatch(expected) is None or
            expected not in self.queue.allowed or proposed!=expected):
            return {"status":"BLOCKED","error":"CASE_ID_NOT_OWNER_BOUND"}
        job_id=parameters.get("job_id")
        if job_id is None:
            queued=self.queue.submit(expected)
            job_id=queued["job_id"]
        elif type(job_id) is not str or JOB_ID.fullmatch(job_id) is None:
            return {"status":"BLOCKED","error":"JOB_ID_INVALID"}
        row=self.queue.conn.execute(
            "SELECT case_sha256 FROM qa_jobs WHERE job_id=?",
            (job_id,)).fetchone()
        if row is None or row[0]!=expected:
            return {"status":"BLOCKED","error":"JOB_CASE_MISMATCH"}
        state=self.queue.status(job_id)
        if state["state"]=="COMPLETED":
            verified=state.get("investigation") or {}
            if (verified.get("o5_o13_o15_verified") is not True or
                verified.get("fresh_read_after_model_request") is not True or
                verified.get("repair_certified") is not False):
                return {"status":"BLOCKED","error":"QA_RECEIPT_NOT_VERIFIED"}
            return {"status":"READ_VERIFIED",
                    "query_id":QA_QUERY,"case_sha256":expected,
                    "job_id":job_id,
                    "source":verified.get("qa_scope"),
                    "receipt_sha256":verified.get("receipt_sha256"),
                    "provenance_verified":True,
                    "root_cause_certified":False,
                    "repair_certified":False,
                    "requires_human_review":True}
        if state["state"] in ("FAILED","EXPIRED"):
            return {"status":"BLOCKED","error":"QA_WORKER_DID_NOT_COMPLETE",
                    "job_id":job_id}
        return {"status":"PENDING","error":"NO_CORPORATE_RECEIPT_YET",
                "job_id":job_id,"provenance_verified":False,
                "repair_certified":False}

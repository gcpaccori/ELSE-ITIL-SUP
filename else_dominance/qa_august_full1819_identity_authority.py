"""Deterministic fail-closed authority for August full1819 business identity.

This is not an LLM oracle. It consumes only a locally HMAC-verified Windows QA
receipt and presents coarse statuses, not raw PKs. Historical state and
business causality remain unverified even after a present-day typed PK match.
"""
from __future__ import annotations
from datetime import datetime
from hashlib import sha256
import hmac
import json
from pathlib import Path
import re

SCHEMA="else.itil.qa.aug2026-full1819-company-typed.v1"
HASH=re.compile(r"^[0-9a-f]{64}$")
COMPANY_DB={"1":"dbComercial001_D","3":"dbComercial003_D"}
PASS_STATUS={"SINGLE_EXACT_TYPED_PK_QA_OBSERVATION",
             "MULTIPLE_EXACT_TYPED_PKS_NO_PRIMARY_INFERRED"}
REASONS={
    "NO_EXPLICIT_TYPED_BUSINESS_KEY_IN_REQUEST",
    "EXPLICIT_TYPED_KEY_NOT_FOUND_IN_COMPANY_DB",
    "COMPANY_PROVIDER_ROUTE_NOT_CERTIFIED",
    "FOREIGN_BRANCH_MATCH_REJECTED",
    *PASS_STATUS,
}

def demand(value:bool,why:str)->None:
    if not value:raise ValueError(why)

def verify_signed_receipt(*,receipt:Path,proof:Path,source_reader:Path,
                          signer:Path)->tuple[dict,str]:
    payload=receipt.read_bytes()
    obj=json.loads(payload)
    sign=json.loads(proof.read_bytes())
    code_sha=sha256(source_reader.read_bytes()).hexdigest()
    receipt_sha=sha256(payload).hexdigest()
    key=signer.read_bytes()
    demand(len(key)==32,"SIGNER_NOT_32_BYTES")
    required=hmac.new(key,f"{SCHEMA}:{code_sha}:{receipt_sha}".encode(),
                      "sha256").hexdigest()
    demand(obj.get("schema")==SCHEMA and obj.get("source_sha256")==code_sha
        and sign.get("schema")==SCHEMA+"-hmac.v1"
        and sign.get("source_sha256")==code_sha
        and sign.get("receipt_sha256")==receipt_sha
        and sign.get("read_only") is True
        and hmac.compare_digest(str(sign.get("hmac_sha256","")),required),
        "AUG_FULL1819_TYPED_RECEIPT_HMAC_OR_CODE_MISMATCH")
    demand(obj.get("history_not_read") is True
        and obj.get("business_writes")==0
        and obj.get("read_only") is True,
        "AUG_FULL1819_TYPED_SOURCE_HISTORY_OR_WRITE_FORBIDDEN")
    return obj,receipt_sha

class AugustFull1819EvidenceAuthority:
    def __init__(self,payload:dict,receipt_sha:str):
        demand(type(receipt_sha) is str and HASH.fullmatch(receipt_sha) is not None,
               "SIGNED_RECEIPT_SHA_REQUIRED")
        summary=payload.get("report")
        cases=payload.get("case_metadata")
        decisions=payload.get("case_decisions")
        matches=payload.get("typed_matches")
        demand(isinstance(summary,dict) and summary.get("evaluated_cases")==1819
             and summary.get("source_cases")==1819
             and summary.get("solution_read") is False
             and summary.get("typed_labels_used_no_history") is True
             and summary.get("legacy_generic_cross_db_matches_are_not_promoted_to_authority") is True
             and isinstance(cases,list) and isinstance(decisions,list)
             and isinstance(matches,list)
             and len(cases)==len(decisions)==1819,
             "AUG_FULL1819_TYPED_100_RECEIPT_SCHEMA_INVALID")
        by_rank={}
        for case in cases:
            rank=case["rank"]
            demand(type(rank) is int and 1<=rank<=1819 and rank not in by_rank,
                   "AUG_FULL1819_TYPED_CASE_RANK_DRIFT")
            demand(HASH.fullmatch(case["case_sha256"]) is not None
                   and case["source_only"] is True
                   and case["history_not_read"] is True,
                   "AUG_FULL1819_TYPED_SOURCE_SCOPE_INVALID")
            by_rank[rank]=case
        self.decisions={}
        for decision in decisions:
            rank=decision["rank"]
            demand(rank in by_rank and
                   decision["case_sha256"]==by_rank[rank]["case_sha256"]
                   and decision["status"] in REASONS
                   and decision["repair_certified"] is False
                   and decision["historical_causality_certified"] is False
                   and decision["timestamp_only_november_qa"] is True,
                   "AUG_FULL1819_TYPED_CASE_DECISION_INVALID")
            demand(rank not in self.decisions,"AUG_FULL1819_TYPED_DUPLICATED_CASE_DECISION")
            scoped=by_rank[rank]
            if scoped["itil_company"] not in COMPANY_DB:
                demand(decision["status"]=="COMPANY_PROVIDER_ROUTE_NOT_CERTIFIED"
                       and decision["company_route_verified"] is False,
                       "AUG_FULL1819_TYPED_UNSUPPORTED_COMPANY_CANNOT_PASS")
            else:
                demand(decision["company_route_verified"] is True
                       and decision["status"]!="COMPANY_PROVIDER_ROUTE_NOT_CERTIFIED",
                       "AUG_FULL1819_TYPED_COMPANY_ROUTE_CONTRADICTION")
            self.decisions[rank]=decision
        seen=set()
        matched={rank:set() for rank in by_rank}
        for obs in matches:
            rank=obs["rank"]
            demand(rank in by_rank
                   and obs["case_sha256"]==by_rank[rank]["case_sha256"]
                   and obs.get("company")==by_rank[rank]["itil_company"]
                   and obs.get("qa_database")==COMPANY_DB.get(obs.get("company"))
                   and obs.get("explicit_request_label") is True
                   and obs.get("same_company_provider_route") is True
                   and HASH.fullmatch(obs.get("pk_sha256","")) is not None
                   and obs.get("itil_branch")==by_rank[rank]["itil_branch"]
                   and obs.get("branch_matches")==(
                       obs.get("business_branch")==obs.get("itil_branch")),
                   "AUG_FULL1819_TYPED_CROSS_COMPANY_BRANCH_OR_SOURCE_FORGERY")
            link=(rank,obs["business_kind"],obs["pk_sha256"])
            demand(link not in seen,"AUG_FULL1819_TYPED_DUPLICATED_PK_OBSERVATION")
            seen.add(link)
            if obs["branch_matches"]:
                matched[rank].add((obs["business_kind"],obs["pk_sha256"]))
        for rank,decision in self.decisions.items():
            n=len(matched[rank])
            demand(n==decision["typed_business_link_count"],
                   "AUG_FULL1819_TYPED_CASE_LINK_COUNT_DRIFT")
            if n==0:
                demand(decision["status"] not in PASS_STATUS,
                       "AUG_FULL1819_TYPED_ZERO_EVIDENCE_FALSE_PASS")
            elif n==1:
                demand(decision["status"]=="SINGLE_EXACT_TYPED_PK_QA_OBSERVATION",
                       "AUG_FULL1819_TYPED_WRONG_ONE_LINK_STATUS")
            else:
                demand(decision["status"]=="MULTIPLE_EXACT_TYPED_PKS_NO_PRIMARY_INFERRED",
                       "AUG_FULL1819_TYPED_UNJUSTIFIED_PRIMARY")
        demand(len(self.decisions)==1819,"AUG_FULL1819_TYPED_100_DECISIONS_NOT_COMPLETE")
        self.by_case={v["case_sha256"]:(v,self.decisions[k]) for k,v in by_rank.items()}
        self.receipt_sha=receipt_sha
        self.summary=summary

    def inspect(self,*,case_sha256:str,module_code:str,as_of:str,
                retrospective_qa:bool=False)->dict:
        if retrospective_qa is not True:
            return {"status":"BLOCKED","reason":"OPERATOR_QA_AUTHORIZATION_REQUIRED"}
        if (type(case_sha256) is not str or HASH.fullmatch(case_sha256) is None
                or type(module_code) is not str or not module_code
                or type(as_of) is not str or not re.fullmatch(
                    r"2026-08-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?)?",as_of)):
            return {"status":"BLOCKED","reason":"AUGUST_EXACT_CASE_SCOPE_REQUIRED"}
        pair=self.by_case.get(case_sha256)
        if pair is None or pair[0]["module_code"]!=module_code:
            return {"status":"BLOCKED","reason":"CASE_OR_MODULE_NOT_IN_SIGNED_FULL1819"}
        try:
            requested=datetime.fromisoformat(as_of)
            opened=datetime.fromisoformat(pair[0]["opened_at"])
        except ValueError:
            return {"status":"BLOCKED","reason":"INVALID_AS_OF_TIMESTAMP"}
        if requested.date()<opened.date():
            return {"status":"BLOCKED","reason":"AS_OF_BEFORE_INCIDENT"}
        decision=pair[1]
        return {
            "status":decision["status"],
            "module_code":module_code,
            "qa_period":"2026-08",
            "signed_receipt_sha256":self.receipt_sha,
            "source_company":pair[0]["itil_company"],
            "source_module_bound":True,
            "verified_typed_pk_observation_count":decision["typed_business_link_count"],
            "retrospective_qa_only":True,
            "incident_time_business_state_verified":False,
            "historical_fix_or_root_cause_certified":False,
            "manual_procedural_evidence_still_needed":True,
            "company_scoped_read_only":True,
            "raw_business_keys_disclosed":False,
            "business_mutations":0,
        }

def from_full1819_windows_paths(*,receipt:Path,proof:Path,source_reader:Path,
                       signer:Path)->AugustFull1819EvidenceAuthority:
    payload,digest=verify_signed_receipt(receipt=receipt,proof=proof,
                                         source_reader=source_reader,signer=signer)
    return AugustFull1819EvidenceAuthority(payload,digest)

"""Reusable high-leverage investigation capability, not a Pareto ticket classifier.

Select the smallest executable set of *registered real Hands* that supplies
the requested evidence. Start real work through the existing durable
Windows/NuGet queue and return the verified investigation when finished.

No generic source catalogs, hypothetical connectors, regex-only classifications,
model-defined SQL, mutations, or claims of 80% resolution are admitted.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Mapping

from .qa_dispatch_queue import QaDispatchQueue, SCHEMA as QUEUE_SCHEMA

SCHEMA="else.itil.core-evidence-capability.v1"
SUPPORTED_GOALS=frozenset({
    "ITIL_CASE_EXISTS","ITIL_SERVICE","ITIL_MODULE",
    "ITIL_CLASSIFICATION","ITIL_ORIGIN","ITIL_TICKET_STATUS",
    "COMMERCIAL_STATE","SAP_ORDER_RESPONSE",
    "EFFECTIVE_PERMISSIONS","APP_RUNTIME_STATE",
    "PRECEDENT_PROCEDURE",
})
DEFAULT_GOALS=("ITIL_CASE_EXISTS","ITIL_SERVICE","ITIL_MODULE")


def require(ok:bool, code:str):
    if not ok:
        raise ValueError(code)


@dataclass(frozen=True)
class ExecutableHand:
    capability_id:str
    observations:frozenset[str]
    cost:int
    # A real backend starts the work and returns a durable job identifier.
    submit:Callable[[str],dict]

    def __post_init__(self):
        require(type(self.capability_id) is str and
                3<=len(self.capability_id)<=100,
                "HAND_ID_INVALID")
        require(type(self.observations) is frozenset and
                self.observations and
                self.observations<=SUPPORTED_GOALS,
                "HAND_OBSERVATIONS_INVALID")
        require(type(self.cost) is int and 1<=self.cost<=100,
                "HAND_COST_INVALID")
        require(callable(self.submit),"HAND_BACKEND_NOT_EXECUTABLE")


def minimal_registered_hands(goals, available:tuple[ExecutableHand,...],
                             *, max_hands=2) ->dict:
    """Exact small-set cover (at most 6 Hands) with deterministic objective.

    Prioritize number of requested observations actually covered, then
    fewer Hands, lower summed execution cost, stable names. This deliberately
    does NOT assume fabricated success probabilities or solve rates.
    """
    require(type(goals) in (list,tuple) and goals,
            "EVIDENCE_GOALS_REQUIRED")
    require(len(goals)<=8 and all(type(g) is str and g in SUPPORTED_GOALS
                for g in goals),"GOAL_NOT_REGISTERED")
    require(len(set(goals))==len(goals),"DUPLICATE_EVIDENCE_GOAL")
    require(type(available) is tuple and len(available)<=6 and
            all(type(h) is ExecutableHand for h in available),
            "REGISTRY_NOT_EXECUTABLE")
    require(len({h.capability_id for h in available})==len(available),
            "DUPLICATE_HAND_ID")
    require(type(max_hands) is int and 1<=max_hands<=3,
            "HAND_BUDGET_INVALID")
    requested=frozenset(goals)
    by_id=sorted(available,key=lambda h:h.capability_id)
    candidates=[()]
    for count in range(1,min(max_hands,len(by_id))+1):
        candidates.extend(combinations(by_id,count))
    def rank(hands):
        covered=frozenset().union(*(h.observations for h in hands))
        match=requested & covered
        return (-len(match),len(hands),sum(h.cost for h in hands),
                tuple(h.capability_id for h in hands))
    selected=min(candidates,key=rank)
    covered=requested & frozenset().union(
        *(h.observations for h in selected))
    missing=tuple(x for x in goals if x not in covered)
    return {
        "schema":SCHEMA,
        "requested_goals":list(goals),
        "selected_capability_ids":[h.capability_id for h in selected],
        "covered_goals":[x for x in goals if x in covered],
        "unavailable_goals":list(missing),
        "selected_cost_units":sum(h.cost for h in selected),
        "selected":selected,
        "all_goals_covered":not bool(missing),
        "repair_certified":False,
        "root_cause_certified":False,
    }


class ParetoInvestigationCore:
    """Actually dispatch available Hands, never count missing as executed."""

    def __init__(self,queue:QaDispatchQueue,
                 extra_hands:tuple[ExecutableHand,...]=()):
        self.queue=queue
        # This is the ONLY currently installed live QA Hand in the
        # dispatcher: it performs a fresh per-ticket Sep NuGet SELECT and
        # requires independent O5/O13/O15 receipt verification.
        actual=ExecutableHand(
            capability_id=self.queue.profile["hand_id"],
            observations=frozenset({"ITIL_CASE_EXISTS","ITIL_SERVICE",
                                    "ITIL_MODULE","ITIL_CLASSIFICATION",
                                    "ITIL_ORIGIN","ITIL_TICKET_STATUS"}),
            cost=1,
            submit=self.queue.submit)
        self.hands=(actual,)+extra_hands

    def start(self,case_sha256:str,goals=DEFAULT_GOALS,
              *,max_hands=2)->dict:
        require(type(case_sha256) is str and case_sha256 in self.queue.allowed,
                "CASE_NOT_AUTHORIZED_FOR_REAL_HAND")
        plan=minimal_registered_hands(goals,self.hands,max_hands=max_hands)
        results=[]
        for hand_id in plan["selected_capability_ids"]:
            hand=next(h for h in self.hands if h.capability_id==hand_id)
            job=hand.submit(case_sha256)
            require(type(job) is dict and
                    job.get("state") in ("QUEUED","RUNNING"),
                    "REAL_HAND_DID_NOT_START")
            results.append({"capability_id":hand_id,
                            "job_id":job["job_id"],
                            "state":job["state"]})
        return {"schema":SCHEMA,
                "case_sha_prefix":case_sha256[:16],
                "status":"QUEUED" if results else "NO_EXECUTABLE_HAND",
                "executions_started":results,
                "covered_goals":plan["covered_goals"],
                "unavailable_goals":plan["unavailable_goals"],
                "all_goals_covered":plan["all_goals_covered"],
                "real_hands_started":len(results),
                "root_cause_certified":False,
                "repair_certified":False,
                "human_review_required":True}

    def inspect(self,job_id:str)->dict:
        job=self.queue.status(job_id)
        require(job.get("schema")==QUEUE_SCHEMA,
                "NOT_A_REAL_QUEUE_RESULT")
        response={
            "schema":SCHEMA,
            "job_id":job_id,
            "state":job["state"],
            "case_sha_prefix":job["case_sha_prefix"],
            "real_hand":self.queue.profile["hand_id"],
            "root_cause_certified":False,
            "repair_certified":False,
            "human_review_required":True,
        }
        if job["state"]=="COMPLETED":
            evidence=job.get("investigation") or {}
            require(evidence.get("o5_o13_o15_verified") is True and
                    evidence.get("fresh_read_after_model_request") is True and
                    evidence.get("repair_certified") is False,
                    "NONVERIFIED_QUEUE_RESULT")
            response.update({
                "status":"EVIDENCE_VERIFIED",
                "receipt_sha256":evidence["receipt_sha256"],
                "diagnosis_status":evidence["diagnosis_status"],
                "quality_accepted":evidence["quality_accepted"],
                "proposal":evidence.get("proposal",{}),
                "verified_ticket_metadata":evidence.get("ticket_metadata",{}),
                "missing_causes_proven":False,
            })
        elif job["state"] in ("FAILED","EXPIRED"):
            response.update({
                "status":"INVESTIGATION_NOT_COMPLETED",
                "error_code":job.get("error_code","QA_WORKER_UNAVAILABLE"),
            })
        else:
            response["status"]="IN_PROGRESS"
        return response

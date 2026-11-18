"""Human evidence readiness gate for private ELSE-ITIL novice study.

The packet is private and contains incident excerpts. The output is aggregate
ONLY. A self-asserted review never certifies root cause, corporate authority,
or real human identity. No ratings == PENDING, not automatic 0% accuracy.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from hashlib import sha256
from pathlib import Path
import json,re

PACKET=Path(
 "/home/u23u/else_itil_guided_v4_20261118/private/"
 "novice_human_review_packet_v4.private.jsonl")
META=PACKET.with_name("novice_human_review_metadata_v4.private.json")
RATINGS=Path(
 "/home/u23u/else_itil_maturity_v5_20261118/private/"
 "novice_review_submissions.private.jsonl")
OUT=Path(
 "/home/u23u/else_itil_maturity_v5_20261118/repo/data/"
 "novice_human_review_readiness_v5.json")

CODE=re.compile(r"^QA-[0-9]{2}$")
ALIAS=re.compile(r"^[a-z][a-z0-9._-]{3,63}$")


def _jsonlines(path:Path)->list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def inspect(packet:Path,metadata:Path,ratings:Path|None=None)->dict:
    if not packet.is_file() or not metadata.is_file():
        raise ValueError("NOVICE_PRIVATE_PACKET_MISSING")
    if packet.is_symlink() or metadata.is_symlink():
        raise ValueError("NOVICE_PACKET_SYMLINK")
    meta=json.loads(metadata.read_text())
    if (meta.get("schema")!="else.itil.qa.human-novice-review-packet.v1"
        or meta.get("cases")!=24 or meta.get("turns")!=72):
        raise ValueError("NOVICE_PACKET_METADATA_UNTRUSTED")
    sha=sha256(packet.read_bytes()).hexdigest()
    if meta.get("private_packet_sha256")!=sha:
        raise ValueError("NOVICE_PACKET_HASH_MISMATCH")
    cases=_jsonlines(packet)
    case_set={r.get("blind_case_code") for r in cases}
    if (len(cases)!=24 or len(case_set)!=24 or
            not all(isinstance(c,str) and CODE.fullmatch(c) for c in case_set)
            or any(len(r.get("turns",[]))!=3 for r in cases)):
        raise ValueError("NOVICE_PACKET_CASES_INVALID")
    marks=[]
    if ratings is not None and ratings.exists():
        if ratings.is_symlink() or ratings.stat().st_mode & 0o077:
            raise ValueError("NOVICE_RATINGS_PRIVATE_PERMISSIONS_REQUIRED")
        marks=_jsonlines(ratings)
    seen=set()
    expert=defaultdict(set)
    observers=defaultdict(set)
    unique_participants=set()
    for r in marks:
        if not isinstance(r,dict) or set(r)!={
            "blind_case_code","reviewer_alias","role",
            "saw_model_identity","observed_real_person",
            "privacy_review_approved","scores"}:
            raise ValueError("NOVICE_MARKS_SCHEMA_INVALID")
        code,alias=r["blind_case_code"],r["reviewer_alias"]
        role=r["role"]
        if (code not in case_set or not isinstance(alias,str) or
                not ALIAS.fullmatch(alias) or role not in
                ("technician","novice_observer")):
            raise ValueError("NOVICE_MARKS_SUBJECT_OR_ROLE_INVALID")
        if r["saw_model_identity"] is not False or (
            r["privacy_review_approved"] is not True):
            raise ValueError("NOVICE_REVIEW_BLINDNESS_OR_PRIVACY_NOT_MET")
        if type(r["observed_real_person"]) is not bool:
            raise ValueError("NOVICE_OBSERVATION_REQUIRED")
        key=(code,role,alias)
        if key in seen:
            raise ValueError("NOVICE_DUPLICATE_REVIEW")
        seen.add(key)
        scores=r["scores"]
        if not isinstance(scores,list) or len(scores)!=3 or not all(
                type(v) is int and 0<=v<=2 for v in scores):
            raise ValueError("NOVICE_SCORES_INVALID")
        if role=="technician":
            expert[code].add(alias)
        else:
            if r["observed_real_person"] is not True:
                raise ValueError("NOVICE_UNOBSERVED_PERSON_AS_HUMAN")
            observers[code].add(alias)
            unique_participants.add(alias)
    expert_ready=sum(len(expert[code])>=2 for code in case_set)
    novice_ready=sum(len(observers[code])>=1 for code in case_set)
    reviewer_count=len(set(r["reviewer_alias"] for r in marks))
    # Technical adequacy of an interview is not independently confirmed by this
    # form. DO NOT promote model root-cause accuracy from self-reported scores.
    return {
      "schema":"else.itil.qa.human-review-gate.v1",
      "cases_in_private_packet":24,
      "turns_in_private_packet":72,
      "rating_records_provided":len(marks),
      "reviewer_aliases_submitted":reviewer_count,
      "cases_with_two_technical_reviews":expert_ready,
      "cases_with_novice_observation":novice_ready,
      "unique_observed_novice_aliases":len(unique_participants),
      "min_technical_per_case":2,
      "min_distinct_real_novices":6,
      "review_coverage_complete":(expert_ready==24 and novice_ready==24
                                    and len(unique_participants)>=6),
      "actual_independent_corporate_evidence_validated":False,
      "human_identity_externally_verified":False,
      "causal_diagnosis_certified":False,
      "status":"PENDING_CORPORATE_VERIFICATION"
                if expert_ready==24 and novice_ready==24 and
                   len(unique_participants)>=6 else "PENDING_HUMAN_REVIEW",
      "source_packet_sha256":sha,
      "private_case_text_published":False,
      "never_convert_form_scores_to_causal_truth":True,
    }


def main():
    assert not OUT.exists(),"REFUSE_TO_OVERWRITE_REVIEW_SNAPSHOT"
    result=inspect(PACKET,META,RATINGS)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,
                              sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":result["status"],
      "cases":result["cases_in_private_packet"],
      "rated":result["rating_records_provided"],
      "root_causes_certified":result["causal_diagnosis_certified"]}))


if __name__=="__main__":
    main()

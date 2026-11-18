"""Source-bound readiness snapshot. A NO_GO audit cannot become GO at runtime.

This is an evidence ledger, not a live SQL poll. The source is only fresh when
an independent authorized reader supplies newer signed evidence. The model
doesn't get to write or declare its own maturity.
"""
from __future__ import annotations
from datetime import date,datetime,timezone
from hashlib import sha256
from pathlib import Path
import json


def load_readiness(scorecard:Path,evidence:Path,*,now:date|None=None)->dict:
    scorecard=Path(scorecard)
    evidence=Path(evidence)
    if scorecard.is_symlink() or evidence.is_symlink():
        raise ValueError("READINESS_FILE_SYMLINK")
    a=json.loads(scorecard.read_text(encoding="utf8"))
    b=json.loads(evidence.read_text(encoding="utf8"))
    if (a.get("schema")!="else.itil.qa.2026-sep545-maturity-decision.v1"
        or b.get("schema")!="else.itil.qa.2026-september-full545-maturity.v1"):
        raise ValueError("READINESS_SOURCE_SCHEMA_UNTRUSTED")
    if (a.get("september_all_incidents_bound")!=545 or
        b.get("september_total")!=545 or
        not b.get("september_all_cases_independently_bound_to_windows") or
        a.get("source_binding_fingerprint")!=b.get("identity_case_set_sha256")):
        raise ValueError("READINESS_SOURCE_BINDING_MISMATCH")
    if a.get("decision")!="NO":
        # The current evidence cannot certify GO even if a JSON value is edited.
        raise ValueError("READINESS_UNSUPPORTED_GO_CLAIM")
    if a.get("independently_certified_diagnoses")!=0 or a.get("individual_human_reviews")!=0:
        raise ValueError("READINESS_UNVERIFIED_EVIDENCE_CLAIM")
    areas=a.get("maturity_domains")
    if (not isinstance(areas,list) or len(areas)!=20 or
        any(not isinstance(x,dict) or
            x.get("status") not in {"FAIL","NOT_CERTIFIED","NOT_MATURE",
                                   "PARTIAL","VERIFIED_MECHANISM"} for x in areas)):
        raise ValueError("READINESS_AREAS_INVALID")
    last=datetime.fromisoformat(b["september_last_date"]).date()
    audit_date=date.fromisoformat(a["date"])
    today=now or datetime.now(timezone.utc).date()
    if last>today or audit_date>today:
        raise ValueError("READINESS_FUTURE_EVIDENCE")
    days=(today-last).days
    problems=[x["area"] for x in areas if x["status"] not in
              ("VERIFIED_MECHANISM",)]
    return {
      "schema":"else.itil.guidance-maturity-readiness.v1",
      "decision":"NO_GO",
      "operating_mode":"SUPERVISED_PRIVATE_PILOT_ONLY",
      "snapshot_date":a["date"],
      "snapshot_age_days":(today-audit_date).days,
      "last_recorded_incident_date":last.isoformat(),
      "last_observed_incident_age_days":days,
      "source_coverage":"ELSE70/dbITIL_D only; no live corporate ingestion connected",
      "zero_october_incidents":"OBSERVED_IN_SELECTED_QA_SOURCE_ONLY",
      "no_incident_is_not_healthy_source":True,
      "source_freshness_certified":False,
      "root_cause_accuracy_certified":False,
      "novice_comprehension_certified":False,
      "repair_actions_enabled":False,
      "gaps_count":len(problems),
      "domain_counts":{k:sum(x["status"]==k for x in areas) for k in
                       ("FAIL","NOT_CERTIFIED","NOT_MATURE","PARTIAL",
                        "VERIFIED_MECHANISM")},
      "sha256_scorecard":sha256(scorecard.read_bytes()).hexdigest(),
      "sha256_source_summary":sha256(evidence.read_bytes()).hexdigest(),
      "live_business_source_queried":False,
      "no_unverified_maturity_promotion":True,
    }

def load_human_review_status(path:Path)->dict:
    """No user scoring or causal truth derived from unverified review forms."""
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("HUMAN_REVIEW_SNAPSHOT_MISSING_OR_SYMLINK")
    a=json.loads(path.read_text(encoding="utf8"))
    if (a.get("schema")!="else.itil.qa.human-review-gate.v1"
        or a.get("cases_in_private_packet")!=24
        or a.get("causal_diagnosis_certified") is not False
        or a.get("actual_independent_corporate_evidence_validated") is not False
        or a.get("human_identity_externally_verified") is not False
        or a.get("status") not in ("PENDING_HUMAN_REVIEW",
                                   "PENDING_CORPORATE_VERIFICATION")):
        raise ValueError("HUMAN_REVIEW_SNAPSHOT_CANNOT_CERTIFY")
    return {
       "status":a["status"],
       "packet_cases":24,
       "rating_records_submitted":a["rating_records_provided"],
       "cases_with_two_technical_reviews":a["cases_with_two_technical_reviews"],
       "cases_with_novice_observation":a["cases_with_novice_observation"],
       "causal_diagnosis_certified":False,
       "human_identity_externally_verified":False,
       "snapshot_not_a_current_live_evaluation":True,
       "sha256_snapshot":sha256(path.read_bytes()).hexdigest(),
    }

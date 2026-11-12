"""Independent bound, privacy-preserving audit of August 2026 peer comparison."""
from pathlib import Path
from collections import Counter,defaultdict
from hashlib import sha256
from datetime import datetime,timezone
import json
BASE=Path("/home/u23u/else_itil_aug2026_qa_20261110")
ROOT=Path("/home/u23u/else_itil_aug2026_review_private_20261110")
def read(name,key,base=ROOT):
 p=base/name
 result={}
 for line in p.read_bytes().splitlines():
  if not line:continue
  x=json.loads(line)
  s=x[key]
  if s in result:raise ValueError("DUPLICATE_CASE")
  result[s]=x
 return result,p
def canonical(x):
 return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def need(x,msg):
 if not x:raise ValueError(msg)
def main():
 target=ROOT/"aug2026_peer_independent_final_audit.json"
 detail=ROOT/"aug2026_peer_independent_per_case.private.jsonl"
 need(not target.exists() and not detail.exists(),"AUDIT_ALREADY_EXISTS")
 orig,original_file=read("aug2026_qwen9b.private.jsonl","ticket_sha256",BASE)
 blind,blind_file=read("aug2026_blind_redacted.private.jsonl","ticket_sha256",BASE)
 gold,hold_file=read("aug2026_gold_redacted_for_peer.private.jsonl","case_sha256")
 peer,peer_file=read("aug2026_peer4b.private.jsonl","case_sha256")
 extra,extra_file=read("aug2026_peer4b_unavailable_retry.private.jsonl","case_sha256")
 need(all(len(x)==1819 for x in (orig,blind,gold,peer)) and
      set(orig)==set(blind)==set(gold)==set(peer),"SOURCE_ID_DRIFT")
 audit=json.loads((BASE/"aug2026_independent_full_audit.json").read_text())
 hold=json.loads((ROOT/"aug2026_gold_redacted_for_peer_manifest.json").read_text())
 need(audit["complete"] and audit["journal_sha256"]==sha256(original_file.read_bytes()).hexdigest()
      and audit["blind_sha256"]==sha256(blind_file.read_bytes()).hexdigest()
      and hold["redacted_history_sha256"]==sha256(hold_file.read_bytes()).hexdigest()
      and hold["gold_exposure_to_original_qwen9b"] is False,
      "FROZEN_INPUT_HASH_CHANGED")
 for k,v in extra.items():
  need(k in peer and peer[k]["state"]=="PEER_UNAVAILABLE"
       and v["state"] in ("PEER_COMPLETED","PEER_UNAVAILABLE")
       and v["original_result_sha256"]==peer[k]["original_result_sha256"]
       and v["history_redacted_row_sha256"]==peer[k]["history_redacted_row_sha256"],
       "RECOVERY_BAD_BINDING")
 peer.update({k:v for k,v in extra.items() if v["state"]=="PEER_COMPLETED"})
 state=Counter();relation=Counter();quality=Counter()
 specificity=Counter();missing=Counter();reason=Counter();byservice=defaultdict(Counter)
 entries=[]
 for key in sorted(orig):
  x=orig[key];h=gold[key];p=peer[key]
  need(p["original_result_sha256"]==sha256(canonical(x)).hexdigest()
       and p["history_redacted_row_sha256"]==sha256(canonical(h)).hexdigest()
       and p["original_month_journal_sha256"]==audit["journal_sha256"]
       and p["historical_holdout_sha256"]==hold["redacted_history_sha256"]
       and p["human_validation"] is False
       and p["causal_truth_certified"] is False
       and p["gold_shown_to_original_qwen9b"] is False,"PEER_ROW_PROVENANCE_INVALID")
  st=p["state"]
  if not x["structural_accepted"]:
   need(st=="NOT_COMPARABLE_CONTRACT_REJECTED","REJECTED_CASE_FALSE_PEER")
  elif not h["historical_resolution_redacted"].strip():
   need(st=="NOT_COMPARABLE_EMPTY_HISTORY","EMPTY_HISTORY_FALSE_PEER")
  else:need(st in ("PEER_COMPLETED","PEER_UNAVAILABLE"),"NO_PEER_FOR_COMPARABLE")
  state[st]+=1
  service=blind[key]["service_code"]
  byservice[service]["all"]+=1
  if st=="PEER_COMPLETED":
   need(p["relation"] in ("SUPPORTED","CONFLICT","NOT_DETERMINABLE")
        and p["history_quality"] in ("ACTIONABLE","VAGUE","EMPTY")
        and p["plan_specificity"] in ("SPECIFIC","PARTIAL","GENERIC")
        and type(p["missing_verifiable_test"]) is bool,"PEER_LABEL_SCHEMA_INVALID")
   relation[p["relation"]]+=1;quality[p["history_quality"]]+=1
   specificity[p["plan_specificity"]]+=1
   missing["missing" if p["missing_verifiable_test"] else "peer_present"]+=1
   reason[p["reason_code"]]+=1
   byservice[service][p["relation"]]+=1
  entries.append({"case_sha256":key,"service_code":service,
    "contract_accepted":x["structural_accepted"],"peer_state":st,
    "peer_relation":p["relation"],"history_quality":p.get("history_quality"),
    "human_confirmed":False,"repair_certified":False})
 need(state["NOT_COMPARABLE_CONTRACT_REJECTED"]==9
      and state["NOT_COMPARABLE_EMPTY_HISTORY"]==154
      and state["PEER_COMPLETED"]+state["PEER_UNAVAILABLE"]==1656,
      "EXPECTED_COHORT_SPLIT_INVALID")
 lexical=json.loads((ROOT/"aug2026_full_1810_lexical_comparison.json").read_text())
 nine=json.loads((ROOT/"aug2026_rejected9_independent_report.json").read_text())
 five=json.loads((ROOT/"aug2026_rejected5_targeted_summary.json").read_text())
 need(lexical["nonempty_history_comparable"]==1656
      and nine["not_accepted"]==9
      and five["actionable_rejected_retried"]==5,"OTHER_AUDITS_DRIFT")
 raw=b"\n".join(canonical(v) for v in entries)+b"\n"
 with detail.open("xb") as f:f.write(raw)
 services=sorted(({"service":k,"cases":v["all"],"supported":v["SUPPORTED"],
                   "conflict":v["CONFLICT"],"indeterminate":v["NOT_DETERMINABLE"]}
                  for k,v in byservice.items()),key=lambda x:-x["cases"])
 summary={"schema":"else.itil.aug2026.peer-semantic-independent-audit.v1",
  "cases":1819,"original_accepted":1810,"original_rejected":9,
  "accepted_with_history":1656,"accepted_empty_history":154,
  "peer_states":dict(state),"relations_model_opinion_not_ground_truth":dict(relation),
  "history_quality_model_opinion":dict(quality),
  "plan_specificity_model_opinion":dict(specificity),
  "missing_verifiable_test_model_opinion":dict(missing),
  "reason_codes_model_opinion":dict(reason),
  "top_services":services[:10],
  "rejected_nine_reasons":nine["counts_by_type"],
  "separate_targeted_retry_pass":five["second_pass_contract_accepted"],
  "separate_targeted_retry_rejected":five["still_rejected"],
  "lexical_mean_actual":lexical["matched_tfidf_cosine_mean"],
  "lexical_mean_same_service_control":lexical["same_service_shuffled_control_mean"],
  "lexical_actual_exceeds_control":lexical["matched_exceeds_same_service_control"],
  "source_journal_sha256":sha256(original_file.read_bytes()).hexdigest(),
  "peer_journal_sha256":sha256(peer_file.read_bytes()).hexdigest(),
  "peer_retry_sha256":sha256(extra_file.read_bytes()).hexdigest(),
  "per_case_audit_sha256":sha256(raw).hexdigest(),
  "root_cause_certified":0,"human_reviewed":0,"repairs_certified":0,
  "historical_notes_certified":False,"original_outputs_unchanged":True,
  "audited_utc":datetime.now(timezone.utc).isoformat()}
 with target.open("x") as f:json.dump(summary,f,indent=2,sort_keys=True)
 print(json.dumps(summary,sort_keys=True))
if __name__=="__main__":main()

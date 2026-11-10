"""Synthetic Jan10 population tests; no corporate incidents in repository."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path

import pytest
from qa.jan10_pareto_eval import evaluate


def save(path,records):
    path.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"
                            for x in records),encoding="utf-8")


def fixture(root):
    root.mkdir()
    requests=[]
    gold=[]
    models=[]
    peer=[]
    for i in range(1987):
        sha=sha256(f"synthetic-qa-{i}".encode()).hexdigest()
        opened="2026-01-05T10:00:00" if i<638 else "2026-01-12T10:00:00"
        requests.append({
            "case_sha256":sha,"month":"2026-01","opened_at":opened,
            "service_code":"1","module_code":"0102100100000",
            "classification_code":"101",
            "incident_text":"Incidencia sobre suministro y medidor de prueba.",
            "has_historical_solution":True})
        gold.append({"case_sha256":sha,
                     "historical_solution":"Se evaluó el caso sintético."})
        models.append({"case_sha256":sha,"model_completed":True,
                       "raw_gate_accepted":True,
                       "source_bound_gate_accepted":True,
                       "source_binding_added":["ITIL.taIncidente"],
                       "historical_solution_shown":False,
                       "normalized_plan":{
                           "fuentes":["ITIL.taIncidente"],
                           "diagnostico":"Hipótesis no confirmada",
                           "pasos":[]}})
        peer.append({"case_sha256":sha,"judge_completed":True,
                     "judge_result":{
                       "history_quality":"VAGUE",
                       "diagnosis_relation":"NOT_DETERMINABLE",
                       "action_relation":"NOT_DETERMINABLE",
                       "unjustified_mutation":False,
                       "domain_mismatch":False}})
    save(root/"jan2026_requests.private.jsonl",requests)
    save(root/"jan2026_historical_solutions.private.jsonl",gold)
    save(root/"qwen9b_jan2026_full_shard_0.private.jsonl",models[:994])
    save(root/"qwen9b_jan2026_full_shard_1.private.jsonl",models[994:])
    save(root/"jan2026_independent_4b_full_shard_0.private.jsonl",peer[:994])
    save(root/"jan2026_independent_4b_full_shard_1.private.jsonl",peer[994:])
    return requests


def test_complete_638_population_is_deterministic_and_rejects_false_accuracy(tmp_path):
    root=tmp_path/"source"
    fixture(root)
    one=evaluate(root,tmp_path/"result1")
    two=evaluate(root,tmp_path/"result2")
    assert one["evaluated_cases"]==638
    assert one["cases_unique"]==638
    assert one["pareto_top3_cases"]==638
    assert one["lane_counts"]=={"COMMERCIAL_OT":638}
    assert one["qwen9b_prior_baseline"]["posthoc_source_binding_added_cases"]==638
    assert one["new_evidence_gate_decisions"]=={"MISSING_VERIFIED_EVIDENCE":638}
    assert one["human_validations"]==0
    assert one["functional_repair_certified"]==0
    assert one["per_case_result_sha256"]==two["per_case_result_sha256"]


def test_gold_must_not_be_part_of_original_requests(tmp_path):
    root=tmp_path/"source"
    requests=fixture(root)
    requests[0]["historical_solution"]="This is a synthetic answer leak."
    save(root/"jan2026_requests.private.jsonl",requests)
    with pytest.raises(ValueError,match="GOLD_LEAKED_IN_INPUT_EXPORT"):
        evaluate(root,tmp_path/"result")


def test_duplicate_shard_record_is_rejected(tmp_path):
    root=tmp_path/"source"
    fixture(root)
    source=root/"qwen9b_jan2026_full_shard_1.private.jsonl"
    records=[json.loads(x) for x in source.read_text().splitlines()]
    records[0]["case_sha256"]=records[1]["case_sha256"]
    save(source,records)
    with pytest.raises(ValueError,match="DUPLICATE_CASE_SHA_QWEN9B"):
        evaluate(root,tmp_path/"result")


def test_wrong_population_size_not_silently_sampled(tmp_path):
    root=tmp_path/"source"
    rows=fixture(root)
    rows[0]["opened_at"]="2026-01-16T10:00:00"
    save(root/"jan2026_requests.private.jsonl",rows)
    with pytest.raises(ValueError,match="JAN10_SCOPE_NOT_638"):
        evaluate(root,tmp_path/"result")

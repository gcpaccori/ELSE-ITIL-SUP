"""Exact 50 preventive-rule indicator contract + observed QA source recovery.

The source evidence is an immutable observation of a QA lookup, not a value for
either original indicator. Never equate a source table, historical count, or
current QA row with a predictive backtest PASS.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import csv
import json
import re

DATA=Path(__file__).resolve().parents[1]/"data"/"qa50"
VALID_SOURCE_STATUS={"ROW_OBSERVED","EMPTY","BLOCKED"}
RULE_RE=re.compile(r"(?:CO0[1-9]|EUC0[1-8]|ID0[1-8]|NET(?:0[1-9]|1[01])|OP(?:0[1-9]|10)|SEC0[1-4])\Z")
EXPECTED_FAMILIES={"CO":9,"EUC":8,"ID":8,"NET":11,"OP":10,"SEC":4}

class Preventive50Catalog:
    def __init__(self, directory=DATA):
        directory=Path(directory)
        def load_tsv(name):
            with (directory/name).open(encoding="utf-8",newline="") as f:
                return list(csv.DictReader(f,delimiter="\t"))
        metrics=load_tsv("original_50_metric_pairs.tsv")
        mapped=load_tsv("metric_candidate_sources.tsv")
        snap=json.loads((directory/"observed_50_sources.json").read_text(encoding="utf-8"))
        lanes=json.loads((directory/"original_50_lanes_recovered.json").read_text(encoding="utf-8"))
        if (len(metrics)!=50 or len(mapped)!=50
           or len({x["capability_id"] for x in metrics})!=50
           or [m["capability_id"] for m in metrics]!=[m["capability_id"] for m in mapped]
           or any(not RULE_RE.fullmatch(m["capability_id"]) for m in metrics)):
            raise ValueError("PREVENTIVE_50_ORIGINAL_CONTRACT_MISMATCH")
        if any(not m["primary_metric"] or not m["secondary_metric"] for m in metrics):
            raise ValueError("PREVENTIVE_100_SIGNALS_INCOMPLETE")
        families=Counter(re.match(r"[A-Z]+",m["capability_id"]).group()
                         for m in metrics)
        if dict(families)!=EXPECTED_FAMILIES:
            raise ValueError("PREVENTIVE_50_FAMILY_DISTRIBUTION_DRIFT")
        if (snap["schema"]!="else.itil.qa.preventive-50-public-source-summary.v1"
            or snap["source_queries"]!=50
            or len(snap["sources"])!=50
            or snap["aggregate_queries"]!=12
            or snap["aggregate_reads"]!=10
            or snap["technical_predictions_certified"] is not False
            or snap["business_ticket_conclusion_certified"] is not False):
            raise ValueError("PREVENTIVE_50_QA_SOURCE_SNAPSHOT_INVALID")
        self.sources={}
        for row in snap["sources"]:
            key=row["group"]+"/"+row["source"]
            if (row["status"] not in VALID_SOURCE_STATUS or key in self.sources):
                raise ValueError("PREVENTIVE_50_SOURCE_DUPLICATED_OR_INVALID")
            self.sources[key]=row["status"]
        c=Counter(self.sources.values())
        if (c["ROW_OBSERVED"],c["EMPTY"],c["BLOCKED"])!=(44,5,1):
            raise ValueError("PREVENTIVE_50_QA_SOURCE_DISTRIBUTION_DRIFT")
        self.rules={}
        for metric,mapping in zip(metrics,mapped):
            ident=metric["capability_id"]
            sources=[x for x in mapping["candidate_sources"].split(";") if x and x!="-"]
            if len(sources)!=len(set(sources)) or any(x not in self.sources for x in sources):
                raise ValueError("PREVENTIVE_50_CANDIDATE_SOURCE_NOT_IN_QA_RECEIPT")
            usable=sum(self.sources[x]=="ROW_OBSERVED" for x in sources)
            status=("RELATED_SOURCE_HAS_ROWS" if usable else
                    "ONLY_EMPTY_OR_BLOCKED_SOURCES" if sources else
                    "NO_RELEVANT_SOURCE_MAPPED")
            self.rules[ident]={
                "capability_id":ident,
                "required_primary_metric":metric["primary_metric"],
                "required_secondary_metric":metric["secondary_metric"],
                "candidate_sources":[{"source":x,"qa_row_status":self.sources[x]} for x in sources],
                "source_coverage_status":status,
                "primary_real_signal_certified":False,
                "secondary_real_signal_certified":False,
                "same_asset_and_time_evidence":False,
                "predictive_verdict":"ABSTAIN_NOT_ENOUGH_SIGNAL_EVIDENCE",
                "next_step":"Measure both exact indicators for the same asset and historical time window",
            }
        summary=Counter(x["source_coverage_status"] for x in self.rules.values())
        if (summary["RELATED_SOURCE_HAS_ROWS"]!=34
            or summary["ONLY_EMPTY_OR_BLOCKED_SOURCES"]!=2
            or summary["NO_RELEVANT_SOURCE_MAPPED"]!=14):
            raise ValueError("PREVENTIVE_50_SOURCE_COVERAGE_DRIFT")
        if (lanes["schema"]!="else.itil.qa.recovered-original-lanes-20261111.v1"
            or lanes["archived_independent_business_e2e_certifications"]!=0
            or len(lanes["lanes"])!=2
            or any(r["queries"]!=50 or r["exact_qa_rows_and_modules"]!=50
                   or r["missing"]!=0 or r["blocked"]!=0
                   or r["e2e_campaign_certified"] is not False
                   for r in lanes["lanes"].values())):
            raise ValueError("PREVENTIVE_50_ARCHIVED_LANE_RECOVERY_DRIFT")
        self.snapshot=snap
        self.lanes=lanes
    def describe(self,capability_id):
        if type(capability_id) is not str or capability_id not in self.rules:
            return {"status":"BLOCKED","error":"UNKNOWN_OR_UNREGISTERED_50_CAPABILITY"}
        return {**self.rules[capability_id],
                "status":"QA_SOURCE_MAPPING_ONLY_NOT_PREDICTIVE_PASS",
                "source_snapshot_sha256":self.snapshot["windows_receipt_sha256"],
                "live_telemetry_queried_now":False,
                "business_modifications":0}
    def summary(self):
        return {
            "status":"SOURCE_RECOVERY_COMPLETE_PREDICTIVE_BACKTEST_NOT_CERTIFIED",
            "original_rules":50,"original_indicators":100,
            "qa_tables_probed":50,"qa_tables_with_rows":44,
            "qa_tables_empty":5,"qa_tables_blocked":1,
            "qa_aggregates_read":10,
            "rules_with_related_data_sources":34,
            "rules_with_only_empty_or_blocked_sources":2,
            "rules_without_relevant_sql_source":14,
            "original_indicator_pairs_verified":0,
            "original_predictive_abstentions_remaining":50,
            "archived_october_lanes_recovered":100,
            "archived_october_lanes_e2e_certified":0,
            "source_snapshot_sha256":self.snapshot["windows_receipt_sha256"],
            "source_only_not_business_repair":True
        }

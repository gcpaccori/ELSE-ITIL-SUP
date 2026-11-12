"""Reconstructed source coverage for the original 50 preventive ITIL capabilities."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import shutil
import pytest

from else_dominance.preventive50_recovery import Preventive50Catalog,DATA
from else_dominance.sources import EvidenceTools
from else_dominance.agent import InvestigationAgent

def test_all_50_original_indicators_present():
    c=Preventive50Catalog()
    assert len(c.rules)==50
    assert len(c.sources)==50
    assert sum(len((r['required_primary_metric'],r['required_secondary_metric']))
               for r in c.rules.values())==100
    assert {'CO01','EUC04','ID03','NET04','OP06','SEC04'}<=set(c.rules)
    assert all(x['predictive_verdict']=='ABSTAIN_NOT_ENOUGH_SIGNAL_EVIDENCE' for x in c.rules.values())

def test_real_source_distribution_and_original_two_lanes():
    s=Preventive50Catalog().summary()
    assert s['qa_tables_with_rows']==44
    assert s['qa_tables_empty']==5
    assert s['qa_tables_blocked']==1
    assert s['rules_with_related_data_sources']==34
    assert s['rules_with_only_empty_or_blocked_sources']==2
    assert s['rules_without_relevant_sql_source']==14
    assert s['original_indicator_pairs_verified']==0
    assert s['archived_october_lanes_recovered']==100
    assert s['archived_october_lanes_e2e_certified']==0

def test_original_named_capability_not_false_predictive_pass():
    c=Preventive50Catalog()
    r=c.describe('EUC04')
    assert r['required_primary_metric']=='repeat_failures_after_maintenance_30d'
    assert r['required_secondary_metric']=='same_lot_failures_30d'
    assert all(x['qa_row_status']=='ROW_OBSERVED' for x in r['candidate_sources'])
    assert r['primary_real_signal_certified'] is False
    assert r['secondary_real_signal_certified'] is False
    assert r['same_asset_and_time_evidence'] is False

def test_empty_backup_tables_not_certified():
    r=Preventive50Catalog().describe('NET04')
    assert r['required_primary_metric']=='backup_age_hours'
    assert r['source_coverage_status']=='ONLY_EMPTY_OR_BLOCKED_SOURCES'
    assert r['predictive_verdict'].startswith('ABSTAIN')

def test_missing_telemetry_and_unknown_capability():
    cat=Preventive50Catalog()
    assert cat.describe('NET01')['source_coverage_status']=='NO_RELEVANT_SOURCE_MAPPED'
    assert cat.describe('DELETE')['status']=='BLOCKED'
    assert cat.describe('NET12')['status']=='BLOCKED'
    assert cat.describe('')['status']=='BLOCKED'

class NotUsed:pass

def test_tools_registered_read_only_and_no_sql_arguments():
    tool=EvidenceTools(NotUsed(),NotUsed(),preventive_50=Preventive50Catalog())
    assert 'inspect_preventive50_source' in tool.descriptions
    assert tool.execute('inspect_preventive50_source',{'capability_id':'NET04'}, {})['status']=='QA_SOURCE_MAPPING_ONLY_NOT_PREDICTIVE_PASS'
    assert tool.execute('inspect_preventive50_source',{'capability_id':'NET04','sql':'DROP TABLE x'}, {})['status']=='BLOCKED'
    assert tool.execute('inspect_preventive50_source',{'capability_id':'SOMETHING'}, {})['status']=='BLOCKED'
    assert tool.execute('inspect_preventive50_source',{}, {})['status']=='BLOCKED'

def test_predictive_source_map_cannot_prove_causal_answer():
    observation=Preventive50Catalog().describe('CO01')
    response={'type':'final','status':'PLAN_PROPUESTO','confidence':'HIGH',
       'hypotheses':[{'cause':'Issue automatically diagnosed',
                      'evidence_refs':['TOOL:1'],'test':'Fix now'}],
       'proposed_steps':[{'action':'Close','precondition':'none','verification':'unknown',
                          'evidence_refs':['TOOL:1']}]
    }
    final=InvestigationAgent._validate(response,{
      'TOOL:1':{'name':'inspect_preventive50_source','result':observation}})
    assert final['status']=='INVESTIGACION_PENDIENTE'
    assert final['live_source_evidence_available'] is False
    assert final['can_claim_resolved'] is False

@pytest.fixture
def fake_catalog(tmp_path):
    path=tmp_path/'recovered'
    shutil.copytree(DATA,path)
    return path

def test_missing_pair_rejected(fake_catalog):
    p=fake_catalog/'original_50_metric_pairs.tsv'
    lines=p.read_text().splitlines()
    p.write_text('\n'.join(lines[:-1])+'\n')
    with pytest.raises(ValueError,match='50_ORIGINAL'):
        Preventive50Catalog(fake_catalog)

def test_source_swap_rejected(fake_catalog):
    p=fake_catalog/'metric_candidate_sources.tsv'
    text=p.read_text().replace('ITIL/dbo.taMantenimientoEquipoAtencion','COMMERCIAL/dbo.UNKNOWN_TABLE')
    p.write_text(text)
    with pytest.raises(ValueError,match='SOURCE_NOT_IN_QA'):
        Preventive50Catalog(fake_catalog)

def test_false_snapshot_claim_rejected(fake_catalog):
    p=fake_catalog/'observed_50_sources.json'
    x=json.loads(p.read_text())
    x['technical_predictions_certified']=True
    p.write_text(json.dumps(x))
    with pytest.raises(ValueError,match='SOURCE_SNAPSHOT_INVALID'):
        Preventive50Catalog(fake_catalog)

def test_false_campaign_e2e_claim_rejected(fake_catalog):
    p=fake_catalog/'original_50_lanes_recovered.json'
    x=json.loads(p.read_text())
    x['lanes']['A']['e2e_campaign_certified']=True
    p.write_text(json.dumps(x))
    with pytest.raises(ValueError,match='LANE_RECOVERY_DRIFT'):
        Preventive50Catalog(fake_catalog)

def test_source_probes_not_a_measurement(tmp_path):
    cat=Preventive50Catalog()
    assert all(not x['primary_real_signal_certified'] and
               not x['secondary_real_signal_certified'] for x in cat.rules.values())

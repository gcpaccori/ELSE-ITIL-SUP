"""Synthetic contract tests; never bundle user incident text or historical notes."""
from pathlib import Path
import json
import pytest
from else_dominance.historical_procedures import (
    HistoricalProcedureCatalog,extract_note_mentions,CATALOG_SCHEMA)
from else_dominance.sources import EvidenceTools
from qa.may2026.evaluate_private_procedure_holdout import score

def sample(tmp_path):
    obj={
      "schema":CATALOG_SCHEMA,
      "cohort_total":300,"includes_heldout_fourth":False,
      "notes_with_mentions":4,"unique_module_patterns":2,
      "business_changes_executed":0,
      "source_receipts":[
          {"cohort":"may_first100"},{"cohort":"may_next100"},
          {"cohort":"may_third100"}],
      "modules":{
        "0102100100000":{
          "total_notes":19,"notes_with_mentions":4,
          "patterns":[
            {"kind":"UPDATE_MENTIONED","table":"tacobranza",
             "fields":["codigocaja"],"count":3,
             "execution_confirmed":False,"historical_note_only":True},
            {"kind":"DELETE_MENTIONED","table":"tacobranza",
             "fields":[],"count":1,
             "execution_confirmed":False,"historical_note_only":True}
          ]
        }
      }
    }
    path=tmp_path/"private.json"
    path.write_text(json.dumps(obj))
    return path

def test_comment_is_mentioned_not_executed():
    src="SELECT 1; -- UPDATE a SET a.CodigoCaja = 50 FROM taCobranza a"
    p=extract_note_mentions(src,allow_table_columns={'tacobranza':{'codigocaja'}})
    assert p==[{"kind":"UPDATE_MENTIONED","table":"tacobranza",
                "fields":["codigocaja"],"execution_confirmed":False,
                "historical_note_only":True}]
    assert not any(x.get('sql') or x.get('value') for x in p)

def test_metadata_denies_unverified_fields():
    src="UPDATE a SET a.ImaginaryField = 5 FROM taCobranza a"
    p=extract_note_mentions(src,allow_table_columns={'tacobranza':{'codigocaja'}})
    assert p==[]
    assert extract_note_mentions("DELETE FROM FakeTable",
        allow_table_columns={'tacobranza':{'codigocaja'}})==[]

def test_sql_values_not_exposed():
    p=extract_note_mentions("UPDATE a SET a.CodigoCaja = 91234567 FROM taCobranza a")
    assert p and '91234567' not in json.dumps(p)

def test_catalog_summary_and_no_false_execution(tmp_path):
    c=HistoricalProcedureCatalog(sample(tmp_path))
    r=c.describe('0102100100000')
    assert r['notes_seen']==19
    assert r['notes_with_structured_mentions']==4
    assert all(p['execution_confirmed'] is False for p in r['candidate_patterns'])
    assert r['diagnosis_verified'] is False
    assert r['repairs_certified']==0
    assert c.summary()['heldout_fourth_used'] is False

def test_unseen_and_invalid_module_abstain(tmp_path):
    c=HistoricalProcedureCatalog(sample(tmp_path))
    assert c.describe('999999')['status']=='NO_HISTORICAL_PATTERN_AVAILABLE'
    assert c.describe('DELETE FROM')['status']=='BLOCKED'
    assert c.describe('')['status']=='BLOCKED'

def test_history_tool_enforces_exact_module_and_args(tmp_path):
    cat=HistoricalProcedureCatalog(sample(tmp_path))
    class Dummy:pass
    tools=EvidenceTools(Dummy(),Dummy(),historical_patterns=cat)
    assert 'inspect_historical_procedures' in tools.descriptions
    ctx={'module_code':'0102100100000'}
    good=tools.execute('inspect_historical_procedures',
                       {'module_code':'0102100100000'},ctx)
    assert good['status']=='HISTORICAL_NOTES_ONLY_NOT_VERIFIED_EXECUTIONS'
    assert good['requires_ticket_specific_read'] is True
    assert tools.execute('inspect_historical_procedures',
         {'module_code':'0102100100000','sql':'UPDATE x'},ctx)['status']=='BLOCKED'
    assert tools.execute('inspect_historical_procedures',
         {'module_code':'0102100100000'}, {})['status']=='BLOCKED'
    assert tools.execute('inspect_historical_procedures',
         {'module_code':'999999'},ctx)['status']=='BLOCKED'
    assert tools.execute('inspect_historical_procedures',
         {},ctx)['status']=='BLOCKED'

def test_history_not_loaded_is_denied():
    class Dummy:pass
    tools=EvidenceTools(Dummy(),Dummy())
    assert tools.execute('inspect_historical_procedures',
      {'module_code':'0102100100000'},{'module_code':'0102100100000'})['status']=='BLOCKED'

def test_catalog_blocks_fourth_cohort_contamination(tmp_path):
    p=sample(tmp_path)
    payload=json.loads(p.read_text())
    payload['includes_heldout_fourth']=True
    p.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='CONTAMINATION'):
        HistoricalProcedureCatalog(p)

def test_catalog_blocks_corrupted_schema_or_references(tmp_path):
    p=sample(tmp_path)
    payload=json.loads(p.read_text())
    payload['modules']['0102100100000']['patterns'][0]['table']='DROP TABLE'
    p.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='PATTERN_INVALID'):
        HistoricalProcedureCatalog(p)

def test_holdout_uses_exact_kind_table_field_not_keyword(tmp_path):
    c=HistoricalProcedureCatalog(sample(tmp_path))
    inputs=[{
        'case_sha256':f'{n:064x}','module_code':'0102100100000'}
        for n in range(1,101)]
    gold=[{'case_sha256':f'{n:064x}',
           'historical_solution_redacted':(
            'UPDATE a SET a.CodigoCaja=55 FROM taCobranza a' if n==1 else
            'UPDATE a SET a.CodigoMovimiento=55 FROM taCobranza a' if n==2 else
            'se atendio')} for n in range(1,101)]
    result=score(c,{'selected':100,'results':inputs},
                 {'historical_count':100,'historical_records':gold})
    assert result['exact_kind_table_field_overlap']==1
    assert result['holdout_with_sql_mentions']==2
    assert result['candidate_hints_available']==100
    assert result['matched_root_causes_verified']==0

def test_oversized_note_fails():
    with pytest.raises(ValueError,match='OVERSIZED'):
        extract_note_mentions('x'*30001)

def test_catalog_must_bind_three_training_receipts(tmp_path):
    p=sample(tmp_path)
    obj=json.loads(p.read_text())
    obj['source_receipts'][2]['cohort']='may_fourth100'
    p.write_text(json.dumps(obj))
    with pytest.raises(ValueError,match='TRAINING_ONLY'):
        HistoricalProcedureCatalog(p)

def test_catalog_refuses_fabricated_execution(tmp_path):
    p=sample(tmp_path)
    obj=json.loads(p.read_text())
    obj['modules']['0102100100000']['patterns'][0]['execution_confirmed']=True
    p.write_text(json.dumps(obj))
    with pytest.raises(ValueError,match='PATTERN_INVALID'):
        HistoricalProcedureCatalog(p)

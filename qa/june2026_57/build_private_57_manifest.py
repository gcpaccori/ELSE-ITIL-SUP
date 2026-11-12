"""HMAC-sealed 57-case follow-up; derived from signed May500→June1621 overlap.

This is *posthoc* evidence exploration, NOT a new blind model holdout.
No ticket text, history or private identifier goes to the repository.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json,hmac
from qa.monthend2026.evaluate_monthend import verify_one
from else_dominance.historical_procedures import extract_note_mentions

SCHEMA='else.itil.qa.2026-june57-source-and-history-reference-selection.v1'
PROOF='else.itil.qa.2026-june57-source-and-history-reference-hmac.v1'
ROOT=Path('/home/u23u/else_itil_57_commercial_qa_20261112')
MONTH=Path('/home/u23u/else_itil_juneall_20261112')
KEY=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private').read_bytes()
READER=Path('qa/june2026/JuneAllRead.cs')
source_sha=sha256(READER.read_bytes()).hexdigest()
src,src_digest=verify_one(MONTH/'private/juneall_202606.private.json',KEY,
 source_sha,'else.itil.qa.2026-juneall-source.v1',
 'else.itil.qa.2026-juneall-source-hmac.v1')
gold,gold_digest=verify_one(MONTH/'private/juneall_202606_history.private.json',KEY,
 source_sha,'else.itil.qa.2026-juneall-history.v1',
 'else.itil.qa.2026-juneall-history-hmac.v1')
labels=json.loads((MONTH/'private/june1621_may500_case_labels.private.json').read_bytes())
rows=[]
for label in labels['cases']:
 if not label['flags']['exact_kind_table_fields']:continue
 rk=label['rank'];r=src['results'][rk-1];g=gold['historical_records'][rk-1]
 assert r['case_sha256']==g['case_sha256']==label['case_sha256']
 mentions=extract_note_mentions(g['historical_solution_redacted'])
 tables={x['table'].lower() for x in mentions}
 target=(
   'OT' if 'taordentrabajo' in tables
   else 'COLLECTION' if 'tacobranza' in tables
   else None
 )
 if target is None: continue
 if 'tacobranza' in tables and 'taordentrabajo' in tables:
  raise AssertionError('CROSS_CATEGORY_57_CASE_NOT_PINNED')
 rows.append({
  'rank':rk,'case_sha256':r['case_sha256'],
  'request_sha256':r['description_sha256'],
  'history_sha256':g['historical_solution_sha256'],
  'module_code':r['module_code'],
  'itil_company':r['company'],
  'category':target,
  'historical_precedent_overlap_only':True,
 })
assert len(rows)==57,(len(rows),{x['category'] for x in rows})
assert sum(x['category']=='OT' for x in rows)==22
assert sum(x['category']=='COLLECTION' for x in rows)==35
assert len({x['rank'] for x in rows})==57 and len({x['case_sha256'] for x in rows})==57
rows.sort(key=lambda x:x['rank'])
out={
 'schema':SCHEMA,'source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
 'source_june1621_receipt_sha256':src_digest,
 'history_june1621_receipt_sha256':gold_digest,
 'prior_may500_only_training':True,
 'posthoc_gold_use_for_fixed_test_selection':True,
 'read_only':True,
 'selected':57,'categories':{'OT':22,'COLLECTION':35},
 'rows':rows
}
data=json.dumps(out,ensure_ascii=False,separators=(',',':')).encode()
d=sha256(data).hexdigest()
p=ROOT/'private/june57_manifest.private.json'
p.write_bytes(data);p.chmod(0o600)
p2=p.with_name(p.name+'.proof.json')
p2.write_text(json.dumps({
 'schema':PROOF,'source_sha256':out['source_sha256'],
 'receipt_sha256':d,'hmac_sha256':hmac.new(KEY,
   f'{SCHEMA}:{out["source_sha256"]}:{d}'.encode(),'sha256').hexdigest(),
 'read_only':True
}))
p2.chmod(0o600)
print('SIGNED_SELECTION_N=',len(rows),'OT=',out['categories']['OT'],
 'COLLECTION=',out['categories']['COLLECTION'],'MANIFEST_SHA=',d)

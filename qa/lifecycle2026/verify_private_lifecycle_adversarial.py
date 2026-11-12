"""Operator-only physical receipt adversarial verification (never publish case data)."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import hmac,json,shutil

from else_dominance.qa_itil_native_lifecycle import (
    VerifiedItILNativeLifecycle,verify_lifecycle_field_claim,
    SCHEMA,EVENT_SCHEMA,SOURCE)

ROOT=Path('/home/u23u/else_itil_workflow_qa_20261112')
MONTH=Path('/home/u23u/else_itil_monthend100_20261112')
SIGNER=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private')
FILES=(
    'itil_native_lifecycle_900.private.json',
    'itil_native_lifecycle_900.private.json.proof.json',
    'itil_derivation_events_900.private.json',
    'itil_derivation_events_900.private.json.proof.json')

def load(root:Path):
    return VerifiedItILNativeLifecycle(
        private_root=root,
        reader_file=ROOT/'repo/qa/lifecycle2026/CaseLifecycleRead.cs',
        events_reader_file=ROOT/'repo/qa/lifecycle2026/DerivationEventsRead.cs',
        monthly_root=MONTH/'private',
        month_source_file=MONTH/'postmerge_main/qa/monthend2026/MonthEnd100Read.cs',
        key_file=SIGNER)

def copy_to(path:Path):
    for f in FILES:shutil.copyfile(ROOT/'private'/f,path/f)

def resign_event(root:Path,raw:bytes):
    target=root/FILES[2]
    proof_path=root/FILES[3]
    target.write_bytes(raw)
    proof=json.loads(proof_path.read_bytes())
    digest=sha256(raw).hexdigest()
    proof['receipt_sha256']=digest
    key=SIGNER.read_bytes()
    payload=f"{EVENT_SCHEMA}:{proof['source_sha256']}:{digest}".encode()
    proof['hmac_sha256']=hmac.new(key,payload,sha256).hexdigest()
    proof_path.write_text(json.dumps(proof))

index=load(ROOT/'private')
assert len(index.rows)==900
assert sum(len(x) for x in index.events.values())==1155
assert sum(v["exact_key_equality_derivacion"]>1 for v in index.rows.values())==212
case=next(iter(index.rows.values()))
claimed={
    'case_sha256':case['case_sha256'],
    'module_code':case['module_code'],
    'as_of':case['opened_at'],
    'source':SOURCE,
    'field':'exact_key_equality_derivacion',
    'observed_value':case['exact_key_equality_derivacion'],
    'lifecycle_receipt_sha256':index.receipt_sha256,
}
assert verify_lifecycle_field_claim(index,claimed)['status']=='EXACT_ITIL_LIFECYCLE_FIELD_VALUE_VERIFIED'
for key,new_value in (
  ('case_sha256','0'*64),
  ('module_code','NOT_ORIGINAL_MODULE'),
  ('as_of','2026-10-01'),
  ('source','ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo'),
  ('observed_value',case['exact_key_equality_derivacion']+1),
  ('lifecycle_receipt_sha256','0'*64)):
    assert verify_lifecycle_field_claim(index,{**claimed,key:new_value})['status']=='BLOCKED'
with TemporaryDirectory() as tmp:
    p=Path(tmp);copy_to(p)
    target=p/FILES[0]
    target.write_bytes(target.read_bytes()+b' ')
    try:load(p)
    except ValueError:pass
    else:raise AssertionError('TAMPER_LIFECYCLE_HMAC_FALSE_PASS')
with TemporaryDirectory() as tmp:
    p=Path(tmp);copy_to(p)
    target=p/FILES[2]
    target.write_bytes(target.read_bytes()+b' ')
    try:load(p)
    except ValueError:pass
    else:raise AssertionError('TAMPER_EVENT_HMAC_FALSE_PASS')
with TemporaryDirectory() as tmp:
    p=Path(tmp);copy_to(p)
    events=json.loads((p/FILES[2]).read_bytes())
    other=next(v['case_sha256'] for v in events['results']
               if v['case_sha256']!=events['results'][0]['case_sha256'])
    events['results'][0]['case_sha256']=other
    resign_event(p,json.dumps(events,ensure_ascii=False,separators=(',',':')).encode())
    try:load(p)
    except ValueError:pass
    else:raise AssertionError('RESIGNED_EVENT_CROSS_CASE_FALSE_PASS')
with TemporaryDirectory() as tmp:
    p=Path(tmp);copy_to(p)
    events=json.loads((p/FILES[2]).read_bytes())
    events['formal_itil_to_derivacion_foreign_key_verified']=True
    resign_event(p,json.dumps(events,ensure_ascii=False,separators=(',',':')).encode())
    try:load(p)
    except ValueError:pass
    else:raise AssertionError('RESIGNED_FALSE_FOREIGN_KEY_FALSE_PASS')
print('REAL_NATIVE_ITIL_900_HMAC_AND_EVENT_BINDING=PASS')
print('CHECKS=BAD_CASE,BAD_MODULE,BAD_DATE,BAD_SOURCE,BAD_VALUE,BAD_RECEIPT,TAMPER_PARENT_HMAC,TAMPER_EVENT_HMAC,RESIGNED_CROSS_CASE,RESIGNED_FALSE_FK:ALL_BLOCKED')
print('DERIVATION_EVENTS=1155; DECLARED_FK=0; REPAIRS_CERTIFIED=0; BUSINESS_WRITES=0')

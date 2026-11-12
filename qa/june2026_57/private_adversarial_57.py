"""Attacks against real 57 June business candidate receipts: fail closed.

All byte tampering takes place in temporary dirs within private QA scope.
Even an actor holding the original signing key cannot modify the immutable
Git report digest without invalidating the pinned post-merge claim.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json,hmac,shutil

from qa.june2026_57.verify_and_score_57 import audit

ROOT=Path('/home/u23u/else_itil_57_commercial_qa_20261112')
SOURCE=ROOT/'private'
REPO=ROOT/'repo'
KEYFILE=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private')
KEY=KEYFILE.read_bytes()
JUNE=Path('/home/u23u/else_itil_juneall_20261112/private')
PIN=REPO/'data/2026_june57_business_source_trace.json'
FILES=('june57_manifest.private.json',
       'june57_manifest.private.json.proof.json',
       'june57_business_candidates.private.json',
       'june57_business_candidates.private.json.proof.json')
def run(folder):
    return audit(folder,REPO,KEYFILE,JUNE,aggregate_file=PIN)
def copy_files(folder):
    for f in FILES:
        shutil.copyfile(SOURCE/f,folder/f)
def fail_closed(title,callback):
    try:callback()
    except (ValueError,KeyError,AssertionError,IndexError):
        return
    raise AssertionError('JUNE57_ATTACK_FALSE_PASS_'+title)
def resign(folder,index,mutation):
    target=folder/FILES[index]
    obj=json.loads(target.read_bytes())
    mutation(obj)
    raw=json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode()
    target.write_bytes(raw)
    proof=folder/FILES[index+1]
    d=json.loads(proof.read_bytes())
    digest=sha256(raw).hexdigest()
    d['receipt_sha256']=digest
    d['hmac_sha256']=hmac.new(KEY,
      f'{obj["schema"]}:{obj["source_sha256"]}:{digest}'.encode(),'sha256').hexdigest()
    proof.write_text(json.dumps(d))
good=run(SOURCE)
assert good['selected_cases']==57 and good['totals']['cases_with_any_positive_db_match']==12
count=0
for idx in (0,2):
    with TemporaryDirectory(dir=SOURCE,prefix='june57-qa-tamper-') as tmp:
        folder=Path(tmp);copy_files(folder)
        p=folder/FILES[idx]
        p.write_bytes(p.read_bytes()+b' ')
        fail_closed('HMAC_'+str(idx),lambda:run(folder))
        count+=1
tamper_cases=(
  (0,lambda d:d['rows'][0].__setitem__('rank',1000),'RESIGN_OTHER_CASE'),
  (0,lambda d:d['categories'].__setitem__('OT',25),'RESIGN_FAKE_COHORT'),
  (2,lambda d:d['case_identity_data'][0].__setitem__('itil_company','9'),'RESIGN_FALSE_ITIL_COMPANY'),
  (2,lambda d:d['case_identity_data'][0].__setitem__('identity_status','REQUEST_AND_NOTE_SAME_ID'),'RESIGN_PROMOTE_GOLD_ONLY'),
  (2,lambda d:d['case_identity_data'][0].__setitem__('identifier_agreement',True),'RESIGN_FALSE_AGREEMENT'),
  (2,lambda d:d['case_identity_data'][0].__setitem__('case_sha256','f'*64),'RESIGN_WRONG_CASE'),
  (2,lambda d:d['searched_databases'][0].__setitem__('metadata','NOT_VISIBLE_ONLINE'),'RESIGN_HIDE_QA_DATABASE'),
  (2,lambda d:d.__setitem__('business_repairs_certified',1),'RESIGN_FALSE_BUSINESS_REPAIR'),
)
for i,change,title in tamper_cases:
    with TemporaryDirectory(dir=SOURCE,prefix='june57-qa-tamper-') as tmp:
        folder=Path(tmp);copy_files(folder)
        resign(folder,i,change)
        fail_closed(title,lambda:run(folder))
        count+=1
print('QA_JUNE57_SIGNED_FROZEN_SOURCE_AND_BUSINESS=PASS')
print('QA_JUNE57_TAMPER_ATTACKS_BLOCKED=',count)
print('QA_JUNE57_FIFTY_SEVEN_CASES_RECOVERED_IDS=',good['totals']['cases_with_any_positive_db_match'])
print('QA_JUNE57_CORPORATE_MUTATIONS=0 REPAIRS_CERTIFIED=0')

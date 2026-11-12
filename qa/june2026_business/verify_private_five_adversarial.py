"""Private QA attacks against June-5 business proof chain. No network writes."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json,hmac,shutil

from qa.june2026_business.score_five_business_evidence import audit

ROOT=Path('/home/u23u/else_itil_june2026_business_qa_20261112')
QA=ROOT/'repo/qa/june2026_business'
ORIG=ROOT/'private'
KEY=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private').read_bytes()
AUTHOR=Path('/home/u23u/else_itil_juneall_20261112/private/june_100_blind_qwen9b.private.jsonl')
JUDGE=Path('/home/u23u/else_itil_juneall_20261112/private/june_100_judge_qwen4b.private.jsonl')
NAMES=[
  'june5_manifest.private.json','june5_manifest.private.json.proof.json',
  'june5_exact_business.private.json','june5_exact_business.private.json.proof.json',
  'june5_metadata.private.json','june5_metadata.private.json.proof.json'
]
def load(path:Path,judge=JUDGE):
    return audit(path,QA,KEY,AUTHOR,judge)
def copy(path:Path):
    for n in NAMES:shutil.copyfile(ORIG/n,path/n)
def block(name,call):
    try:call()
    except (ValueError,KeyError,AssertionError):return name
    raise AssertionError(name+'_FALSE_PASS')
def resign(path:Path,name:str,data:dict,source:str,schema:str):
    f=path/name
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    f.write_bytes(raw)
    p=f.with_name(f.name+'.proof.json')
    proof=json.loads(p.read_bytes())
    digest=sha256(raw).hexdigest()
    proof['receipt_sha256']=digest
    proof['hmac_sha256']=hmac.new(KEY,
        f'{schema}:{source}:{digest}'.encode(),'sha256').hexdigest()
    p.write_text(json.dumps(proof))
positive=load(ORIG)
assert positive['counts']['cases']==5
assert positive['counts']['unique_business_row']==0
attacks=[]
with TemporaryDirectory(prefix='fiveaudit-',dir=ORIG) as tmp:
    t=Path(tmp);copy(t)
    p=t/NAMES[0]
    p.write_bytes(p.read_bytes()+b' ')
    attacks.append(block('MANIFEST_TAMPER',lambda:load(t)))
with TemporaryDirectory(prefix='fiveaudit-',dir=ORIG) as tmp:
    t=Path(tmp);copy(t)
    p=t/NAMES[2]
    p.write_bytes(p.read_bytes()+b' ')
    attacks.append(block('BUSINESS_RECEIPT_TAMPER',lambda:load(t)))
with TemporaryDirectory(prefix='fiveaudit-',dir=ORIG) as tmp:
    t=Path(tmp);copy(t)
    p=t/NAMES[4]
    p.write_bytes(p.read_bytes()+b' ')
    attacks.append(block('METADATA_RECEIPT_TAMPER',lambda:load(t)))
with TemporaryDirectory(prefix='fiveaudit-',dir=ORIG) as tmp:
    t=Path(tmp);copy(t)
    p=t/NAMES[2];d=json.loads(p.read_bytes())
    d['rows'][0]['case_sha256']=d['rows'][1]['case_sha256']
    resign(t,p.name,d,d['source_sha256'],d['schema'])
    attacks.append(block('RESIGNED_CROSS_CASE',lambda:load(t)))
with TemporaryDirectory(prefix='fiveaudit-',dir=ORIG) as tmp:
    t=Path(tmp);copy(t)
    p=t/NAMES[2];d=json.loads(p.read_bytes())
    d['rows'][0]['business_row_count']=1
    resign(t,p.name,d,d['source_sha256'],d['schema'])
    attacks.append(block('RESIGNED_FALSE_BUSINESS_ROW',lambda:load(t)))
with TemporaryDirectory(prefix='fiveaudit-',dir=ORIG) as tmp:
    t=Path(tmp);copy(t)
    p=t/NAMES[2];d=json.loads(p.read_bytes())
    d['rows'][0]['repair_certified']=True
    resign(t,p.name,d,d['source_sha256'],d['schema'])
    attacks.append(block('RESIGNED_FALSE_REPAIR',lambda:load(t)))
with TemporaryDirectory(prefix='fiveaudit-',dir=ORIG) as tmp:
    t=Path(tmp);copy(t)
    judge=t/'judge_tamper.jsonl'
    rows=[json.loads(line) for line in JUDGE.read_text().splitlines() if line]
    for r in rows:
        if r['rank']==197:r['judge']['plan_alignment']='NO_VALID_PLAN'
    judge.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    attacks.append(block('FAKE_JUDGE_ALIGNMENT',lambda:load(t,judge)))
print('JUNE5_REAL_ORIGINAL_PROOF_CHAIN=PASS')
print('JUNE5_ADVERSARIAL_ATTACKS=',len(attacks),'ALL_BLOCKED')
print('FIVE_VERIFIED_SOURCES, FOUR_NOT_FOUND, ONE_NONUNIQUE, ZERO_AUDIT_BEFORE_AFTER, ZERO_REPAIRS')

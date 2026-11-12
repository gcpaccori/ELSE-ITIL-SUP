"""Read-only adversarial proof against signed June 1621 and 100 blind judges.

Copies private receipts to a temporary directory INSIDE the authorized
private root. Never exports ticket text, history, or original identifiers.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json,shutil,hmac
from qa.monthend2026.evaluate_monthend import verify_one
from qa.june2026.score_qwen100_vs_history import audit as judge_audit
from qa.june2026.evaluate_all_1621 import audit as all_audit

ROOT=Path('/home/u23u/else_itil_juneall_20261112')
MONTH=Path('/home/u23u/else_itil_monthend100_20261112')
BASE=ROOT/'repo'
KEY=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private')
MAY=Path('/home/u23u/else_itil_may100_qa_20261112')
MODULES=Path('/home/u23u/else_itil_db_knowledge_20261111/derived/ITIL_MODULE_DIRECTORY.json')
SOURCE_FILE=BASE/'qa/june2026/JuneAllRead.cs'
FILES=(
    'juneall_202606.private.json',
    'juneall_202606.private.json.proof.json',
    'juneall_202606_history.private.json',
    'juneall_202606_history.private.json.proof.json',
)
S='else.itil.qa.2026-juneall-source.v1'
SP='else.itil.qa.2026-juneall-source-hmac.v1'
G='else.itil.qa.2026-juneall-history.v1'
GP='else.itil.qa.2026-juneall-history-hmac.v1'
code_sha=sha256(SOURCE_FILE.read_bytes()).hexdigest()
key=KEY.read_bytes()

def check(path):
    return verify_one(path,key,code_sha,S if '_history' not in path.name else G,
            SP if '_history' not in path.name else GP)

def source_and_gold(path):
    a,ash=check(path/FILES[0])
    b,bsh=check(path/FILES[2])
    return a,b,ash,bsh

def clone(root:Path):
    for name in FILES:
        shutil.copyfile(ROOT/'private'/name,root/name)

def resign(root:Path,index:int,data:dict):
    target=root/FILES[index]
    proof=root/FILES[index+1]
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    target.write_bytes(raw)
    evidence=json.loads(proof.read_bytes())
    receipt_sha=sha256(raw).hexdigest()
    schema=S if index==0 else G
    evidence['receipt_sha256']=receipt_sha
    evidence['hmac_sha256']=hmac.new(key,
       f'{schema}:{code_sha}:{receipt_sha}'.encode(),'sha256').hexdigest()
    proof.write_text(json.dumps(evidence))

def fail_closed(label,callback):
    try:
        callback()
    except (ValueError,AssertionError,KeyError):
        return
    raise AssertionError('FALSE_PASS_'+label)

source,history,source_sha,historic_sha=source_and_gold(ROOT/'private')
assert source['selected']==history['historical_count']==1621
assert len({x['case_sha256'] for x in source['results']})==1621
notes=ROOT/'private/june_100_blind_qwen9b.private.jsonl'
judges=ROOT/'private/june_100_judge_qwen4b.private.jsonl'
positive=judge_audit(ROOT/'private',SOURCE_FILE,key,notes,judges)
assert positive['sample_completed']==100
assert positive['counts']['judge_alignment_SAME_MECHANISM']==5

with TemporaryDirectory(prefix='june-tamper-',dir=ROOT/'private') as td:
    p=Path(td);clone(p)
    (p/FILES[0]).write_bytes((p/FILES[0]).read_bytes()+b' ')
    fail_closed('BAD_HMAC_REQUEST',lambda:check(p/FILES[0]))
with TemporaryDirectory(prefix='june-tamper-',dir=ROOT/'private') as td:
    p=Path(td);clone(p)
    (p/FILES[2]).write_bytes((p/FILES[2]).read_bytes()+b' ')
    fail_closed('BAD_HMAC_HISTORY',lambda:check(p/FILES[2]))
with TemporaryDirectory(prefix='june-tamper-',dir=ROOT/'private') as td:
    p=Path(td);clone(p)
    s=json.loads((p/FILES[0]).read_bytes())
    s['results'][0]['case_sha256']='0'*64
    resign(p,0,s)
    fail_closed('RESIGNED_WRONG_CASE',lambda:all_audit(
      p,SOURCE_FILE,MONTH/'private',BASE/'qa/monthend2026/MonthEnd100Read.cs',
      key,MODULES,MONTH/'private/earlier_may_mechanisms.private.json',
      MAY/'private/historical_procedure_patterns.private.json',
      p/'tampered-private-ledger.json'))
with TemporaryDirectory(prefix='june-tamper-',dir=ROOT/'private') as td:
    p=Path(td);clone(p)
    g=json.loads((p/FILES[2]).read_bytes())
    g['historical_records'][0]['case_sha256']=g['historical_records'][1]['case_sha256']
    resign(p,2,g)
    fail_closed('RESIGNED_CROSS_CASE_HISTORY',lambda:all_audit(
      p,SOURCE_FILE,MONTH/'private',BASE/'qa/monthend2026/MonthEnd100Read.cs',
      key,MODULES,MONTH/'private/earlier_may_mechanisms.private.json',
      MAY/'private/historical_procedure_patterns.private.json',
      p/'tampered-private-ledger.json'))
with TemporaryDirectory(prefix='june-tamper-',dir=ROOT/'private') as td:
    p=Path(td);clone(p)
    src=p/'june_100_blind_qwen9b.private.jsonl'
    src.write_bytes(notes.read_bytes())
    rows=[json.loads(line) for line in src.read_text().splitlines() if line]
    rows[0]['gold_exposed']=True
    src.write_text('\n'.join(json.dumps(item) for item in rows)+'\n')
    fail_closed('AUTHOR_GOLD_EXPOSED',lambda:judge_audit(p,SOURCE_FILE,key,src,judges))
with TemporaryDirectory(prefix='june-tamper-',dir=ROOT/'private') as td:
    p=Path(td);clone(p)
    reviewer=p/'june_100_judge_qwen4b.private.jsonl'
    rows=[json.loads(line) for line in judges.read_text().splitlines() if line]
    for row in rows:
        if row['status']=='PROVISIONAL_JUDGE_PASS':
            row['judge']['evidence_quote']='A_QUOTE_THAT_IS_NOT_IN_THIS_NOTE'
            break
    reviewer.write_text('\n'.join(json.dumps(item) for item in rows)+'\n')
    fail_closed('UNSUPPORTED_JUDGE_QUOTE',lambda:judge_audit(p,SOURCE_FILE,key,notes,reviewer))
print('JUNE_ALL_1621_HMAC=PASS; FROZEN_100_AUTHORS_AND_JUDGES=PASS')
print('ADVERSARIAL_REQUEST_HISTORY_HMAC_RESIGNED_CROSSCASE_GOLD_EXPOSURE_FALSE_QUOTE=6/6_BLOCKED')
print('REAL_CORPORATE_WRITES=0; REAL_REPAIRS_CERTIFIED=0')

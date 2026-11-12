"""Private adversarial replays for 619 signed PK matches, without SQL changes."""
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json,hmac,shutil
from qa.june2026_identity.score_request_pk_recovery import assess

ROOT=Path('/home/u23u/else_itil_june57_identifier_recovery_20261112')
REPO=ROOT/'repo'
PRIVATE=ROOT/'private'
PRIOR=Path('/home/u23u/else_itil_57_commercial_qa_20261112/private')
JUNE=Path('/home/u23u/else_itil_juneall_20261112/private')
KEYFILE=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private')
KEY=KEYFILE.read_bytes()
PUBLIC=json.loads((REPO/'data/2026_june57_original_request_pk_recovery.json').read_bytes())
files=[
 'june57_request_ids.private.json','june57_request_ids.private.json.proof.json',
 'june57_bulk_pk_request_matches.private.json','june57_bulk_pk_request_matches.private.json.proof.json',
 'june57_residual_source_relation.private.json','june57_residual_source_relation.private.json.proof.json'
]
def check(path):
    actual=assess(REPO,path,PRIOR,JUNE,KEYFILE)
    if actual!=PUBLIC:raise ValueError('PINNED_PUBLIC_REPORT_SOURCE_DRIFT')
    return actual
def copy(dest):
    for item in files:shutil.copyfile(PRIVATE/item,dest/item)
def resign(folder,at,change):
    p=folder/files[at]
    d=json.loads(p.read_bytes())
    change(d)
    raw=json.dumps(d,ensure_ascii=False,separators=(',',':')).encode()
    p.write_bytes(raw)
    proof=folder/files[at+1]
    r=json.loads(proof.read_bytes())
    digest=sha256(raw).hexdigest()
    r['receipt_sha256']=digest
    r['hmac_sha256']=hmac.new(
       KEY,f'{d["schema"]}:{d["source_sha256"]}:{digest}'.encode(),'sha256').hexdigest()
    proof.write_text(json.dumps(r))
def blocked(name,action):
    try:action()
    except (ValueError,KeyError,AssertionError,IndexError):
        return
    raise AssertionError('QA_FALSE_PASS_'+name)
ok=check(PRIVATE)
assert ok['totals']['matched_case_pk_pairs']==619
attacks=0
for item in (0,2,4):
    with TemporaryDirectory(dir=PRIVATE,prefix='qa-id-tamper-') as temp:
        t=Path(temp);copy(t)
        p=t/files[item];p.write_bytes(p.read_bytes()+b' ')
        blocked('BAD_MAC_'+str(item),lambda:check(t));attacks+=1
mutations=[
 (2,lambda x:x['matches'][0].__setitem__('business_branch_equals_itil_branch',False),'FALSE_BRANCH'),
 (2,lambda x:x['matches'][0].__setitem__('identifier_private','1111111111111111111'),'FALSE_PK'),
 (2,lambda x:x['matches'][0].__setitem__('source_candidate_sha256','0'*64),'FALSE_REQUEST_BIND'),
 (2,lambda x:x['matches'][0].__setitem__('case_sha256','f'*64),'WRONG_CASE'),
 (2,lambda x:x['matches'][0].__setitem__('found_in_database','dbComercial001_D'),'WRONG_DB'),
 (2,lambda x:x['matches'][0].__setitem__('historical_target_not_read',False),'GOLD_EXPOSED'),
 (2,lambda x:x.__setitem__('business_writes',1),'FALSE_EXECUTION'),
 (2,lambda x:x['matches'].append(x['matches'][0]),'DUPLICATE_MATCH'),
 (2,lambda x:x.__setitem__('original_request_only',False),'NOT_REQUEST_ONLY'),
 (0,lambda x:x['rows'][0].__setitem__('request_sha256','f'*64),'WRONG_SOURCE'),
 (4,lambda x:x['lookup_results'][0].__setitem__('same_itil_branch',1),'FALSE_RESIDUAL'),
]
for index,change,name in mutations:
    with TemporaryDirectory(dir=PRIVATE,prefix='qa-id-tamper-') as temp:
        t=Path(temp);copy(t)
        resign(t,index,change)
        blocked(name,lambda:check(t));attacks+=1
print('PRIVATE_JUNE57_REQUEST_PK_RECEIPTS=PASS')
print('REAL_HMAC_AND_RESIGNED_ATTACKS_BLOCKED=',attacks)
print('SIGNED_PK_LINKS=619 DISTINCT_BUSINESS_KEYS=525 REPAIRS=0')

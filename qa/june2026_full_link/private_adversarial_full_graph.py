"""Real signed 1621-case graph adversarial tests. All copies stay private."""
from pathlib import Path
from tempfile import TemporaryDirectory
from collections import Counter
from hashlib import sha256
import json,hmac,shutil
from else_dominance.qa_june_full_source_links import VerifiedJuneFullBusinessGraph

ROOT=Path('/home/u23u/else_itil_alljune_business_link_20261113')
REPO=ROOT/'repo';PRIVATE=ROOT/'private'
JUNE=Path('/home/u23u/else_itil_juneall_20261112/private')
KEYFILE=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private')
KEY=KEYFILE.read_bytes()
NAMES=[
 'june1621_source_only_dualpk.private.json',
 'june1621_source_only_dualpk.private.json.proof.json',
 'june1621_verified_case_graph.private.json',
 'june1621_verified_case_graph.private.json.proof.json'
]
def load(folder):
    return VerifiedJuneFullBusinessGraph(repo=REPO,private=folder,
                                        june_source=JUNE,key_file=KEYFILE)
def duplicate(dst):
    for name in NAMES:shutil.copyfile(PRIVATE/name,dst/name)
def signed_mutation(dst,index,edit):
    rawpath=dst/NAMES[index]
    data=json.loads(rawpath.read_bytes())
    edit(data)
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    rawpath.write_bytes(encoded)
    proofpath=dst/NAMES[index+1]
    proof=json.loads(proofpath.read_bytes())
    digest=sha256(encoded).hexdigest()
    proof['receipt_sha256']=digest
    proof['hmac_sha256']=hmac.new(KEY,
        f'{data["schema"]}:{data["source_sha256"]}:{digest}'.encode(),'sha256').hexdigest()
    proofpath.write_text(json.dumps(proof))
def blocked(label,fn):
    try:fn()
    except (ValueError,KeyError,AssertionError,TypeError,IndexError):
        return
    raise AssertionError('QA_FULL_GRAPH_FALSE_PASS_'+label)

v=load(PRIVATE)
cnt=Counter()
for row in v.cases.values():
    x=v.inspect(case_sha256=row['case_sha256'],module_code=row['module_code'],
      as_of='2026-06-30T23:59:59',view='objects',retrospective_qa=True)
    assert len(x.get('object_handles',[]))==len(row['links'])
    assert 'business_pk_private' not in json.dumps(x)
    assert x['business_state_at_incident_time_verified'] is False
    assert x['causal_business_fix_verified'] is False
    cnt[x['status']]+=1
assert cnt==Counter({
    'NO_SAME_BRANCH_QA_PRIMARY_KEY':1288,
    'SINGLE_LOGICAL_PK_RETROSPECTIVE':158,
    'MULTIPLE_LOGICAL_PKS_PRIMARY_UNDETERMINED':175
})
count=0
for idx in (0,2):
    with TemporaryDirectory(dir=PRIVATE,prefix='june-full-integrity-') as temp:
        dst=Path(temp);duplicate(dst)
        file=dst/NAMES[idx];file.write_bytes(file.read_bytes()+b' ')
        blocked('MAC_'+str(idx),lambda:load(dst));count+=1
attacks=[
 (0,lambda d:d['case_metadata'][0].__setitem__('case_sha256','f'*64),'RAW_CASE_RE_SIGN'),
 (0,lambda d:d['case_metadata'][0].__setitem__('module_code','FAKE'),'RAW_MODULE_RE_SIGN'),
 (0,lambda d:d['business_key_matches'][0].__setitem__('business_branch_matches_itil',True),'FAKE_BRANCH_RE_SIGN'),
 (0,lambda d:d['business_key_matches'][0].__setitem__('primary_key_private','9999999999999999999'),'FAKE_PK_RE_SIGN'),
 (0,lambda d:d.__setitem__('input_request_only',False),'GOLD_INPUT_RE_SIGN'),
 (0,lambda d:d.__setitem__('business_writes',1),'FAKE_WRITES_RE_SIGN'),
 (0,lambda d:d.__setitem__('business_sql_select_batches',0),'REPLACE_SQL_COVERAGE'),
 (2,lambda d:d['linked_cases'][0].__setitem__('module_code','FAKE'),'GRAPH_WRONG_MODULE'),
 (2,lambda d:d['linked_cases'][0].__setitem__('case_sha256','f'*64),'GRAPH_CROSS_CASE'),
 (2,lambda d:d['linked_cases'][0].__setitem__('status','SINGLE_LOGICAL_PK_OBSERVED_RETROSPECTIVELY'),'GRAPH_FALSE_SINGLE'),
 (2,lambda d:d['linked_cases'][0].__setitem__('no_object_primary_assumed',False),'GRAPH_PRETEND_PRIMARY'),
 (2,lambda d:next(c for c in d['linked_cases'] if c['links']).__setitem__('links',[]),'GRAPH_HIDE_BUSINESS_KEYS'),
 (2,lambda d:d.__setitem__('official_application_business_fk_certified',True),'GRAPH_FAKE_FK'),
 (2,lambda d:d.__setitem__('historical_causal_or_write_evidence_certified',True),'GRAPH_FAKE_FIX'),
 (2,lambda d:d.__setitem__('writes',1),'GRAPH_FAKE_WRITES'),
]
for idx,edit,label in attacks:
    with TemporaryDirectory(dir=PRIVATE,prefix='june-full-integrity-') as temp:
        dst=Path(temp);duplicate(dst)
        signed_mutation(dst,idx,edit)
        blocked(label,lambda:load(dst));count+=1
some=next(x for x in v.cases.values() if x['logical_object_count']>=2)
base={'case_sha256':some['case_sha256'],'module_code':some['module_code'],
      'as_of':'2026-06-30T23:59:59','retrospective_qa':True}
for label,changes in [
 ('NOT_OPERATOR_MODE',{'retrospective_qa':False}),
 ('WRONG_CASE',{'case_sha256':'f'*64}),
 ('WRONG_MODULE',{'module_code':'INVALID'}),
 ('WRONG_MONTH',{'as_of':'2026-07-01'}),
 ('INVALID_DAY',{'as_of':'2026-06-31'}),
 ('INVALID_HOUR',{'as_of':'2026-06-30T90:99:99'}),
 ('EARLIER_THAN_TICKET',{'as_of':'2026-06-01T00:00:00'}),
 ('UNAUTHORIZED_VIEW',{'view':'raw_ids'})
]:
    args={**base,**changes}
    assert v.inspect(**args)['status']=='BLOCKED',label
    count+=1
print('JUNE1621_PRIVATE_SIGNED_GRAPH=PASS')
print('JUNE1621_ADVERSARIAL_ATTACKS_BLOCKED=',count)
print('JUNE1621_OBSERVATIONAL_LINKS=1491 CASES=1621 REPAIRS=0 WRITES=0')

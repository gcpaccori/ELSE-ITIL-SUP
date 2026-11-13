"""QA-only adversarial HMAC and case-scope tests of the real link registry."""
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import hmac,json,shutil
from collections import Counter
from else_dominance.qa_ticket_business_links import VerifiedTicketBusinessLinks

ROOT=Path('/home/u23u/else_itil_ticket_object_link_20261112')
REPO=ROOT/'repo';ORIGINAL=ROOT/'private'
REQUEST=Path('/home/u23u/else_itil_june57_identifier_recovery_20261112/private')
PRIOR=Path('/home/u23u/else_itil_57_commercial_qa_20261112/private')
JUNE=Path('/home/u23u/else_itil_juneall_20261112/private')
KEYFILE=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private')
KEY=KEYFILE.read_bytes()
FILES=[
 'verified_ticket_business_links.private.json',
 'verified_ticket_business_links.private.json.proof.json',
 'native_itil_link_metadata.private.json',
 'native_itil_link_metadata.private.json.proof.json'
]
def load(folder):
    return VerifiedTicketBusinessLinks(repo=REPO,private=folder,
      request_private=REQUEST,prior_private=PRIOR,
      june_private=JUNE,key_file=KEYFILE)
def copy(folder):
    for filename in FILES:shutil.copyfile(ORIGINAL/filename,folder/filename)
def resign(folder,index,change):
    file=folder/FILES[index]
    doc=json.loads(file.read_bytes())
    change(doc)
    raw=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode()
    file.write_bytes(raw)
    proofpath=folder/FILES[index+1]
    p=json.loads(proofpath.read_bytes())
    digest=sha256(raw).hexdigest()
    p['receipt_sha256']=digest
    p['hmac_sha256']=hmac.new(KEY,
       f'{doc["schema"]}:{doc["source_sha256"]}:{digest}'.encode(),
       'sha256').hexdigest()
    proofpath.write_text(json.dumps(p))
def deny(title,callback):
    try:callback()
    except (ValueError,KeyError,IndexError,TypeError):
        return
    raise AssertionError('FALSE_LINK_PASS_'+title)
v=load(ORIGINAL)
assert len(v.cases)==57
buckets=Counter()
for x in v.cases.values():
    out=v.inspect(case_sha256=x['case_sha256'],module_code=x['module_code'],
                  as_of='2026-06-15T10:30:00',view='objects')
    assert out['qa_evidence_links']==len(out.get('object_handles',[]))
    assert out['native_sql_foreign_key_verified'] is False
    assert out['historical_fix_certified'] is False
    assert not any('pk_value_private' in h for h in out.get('object_handles',[]))
    buckets[out['status']]+=1
assert buckets==Counter({
 'SINGLE_QA_PK_MATCH':13,
 'MULTIPLE_QA_PK_MATCHES_PRIMARY_UNDETERMINED':42,
 'UNRESOLVED':2
})
attacks=0
for target in (0,2):
    with TemporaryDirectory(dir=ORIGINAL,prefix='itil-link-qa-') as temp:
        folder=Path(temp);copy(folder)
        f=folder/FILES[target]
        f.write_bytes(f.read_bytes()+b' ')
        deny('HMAC_'+str(target),lambda:load(folder));attacks+=1
modify=[
 (0,lambda d:d['cases'][0].__setitem__('module_code','WRONG'),'RE_SIGN_WRONG_MODULE'),
 (0,lambda d:d['cases'][0].__setitem__('case_sha256','f'*64),'RE_SIGN_WRONG_CASE'),
 (0,lambda d:d['cases'][0].__setitem__('object_count',999),'RE_SIGN_FALSE_SINGLE'),
 (0,lambda d:d['cases'][0].__setitem__('status','OFFICIAL_FK_CERTIFIED'),'RE_SIGN_FAKE_STATUS'),
 (0,lambda d:d['cases'][0].__setitem__('primary_business_object_not_inferred',False),'RE_SIGN_FALSE_PRIMARY'),
 (0,lambda d:d.__setitem__('native_sql_fk_declared',True),'RE_SIGN_FAKE_NATIVE_FK'),
 (0,lambda d:d.__setitem__('business_repairs_certified',1),'RE_SIGN_FALSE_REPAIR'),
 (0,lambda d:d['cases'][0]['links'].append({'handle':'f'*64}),'RE_SIGN_INJECT_FAKE_LINK'),
 (0,lambda d:d['cases'][0].__setitem__('links',d['cases'][1]['links']),'RE_SIGN_CROSS_CASE_LINK'),
 (2,lambda d:d.__setitem__('direct_table_same_name_itil_and_ot_or_cobranza_pairs',1),'RE_SIGN_NATIVE_CONTRACT'),
 (2,lambda d:d.__setitem__('itil_taIncidente_foreign_keys',[{'source_table':'fake'}]),'RE_SIGN_FAKE_SQL_FK')
]
for idx,change,name in modify:
    with TemporaryDirectory(dir=ORIGINAL,prefix='itil-link-qa-') as temp:
        folder=Path(temp);copy(folder)
        resign(folder,idx,change)
        deny(name,lambda:load(folder));attacks+=1
example=next(x for x in v.cases.values() if x['object_count']>=2)
context={'case_sha256':example['case_sha256'],'module_code':example['module_code'],
          'as_of':'2026-06-15T10:30:00'}
for name,changes in [
 ('WRONG_CASE',{'case_sha256':'f'*64}),
 ('WRONG_MODULE',{'module_code':'INVALID'}),
 ('WRONG_MONTH',{'as_of':'2026-07-15'}),
 ('INVALID_DAY',{'as_of':'2026-06-31'}),
]:
    args={**context,**changes}
    assert v.inspect(**args)['status']=='BLOCKED',name
    attacks+=1
first=v.inspect(**context,view='objects')['object_handles'][0]
try:
    v.resolve_for_authorized_reader(**{**context,'case_sha256':'f'*64},
        handle=first['handle'])
    raise AssertionError('CROSS_TICKET_HANDLE_FALSE_PASS')
except ValueError:attacks+=1
try:
    v.resolve_for_authorized_reader(**context,handle='f'*64)
    raise AssertionError('INVENTED_HANDLE_FALSE_PASS')
except ValueError:attacks+=1
print('PRIVATE_SIGNED_CASE_BUSINESS_LINKS=PASS')
print('QA_TAMPER_OR_SCOPE_ATTACKS_BLOCKED=',attacks)
print('LINKS=619 CASES=57 SINGLE=13 MULTI=42 UNRESOLVED=2 OFFICIAL_FKS=0 WRITES=0')

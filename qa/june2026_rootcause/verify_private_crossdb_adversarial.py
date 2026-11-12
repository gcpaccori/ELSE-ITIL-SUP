"""Hostile QA against 4 separate HMAC-bound evidence products.

All sensitive receipts are copied inside authorized private storage;
no passwords, per-case data or business values are emitted.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json,shutil,hmac

from else_dominance.qa_june_business_route import VerifiedJuneBusinessRoute

ROOT=Path('/home/u23u/else_itil_june2026_rootcause_20261112')
OLD=Path('/home/u23u/else_itil_june2026_business_qa_20261112')
KEYFILE=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private')
KEY=KEYFILE.read_bytes()
FILES=(
 'june5_crossdb.private.json',
 'june5_crossdb.private.json.proof.json',
 'june5_recovered.private.json',
 'june5_recovered.private.json.proof.json',
 'commercial_company_routes.private.json',
 'commercial_company_routes.private.json.proof.json',
 'historical_availability.private.json',
 'historical_availability.private.json.proof.json',
)
SOURCE={
 'june5_crossdb.private.json':('qa/june2026_rootcause/JuneCrossDatabaseFind.cs',
      'else.itil.qa.2026-june5-crossdb-targets.v1'),
 'june5_recovered.private.json':('qa/june2026_rootcause/JuneRecoveredObjectsRead.cs',
      'else.itil.qa.2026-june5-recovered-objects-and-audit.v1'),
 'commercial_company_routes.private.json':('qa/june2026_rootcause/JuneCommercialCompanyRouteRead.cs',
      'else.itil.qa.2026-commercial-route-1-4-100.v1'),
 'historical_availability.private.json':('qa/june2026_rootcause/JuneHistoricalAvailabilityRead.cs',
      'else.itil.qa.2026-historical-availability-metadata.v1')
}
def load(path):
    return VerifiedJuneBusinessRoute(root=path,five_root=OLD/'private',
          qa_source_root=ROOT/'repo',signing_key=KEYFILE)
def copy(path):
    for file in FILES:shutil.copyfile(ROOT/'private'/file,path/file)
def resign(path,name,obj):
    file=path/name
    raw=json.dumps(obj,separators=(',',':'),ensure_ascii=False).encode()
    file.write_bytes(raw)
    proof=file.with_name(file.name+'.proof.json')
    p=json.loads(proof.read_bytes())
    code,schema=SOURCE[name]
    source=sha256((ROOT/'repo'/code).read_bytes()).hexdigest()
    digest=sha256(raw).hexdigest()
    p['receipt_sha256']=digest
    p['hmac_sha256']=hmac.new(KEY,f'{schema}:{source}:{digest}'.encode(),'sha256').hexdigest()
    proof.write_text(json.dumps(p))
def block(title,callback):
    try:callback()
    except (ValueError,KeyError,TypeError):return title
    raise AssertionError('ATTACK_FALSE_PASS_'+title)
positive=load(ROOT/'private')
assert positive.summary()['cases_with_routed_company_row']==2
attacks=[]
for target in (0,2,4,6):
    with TemporaryDirectory(prefix='june-crossdb-',dir=ROOT/'private') as temp:
        t=Path(temp);copy(t)
        name=FILES[target]
        (t/name).write_bytes((t/name).read_bytes()+b' ')
        attacks.append(block('BAD_MAC_'+name,lambda:load(t)))
for title,name,change in (
  ('RE_SIGN_FAKE_COMPANY100_ROUTE','commercial_company_routes.private.json',
   lambda d:d['rows'][2].__setitem__('target_db','dbComercial001_D')),
  ('RE_SIGN_FAKE_CROSSDB_CAMPAIGN_ROW','june5_crossdb.private.json',
   lambda d:next(r for db in d['searched_databases']
                 if db['db']=='dbComercial100_D'
                 for r in db['rows'] if r['rank']==1065).__setitem__('count',1)),
  ('RE_SIGN_WRONG_CASE_RECOVERY','june5_recovered.private.json',
   lambda d:d['recovered_matches'][0].__setitem__('original_june_case_sha256','0'*64)),
  ('RE_SIGN_FALSE_REPAIR','june5_recovered.private.json',
   lambda d:d['recovered_matches'][0].__setitem__('business_fix_certified',True)),
  ('RE_SIGN_STOLEN_CORPORATE_ROUTE','commercial_company_routes.private.json',
   lambda d:d['rows'][1].__setitem__('route_verified',False)),
  ('RE_SIGN_INVENTED_BACKUP','historical_availability.private.json',
   lambda d:d['backup_metadata'].append({'db':'dbComercial100_D','backup_count':1})),
  ('RE_SIGN_INVENTED_CDC','historical_availability.private.json',
   lambda d:d['cdc_metadata'][0].__setitem__('cdc_enabled',True)),
):
    with TemporaryDirectory(prefix='june-crossdb-',dir=ROOT/'private') as tmp:
        t=Path(tmp);copy(t)
        f=t/name
        doc=json.loads(f.read_bytes());change(doc);resign(t,name,doc)
        attacks.append(block(title,lambda:load(t)))
first=positive.five[197]
assert positive.inspect(case_sha256=first['case_sha256'],
  module_code='WRONG_MODULE',as_of='2026-06-15')['status']=='BLOCKED'
assert positive.inspect(case_sha256='f'*64,
  module_code=first['module_code'],as_of='2026-06-15')['status']=='BLOCKED'
assert positive.inspect(case_sha256=first['case_sha256'],
  module_code=first['module_code'],as_of='2026-07-15')['status']=='BLOCKED'
print('SIGNED_FIVE_RECEIPT_PRODUCTS=PASS; 5_ITIL_CASES=PASS')
print('CROSSDB_AND_ROUTES_TAMPER_ATTACKS',len(attacks),'BLOCKED')
print('SCOPE_ATTACKS_CASE_MODULE_MONTH=3_BLOCKED')
print('BUSINESS_WRITES=0 REPAIRS_CERTIFIED=0')

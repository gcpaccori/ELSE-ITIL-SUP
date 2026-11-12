"""Operator-only hostile QA checks against independently HMAC-signed receipts."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json,shutil,hmac
from else_dominance.qa_derivation_contracts import (
  VerifiedDerivationContracts, METADATA_SCHEMA, ROUTE_SCHEMA)
from else_dominance.qa_itil_native_lifecycle import VerifiedItILNativeLifecycle

ROOT=Path('/home/u23u/else_itil_deriv_semantics_contracts_20261112')
LIFECYCLE=Path('/home/u23u/else_itil_workflow_qa_20261112')
MONTH=Path('/home/u23u/else_itil_monthend100_20261112')
KEY=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private')
FILES=(
  'derivation_contracts_metadata.private.json',
  'derivation_contracts_metadata.private.json.proof.json',
  'module_route_900.private.json',
  'module_route_900.private.json.proof.json')
lifecycle=VerifiedItILNativeLifecycle(
  private_root=LIFECYCLE/'private',
  reader_file=ROOT/'repo/qa/lifecycle2026/CaseLifecycleRead.cs',
  events_reader_file=ROOT/'repo/qa/lifecycle2026/DerivationEventsRead.cs',
  monthly_root=MONTH/'private',
  month_source_file=ROOT/'repo/qa/monthend2026/MonthEnd100Read.cs',
  key_file=KEY)

def load(path):
    return VerifiedDerivationContracts(
      private_root=path,
      metadata_source=ROOT/'repo/qa/derivation2026/DerivationContractsProbe.cs',
      route_source=ROOT/'repo/qa/derivation2026/ModuleRouteRead.cs',
      monthly_root=MONTH/'private',
      month_reader=ROOT/'repo/qa/monthend2026/MonthEnd100Read.cs',
      signing_key=KEY,
      lifecycle=lifecycle)
def safe_copy(p):
    for name in FILES:
        shutil.copy2(ROOT/'private'/name,p/name)
def resign(path,which,new):
    src=path/FILES[which]
    proof_path=path/FILES[which+1]
    raw=json.dumps(new,ensure_ascii=False,separators=(',',':')).encode()
    src.write_bytes(raw)
    proof=json.loads(proof_path.read_bytes())
    digest=sha256(raw).hexdigest()
    proof['receipt_sha256']=digest
    schema=METADATA_SCHEMA if which==0 else ROUTE_SCHEMA
    proof['hmac_sha256']=hmac.new(
       KEY.read_bytes(),f"{schema}:{proof['source_sha256']}:{digest}".encode(),
       sha256).hexdigest()
    proof_path.write_text(json.dumps(proof))
def must_block(label,callback):
    try:callback()
    except (ValueError,KeyError):
        return label
    raise AssertionError(label+' FALSE PASS')

legit=load(ROOT/'private')
assert legit.row_count==900
assert legit.alias_count==662
assert legit.semantics('1')['meaning'] is None
assert legit.semantics('2')['meaning'] is None
assert legit.semantics('3')['meaning'] is None
claims=[]
for index in (0,2):
    with TemporaryDirectory() as tmp:
        p=Path(tmp);safe_copy(p)
        path=p/FILES[index]
        path.write_bytes(path.read_bytes()+b' ')
        claims.append(must_block('HMAC_TAMPER_'+str(index),lambda:load(p)))
# Malicious worker with signing key still cannot override the exact source-bound contracts:
for label,which,action in [
  ('RESIGNED_FALSE_BUSINESS_FK',2,lambda d:d.__setitem__('module_to_business_entity_fk_certified',True)),
  ('RESIGNED_FALSE_PHYSICAL_ROUTE',2,lambda d:d.__setitem__('alias_to_physical_db_route_certified',True)),
  ('RESIGNED_UNTRUSTED_MODULE_ALIAS',2,lambda d:d['rows'][0].__setitem__('module_declared_alias_bde','dbOther')),
  ('RESIGNED_CROSS_CASE_ROW',2,lambda d:d['rows'][0].__setitem__('case_sha256',d['rows'][1]['case_sha256'])),
  ('RESIGNED_CASE_BUSINESS_KEY',2,lambda d:d['rows'][0].__setitem__('business_object_key_verified',True)),
  ('RESIGNED_FALSE_SEMANTICS',0,lambda d:d.__setitem__('dictionary_semantics_certified',True)),
  ('RESIGNED_UNREVIEWED_SQL_LOGIC',0,lambda d:d['stored_logic_objects_referencing_derivation'].append({'schema':'dbo','name':'fake_sp'})),
]:
    with TemporaryDirectory() as tmp:
        p=Path(tmp);safe_copy(p)
        doc=json.loads((p/FILES[which]).read_bytes())
        action(doc)
        resign(p,which,doc)
        claims.append(must_block(label,lambda:load(p)))
idx=next(iter(legit.rows.values()))
case=idx['case_sha256']
true=legit.inspect_route(case_sha256=case,module_code=idx['module_code'],as_of=idx['month']+'-01')
assert true['status']=='ITIL_MODULE_AND_SERVICE_ROWS_VERIFIED'
assert true['business_entity_fk_certified'] is False
assert legit.proposed_business_join(case_sha256=case,
   module_code=idx['module_code'],as_of=idx['month']+'-01',
   proposed_table='ELSE70/dbDistribucion_D/dbo.taOrdenTrabajo')['status']=='ABSTAIN_BUSINESS_JOIN_NOT_CERTIFIED'
print('PHYSICAL_SIGNED_PROOFS=PASS; 900_CASES=PASS')
print('REAL_TAMPER_AND_RESIGNED_ATTACKS=',len(claims),'ALL_BLOCKED')
print('SEMANTIC_TYPES_1_2_3=UNRESOLVED; BUSINESS_FK_VERIFIED=0; REPAIRS=0; SQL_WRITES=0')

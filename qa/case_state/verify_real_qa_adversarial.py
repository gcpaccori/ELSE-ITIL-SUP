"""Private operator-only physical evidence and deliberate tampering proof.

The real Windows receipt is not checked into Git. This script exercises
source/receipt HMAC, no mixed ticket, wrong module, wrong business field
and false state claims against the real 90+42 stored QA observations.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,shutil
from else_dominance.qa_case_state_evidence import VerifiedCaseStateIndex,verify_claim
from else_dominance.qa_reported_ot_evidence import (
    VerifiedReportedOtIndex,verify_reported_ot_claim)
from qa.case_state.evaluate_900_reported_ot import score as score_ot

C=Path('/home/u23u/else_itil_case_state_20261112')
M=Path('/home/u23u/else_itil_monthend100_20261112')
KEY=Path('/home/u23u/else_itil_aug_domain_hand_qa_20261110/worker_hmac.private')
def itk(root):
    return VerifiedCaseStateIndex(
        private_root=root,source_file=C/'repo/qa/case_state/CaseStateRead.cs',
        month_private=M/'private',month_source=M/'postmerge_main/qa/monthend2026/MonthEnd100Read.cs',
        key_file=KEY)
def ots(root):
    return VerifiedReportedOtIndex(
        private_root=root,source_file=C/'repo/qa/case_state/ReportedOtDomainRead.cs',
        month_private=M/'private',month_source=M/'postmerge_main/qa/monthend2026/MonthEnd100Read.cs',
        key_file=KEY)
a=itk(C/'private')
b=ots(C/'private')
assert len(a.rows)==90 and b.reported==42 and b.found==9
assert sum(len(r['observed_fields']) for r in a.rows.values())==720
assert score_ot(b)['domain_exact_field_values_verified']==63
case=next(iter(a.rows.values()))
status=a.inspect(case_sha256=case['case_sha256'],
   module_code=case['observed_fields']['CodigoModulo'],
   as_of=case['month']+'-01',field='CodigoEstadoIncidente')
claim={
  'case_sha256':case['case_sha256'],'module_code':case['observed_fields']['CodigoModulo'],
  'as_of':case['month']+'-01',
  'source':status['source'],'field':status['field'],
  'observed_value':status['observed_value'],
  'receipt_sha256':status['receipt_sha256']}
assert verify_claim(a,claim)['status']=='FIELD_VALUE_EXACTLY_VERIFIED_IN_QA_SNAPSHOT'
assert verify_claim(a,{**claim,'observed_value':'FAKE'})['status']=='BLOCKED'
assert verify_claim(a,{**claim,'receipt_sha256':'0'*64})['status']=='BLOCKED'
assert verify_claim(a,{**claim,'case_sha256':'0'*64})['status']=='BLOCKED'
assert verify_claim(a,{**claim,'module_code':'OTHER'})['status']=='BLOCKED'
assert verify_claim(a,{**claim,'as_of':'2026-10-02'})['status']=='BLOCKED'
true_ot=next(r for r in b.rows.values() if r['row_count']==1)
observed=b.inspect(case_sha256=true_ot['case_sha256'],
   module_code=true_ot['case_module_code'],as_of=true_ot['month']+'-01',
   field='CodigoEstadoOrdenTrabajo')
assert observed['status']=='READ_VERIFIED_REPORTED_OT_QA_FIELD'
claim_ot={
 'case_sha256':true_ot['case_sha256'],
 'module_code':true_ot['case_module_code'],'as_of':true_ot['month']+'-01',
 'source':observed['source'],'field':observed['field'],
 'observed_value':observed['observed_value'],
 'receipt_sha256':observed['receipt_sha256'],
 'reported_ot_sha256':observed['reported_ot_sha256']}
assert verify_reported_ot_claim(b,claim_ot)['status']=='REPORTED_OT_FIELD_EXACT_QA_VALUE_VERIFIED'
assert verify_reported_ot_claim(b,{**claim_ot,'reported_ot_sha256':'0'*64})['status']=='BLOCKED'
assert verify_reported_ot_claim(b,{**claim_ot,'observed_value':'NO'})['status']=='BLOCKED'
with TemporaryDirectory() as d:
    p=Path(d)
    for file in ('case_state_90.private.json','case_state_90.private.json.proof.json'):
        shutil.copyfile(C/'private'/file,p/file)
    original=p/'case_state_90.private.json'
    original.write_bytes(original.read_bytes()+b' ')
    try:itk(p)
    except ValueError:pass
    else:raise AssertionError('FORGED_CASE_STATE_RECEIPT_PASS')
with TemporaryDirectory() as d:
    p=Path(d)
    for file in ('reported_ot_domain.private.json','reported_ot_domain.private.json.proof.json'):
        shutil.copyfile(C/'private'/file,p/file)
    proof=p/'reported_ot_domain.private.json.proof.json'
    data=json.loads(proof.read_text())
    data['hmac_sha256']='0'*64
    proof.write_text(json.dumps(data))
    try:ots(p)
    except ValueError:pass
    else:raise AssertionError('FORGED_REPORTED_OT_HMAC_PASS')
print('PHYSICAL_QA_EVIDENCE_GATE_PASS cases=90 itil_fields=720 ot_candidates=42 ot_found=9 ot_fields=63')
print('TAMPER_HMAC=FAIL_CLOSED; WRONG_VALUE=FAIL_CLOSED; WRONG_TICKET=FAIL_CLOSED; WRONG_MODULE=FAIL_CLOSED; WRONG_MONTH=FAIL_CLOSED')
print('OFFICIAL_BUSINESS_LINKS=0; CAUSAL_FIXES=0; DATA_MODIFICATIONS=0')

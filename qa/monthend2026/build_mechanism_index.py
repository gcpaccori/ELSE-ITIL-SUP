"""Build private lexical mechanism mention index from authenticated May pages 1-3."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from hashlib import sha256
from else_dominance.historical_mechanism_matching import build_private_mechanism_index
from qa.may2026.score_private_history import verify_receipt
PAGES=(("may_first100","MayFirst100Read.cs"),
       ("may_next100","MayNext100Read.cs"),
       ("may_third100","MayThird100Read.cs"))
def build(private:Path,qa:Path,key:bytes)->dict:
    records=[];seen=set();receipts=[]
    for basename,code in PAGES:
        a,a_sha=verify_receipt(private,qa,key,basename,code)
        b,b_sha=verify_receipt(private,qa,key,basename,code,history=True)
        assert b['cohort_source_sha256']==a_sha
        assert a['selected']==b['historical_count']==100
        receipts.append({'cohort':basename,'source_receipt_sha256':a_sha,
                         'history_receipt_sha256':b_sha})
        for req,hist in zip(a['results'],b['historical_records']):
            case=req['case_sha256']
            if case!=hist['case_sha256'] or case in seen:
                raise ValueError("TRAINING_SOURCE_GOLD_NOT_BOUND")
            seen.add(case)
            records.append((req['module_code'],
                            hist['historical_solution_redacted']))
    if len(seen)!=300:
        raise ValueError("TRAINING_SOURCE_NOT_EXACT_THREE_HUNDRED")
    data=build_private_mechanism_index(records)
    data['source_receipts']=receipts
    return data
def main():
    p=argparse.ArgumentParser()
    for arg in ('private','qa-may','key','out'):
        p.add_argument('--'+arg,required=True,type=Path)
    a=p.parse_args()
    data=build(a.private,a.qa_may,a.key.read_bytes())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    a.out.chmod(0o600)
    print(json.dumps({
        'trained_cases':data['train_cases'],
        'modules':len(data['modules']),
        'historical_notes_with_explicit_mechanism':data['notes_with_mechanisms'],
        'distinct_module_mechanisms':sum(len(x['mentions']) for x in data['modules'].values()),
        'actual_executions_certified':0}))
if __name__=='__main__':main()

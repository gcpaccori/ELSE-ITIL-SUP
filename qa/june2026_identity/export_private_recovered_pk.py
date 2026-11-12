"""Export 619 verified QA business key observations to a private 0600 CSV.

Public artifacts intentionally contain no original primary key values.
This command requires the original signed Windows QA receipt and key.
"""
from argparse import ArgumentParser
from pathlib import Path
from hashlib import sha256
import csv,io,json,hmac,os
from qa.monthend2026.evaluate_monthend import verify_one

SCHEMA='else.itil.qa.2026-june57-recovered-pks-private-csv.v1'

def run(repo:Path,private:Path,keyfile:Path,dest:Path):
    src=repo/'qa/june2026_identity/June57BulkPrimaryKeyMatch.cs'
    key=keyfile.read_bytes()
    data,proof=verify_one(
        private/'june57_bulk_pk_request_matches.private.json',
        key,sha256(src.read_bytes()).hexdigest(),
        'else.itil.qa.2026-june57-request-bulk-primary-key-lookup.v1',
        'else.itil.qa.2026-june57-request-bulk-primary-key-lookup-hmac.v1')
    assert len(key)==32
    assert data['read_only'] is True and data['business_writes']==0
    assert data['historical_note_column_selected'] is False
    assert data['original_request_only'] is True
    assert len(data['matches'])==619
    assert dest.resolve().parent==private.resolve()
    assert not dest.is_symlink()
    out=io.StringIO(newline='')
    writer=csv.writer(out)
    writer.writerow(('rank','case_sha256','kind','primary_key',
                     'qa_database','business_branch','source_provenance','status'))
    unique=set()
    for r in sorted(data['matches'],key=lambda x:(
            x['rank'],x['category'],x['identifier_private'])):
        code=r['identifier_private']
        assert sha256(code.encode()).hexdigest()==r['source_candidate_sha256']
        assert r['business_branch_equals_itil_branch'] is True
        unique.add((r['category'],code))
        writer.writerow((r['rank'],r['case_sha256'],r['category'],code,
            r['found_in_database'],r['business_branch'],
            'ITIL_ORIGINAL_REQUEST_EXACT_PK_MATCH',
            'CURRENT_QA_MATCH_NOT_A_HISTORICAL_REPAIR'))
    assert len(unique)==525
    raw=out.getvalue().encode('utf-8')
    dest.write_bytes(raw);os.chmod(dest,0o600)
    code_sha=sha256(Path(__file__).read_bytes()).hexdigest()
    csv_sha=sha256(raw).hexdigest()
    seal=hmac.new(key,f'{SCHEMA}:{code_sha}:{proof}:{csv_sha}'.encode(),
                  'sha256').hexdigest()
    sealfile=dest.with_name(dest.name+'.proof.json')
    sealfile.write_text(json.dumps({
       'schema':SCHEMA,'exporter_source_sha256':code_sha,
       'origin_signed_bulk_receipt_sha256':proof,
       'csv_sha256':csv_sha,'hmac_sha256':seal,
       'observations':619,'distinct_business_keys':525,
       'historic_repairs_certified':0,'read_only':True
    },indent=2))
    os.chmod(sealfile,0o600)
    print('PRIVATE_CSV_SIGNED=PASS',
          'ROWS=619','DISTINCT_BUSINESS_KEYS=525',
          'FILE_MODE=0600','HISTORIC_REPAIRS=0')
if __name__=='__main__':
    p=ArgumentParser()
    for x in ('repo','private','key','output'):
        p.add_argument('--'+x,type=Path,required=True)
    a=p.parse_args()
    run(a.repo,a.private,a.key,a.output)

"""Independent backward compatibility: all 619 signed June57 PK rows survive.

This uses no historical text, no business writes and no sensitive output.
Source receipts are signed HMAC and verified against the exact reader code.
"""
from __future__ import annotations
from pathlib import Path
from argparse import ArgumentParser
from hashlib import sha256
from qa.monthend2026.evaluate_monthend import verify_one

def check(repo,full_private,old_private,keyfile):
    key=keyfile.read_bytes()
    full,full_digest=verify_one(
        full_private/'june1621_source_only_dualpk.private.json',key,
        sha256((repo/'qa/june2026_full_link/JuneAllSourceOnlyPkRead.cs').read_bytes()).hexdigest(),
        'else.itil.qa.2026-june1621-source-only-dual-pk-discovery.v1',
        'else.itil.qa.2026-june1621-source-only-dual-pk-discovery-hmac.v1')
    old,old_digest=verify_one(
        old_private/'june57_bulk_pk_request_matches.private.json',key,
        sha256((repo/'qa/june2026_identity/June57BulkPrimaryKeyMatch.cs').read_bytes()).hexdigest(),
        'else.itil.qa.2026-june57-request-bulk-primary-key-lookup.v1',
        'else.itil.qa.2026-june57-request-bulk-primary-key-lookup-hmac.v1')
    before={
        (r['case_sha256'],r['category'],r['source_candidate_sha256'],r['found_in_database'])
        for r in old['matches']
    }
    after={
        (r['case_sha256'],r['kind'],r['primary_key_sha256'],r['source_database'])
        for r in full['business_key_matches']
        if r['business_branch_matches_itil'] is True
    }
    if (len(before)!=619 or len(after)<619 or len(before-after)!=0
       or full['source_cases']!=1621 or old['selected_cases']!=57):
        raise ValueError('FULL_JUNE_LOST_PREVIOUS_SIGNED_57_CASE_PK_OBSERVATIONS')
    return {
        'prior_57_relation_observations':len(before),
        'retained_in_exhaustive_1621':len(before & after),
        'lost':0,
        'prior_receipt_sha256':old_digest,
        'full_month_receipt_sha256':full_digest,
        'business_writes':0
    }
def main():
    p=ArgumentParser()
    for name in ('repo','full-private','old-private','key'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    result=check(a.repo,a.full_private,a.old_private,a.key)
    print('SIGNATURE_VERIFIED_JUNE57_TO_JUNE1621_NONREGRESSION=PASS')
    print('PREVIOUS_RELATIONS=619 RETAINED=619 LOST=0 BUSINESS_WRITES=0')
if __name__=='__main__':main()

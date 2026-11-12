"""Aggregate-only verified corporate route diagnostic; no ticket identifiers."""
from argparse import ArgumentParser
from pathlib import Path
import json
from else_dominance.qa_june_business_route import VerifiedJuneBusinessRoute

def main():
    p=ArgumentParser()
    for name in ('private','five-private','key','output'):
        p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    v=VerifiedJuneBusinessRoute(root=a.private,five_root=a.five_private,
        qa_source_root=root,signing_key=a.key)
    obj=v.summary()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
    print('SIGNED_JUNE_QA_BUSINESS_ROUTE',json.dumps({
       'cases':obj['selected_june_cases'],
       'databases':obj['databases_checked'],
       'company_routes':obj['official_routes'],
       'cases_with_any_ot_row':obj['cases_with_any_unique_ot_row_across_sources'],
       'cases_with_verified_transactional_company_route':obj['cases_with_routed_company_row'],
       'gerencial_only':obj['historical_objects_found_in_gerencial_only'],
       'source_divergence':obj['cases_with_different_routed_and_gerencial_qa_state'],
       'repairs':obj['business_repairs_certified']},ensure_ascii=False))
if __name__=='__main__':main()

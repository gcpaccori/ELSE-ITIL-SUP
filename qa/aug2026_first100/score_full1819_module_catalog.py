"""No-LLM module routing coverage for full August 2026 source-only cases.

The atlas is metadata-only and explicitly not a verified deployed runtime
map; alias_bd is never automatically interpreted as a SQL database address.
"""
from __future__ import annotations
import argparse,collections,gzip,hashlib,json
from pathlib import Path


def score(atlas:dict,blind:list[dict],manifest:dict)->dict:
    if (atlas.get("schema")!="else.itil.qa.cross-domain-knowledge-atlas.v1"
            and "itil_module_directory" not in atlas):
        raise ValueError("ATLAS_SCHEMA_NOT_RECOGNIZED")
    if len(blind)!=1819 or manifest["cases"]!=1819:
        raise ValueError("AUGUST_SOURCE_COUNT_INVALID")
    mapped={}
    for entry in atlas["itil_module_directory"]:
        key=entry["codigo_modulo_trimmed_for_repo_name"]
        if key in mapped:raise ValueError("DUPLICATE_CANONICAL_MODULE")
        mapped[key]=entry
    first=blind
    count=collections.Counter()
    modules=set()
    for row in first:
        if row["month"]!="2026-08" or row["historical_resolution"]!="WITHHELD":
            raise ValueError("SOURCE_SCOPE_VIOLATION")
        code=row["module_code"].strip()
        modules.add(code)
        entry=mapped.get(code)
        if entry is None:
            count["not_in_itil_directory"]+=1
            continue
        count["module_directory_match"]+=1
        count["database_alias_declared"]+=bool(entry.get("alias_bd_declared"))
        count["candidate_repository_present"]+=bool(entry.get("candidate_repository_present"))
        count["candidate_csharp_present"]+=entry.get("candidate_repository_csharp_file_count",0)>0
    return {
      "schema":"else.itil.qa.aug2026-full1819-module-candidate-metadata.v1",
      "cases":1819,"unique_source_module_codes":len(modules),
      "counts":dict(sorted(count.items())),
      "atlas_runtime_modules_not_deployment_verified":True,
      "declared_database_alias_not_equivalent_to_physical_database":True,
      "csharp_repository_not_verified_runtime_version":True,
      "repair_or_business_link_proven":False,
      "historical_solution_not_read":True
    }

def main():
    p=argparse.ArgumentParser()
    for arg in ("atlas","blind","manifest","out"):p.add_argument("--"+arg,type=Path,required=True)
    args=p.parse_args()
    manifest=json.loads(args.manifest.read_text())
    assert hashlib.sha256(args.blind.read_bytes()).hexdigest()==manifest["blind_sha256"],"AUG_BLIND_HASH_DRIFT"
    with gzip.open(args.atlas,"rt",encoding="utf-8") as f:atlas=json.load(f)
    blind=[json.loads(x) for x in args.blind.read_text().splitlines() if x.strip()]
    report=score(atlas,blind,manifest)
    report["qa_atlas_sha256"]=hashlib.sha256(args.atlas.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("AUG_FULL1819_MODULE_CATALOG_AGGREGATE_PASS",report["counts"])

if __name__=="__main__":main()

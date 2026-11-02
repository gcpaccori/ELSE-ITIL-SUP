import argparse
from datetime import datetime
import json
import os
from pathlib import Path
from .memory import CaseMemory
from .sources import SourceCatalog, EvidenceTools
from .agent import OpenAICompatibleModel, InvestigationAgent

DEFAULT_CATALOG=Path(__file__).parents[1]/'data'/'source_catalog.json'

def main():
 p=argparse.ArgumentParser(description='ELSE TIC Dominancia v0.7 LLM investigator')
 p.add_argument('--db',default='knowledge.sqlite');sub=p.add_subparsers(dest='action',required=True)
 a=sub.add_parser('stats')
 a=sub.add_parser('sources');a.add_argument('--search',default='')
 a=sub.add_parser('ingest');a.add_argument('--jsonl',required=True);a.add_argument('--captured-at',required=True)
 a=sub.add_parser('investigate');a.add_argument('--description',required=True);a.add_argument('--service',required=True)
 a.add_argument('--module',default='');a.add_argument('--class-code',default='');a.add_argument('--version',default='UNKNOWN')
 a.add_argument('--as-of',default='2026-01-01T00:00:00');a.add_argument('--max-steps',type=int,default=8)
 args=p.parse_args()
 m=CaseMemory(args.db)
 try:
  cat=SourceCatalog(DEFAULT_CATALOG)
  if args.action=='stats': out={'indexed_cases':m.count(),'source_catalog_count':len(cat.sources),'relations':len(cat.data['relations'])}
  elif args.action=='sources':out=cat.search(args.search) if args.search else cat.data
  elif args.action=='ingest':
   rows=[]
   for line in Path(args.jsonl).read_text(encoding='utf-8').splitlines():
    if line.strip():rows.append(json.loads(line))
   out=m.ingest(rows,captured_at=args.captured_at)
  elif args.action=='investigate':
   url=os.getenv('TIC_LLM_BASE_URL')
   model=os.getenv('TIC_LLM_MODEL')
   if not url or not model:p.error('TIC_LLM_BASE_URL and TIC_LLM_MODEL required for a REAL LLM; no fake model is used')
   llm=OpenAICompatibleModel(url,model,api_key=os.getenv('TIC_LLM_API_KEY',''))
   agent=InvestigationAgent(llm,EvidenceTools(m,cat),m,max_steps=args.max_steps)
   item={'description':args.description,'service_code':args.service,'module_code':args.module,
     'classification_code':args.class_code,'system_version':args.version,'as_of':args.as_of}
   out=agent.investigate(item,now=datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
  print(json.dumps(out,ensure_ascii=False,indent=2))
 finally:m.close()

if __name__=='__main__':main()

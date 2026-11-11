"""Command line for actual LLM investigation; never silently use a fake model."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from .memory import CaseMemory
from .sources import SourceCatalog,EvidenceTools
from .agent import OpenAICompatibleModel,InvestigationAgent
from .engineer import ResolutionGate,report_md
from .batch_2026 import HoldoutBatch

ROOT=Path(__file__).parents[1]

def main():
    p=argparse.ArgumentParser(description='ELSE TIC RIV v0.8 — IA investigadora con planes y roles condicionados')
    p.add_argument('--db',default='knowledge.sqlite',help='Ubicar SOLO en entorno corporativo autorizado')
    sub=p.add_subparsers(dest='task',required=True)
    c=sub.add_parser('resolve',help='Ejecuta un agente LLM real, en lectura')
    c.add_argument('--input',required=True,help='JSON con descripcion, servicio, modulo, fecha')
    c.add_argument('--out',help='Expediente JSON local autorizado')
    c.add_argument('--markdown',help='Expediente Markdown')
    c.add_argument('--max-steps',type=int,default=8)
    k=sub.add_parser('check-query',help='Valida schema/privilegios sin ejecutar SQL')
    k.add_argument('--id',required=True); k.add_argument('--source',required=True); k.add_argument('--columns',required=True)
    k.add_argument('--sql',default='')
    b=sub.add_parser('batch-2026',help='Evaluación LLM de expedientes 2026 autorizados, reanudable')
    b.add_argument('--jsonl',required=True);b.add_argument('--out',required=True);b.add_argument('--limit',type=int,default=0);b.add_argument('--max-steps',type=int,default=8)
    qc=sub.add_parser('qa-connectivity',help='Verifica recibo HMAC de la última lectura real del trabajador Windows QA (no reejecuta SQL)')
    qc.add_argument('--profile',default='',help='ID fijo de perfil, o vacío para todas las once fuentes')
    s=sub.add_parser('stats')
    a=p.parse_args()
    catalog_path=os.getenv('TIC_CATALOG_PATH','')
    qa_root=os.getenv('TIC_QA_CONNECTIVITY_ROOT','')
    if not catalog_path and a.task!='qa-connectivity':
        p.error('TIC_CATALOG_PATH debe apuntar a un catálogo privado verificado')
    catalog=SourceCatalog(catalog_path) if catalog_path else None
    if catalog is not None and catalog.data.get('public_demo_only') is True:
        p.error('Catálogo sintético no permitido para ejecución corporativa')
    qa_catalog=None
    if qa_root:
        from .qa_verified_connectivity import QaSignedConnectionCatalog,verify_qa_probe
        qa_catalog=QaSignedConnectionCatalog(root=Path(qa_root))
    if a.task=='qa-connectivity':
        if qa_catalog is None:
            p.error('TIC_QA_CONNECTIVITY_ROOT requerido para recibos QA privados')
        from .qa_verified_connectivity import verify_qa_probe
        try:
            result=qa_catalog.report(a.profile) if a.profile else verify_qa_probe(root=Path(qa_root))
        except (ValueError,OSError,KeyError,TypeError) as ex:
            p.error('Recibo de conectividad QA no verificable o caducado: '+type(ex).__name__)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
    if a.task=='check-query':
        result=ResolutionGate(catalog).validate_query_proposal(a.id,a.source,a.columns.split(','),sql=a.sql)
    else:
        memory=CaseMemory(a.db)
        try:
            if a.task=='stats':result={'corpus_individual_indexado':memory.count(),'catalogo_fuentes':len(catalog.sources),'relaciones':len(catalog.data['relations'])}
            else:
                model_url=os.getenv('TIC_LLM_BASE_URL','')
                model_id=os.getenv('TIC_LLM_MODEL','')
                if not model_url or not model_id:p.error('Se requiere TIC_LLM_BASE_URL y TIC_LLM_MODEL de un endpoint corporativo autorizado')
                llm=OpenAICompatibleModel(model_url,model_id,os.getenv('TIC_LLM_API_KEY',''))
                agent=InvestigationAgent(llm,EvidenceTools(memory,catalog,qa_catalog=qa_catalog),memory,max_steps=a.max_steps)
                if a.task=='batch-2026':
                    result=HoldoutBatch(agent,ResolutionGate(catalog),now=datetime.now().strftime('%Y-%m-%dT%H:%M:%S')).run(a.jsonl,a.out,max_cases=a.limit)
                    print(json.dumps(result,ensure_ascii=False,indent=2));return
                incident=json.loads(Path(a.input).read_text('utf-8'))
                if not isinstance(incident,dict) or not str(incident.get('description') or '').strip():p.error('JSON de incidente inválido')
                if not incident.get('as_of'):p.error('as_of necesario: fecha del incidente, no fecha actual')
                raw=agent.investigate(incident,now=datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
                result=ResolutionGate(catalog).audit(raw,incident)
                result['trace']={'session_id':raw.get('session_id'),'num_herramientas':raw.get('tool_calls'),'status_interno':raw.get('status'),'invalid_references':raw.get('invalid_references',[]),'unsupported_claims':raw.get('unsupported_claims',[])}
                result['modelo_real']={'id':model_id,'endpoint_operativo':model_url.startswith('http://127.0.0.1:') or model_url.startswith('https://')}
                if a.out:Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
                if a.markdown:Path(a.markdown).write_text(report_md(result),'utf-8')
        finally:memory.close()
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

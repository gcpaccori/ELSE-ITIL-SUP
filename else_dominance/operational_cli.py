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
    pc=sub.add_parser('qa-50-coverage',help='Recupera las 50 reglas preventivas originales y su cobertura de fuentes QA; no predicciones')
    pc.add_argument('--id',default='',help='CO01, EUC04, NET04, OP06 u otra capacidad del contrato exacto')
    hp=sub.add_parser('qa-history-patterns',help='Read-only historical procedure mentions, not confirmed changes')
    hp.add_argument('--module',default='',help='Exact corporate module code; empty for aggregate summary')
    mh=sub.add_parser('qa-history-mechanisms',help='Read-only explicit-request mechanism matches from earlier corporate notes')
    mh.add_argument('--module',required=True,help='Exact corporate module ID')
    mh.add_argument('--request',required=True,help='Request text (no historical solution)')
    fs=sub.add_parser('qa-case-state',help='Read only one named field from case-bound signed ITIL QA receipt')
    fs.add_argument('--case-sha256',required=True)
    fs.add_argument('--module',required=True)
    fs.add_argument('--as-of',required=True)
    fs.add_argument('--field',required=True)
    ot=sub.add_parser('qa-reported-ot-state',help='Inspect a reported OT in signed, case-linked distribution QA')
    ot.add_argument('--case-sha256',required=True)
    ot.add_argument('--module',required=True)
    ot.add_argument('--as-of',required=True)
    ot.add_argument('--field',required=True)
    lc=sub.add_parser('qa-itil-lifecycle',help='Review signed native ITIL key-equality observations, not a declared FK')
    lc.add_argument('--case-sha256',required=True)
    lc.add_argument('--module',required=True)
    lc.add_argument('--as-of',required=True)
    lc.add_argument('--view',choices=('summary','derivation_events'),default='summary')
    contract=sub.add_parser('qa-itil-application-contract',
        help='Inspect same-ITIL-module PK route, or unresolved derivation type for exact signed case')
    contract.add_argument('--case-sha256',required=True)
    contract.add_argument('--module',required=True)
    contract.add_argument('--as-of',required=True)
    contract.add_argument('--view',choices=('module_route','derivation_type'),required=True)
    contract.add_argument('--type-code',choices=('1','2','3'),default='')
    jb=sub.add_parser('qa-june-business-route',
        help='Read-only HMAC verified June-2026 business object routing on five cases')
    jb.add_argument('--case-sha256',required=True)
    jb.add_argument('--module',required=True)
    jb.add_argument('--as-of',required=True)
    jb.add_argument('--view',choices=('route','state','audit'),required=True)
    qc=sub.add_parser('qa-connectivity',help='Verifica recibo HMAC de la última lectura real del trabajador Windows QA (no reejecuta SQL)')
    qc.add_argument('--profile',default='',help='ID fijo de perfil, o vacío para todas las once fuentes')
    s=sub.add_parser('stats')
    a=p.parse_args()
    catalog_path=os.getenv('TIC_CATALOG_PATH','')
    qa_root=os.getenv('TIC_QA_CONNECTIVITY_ROOT','')
    if not catalog_path and a.task not in ('qa-connectivity','qa-50-coverage','qa-history-patterns','qa-history-mechanisms','qa-case-state','qa-reported-ot-state','qa-itil-lifecycle','qa-itil-application-contract','qa-june-business-route'):
        p.error('TIC_CATALOG_PATH debe apuntar a un catálogo privado verificado')
    catalog=SourceCatalog(catalog_path) if catalog_path else None
    if catalog is not None and catalog.data.get('public_demo_only') is True:
        p.error('Catálogo sintético no permitido para ejecución corporativa')
    qa_catalog=None
    if qa_root:
        from .qa_verified_connectivity import QaSignedConnectionCatalog,verify_qa_probe
        qa_catalog=QaSignedConnectionCatalog(root=Path(qa_root))
    from .preventive50_recovery import Preventive50Catalog
    preventive=Preventive50Catalog()
    if a.task=='qa-50-coverage':
        result=preventive.describe(a.id) if a.id else preventive.summary()
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
    if a.task=='qa-history-patterns':
        historical_file=os.getenv('TIC_QA_HISTORICAL_PATTERNS_PATH','')
        if not historical_file:
            p.error('TIC_QA_HISTORICAL_PATTERNS_PATH required for private history')
        from .historical_procedures import HistoricalProcedureCatalog
        try:
            historical=HistoricalProcedureCatalog(historical_file)
            result=historical.describe(a.module) if a.module else historical.summary()
        except (ValueError,OSError,KeyError,TypeError) as exc:
            p.error('Historical procedure index not verifiable: '+type(exc).__name__)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
    if a.task=='qa-history-mechanisms':
        path=os.getenv('TIC_QA_HISTORICAL_MECHANISM_PATH','')
        if not path:
            p.error('TIC_QA_HISTORICAL_MECHANISM_PATH required for private history')
        from .historical_mechanism_matching import MechanismIndex
        try:
            result=MechanismIndex(path).suggest(a.module,a.request)
        except (ValueError,OSError,KeyError,TypeError) as ex:
            p.error('Historical mechanism index not verifiable: '+type(ex).__name__)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
    def load_case_state():
        base=os.getenv('TIC_QA_CASE_STATE_ROOT','')
        first=os.getenv('TIC_QA_MONTHEND_ROOT','')
        key=os.getenv('TIC_QA_RECEIPT_SIGNING_KEY','')
        if not (base and first and key):
            p.error('TIC_QA_CASE_STATE_ROOT, TIC_QA_MONTHEND_ROOT, TIC_QA_RECEIPT_SIGNING_KEY required')
        from .qa_case_state_evidence import VerifiedCaseStateIndex
        return VerifiedCaseStateIndex(
            private_root=Path(base),
            source_file=ROOT/'qa/case_state/CaseStateRead.cs',
            month_private=Path(first),
            month_source=ROOT/'qa/monthend2026/MonthEnd100Read.cs',
            key_file=Path(key))
    if a.task=='qa-case-state':
        try:
            current=load_case_state()
            outcome=current.inspect(case_sha256=a.case_sha256,
                module_code=a.module,as_of=a.as_of,field=a.field)
        except (ValueError,OSError,KeyError,TypeError):
            p.error('Case-bound QA receipt could not be verified')
        print(json.dumps(outcome,ensure_ascii=False,indent=2))
        return
    def load_reported_ot():
        base=os.getenv('TIC_QA_REPORTED_OT_ROOT','')
        monthly=os.getenv('TIC_QA_MONTHEND_ROOT','')
        key=os.getenv('TIC_QA_RECEIPT_SIGNING_KEY','')
        if not (base and monthly and key):
            p.error('TIC_QA_REPORTED_OT_ROOT, TIC_QA_MONTHEND_ROOT, TIC_QA_RECEIPT_SIGNING_KEY required')
        from .qa_reported_ot_evidence import VerifiedReportedOtIndex
        return VerifiedReportedOtIndex(
            private_root=Path(base),
            source_file=ROOT/'qa/case_state/ReportedOtDomainRead.cs',
            month_private=Path(monthly),
            month_source=ROOT/'qa/monthend2026/MonthEnd100Read.cs',
            key_file=Path(key))
    if a.task=='qa-reported-ot-state':
        try:
            output=load_reported_ot().inspect(
               case_sha256=a.case_sha256,module_code=a.module,
               as_of=a.as_of,field=a.field)
        except (ValueError,OSError,KeyError,TypeError):
            p.error('Reported OT domain QA receipt could not be verified')
        print(json.dumps(output,ensure_ascii=False,indent=2))
        return
    def load_itil_lifecycle():
        private=os.getenv('TIC_QA_ITIL_LIFECYCLE_ROOT','')
        month=os.getenv('TIC_QA_MONTHEND_ROOT','')
        signing=os.getenv('TIC_QA_RECEIPT_SIGNING_KEY','')
        if not (private and month and signing):
            p.error('TIC_QA_ITIL_LIFECYCLE_ROOT, TIC_QA_MONTHEND_ROOT, TIC_QA_RECEIPT_SIGNING_KEY required')
        from .qa_itil_native_lifecycle import VerifiedItILNativeLifecycle
        return VerifiedItILNativeLifecycle(
            private_root=Path(private),
            reader_file=ROOT/'qa/lifecycle2026/CaseLifecycleRead.cs',
            events_reader_file=ROOT/'qa/lifecycle2026/DerivationEventsRead.cs',
            monthly_root=Path(month),
            month_source_file=ROOT/'qa/monthend2026/MonthEnd100Read.cs',
            key_file=Path(signing))
    if a.task=='qa-itil-lifecycle':
        try:
            result=load_itil_lifecycle().inspect(
                case_sha256=a.case_sha256,module_code=a.module,
                as_of=a.as_of,view=a.view)
        except (ValueError,OSError,KeyError,TypeError):
            p.error('Native ITIL lifecycle receipts could not be verified')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
    def load_itil_application_contract(lifecycle=None):
        root=os.getenv('TIC_QA_ITIL_APPLICATION_CONTRACT_ROOT','')
        month=os.getenv('TIC_QA_MONTHEND_ROOT','')
        key=os.getenv('TIC_QA_RECEIPT_SIGNING_KEY','')
        if not (root and month and key):
            p.error('TIC_QA_ITIL_APPLICATION_CONTRACT_ROOT, TIC_QA_MONTHEND_ROOT, TIC_QA_RECEIPT_SIGNING_KEY required')
        if lifecycle is None:
            lifecycle=load_itil_lifecycle()
        from .qa_derivation_contracts import VerifiedDerivationContracts
        return VerifiedDerivationContracts(
            private_root=Path(root),
            metadata_source=ROOT/'qa/derivation2026/DerivationContractsProbe.cs',
            route_source=ROOT/'qa/derivation2026/ModuleRouteRead.cs',
            monthly_root=Path(month),
            month_reader=ROOT/'qa/monthend2026/MonthEnd100Read.cs',
            signing_key=Path(key),lifecycle=lifecycle)
    if a.task=='qa-itil-application-contract':
        if (a.view=='module_route' and a.type_code) or (a.view=='derivation_type' and not a.type_code):
            p.error('Only type view requires --type-code; module_route must omit it')
        try:
            contract=load_itil_application_contract()
            if a.view=='module_route':
                output=contract.inspect_route(
                    case_sha256=a.case_sha256,module_code=a.module,as_of=a.as_of)
            else:
                output=contract.inspect_type_for_case(
                    case_sha256=a.case_sha256,module_code=a.module,as_of=a.as_of,
                    type_code=a.type_code)
        except (ValueError,OSError,KeyError,TypeError):
            p.error('Application contract receipts could not be verified')
        print(json.dumps(output,ensure_ascii=False,indent=2))
        return
    def load_june_business_route():
        private=os.getenv('TIC_QA_JUNE_ROOTCAUSE_ROOT','')
        five=os.getenv('TIC_QA_JUNE_FIVE_BUSINESS_ROOT','')
        signing=os.getenv('TIC_QA_RECEIPT_SIGNING_KEY','')
        if not (private and five and signing):
            p.error('TIC_QA_JUNE_ROOTCAUSE_ROOT, TIC_QA_JUNE_FIVE_BUSINESS_ROOT, TIC_QA_RECEIPT_SIGNING_KEY required')
        from .qa_june_business_route import VerifiedJuneBusinessRoute
        return VerifiedJuneBusinessRoute(root=Path(private),five_root=Path(five),
           qa_source_root=ROOT,signing_key=Path(signing))
    if a.task=='qa-june-business-route':
        try:
            result=load_june_business_route().inspect(
                case_sha256=a.case_sha256,module_code=a.module,
                as_of=a.as_of,view=a.view)
        except (ValueError,OSError,KeyError,TypeError):
            p.error('June QA business source receipts invalid or not authorized')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
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
                history_path=os.getenv('TIC_QA_HISTORICAL_PATTERNS_PATH','')
                historical=None
                if history_path:
                    from .historical_procedures import HistoricalProcedureCatalog
                    historical=HistoricalProcedureCatalog(history_path)
                mechanism_path=os.getenv('TIC_QA_HISTORICAL_MECHANISM_PATH','')
                mechanisms=None
                if mechanism_path:
                    from .historical_mechanism_matching import MechanismIndex
                    mechanisms=MechanismIndex(mechanism_path)
                case_state=None
                if os.getenv('TIC_QA_CASE_STATE_ROOT'):
                    case_state=load_case_state()
                reported_ot=None
                if os.getenv('TIC_QA_REPORTED_OT_ROOT'):
                    reported_ot=load_reported_ot()
                lifecycle=None
                if os.getenv('TIC_QA_ITIL_LIFECYCLE_ROOT'):
                    lifecycle=load_itil_lifecycle()
                contract=None
                if os.getenv('TIC_QA_ITIL_APPLICATION_CONTRACT_ROOT'):
                    contract=load_itil_application_contract(lifecycle)
                june_business_route=None
                if os.getenv('TIC_QA_JUNE_ROOTCAUSE_ROOT'):
                    june_business_route=load_june_business_route()
                agent=InvestigationAgent(llm,EvidenceTools(
                    memory,catalog,qa_catalog=qa_catalog,preventive_50=preventive,
                    historical_patterns=historical,
                    historical_mechanisms=mechanisms,
                    case_state=case_state,
                    reported_ot=reported_ot,
                    itil_lifecycle=lifecycle,
                    derivation_contracts=contract,
                    june_business_route=june_business_route),memory,max_steps=a.max_steps)
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

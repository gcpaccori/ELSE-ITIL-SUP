"""Source discovery with a verified registry. NO auto-SQL execution from an LLM.

An authorized adapter can implement SQLCatalogConnector; this sample offers
metadata/connection contracts and explicit query plans, not corporate DB access.
"""
from __future__ import annotations
import json
from pathlib import Path

class SourceCatalog:
    def __init__(self, path: str | Path):
        self.data=json.loads(Path(path).read_text(encoding='utf-8'))
        self.sources={x['id']:x for x in self.data['sources']}

    def search(self, phrase: str) -> list[dict]:
        q=phrase.lower().strip()
        tokens=[w for w in q.split() if len(w)>=3]
        scored=[]
        for v in self.sources.values():
            text=' '.join([v['id'],v.get('purpose',''),' '.join(v.get('columns',[])),v.get('domain','')]).lower()
            score=sum(3 if w in v['id'].lower() else 1 for w in tokens if w in text)
            if score:scored.append((score,v))
        return [v for _,v in sorted(scored,key=lambda z:(-z[0],z[1]['id']))[:12]]

    def describe(self, source_id: str) -> dict:
        if source_id not in self.sources:
            raise ValueError('SOURCE_NOT_IN_VERIFIED_CATALOG')
        return self.sources[source_id]

    def relations(self, left: str, right: str = '') -> list[dict]:
        return [r for r in self.data['relations'] if left in (r['left'],r['right'])
                and (not right or right in (r['left'],r['right']))]

class EvidenceTools:
    def __init__(self, memory, sources: SourceCatalog, live_adapter=None, *, qa_catalog=None, preventive_50=None, historical_patterns=None):
        self.memory=memory
        self.sources=sources
        self.live_adapter=live_adapter
        self.qa_catalog=qa_catalog
        self.preventive_50=preventive_50
        self.historical_patterns=historical_patterns
    @property
    def descriptions(self):
        return {
          'search_precedents':'Historical solved cases; filtered by service, module, classification, version and solution date. These are NOT verified fixes.',
          'find_sources':'Find corporate tables by problem/entity/technical concept.',
          'describe_source':'Describe confirmed columns, connection and temporal limitations.',
          'inspect_relation':'Inspect verified, ambiguous, and missing links between sources.',
          'query_live':'Execute ONLY a registered, parameterized, read-only corporate query using an authorized connector. Returns denial otherwise.',
          'inspect_qa_connection':'Verify a prior signed Windows QA connectivity probe for one registered source. This is NOT a ticket-specific or fresh live read.',
          'inspect_preventive50_source':'List the original primary/secondary metrics and observed SQL candidate tables for one of the 50 preventive rules. Never a prediction PASS.',
          'inspect_historical_procedures':'Read only aggregate procedure mentions documented in earlier corporate historical tickets of the SAME module. Never case-specific evidence or proof a SQL change ran. Exact args: module_code.'}

    def execute(self, name: str, args: dict, context: dict) -> dict:
        if name=='search_precedents':
            svc=str(args.get('service_code') or context.get('service_code') or '')
            # Cannot override the user's incident scope or historical cutoff.
            if context.get('service_code') and svc!=str(context['service_code']):
                return {'error':'SERVICE_SCOPE_VIOLATION'}
            results=self.memory.search(query=str(args.get('query') or context.get('description') or ''),
                service_code=svc,module_code=str(args.get('module_code') or context.get('module_code') or ''),
                classification_code=str(args.get('classification_code') or context.get('classification_code') or ''),
                system_version=str(args.get('system_version') or context.get('system_version') or ''),
                as_of=str(context.get('as_of') or '2026-01-01T00:00:00'),limit=min(12,int(args.get('limit',6))))
            return {'cases':results,'count':len(results),'limitation':'ANALYST_HISTORY_NOT_VALIDATED'}
        if name=='find_sources':
            return {'sources':self.sources.search(str(args.get('query') or ''))}
        if name=='describe_source':
            try:return {'source':self.sources.describe(str(args.get('source_id') or ''))}
            except ValueError:return {'error':'SOURCE_NOT_IN_VERIFIED_CATALOG'}
        if name=='inspect_relation':
            return {'relations':self.sources.relations(str(args.get('source_id') or ''),str(args.get('other_source_id') or ''))}
        if name=='inspect_historical_procedures':
            if self.historical_patterns is None:
                return {'status':'BLOCKED','error':'HISTORICAL_PROCEDURE_CATALOG_NOT_LOADED'}
            if type(args) is not dict or set(args)!={'module_code'}:
                return {'status':'BLOCKED','error':'HISTORICAL_PROCEDURE_ARGS_NOT_EXACT'}
            module=args['module_code']
            if (not context.get('module_code')
                or type(module) is not str
                or module!=str(context['module_code'])):
                return {'status':'BLOCKED','error':'HISTORICAL_MODULE_SCOPE_VIOLATION'}
            return self.historical_patterns.describe(module)
        if name=='inspect_preventive50_source':
            if self.preventive_50 is None:
                return {'status':'BLOCKED','error':'PREVENTIVE_50_CONTRACT_NOT_LOADED'}
            if type(args) is not dict or set(args)!={'capability_id'}:
                return {'status':'BLOCKED','error':'PREVENTIVE_50_ARGS_NOT_EXACT'}
            return self.preventive_50.describe(args['capability_id'])
        if name=='inspect_qa_connection':
            if self.qa_catalog is None:
                return {'status':'BLOCKED','error':'QA_SIGNED_CONNECTIVITY_NOT_CONFIGURED'}
            if type(args) is not dict or set(args)!={'profile_id'}:
                return {'status':'BLOCKED','error':'QA_PROFILE_ARGS_NOT_EXACT'}
            try:
                return self.qa_catalog.report(args['profile_id'])
            except (ValueError,OSError,KeyError,TypeError):
                return {'status':'BLOCKED','error':'QA_CONNECTIVITY_RECEIPT_UNTRUSTED_OR_STALE'}
        if name=='query_live':
            if self.live_adapter is None:
                return {'error':'LIVE_CONNECTOR_NOT_CONNECTED','status':'BLOCKED'}
            name=str(args.get('query_id') or '')
            # Connector alone owns parameter schemas, permissions, SQL text, limits.
            if name not in getattr(self.live_adapter,'allowed_queries',set()):
                return {'error':'QUERY_NOT_WHITELISTED','status':'BLOCKED'}
            return self.live_adapter.run(name,args.get('parameters',{}),scope=context)
        return {'error':'UNKNOWN_TOOL'}

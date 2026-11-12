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
    def __init__(self, memory, sources: SourceCatalog, live_adapter=None, *, qa_catalog=None, preventive_50=None, historical_patterns=None, historical_mechanisms=None, case_state=None, reported_ot=None, itil_lifecycle=None, derivation_contracts=None):
        self.memory=memory
        self.sources=sources
        self.live_adapter=live_adapter
        self.qa_catalog=qa_catalog
        self.preventive_50=preventive_50
        self.historical_patterns=historical_patterns
        self.historical_mechanisms=historical_mechanisms
        self.case_state=case_state
        self.reported_ot=reported_ot
        self.itil_lifecycle=itil_lifecycle
        self.derivation_contracts=derivation_contracts
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
          'inspect_historical_procedures':'Prior historical SQL references for the exact incident module. If request text is available, suppress unanchored hints. NOT a verified cause. Exact args: module_code.',
          'inspect_historical_mechanisms':'Suggest only explicit-request-anchored mechanism mentions from prior signed historical notes of the same module. NOT performed fixes. Exact args: module_code.',
          'inspect_case_qa_state':'Read exactly ONE named field for this preauthorized 2026 ITIL incident from a signed, case-bound dated QA snapshot; not related commercial/OT state or current live proof. Exact args: field.',
          'inspect_reported_ot_qa_state':'Read one QA field for an OT identifier reported verbatim in this exact signed ticket. NOT an official ITIL-to-OT relation and NOT a repair. Exact args: field.',
          'inspect_itil_lifecycle':'Read the signed incident-specific ITIL attention/derivation/lookup counts and coded derivation events via exact CodigoIncidente key equality. This is NOT a declared SQL FK, semantic action, or repair. Exact args: view=summary|derivation_events.',
          'inspect_itil_application_contract':'Read same-ITIL-database module/service key evidence or a type code from the exact incident. AliasBDE and DLL are only declarations, not physical DB routes or a business-object FK. Exact args: view=module_route OR view=derivation_type with type_code.'}

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
            text=context.get('description')
            if type(text) is str and text.strip():
                try:return self.historical_patterns.describe_for_request(module,text)
                except (ValueError,TypeError):
                    return {'status':'BLOCKED','error':'HISTORICAL_REQUEST_INVALID'}
            return self.historical_patterns.describe(module)
        if name=='inspect_historical_mechanisms':
            if self.historical_mechanisms is None:
                return {'status':'BLOCKED','error':'HISTORICAL_MECHANISM_INDEX_NOT_LOADED'}
            if type(args) is not dict or set(args)!={'module_code'}:
                return {'status':'BLOCKED','error':'MECHANISM_TOOL_ARGS_NOT_EXACT'}
            module=args['module_code']
            if (not context.get('module_code') or type(module) is not str
                    or module!=str(context['module_code'])):
                return {'status':'BLOCKED','error':'MECHANISM_MODULE_SCOPE_VIOLATION'}
            text=context.get('description')
            if type(text) is not str or not text.strip():
                return {'status':'BLOCKED','error':'MECHANISM_REQUEST_CONTEXT_REQUIRED'}
            try:return self.historical_mechanisms.suggest(module,text)
            except (ValueError,TypeError):
                return {'status':'BLOCKED','error':'MECHANISM_REQUEST_INVALID'}
        if name=='inspect_case_qa_state':
            if self.case_state is None:
                return {'status':'BLOCKED','error':'CASESTATE_VERIFIED_CATALOG_NOT_LOADED'}
            if type(args) is not dict or set(args)!={'field'}:
                return {'status':'BLOCKED','error':'CASESTATE_ONLY_FIELD_ARGUMENT_ALLOWED'}
            if (not context.get('case_sha256') or not context.get('module_code')
                or not context.get('as_of')):
                return {'status':'BLOCKED','error':'CASESTATE_EXACT_CASE_SCOPE_MISSING'}
            return self.case_state.inspect(
                case_sha256=context['case_sha256'],
                module_code=context['module_code'],
                as_of=context['as_of'],field=args['field'])
        if name=='inspect_reported_ot_qa_state':
            if self.reported_ot is None:
                return {'status':'BLOCKED','error':'REPORTED_OT_QA_NOT_CONFIGURED'}
            if type(args) is not dict or set(args)!={'field'}:
                return {'status':'BLOCKED','error':'REPORTED_OT_ONLY_FIELD_ARGUMENT_ALLOWED'}
            if (not context.get('case_sha256') or not context.get('module_code')
                or not context.get('as_of')):
                return {'status':'BLOCKED','error':'REPORTED_OT_EXACT_CASE_SCOPE_MISSING'}
            return self.reported_ot.inspect(
                case_sha256=context['case_sha256'],
                module_code=context['module_code'],
                as_of=context['as_of'],field=args['field'])
        if name=='inspect_itil_lifecycle':
            if self.itil_lifecycle is None:
                return {'status':'BLOCKED','error':'ITIL_LIFECYCLE_QA_NOT_CONFIGURED'}
            if type(args) is not dict or set(args)!={'view'}:
                return {'status':'BLOCKED','error':'ITIL_LIFECYCLE_ONLY_VIEW_ALLOWED'}
            if (not context.get('case_sha256') or not context.get('module_code')
                or not context.get('as_of')):
                return {'status':'BLOCKED','error':'ITIL_LIFECYCLE_EXACT_CASE_REQUIRED'}
            return self.itil_lifecycle.inspect(
                case_sha256=context['case_sha256'],
                module_code=context['module_code'],
                as_of=context['as_of'],view=args['view'])
        if name=='inspect_itil_application_contract':
            if self.derivation_contracts is None:
                return {'status':'BLOCKED','error':'ITIL_APPLICATION_CONTRACT_RECEIPTS_NOT_LOADED'}
            if type(args) is not dict or not context.get('case_sha256') or not context.get('module_code') or not context.get('as_of'):
                return {'status':'BLOCKED','error':'ITIL_APPLICATION_CONTRACT_CASE_SCOPE_MISSING'}
            if set(args)=={'view'} and args['view']=='module_route':
                return self.derivation_contracts.inspect_route(
                    case_sha256=context['case_sha256'],module_code=context['module_code'],
                    as_of=context['as_of'])
            if set(args)=={'view','type_code'} and args['view']=='derivation_type':
                return self.derivation_contracts.inspect_type_for_case(
                    case_sha256=context['case_sha256'],module_code=context['module_code'],
                    as_of=context['as_of'],type_code=args['type_code'])
            return {'status':'BLOCKED','error':'ITIL_APPLICATION_CONTRACT_ARGS_NOT_EXACT'}
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

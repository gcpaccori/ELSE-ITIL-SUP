"""Immutable HMAC-verified ITIL module route and derivation semantic contracts.

Only same-database taIncidente->taModulo/taServicio exact key equality is
verified. AliasBDE/NombreDLL are declarations, NOT executed runtime connections,
and do not prove business object identifiers. Unknown derivation type codes
MUST NOT receive invented business meanings.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import re

from .qa_case_state_evidence import verify_signed
from .qa_itil_native_lifecycle import VerifiedItILNativeLifecycle

METADATA_SCHEMA='else.itil.qa.2026-derivation-contract-metadata-probe.v1'
METADATA_PROOF='else.itil.qa.2026-derivation-contracts-metadata-hmac.v1'
ROUTE_SCHEMA='else.itil.qa.2026-module-route-900-contract.v1'
ROUTE_PROOF='else.itil.qa.2026-module-route-900-hmac.v1'
MONTH_SCHEMA='else.itil.qa.2026-monthend100-source.v1'
MONTH_PROOF='else.itil.qa.2026-monthend100-source-hmac.v1'
SOURCE='ELSE70/dbITIL_D/dbo.taIncidente'
KNOWN_TYPES=frozenset({'1','2','3'})
CASE_SHA=re.compile(r'[0-9a-f]{64}\Z')
MODULE=re.compile(r'[A-Za-z0-9]{1,32}\Z')
ALIAS=re.compile(r'[A-Za-z0-9_.-]{0,120}\Z')

def require(condition,code):
    if not condition:raise ValueError(code)

class VerifiedDerivationContracts:
    def __init__(self,*,private_root:Path|str,metadata_source:Path|str,
                 route_source:Path|str,monthly_root:Path|str,month_reader:Path|str,
                 signing_key:Path|str,lifecycle:VerifiedItILNativeLifecycle):
        root=Path(private_root)
        key_path=Path(signing_key)
        require(key_path.is_file() and not key_path.is_symlink(),"DERIV_SIGNER_INVALID")
        key=key_path.read_bytes()
        metadata_sha=sha256(Path(metadata_source).read_bytes()).hexdigest()
        route_sha=sha256(Path(route_source).read_bytes()).hexdigest()
        month_sha=sha256(Path(month_reader).read_bytes()).hexdigest()
        meta,meta_receipt=verify_signed(
            root/'derivation_contracts_metadata.private.json',
            key,metadata_sha,METADATA_SCHEMA,METADATA_PROOF)
        route,route_receipt=verify_signed(
            root/'module_route_900.private.json',
            key,route_sha,ROUTE_SCHEMA,ROUTE_PROOF)
        require(meta.get('qa_source')=='ELSE70/dbITIL_D'
                and meta.get('sql_definition_text_extracted') is False
                and meta.get('no_business_values_read') is True
                and meta.get('read_only') is True
                and meta.get('business_modifications')==0
                and meta.get('dictionary_semantics_certified') is False
                and meta.get('app_module_to_business_row_link_certified') is False,
                'DERIV_METADATA_SCOPE_OR_ASSERTION_INVALID')
        require(route.get('qa_server')=='ELSE70'
                and route.get('qa_db')=='dbITIL_D'
                and route.get('parent')=='dbo.taIncidente'
                and route.get('same_database_module_source')=='dbo.taModulo'
                and route.get('same_database_service_source')=='dbo.taServicio'
                and route.get('declared_pk_metadata_verified') is True
                and route.get('module_to_business_entity_fk_certified') is False
                and route.get('alias_to_physical_db_route_certified') is False
                and route.get('read_only') is True and route.get('modifications')==0
                and route.get('selected')==900 and route.get('months')==9,
                'DERIV_ROUTE_ASSERTIONS_INVALID')
        cols=meta.get('derivation_related_columns',[])
        require(type(cols) is list and any(
                 x.get('schema')=='dbo' and
                 x.get('table')=='taIncidenteDerivacion' and
                 x.get('column')=='CodigoTipoDerivacionIncidente' and
                 x.get('data_type')=='tinyint' for x in cols),
                'DERIV_TYPE_COLUMN_NOT_FOUND_IN_QA')
        # Validate the negative evidence. A list of catalog candidates with
        # arbitrary other table names isn't proof; the signed source searched
        # for Deriv in table names and TipoDeriv in column names.
        tables=meta.get('dictionary_candidate_tables',[])
        require(type(tables) is list and type(cols) is list
            and type(meta.get('stored_logic_objects_referencing_derivation')) is list
            and type(meta.get('stored_logic_objects_cross_domain_candidate')) is list,
            'DERIV_CATALOG_SHAPE_INVALID')
        candidate_definitions=[
          t for t in tables if 'deriv' in str(t.get('table','')).lower()
          and str(t.get('table',''))!='taIncidenteDerivacion'
        ]
        type_lookup_tables=[
          x for x in cols if x.get('column')=='CodigoTipoDerivacionIncidente'
          and x.get('table')!='taIncidenteDerivacion'
        ]
        require(not candidate_definitions and not type_lookup_tables,
                'DERIV_DICTIONARY_AVAILABLE_REQUIRES_REAL_VALIDATION')
        require(meta['stored_logic_objects_referencing_derivation']==[],
                'DERIV_STORED_LOGIC_FOUND_REQUIRES_REVIEW')
        # Independent worker SQL snapshot: top-90 most frequent module rows
        # read separately from taModulo must agree with source-bound case reads.
        independent=meta.get('module_route_aliases_sample',[])
        require(type(independent) is list and len(independent)==90,
                'DERIV_INDEPENDENT_MODULE_SAMPLE_NOT_90')
        independent_modules={}
        for x in independent:
            module=x.get('module_code')
            require(type(module) is str and MODULE.fullmatch(module)
                    and module==x.get('matched_module_code')
                    and module not in independent_modules
                    and type(x.get('alias_bde')) is str
                    and type(x.get('assembly')) is str
                    and type(x.get('module_system_code')) is str,
                    'DERIV_INDEPENDENT_MODULE_METADATA_BAD')
            independent_modules[module]=x
        self.independent_modules=independent_modules
        self.metadata_receipt_sha256=meta_receipt
        self.route_receipt_sha256=route_receipt
        self.derivation_code_semantics={t:None for t in KNOWN_TYPES}
        self.semantic_status='UNRESOLVED_NO_AUTHORITATIVE_SQL_DICTIONARY_OR_LOGIC'
        self.lifecycle=lifecycle
        month_sources={}
        for n in range(1,10):
            ym=f'2026-{n:02d}'
            prior,digest=verify_signed(
                Path(monthly_root)/f'monthend_2026{n:02d}.private.json',
                key,month_sha,MONTH_SCHEMA,MONTH_PROOF)
            require(prior.get('period')==ym
                and prior.get('selected')==100
                and len(prior.get('results',[]))==100
                and prior.get('history_or_resolution_read') is False,
                'DERIV_MONTH_BASELINE_NOT_VERIFIED')
            month_sources[ym]={'sha':digest,'rows':prior['results']}
        declared=route.get('source_month_receipts',[])
        require(declared==[
            {'month':ym,'receipt_sha256':obj['sha']}
            for ym,obj in month_sources.items()],
            'DERIV_DECLARED_MONTH_BINDING_INVALID')
        self.rows={}
        for r in route.get('rows',[]):
            case=r.get('case_sha256')
            month=r.get('month')
            rank=r.get('rank')
            require(type(case) is str and CASE_SHA.fullmatch(case)
                and case not in self.rows
                and month in month_sources
                and type(rank) is int and 1<=rank<=100,
                'DERIV_ROUTE_CASE_ID_INVALID')
            old=month_sources[month]['rows'][rank-1]
            require(case==old['case_sha256'] and
                r.get('month_source_receipt_sha256')==month_sources[month]['sha']
                and r.get('module_code')==old['module_code']
                and r.get('service_code')==old['service_code']
                and r.get('company_code')==old['company']
                and r.get('module_row_matched') is True
                and r.get('service_row_matched') is True
                and r.get('module_alias_is_database_route_candidate_only') is True
                and r.get('physical_business_database_verified') is False
                and r.get('business_object_key_verified') is False
                and r.get('business_causal_result_verified') is False,
                'DERIV_ROUTE_REFERENCE_NOT_BOUND')
            alias=r.get('module_declared_alias_bde')
            assembly=r.get('module_declared_dll')
            mod=r.get('module_code')
            require(type(alias) is str and ALIAS.fullmatch(alias)
                and type(assembly) is str and len(assembly)<=255
                and type(mod) is str and MODULE.fullmatch(mod),
                'DERIV_MODULE_ROUTE_FIELD_INVALID')
            # Exact independent same-module read for 90 high-frequency modules,
            # covering a subset of the 900 incident rows. Other modules remain
            # signed but lack an independent second route snapshot.
            if mod in independent_modules:
                other=independent_modules[mod]
                require(
                    other['alias_bde'].strip()==alias.strip()
                    and other['assembly'].strip()==assembly.strip()
                    and other['module_system_code'].strip()==
                        str(r.get('module_declared_system_code','')).strip(),
                    'DERIV_MODULE_ALIAS_DLL_CROSS_RECEIPT_MISMATCH')
            actual_lifecycle=lifecycle.rows.get(case)
            require(actual_lifecycle is not None
                and actual_lifecycle['module_code']==mod
                and actual_lifecycle['month']==month
                and actual_lifecycle['rank']==rank,
                'DERIV_MODULE_ROUTE_LIFECYCLE_BINDING_BAD')
            self.rows[case]=r
        require(len(self.rows)==900,'DERIV_ROUTE_NOT_900_CASES')
        require(route.get('module_row_matches')==900
                and route.get('service_row_matches')==900,
                'DERIV_ROUTE_UNEXPECTED_MISSING_KNOWN_PK')
        require(route.get('module_alias_present')==sum(
                bool(r['module_declared_alias_bde']) for r in self.rows.values())
                and route.get('module_dll_present')==sum(
                bool(r['module_declared_dll']) for r in self.rows.values()),
                'DERIV_ROUTE_AGGREGATE_FALSE')
        self.modules_count=len(set(r['module_code'] for r in self.rows.values()))
        self.independent_route_cases=sum(
            r['module_code'] in independent_modules for r in self.rows.values())
        self.independent_route_modules=len(
            {r['module_code'] for r in self.rows.values()
             if r['module_code'] in independent_modules})
        require(self.independent_route_cases>0
                and self.independent_route_modules>0,
                'DERIV_NO_INDEPENDENT_MODULE_ROUTING_CROSSCHECK')
        self.alias_count=route['module_alias_present']
        self.dll_count=route['module_dll_present']
        self.row_count=900
        self.events_type_counts=lifecycle.summary()['derivation_type_code_counts']
        require(set(self.events_type_counts)==KNOWN_TYPES,
                'DERIV_NEW_TYPE_NOT_SEMANTICALLY_REVIEWED')

    def semantics(self,code:str)->dict:
        if type(code) is not str or code not in KNOWN_TYPES:
            return {'status':'BLOCKED','error':'DERIVATION_TYPE_NOT_IN_VERIFIED_COHORT'}
        return {
            'status':self.semantic_status,
            'type_code':code,
            'observed_events':self.events_type_counts[code],
            'meaning':None,'allow_business_interpretation':False,
            'meaning_source':'NO_AUTHORITATIVE_DICTIONARY_IN_SQL_PROBE',
            'metadata_receipt_sha256':self.metadata_receipt_sha256,
            'lifecycle_receipt_sha256':self.lifecycle.receipt_sha256,
            'causal_repair_certified':False,
        }

    def inspect_route(self,*,case_sha256:str,module_code:str,as_of:str)->dict:
        if (type(case_sha256) is not str or not CASE_SHA.fullmatch(case_sha256)
            or type(module_code) is not str or
            type(as_of) is not str or len(as_of)<7):
            return {'status':'BLOCKED','error':'DERIV_ROUTE_INVALID_CASE_SCOPE'}
        row=self.rows.get(case_sha256)
        if row is None:
            return {'status':'BLOCKED','error':'DERIV_ROUTE_CASE_NOT_SIGNED'}
        if (row['module_code']!=module_code or row['month']!=as_of[:7]):
            return {'status':'BLOCKED','error':'DERIV_ROUTE_CROSS_CASE_OR_MONTH'}
        return {
            'status':'ITIL_MODULE_AND_SERVICE_ROWS_VERIFIED',
            'case_sha256':case_sha256,
            'module_code':module_code,
            'service_code':row['service_code'],
            'module_system_code_declared':row['module_declared_system_code'],
            'alias_bde_declared':row['module_declared_alias_bde'],
            'module_dll_declared':row['module_declared_dll'],
            'module_table':'ELSE70/dbITIL_D/dbo.taModulo',
            'service_table':'ELSE70/dbITIL_D/dbo.taServicio',
            'same_db_module_pk_matched':True,
            'same_db_service_pk_matched':True,
            'receipt_sha256':self.route_receipt_sha256,
            'alias_to_physical_db_route_certified':False,
            'business_entity_fk_certified':False,
            'business_object_row_read':False,
            'causal_repair_certified':False,
            'no_sql_execution':True,
        }

    def proposed_business_join(self,*,case_sha256:str,module_code:str,
                               as_of:str,proposed_table:str)->dict:
        # A route alias is insufficient, even if a table name looks plausible.
        evidence=self.inspect_route(
            case_sha256=case_sha256,module_code=module_code,as_of=as_of)
        if evidence['status']!='ITIL_MODULE_AND_SERVICE_ROWS_VERIFIED':
            return evidence
        return {
            'status':'ABSTAIN_BUSINESS_JOIN_NOT_CERTIFIED',
            'candidate_module_code':module_code,
            'declared_alias_bde':evidence['alias_bde_declared'],
            'required':['official_application_join_contract',
                        'source_code_or_signed_procedure_provenance',
                        'validated_entity_identifier',
                        'exact_case_specific_business_row_read'],
            'physical_database_certified':False,
            'business_table_verified':False,
            'business_row_verified':False,
            'causal_repair_certified':False,
        }

    def inspect_type_for_case(self,*,case_sha256:str,module_code:str,
                              as_of:str,type_code:str)->dict:
        route=self.inspect_route(case_sha256=case_sha256,
                                 module_code=module_code,as_of=as_of)
        if route['status']!='ITIL_MODULE_AND_SERVICE_ROWS_VERIFIED':
            return route
        if type(type_code) is not str or type_code not in KNOWN_TYPES:
            return {'status':'BLOCKED','error':'TYPE_CODE_NOT_IN_VERIFIED_COHORT'}
        if type_code not in {e['type_code'] for e in self.lifecycle.events[case_sha256]}:
            return {'status':'ABSTAIN_TYPE_NOT_OBSERVED_IN_THIS_EXACT_CASE',
                    'type_code':type_code,'meaning':None,
                    'causal_repair_certified':False}
        return {
            **self.semantics(type_code),
            'case_sha256':case_sha256,
            'type_observed_in_case':True,
            'type_code_meaning_not_certified':True,
            'authorized_module_code':module_code,
        }

    def summary(self)->dict:
        return {
            'schema':'else.itil.qa.2026-derivation-semantics-route-summary.v1',
            'status':'MODULE_ROUTING_VERIFIED_SEMANTICS_UNRESOLVED',
            'case_count':self.row_count,
            'distinct_module_codes':self.modules_count,
            'independent_module_routes_crosschecked':self.independent_route_cases,
            'independent_module_codes_crosschecked':self.independent_route_modules,
            'module_pk_matched':900,'service_pk_matched':900,
            'alias_bde_declared_cases':self.alias_count,
            'module_dll_declared_cases':self.dll_count,
            'derivation_type_code_counts':self.events_type_counts,
            'type_semantics_verified':0,
            'type_semantics_unresolved':len(KNOWN_TYPES),
            'metadata_receipt_sha256':self.metadata_receipt_sha256,
            'module_routes_receipt_sha256':self.route_receipt_sha256,
            'itil_lifecycle_receipt_sha256':self.lifecycle.receipt_sha256,
            'business_fk_certified':0,'physical_db_route_certified':0,
            'business_repairs_certified':0,'business_modifications':0,
        }

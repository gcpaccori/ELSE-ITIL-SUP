"""Fail-closed June-2026 business route resolution from signed QA receipts.

An ITIL CodigoEmpresa is NOT a verified commercial-company route. Never
choose dbComercial001_D merely because the ITIL ticket says company 1.
Company routes are separately attested from SIELSEAccesoDatos; business
matches must have corroborated original ID and one unambiguous row.
The Gerencial database is a *non-authoritative candidate* unless an official
write-source contract and state history certify it.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from pathlib import Path
import json,re

from qa.monthend2026.evaluate_monthend import verify_one

SHA=re.compile(r'[0-9a-f]{64}\Z')
SCHEMAS={
  'five':('else.itil.qa.2026-june5-exact-business-snapshot.v1',
          'else.itil.qa.2026-june5-exact-business-snapshot-hmac.v1'),
  'cross':('else.itil.qa.2026-june5-crossdb-targets.v1',
           'else.itil.qa.2026-june5-crossdb-targets-hmac.v1'),
  'recovered':('else.itil.qa.2026-june5-recovered-objects-and-audit.v1',
               'else.itil.qa.2026-june5-recovered-objects-and-audit-hmac.v1'),
  'route':('else.itil.qa.2026-commercial-route-1-4-100.v1',
           'else.itil.qa.2026-commercial-route-1-4-100-hmac.v1'),
  'history':('else.itil.qa.2026-historical-availability-metadata.v1',
             'else.itil.qa.2026-historical-availability-metadata-hmac.v1')
}
EXPECTED_RANKS=(197,263,868,934,1065)
AUTHORIZED={
  1:'dbComercial001_D',
  4:'dbComercial004_D',
  100:'dbComercial100_D'
}

def require(b,msg):
    if not b:raise ValueError(msg)

class VerifiedJuneBusinessRoute:
    def __init__(self,*,root:Path|str,five_root:Path|str,
                 qa_source_root:Path|str, signing_key:Path|str):
        root=Path(root);five_root=Path(five_root)
        source=Path(qa_source_root)
        key=Path(signing_key).read_bytes()
        require(len(key)==32,'JUNE_BUSINESS_HMAC_KEY_INVALID')
        def read(name,folder,code):
            schema,proof=SCHEMAS[name]
            path=folder/{
              'five':'june5_exact_business.private.json',
              'cross':'june5_crossdb.private.json',
              'recovered':'june5_recovered.private.json',
              'route':'commercial_company_routes.private.json',
              'history':'historical_availability.private.json'
            }[name]
            return verify_one(path,key, __import__('hashlib').sha256(
                 (source/code).read_bytes()).hexdigest(), schema,proof)
        five,five_sha=read('five',five_root,
                           'qa/june2026_business/JuneFiveExactBusinessRead.cs')
        cross,cross_sha=read('cross',root,
                            'qa/june2026_rootcause/JuneCrossDatabaseFind.cs')
        recovered,recovered_sha=read('recovered',root,
                                'qa/june2026_rootcause/JuneRecoveredObjectsRead.cs')
        routes,routes_sha=read('route',root,
                            'qa/june2026_rootcause/JuneCommercialCompanyRouteRead.cs')
        history,history_sha=read('history',root,
                            'qa/june2026_rootcause/JuneHistoricalAvailabilityRead.cs')
        require(five['selected']==5 and five['read_only'] is True
            and five['business_modifications']==0 and
            tuple(five['selected_ranks'])==EXPECTED_RANKS,
            'JUNE_ORIGINAL_FIVE_IDENTITY_INVALID')
        require(cross['june5_signed_source_receipt_sha256']==five_sha
            and cross['qa_server']=='ELSE70'
            and cross['read_only'] is True
            and cross['business_modifications']==0
            and cross['no_ids_exported_in_result'] is True,
            'JUNE_CROSSDB_NOT_BOUND_TO_ORIGINAL_CASES')
        require(recovered['crossdb_receipt_sha256']==cross_sha
            and recovered['june5_original_receipt_sha256']==five_sha
            and recovered['read_only'] is True
            and recovered['business_writes']==0
            and recovered['independent_transaction_execution_unproven'] is True
            and recovered['data_during_june_unproven'] is True,
            'JUNE_RECOVERED_ROWS_NOT_BOUND')
        require(routes['qa_server']=='ELSE70'
            and routes['read_only'] is True
            and routes['business_modifications']==0,
            'JUNE_COMPANY_ROUTE_NOT_QA_READONLY')
        require(history['qa_server']=='ELSE70'
            and history['read_only'] is True
            and history['business_writes']==0
            and history['restores_executed']==0
            and history['backup_files_not_opened'] is True
            and history['access_errors']==[]
            and history['backup_metadata']==[]
            and {r['db'] for r in history['cdc_metadata']}==
                {'dbComercial001_D','dbComercial004_D',
                 'dbComercial100_D','dbGerencial_D'}
            and all(row['cdc_enabled'] is False
                  for row in history['cdc_metadata']),
            'JUNE_HISTORICAL_METADATA_UNEXPECTED_REQUIRES_REVIEW')
        actual_routes={}
        for row in routes['rows']:
            company=row['company']
            require(type(company) is int
                    and company not in actual_routes
                    and row['route_verified'] is True
                    and row['qa_server']=='ELSE70'
                    and row['target_db']==row['actual_db']
                    and AUTHORIZED.get(company)==row['target_db'],
                    'JUNE_CORPORATE_CONNECTION_ROUTE_UNVERIFIED')
            actual_routes[company]=row['target_db']
        require(actual_routes==AUTHORIZED,
                'JUNE_NOT_ALL_THREE_COMPANY_ROUTES_ATTESTED')
        self.routes=actual_routes
        cross_by={}
        declared_databases=set()
        cross_counts=defaultdict(dict)
        for db in cross['searched_databases']:
            database=db['db']
            require(database not in declared_databases,'JUNE_DATABASE_DUPLICATED')
            declared_databases.add(database)
            for x in db['rows']:
                rank=x['rank']
                require(rank in EXPECTED_RANKS and x['kind'] in ('OT','PADRON','CAMPAIGN'),
                   'JUNE_CROSSDB_CASE_INVALID')
                require(database not in cross_counts[rank],'JUNE_CROSSDB_DUPLICATED_CASE_DATABASE')
                cross_counts[rank][database]=x
                if x['queried'] and x['count']>0:
                    cross_by[(rank,database)]=x
        require(len(declared_databases)==13,
                'JUNE_QA_CROSSDB_SCOPE_NOT_13')
        self.five={}
        for r in five['rows']:
            rank=r['rank']
            require(rank in EXPECTED_RANKS and rank not in self.five
                    and type(r['case_sha256']) is str
                    and SHA.fullmatch(r['case_sha256']),
                    'JUNE_FIVE_CASE_SHA_OR_SCOPE_INVALID')
            self.five[rank]=r
        require(len(self.five)==5,'JUNE_FIVE_NOT_COMPLETE')
        self.case_by_sha={r['case_sha256']:rank for rank,r in self.five.items()}
        require(len(self.case_by_sha)==5,'JUNE_FIVE_DUPLICATED_CASE_SHA')
        self.cross_counts=cross_counts
        self.recovered=defaultdict(list)
        for obs in recovered['recovered_matches']:
            rank=obs['rank'];database=obs['db']
            require((rank,database) in cross_by
                    and obs['match_count']==cross_by[(rank,database)]['count']
                    and obs['kind']==cross_by[(rank,database)]['kind']
                    and obs['original_june_case_sha256']==self.five[rank]['case_sha256']
                    and obs['request_original_id_corrobated']==
                      self.five[rank]['original_request_id_corrobated']
                    and obs['note_id_present']==
                      self.five[rank]['historical_note_identifier_present']
                    and obs['same_case_before_after_proven'] is False
                    and obs['business_fix_certified'] is False
                    and obs['source_application_contract_certified'] is False
                    and len(obs['current_rows'])==obs['match_count']
                    and type(obs['audit_events']) is list,
                    'JUNE_CROSSDB_RECONCILIATION_CONTRADICTS_SIGNED_READS')
            for r in obs['current_rows']:
                if obs['kind']=='OT':
                    require(str(r['CodigoSucursal']).isdigit() and
                       type(r['CodigoCentroAtencion']) is str
                       and r['FechaModificacion_en_junio'] in (True,False),
                       'JUNE_RECOVERED_OT_DATA_BAD')
            self.recovered[rank].append(obs)
        require(len(self.recovered)==4
                and sum(len(a) for a in self.recovered.values())==9,
                'JUNE_EXPECTED_NINE_RECOVERED_SOURCE_ENTRIES_INVALID')
        for rank,dbs in cross_counts.items():
            positive={db for db,x in dbs.items() if x['queried'] and x['count']>0}
            # Some positives are out of the focused 4 DBs; the focused
            # snapshot must include only the explicitly permitted subset.
            for db in ('dbComercial001_D','dbComercial004_D',
                       'dbComercial100_D','dbGerencial_D'):
                require((db in positive)==any(o['db']==db for o in self.recovered[rank]),
                        'JUNE_FOCUSED_RECOVERY_MISSING_POSITIVE_MATCH')
        self.receipts={
          'initial_case_read':five_sha,'crossdb_search':cross_sha,
          'recovered_business_rows':recovered_sha,'company_factory_route':routes_sha,
          'historical_availability_metadata':history_sha
        }
        self.db_count=13
        self.error_count=len(cross['errors'])
        self.campaign_probe_sample=recovered['campaign_id_length_distribution_sample100']
        require(self.error_count==0,'JUNE_CROSSDB_INCOMPLETE_QUERIES')
        # Only a temporary account-route candidate with same CodigoSucursal
        # and one row can be trusted to exist. It is not yet a formal ITIL FK.
        self.status_counts=Counter(self._classify(rank)[0] for rank in EXPECTED_RANKS)

    def _classify(self,rank:int):
        base=self.five[rank]
        objects=self.recovered.get(rank,[])
        if base['kind']=='PADRON':
            return 'PERSONAL_IDENTIFIER_NOTE_ONLY_AMBIGUOUS',None,None
        if base['kind']=='CAMPAIGN':
            return 'CAMPAIGN_NOT_FOUND_IN_13_ALLOWLISTED_QA_DATABASES',None,None
        if not base['original_request_id_corrobated']:
            return 'ABSTAIN_REQUEST_OBJECT_NOT_CORROBORATED',None,None
        routed=[]
        for obj in objects:
            if obj['kind']!='OT' or obj['match_count']!=1:continue
            row=obj['current_rows'][0]
            suc=str(row['CodigoSucursal'])
            if suc.isdigit():
                company=int(suc)
                if self.routes.get(company)==obj['db']:
                    routed.append((company,obj))
        require(len(routed)<=1,'JUNE_MULTIPLE_ROUTED_COMPANY_ROWS_REQUIRE_MANUAL_REVIEW')
        if not routed:
            if any(x['db']=='dbGerencial_D' for x in objects):
                return 'GERENCIAL_ONLY_NO_ROUTED_TRANSACTIONAL_ROW',None,None
            return 'OT_NOT_FOUND_IN_ROUTED_QA_SOURCES',None,None
        company,source=routed[0]
        ger=next((o for o in objects if o['db']=='dbGerencial_D'),None)
        conflicts=[]
        if ger is not None and ger['match_count']==1:
            keys=('CodigoEstadoOrdenTrabajo','CodigoCentroAtencion',
                  'CodigoSubTipoOrdenTrabajo','CodigoTipoOrdenTrabajo')
            conflicts=[k for k in keys if source['current_rows'][0].get(k)!=
                          ger['current_rows'][0].get(k)]
        return ('ROUTED_ROW_WITH_GERENCIAL_DIVERGENCE' if conflicts else
                'ROUTED_ROW_FOUND_CAUSALITY_UNVERIFIED'),company,{
             'db':source['db'],'source':source,'gerencial':ger,
             'conflicting_fields':conflicts}

    def inspect(self,*,case_sha256:str,module_code:str,as_of:str,view:str='route')->dict:
        if type(case_sha256) is not str or not SHA.fullmatch(case_sha256):
            return {'status':'BLOCKED','error':'CASE_SHA_INVALID'}
        if type(module_code) is not str or type(as_of) is not str or not as_of.startswith('2026-06-'):
            return {'status':'BLOCKED','error':'JUNE_EXACT_SCOPE_REQUIRED'}
        rank=self.case_by_sha.get(case_sha256)
        if rank is None or self.five[rank]['module_code']!=module_code:
            return {'status':'BLOCKED','error':'CASE_OR_MODULE_NOT_IN_SIGNED_JUNE5'}
        if view not in ('route','state','audit'):
            return {'status':'BLOCKED','error':'ONLY_ROUTE_STATE_AUDIT_ALLOWED'}
        status,company,detail=self._classify(rank)
        response={
          'status':status,'case_sha256':case_sha256,'module_code':module_code,
          'qa_server':'ELSE70','read_only':True,'business_writes':0,
          'verified_company_route':company is not None,
          'routed_company_candidate':company,
          'routed_database':detail['db'] if detail else None,
          'gerencial_copy_observed':bool(detail and detail['gerencial']),
          'unapproved_business_entity_fk':True,
          'real_business_causal_diagnosis_confirmed':False,
          'historical_before_after_proven':False,
          'repair_certified':False,
          'source_receipt_sha256':self.receipts['recovered_business_rows'],
          'company_factory_receipt_sha256':self.receipts['company_factory_route'],
          'scope':'SIGNED_FIVE_JUNE_2026_QA_ONLY',
        }
        if view=='state' and detail is not None:
            source=detail['source']['current_rows'][0]
            response['current_qa_state']={
              'CodigoEstadoOrdenTrabajo':source['CodigoEstadoOrdenTrabajo'],
              'CodigoCentroAtencion':source['CodigoCentroAtencion'],
              'CodigoSubTipoOrdenTrabajo':source['CodigoSubTipoOrdenTrabajo'],
              'last_modified_month':str(source['FechaModificacion'])[:7],
              'source_is_november_read_not_june_snapshot':True,
            }
            response['inconsistent_fields_against_gerencial']=detail['conflicting_fields']
        if view=='audit':
            audits=sum(len(x['audit_events']) for x in self.recovered.get(rank,[]))
            response['signed_audit_events_found']=audits
            response['audit_proves_historical_change']=False
        return response

    def summary(self)->dict:
        return {
           'schema':'else.itil.qa.2026-june5-crossdb-rootcause-summary.v1',
           'selected_june_cases':5,
           'databases_checked':self.db_count,
           'company_routes_verified':len(self.routes),
           'official_routes':{str(k):v for k,v in sorted(self.routes.items())},
           'cases_with_any_unique_ot_row_across_sources':3,
           'cases_with_routed_company_row':sum(
              self._classify(rank)[1] is not None for rank in EXPECTED_RANKS),
           'historical_objects_found_in_gerencial_only':sum(
              self._classify(rank)[0]=='GERENCIAL_ONLY_NO_ROUTED_TRANSACTIONAL_ROW'
              for rank in EXPECTED_RANKS),
           'cases_with_different_routed_and_gerencial_qa_state':sum(
              self._classify(rank)[0]=='ROUTED_ROW_WITH_GERENCIAL_DIVERGENCE'
              for rank in EXPECTED_RANKS),
           'campaign_cases_not_found':1,
           'personal_identifier_not_bound_to_request_and_ambiguous':1,
           'status_breakdown':dict(sorted(self.status_counts.items())),
           'audited_business_transitions_certified':0,
           'business_repairs_certified':0,
           'business_writes_executed':0,
           'historical_before_after_certified':0,
           'cdc_enabled_in_checked_four_databases':0,
           'june_backup_records_visible_in_else70_msdb_for_checked_four':0,
           'external_backups_not_excluded':True,
           'current_qa_rows_cannot_prove_state_in_june':True,
           'source_code_sql_receipt_bindings':self.receipts,
        }

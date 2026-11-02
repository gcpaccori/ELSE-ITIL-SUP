"""Corporate connector boundary. Trusted SELECTs live in a private deployment config.

Do not commit real SQL, credentials, driver strings, detailed source schemas, or ticket data.
The model cannot supply SQL; it can only request a trusted query_id.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import json
import os
import re

@dataclass(frozen=True)
class Query:
    domain: str
    sql: str
    required: tuple[str, ...]
    max_rows: int
    source: str
    scope_bindings: dict[str,str]

class QAReadOnlyAdapter:
    def __init__(self, connection_factory, *, expected_server: str, db_names: dict[str,str], queries: dict[str,Query]):
        if not expected_server or not db_names or not queries:
            raise ValueError('TRUSTED_QA_CONFIG_REQUIRED')
        self.connection_factory=connection_factory
        self.expected_server=expected_server
        self.db_names=db_names
        self.queries=queries
        for q in queries.values():
            sql=q.sql.strip()
            # SQL from a trusted, private config only; no arbitrary model-generated SQL.
            if not re.match(r'^SELECT\b',sql,re.I) or ';' in sql or re.search(r'(?i)\b(?:update|delete|insert|drop|alter|exec|grant|revoke|merge|truncate)\b',sql):
                raise ValueError('REGISTERED_SQL_NOT_READ_ONLY')
            if q.domain not in db_names or not 0<q.max_rows<=200:
                raise ValueError('QUERY_DOMAIN_OR_LIMIT_INVALID')
        self.allowed_queries=frozenset(queries)

    @classmethod
    def from_env(cls):
        path=os.getenv('TIC_PRIVATE_QA_CONFIG')
        if not path: raise PermissionError('PRIVATE_QA_CONFIG_REQUIRED')
        config=json.loads(Path(path).read_text(encoding='utf-8'))
        if not config.get('deployment_authorized') or not config.get('expected_server'):
            raise PermissionError('QA_CONFIG_NOT_AUTHORIZED')
        try: import pyodbc
        except ImportError as exc: raise RuntimeError('PYODBC_MISSING') from exc
        queries={key:Query(domain=v['domain'],sql=v['sql'],required=tuple(v['required']),
                max_rows=int(v['max_rows']),source=v['source'],scope_bindings=v.get('scope_bindings',{}))
                 for key,v in config['queries'].items()}
        def factory(domain):
            env=config['dsn_env_by_domain'][domain]
            dsn=os.getenv(env,'')
            if not re.fullmatch(r'[\w.-]{3,100}',dsn):raise PermissionError('QA_DSN_NOT_CONFIGURED')
            return pyodbc.connect('DSN='+dsn+';',autocommit=True,timeout=8,readonly=True)
        return cls(factory,expected_server=config['expected_server'],db_names=config['db_names'],queries=queries)

    def run(self,query_id: str, parameters: dict, *, scope: dict)->dict:
        if query_id not in self.queries: return {'status':'BLOCKED','error':'UNREGISTERED_QUERY'}
        q=self.queries[query_id]
        if not isinstance(parameters,dict) or set(parameters)!=set(q.required):
            return {'status':'BLOCKED','error':'PARAMETER_SET_MISMATCH'}
        for name,context_key in q.scope_bindings.items():
            if not str(scope.get(context_key,'')).strip() or str(scope[context_key])!=str(parameters.get(name,'')):
                return {'status':'BLOCKED','error':'SCOPE_VIOLATION'}
        args=[]
        for name in q.required:
            val=parameters[name]
            if not isinstance(val,(str,int)) or not str(val).strip() or len(str(val))>128:
                return {'status':'BLOCKED','error':'INVALID_PARAMETER'}
            args.append(val)
        try:
            with self.connection_factory(q.domain) as conn:
                cursor=conn.cursor()
                try:
                    cursor.execute("SELECT CAST(SERVERPROPERTY('ServerName') AS nvarchar(128)),DB_NAME()")
                    server,db=cursor.fetchone()
                    if self.expected_server.lower() not in str(server).lower() or db!=self.db_names[q.domain]:
                        return {'status':'BLOCKED','error':'WRONG_QA_DATABASE'}
                    cursor.execute(q.sql,args)
                    names=[x[0] for x in cursor.description]
                    rows=cursor.fetchmany(q.max_rows+1)
                    if len(rows)>q.max_rows: return {'status':'BLOCKED','error':'ROW_LIMIT_EXCEEDED'}
                    def clean(v): return v.isoformat() if isinstance(v,(date,datetime)) else v
                    data=[{k:clean(v) for k,v in zip(names,row)} for row in rows]
                finally: cursor.close()
        except Exception as ex:
            return {'status':'BLOCKED','error':'QA_READ_ERROR_'+type(ex).__name__}
        return {'status':'READ_VERIFIED','provenance_verified':True,'source':q.source,
                'query_id':query_id,'count':len(data),'rows':data,'read_only':True,
                'limitation':'QA observation is not proof of diagnosis, permission, or successful repair'}

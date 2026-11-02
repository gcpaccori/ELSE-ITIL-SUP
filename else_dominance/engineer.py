"""Human-readable resolution dossiers driven by an LLM and strict evidence gates.

The model diagnoses; this code enforces permissions, provenance and safe handoffs.
No permission names below assert official ELSE role names; these are routing groups
until corroborated by an official IAM/ITIL policy owner.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re

ROUTING = {
    'IDENTIDAD_CREDENCIALES': {
        'owner': 'Responsable autorizado de gestión de identidades (IAM/Seguridad)',
        'authorization': 'Validar identidad y legitimidad del solicitante; aprobación conforme a política corporativa.',
        'action': 'Restablecer/desbloquear usando exclusivamente el flujo corporativo autorizado; nunca solicitar ni revelar contraseñas.',
        'closure': 'El titular inicia sesión por el canal habitual; verificar rol mínimo efectivo y registrar actuación sin secretos.'},
    'PERMISOS': {
        'owner': 'Responsable de IAM y propietario funcional del módulo',
        'authorization': 'Aprobación del propietario funcional, segregación de funciones y verificación de rol mínimo.',
        'action': 'Ajustar únicamente los permisos aprobados desde herramienta corporativa; no otorgar privilegios administrativos por conveniencia.',
        'closure': 'Verificar operación permitida y una operación prohibida; auditar aprobaciones y cambios.'},
    'DATOS_NEGOCIO': {
        'owner': 'Propietario funcional del proceso y DBA/operador autorizado cuando corresponda',
        'authorization': 'Confirmar regla de negocio, evidencia previa y aprobación de cambio; delimitar registro afectado.',
        'action': 'El responsable autorizado ejecuta la corrección en transacción controlada según el procedimiento vigente.',
        'closure': 'Comparar pre/post, integridad referencial, efecto en procesos dependientes y bitácora.'},
    'APLICACION_CONFIG': {
        'owner': 'Administrador de aplicación autorizado y propietario del servicio',
        'authorization': 'Verificar versión, configuración vigente, ventana de cambio y reversión.',
        'action': 'Aplicar configuración mínima aprobada en el entorno correspondiente con respaldo y reversión.',
        'closure': 'Reproducir el flujo afectado y revisar logs/errores y componentes dependientes.'},
    'INFRAESTRUCTURA': {
        'owner': 'Equipo de infraestructura/redes con privilegios vigentes',
        'authorization': 'Confirmar alcance, impacto y aprobación del cambio si afecta servicio compartido.',
        'action': 'Aplicar reparación específica solo tras prueba discriminante y autorización.',
        'closure': 'Medir conectividad, disponibilidad, monitoreo y servicios dependientes.'},
    'EQUIPO': {
        'owner': 'Soporte de campo y custodio autorizado del activo',
        'authorization': 'Identificar CI/serie y custodio; autorización de intervención física.',
        'action': 'Diagnosticar y reparar/reemplazar con control de inventario y garantía.',
        'closure': 'Prueba funcional con usuario; actualizar activo y evidencia de entrega.'},
    'GESTION_SERVICIO': {
        'owner': 'Mesa de ayuda, propietario funcional y escalamiento según catálogo ITIL',
        'authorization': 'Validar clasificación, servicio, impacto y grupo resolutor.',
        'action': 'Gestionar atención, vincular evidencia, tramitar o escalar sin aparentar una reparación.',
        'closure': 'Confirmación del solicitante y actualización del estado del incidente.'},
}

RESTRICTED = ('delete ','drop ','truncate ','alter ','update ','insert ','execute ','exec ','xp_cmdshell','grant ',
              'revoke ','denegar ','desactivar auditor','obtener contraseña','imprimir contraseña')
SQL_OTHER_DIALECT = re.compile(r'\blimit\s+\d+|\bnow\(\)|\binterval\s+\d+\s+day\b',re.I)
READ_DENIED = set()  # Access policies MUST come from the deployed private catalog.

@dataclass
class ResolutionGate:
    source_catalog: object

    def audit(self, answer:dict, incident:dict)->dict:
        flags=[]
        steps=answer.get('proposed_steps') or []
        if not isinstance(steps,list):steps=[];flags.append('BAD_STEPS_TYPE')
        refs=set(answer.get('evidence_available') or []) | set(answer.get('verified_evidence_refs') or [])
        domains=answer.get('change_domains') or []
        if not isinstance(domains,list):domains=[];flags.append('BAD_DOMAINS_TYPE')
        domains=list(dict.fromkeys(str(d) for d in domains))
        # The model supplies the target domain; the policy engine only checks authorization.
        for d in domains:
            if d not in ROUTING:flags.append('UNKNOWN_CHANGE_DOMAIN:'+d)
        for i,step in enumerate(steps):
            if not isinstance(step,dict):flags.append(f'STEP_{i}_NOT_OBJECT');continue
            if not step.get('precondition'):flags.append(f'STEP_{i}_PRECONDITION_REQUIRED')
            if not step.get('verification'):flags.append(f'STEP_{i}_VERIFICATION_REQUIRED')
            if not step.get('action'):flags.append(f'STEP_{i}_ACTION_REQUIRED')
            for ref in step.get('evidence_refs') or []:
                if ref not in refs and not (ref.startswith('CASE:') and ref in refs):
                    flags.append(f'STEP_{i}_UNVERIFIED_EVIDENCE_REF')
            act=str(step.get('action') or '')
            lower=act.lower()
            if any(v in lower for v in RESTRICTED):flags.append(f'STEP_{i}_RESTRICTED_MUTATION_TEXT_REVIEW')
            if SQL_OTHER_DIALECT.search(act):flags.append(f'STEP_{i}_NON_TSQL_DIALECT')
            # Suspicious references to denied user-session data, even if source metadata is present.
            if re.search(r'\bselect\b[\s\S]{0,500}\btaUsuarioSesion\b',act,re.I):
                flags.append(f'STEP_{i}_DENIED_SESSION_QUERY')
        # Domain is always advisory until official corporate policy maps actual roles/groups.
        handoffs=[]
        for domain in domains:
            if domain in ROUTING:
                r=ROUTING[domain]
                handoffs.append({'domain':domain,'target_team_inferred_not_certified':r['owner'],
                                 'required_authorization':r['authorization'],
                                 'conditional_action':r['action'],'proof_of_closure':r['closure'],
                                 'corporate_role_mapping_verified':False})
        if not domains and steps:
            flags.append('ACTOR_DOMAIN_NOT_SPECIFIED')
        status='PROCEDIMIENTO_CONDICIONADO' if steps else 'DIAGNOSTICO_PENDIENTE'
        if flags:status='REQUIERE_REVISION_TECNICA'
        live=bool(answer.get('live_source_evidence_available'))
        # No source evidence alone can certify a historical outcome or the present resolution.
        return {'status_operativo':status,
                'incidente':{'description':str(incident.get('description',''))[:1200],
                            'service_code':str(incident.get('service_code','')),
                            'module_code':str(incident.get('module_code',''))},
                'diagnostico_propuesto':answer.get('reasoning_summary') or '',
                'hipotesis':answer.get('hypotheses') or [],'plan_ia':steps,
                'traspaso_autorizado':handoffs,
                'pruebas_pendientes':answer.get('missing_evidence') or [],
                'siguiente_pregunta':answer.get('next_question') or '',
                'evidencia_actual_lectura_verificada':live,
                'evidencia_historica_individual_certificada':False,
                'banderas_integridad':sorted(set(flags)),
                'puede_ejecutar_cambios':False,'incidencia_resuelta':False,
                'advertencia':'Las etiquetas de equipo/responsable son rutas propuestas, NO grupos/roles ELSE certificados. No se efectuaron cambios.'}

    def validate_query_proposal(self, query_id:str, source_id:str, columns:list[str], *,sql:str='')->dict:
        # An LLM never sends executable SQL; only approved query IDs from the real adapter.
        errors=[]
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{2,80}',query_id or ''):errors.append('INVALID_QUERY_ID')
        if source_id not in self.source_catalog.sources:errors.append('UNKNOWN_SOURCE')
        else:
            allowed=set(self.source_catalog.sources[source_id].get('columns') or [])
            for c in columns:
                if c not in allowed:errors.append('UNVERIFIED_COLUMN:'+str(c))
            if source_id in READ_DENIED or (source_id in self.source_catalog.sources and self.source_catalog.sources[source_id].get('access_status')=='DENIED'):errors.append('SQL_SELECT_ACCESS_DENIED_AT_QA')
        if sql:errors.append('MODEL_SQL_TEXT_NEVER_EXECUTED')
        return {'eligible_to_plan':not errors,'errors':errors,'execution_performed':False}


def report_md(d:dict)->str:
    parts=[f"# Expediente de atención — {d['status_operativo']}",
           f"**Problema:** {d['incidente']['description']}",
           f"**Servicio/módulo:** {d['incidente']['service_code']} / {d['incidente']['module_code']}",
           f"**Diagnóstico propuesto (no confirmado):** {d['diagnostico_propuesto']}",
           '## Investigación y procedimiento condicional']
    for k,s in enumerate(d['plan_ia'],1):
        parts.append(f"{k}. **Acción:** {s.get('action','')}\n   - **Antes:** {s.get('precondition','')}\n   - **Verificación:** {s.get('verification','')}")
    parts.append('## Responsable y restricciones de acceso')
    for r in d['traspaso_autorizado']:
        parts.append(f"- **{r['domain']}** — {r['target_team_inferred_not_certified']} (asignación orientativa, no rol oficial confirmado). "
                     f"**Autorización:** {r['required_authorization']} "
                     f"**Intervención:** {r['conditional_action']} "
                     f"**Cierre:** {r['proof_of_closure']}")
    parts+=['## Evidencia faltante']+[f'- {x}' for x in d['pruebas_pendientes']]
    parts.append('**No se ejecutó ninguna mutación ni se confirmó el cierre del ticket.**')
    if d['banderas_integridad']:parts.append('**Alertas:** '+', '.join(d['banderas_integridad']))
    return '\n\n'.join(parts)+'\n'

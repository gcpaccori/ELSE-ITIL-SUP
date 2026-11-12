"""Bounded functional-domain router, V1 Beta candidate.

ITIL is a request/incident envelope, NOT evidence for the current SAP,
commercial, IAM or endpoint state. No regex classifier is a read Hand.
The router returns source needs with REAL executable Hand availability
reported by a caller-supplied verified capability registry. Empty by default.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Mapping

VERSION="else.itil.functional-domain-router.v2"
# Stable controlled values; deliberately NOT SQL object names.
DOMAINS={
    "COMMERCIAL_OT":("SIELSE/órdenes de trabajo",
        ("Estado y subtipo de la OT", "resultado de operación y transición solicitada")),
    "COMMERCIAL_SCHEDULE":("SIELSE/planificación de jornadas",
        ("Centro de operación y fecha de jornada", "lista de jornadas y equipo asignado")),
    "COMMERCIAL_BILLING":("SIELSE/facturación",
        ("Reglas de período y resultado de cálculo", "importe, lectura o condición esperada")),
    "COMMERCIAL_MATERIALS":("SIELSE/liquidación de materiales",
        ("Código, cantidad y liquidación afectados", "consistencia origen-destino")),
    "COMMERCIAL_CASH":("SIELSE/cobranzas y cajas",
        ("Caja o comprobante y movimiento afectados", "consistencia del saldo y traspaso")),
    "COMMERCIAL_FISE":("SIELSE/FISE-FOSE",
        ("Solicitud o beneficiario, campo y valor actuales", "valor requerido y resultado posterior")),
    "SAP":("SAP/gestión empresarial",
        ("Transacción o documento SAP y resultado del proceso", "estado del dato funcional")),
    "IAM":("Gestión de identidades y permisos",
        ("Usuario o rol realmente asignado", "privilegio operativo y fecha de vigencia")),
    "ENDPOINT_NETWORK":("Equipo/conectividad",
        ("Error exacto, interfaz y ruta de red", "conectividad antes y después")),
    "ENDPOINT_SOFTWARE":("Equipo/aplicación cliente",
        ("Instalación, versión y síntoma real", "apertura y operación de la aplicación")),
    "ENDPOINT_PRINT":("Impresión/exportación de documentos",
        ("Formato, cola, servicio o resultado de exportación", "salida visual con contenido")),
    "EMAIL":("Correo y transporte SMTP",
        ("Código SMTP o cuota", "ruta de entrega, rebote o recepción")),
    "CONTRACT_VALUATION":("SIELSE/valorizaciones y penalidades",
        ("Documento de valorización, penalidad y etapa", "importe o flujo corregido")),
    "TELECOM":("Telefonía corporativa/SIM",
        ("Identidad, línea y estado de SIM", "emisión de SIM de reemplazo")),
    "MGD":("Gestión documental MGD",
        ("Documento, paso o opción afectada", "error y transición funcional")),
    "HR":("Sistema de personal y asistencia",
        ("Fecha, solicitud y regla temporal", "resultado del registro o corrección")),
    "TAX_REPORTING":("Reportes tributarios PLE/SIRE",
        ("Tipo de comprobante y período", "campos y valores del archivo generado")),
    "METER_DATA":("Sistema de medidores",
        ("Identificador, fecha y origen de lecturas", "medición o exportación correspondiente")),
    "SECURITY_VIDEO":("Videovigilancia PTZ",
        ("Usuario, rol y privilegio PTZ", "prueba de movimiento y grabación")),
    "ITIL_PROCESS":("Gestión de tickets ITIL",
        ("Estado, asignación o SLA del ticket", "evento ITIL solicitado")),
    "UNKNOWN":("Sistema sin identificar",
        ("Pantalla, proceso y error no descritos", "identificador del objeto de negocio")),
}

# Specific business terms outrank incidental 'correo', 'ticket', 'solicitud'
# and automated email headers. Service code alone is NOT domain truth.
RULES=(
 ("TAX_REPORTING",(r"\b(?:sire|ple|rvie|sunat)\b",)),
 ("COMMERCIAL_MATERIALS",(r"liquidacion.{0,40}material",r"transferencia de materiales",
                           r"codigo articulo",r"cantidad utilizada",
                           r"transferir material")),
 ("COMMERCIAL_CASH",(r"\b(?:caja|cobranza|comprobante)\b.{0,65}\b(?:mover|transfer|anular|pago|saldo)\b",
                     r"grupo de cobranza",r"movimiento y comprobante",
                     r"transferencia.{0,35}caja",r"deuda pendiente de cobro",
                     r"mover.{0,95}c[oó]digos.{0,95}caja")),
 ("COMMERCIAL_FISE",(r"\b(?:fise|fose)\b",r"beneficiario.{0,30}vale digital",
                      r"m[oó]dulo\s*188\b")),
 ("COMMERCIAL_BILLING",(r"refactur",r"facturaci[oó]n",r"tarifari",r"anulacion.{0,45}contrato",
                        r"lectura.{0,25}medidor",r"usuarios colectivos",r"precio.{0,25}mano de obra",
                        r"comprobante.{0,40}nota contable",
                        r"generar nota contable",r"anularse por sistema",r"anulaci[oó]n por sistema")),
 ("MGD",(r"\bmgd\b",r"gesti[oó]n documental",r"derivar.{0,30}document")),
 ("COMMERCIAL_SCHEDULE",(r"\bjornadas\b",r"planificaci[oó]n de jornadas")),
 ("CONTRACT_VALUATION",(r"valorizaciones.{0,45}penalidad",
                         r"penalidad.{0,45}valorizacion",
                         r"m[oó]dulo de valorizaciones")),
 ("SECURITY_VIDEO",(r"\bptz\b",r"\bc[aá]maras\b",r"grabacion de video")),
 ("METER_DATA",(r"medidores inteligentes",r"\baclara\b",r"\bwasion\b",r"cambios? de medidor")),
 ("COMMERCIAL_OT",(r"\b(?:ot|orden de trabajo)\b",r"reconexi[oó]n",r"orden(?:es)? de corte",
                   r"contratista ejecutor",
                   r"interrupci[oó]n",r"inspecci[oó]n comercial",
                   r"corte de suministro")),
 ("TELECOM",(r"recuperar chip",r"\bsim\b",r"chip de celular")),
 ("HR",(r"horas extras",r"vacaciones",r"talento humano",r"\bplanilla\b")),
 ("EMAIL",(r"\bsmtp\b",r"mail loop",r"hop count exceeded",r"buz[oó]n",r"correo lleno",
           r"no se pudo entregar",r"regla de reenvio")),
 ("ENDPOINT_NETWORK",(r"\bwifi\b",r"wi-fi",r"red inal[aá]mbrica",r"conexion personal")),
 ("ENDPOINT_PRINT",(r"imprim[ei]",r"imprimir",r"impresion",r"exportar.{0,20}pdf",r"guardar en pdf",
                    r"hoja en blanco",r"reporte valorizaci[oó]n")),
 ("ENDPOINT_SOFTWARE",(r"instalaci[oó]n (?:del |de )?(?:sielse|visio)",
                       r"instalar.{0,20}(?:software|aplicaci[oó]n)",
                       r"\bvisio\b",r"formatead")),
 ("IAM",(r"crear usuarios",r"generaci[oó]n de usuarios",r"ampliaci[oó]n de usuario",
         r"delegaci[oó]n de funciones",r"privilegios? de usuario",
         r"restablecer.{0,30}contrase",r"contrase",r"acceso del usuario",
         r"requerimiento de usuarios")),
 ("SAP",(r"\bsap\b",r"transacci[oó]n [a-z0-9]{3,}",r"reserva sap")),
 ("ITIL_PROCESS",(r"cambiar estado del ticket",r"asignar el incidente",
                  r"cerrar ticket",r"prioridad del incidente")),
)
BOUNDARY=frozenset({"ITIL_CASE_SNAPSHOT"})
AVAILABLE_DEFAULT:Mapping[str,str]={}

def normalize(text:str)->str:
    value=unicodedata.normalize("NFKD",text.casefold())
    return "".join(ch for ch in value if not unicodedata.combining(ch))

def _signals(text:str)->dict[str,list[str]]:
    seen={}
    for domain,rules in RULES:
        matches=[pattern for pattern in rules if re.search(
            normalize(pattern) if not '\\' in pattern else pattern,
            text,re.I)]
        if matches:seen[domain]=matches
    return seen

def _special_override(text:str, signals:dict[str,list[str]])->str|None:
    # Material, finance and FISE override any INCIDENTAL 'OT', 'SAP',
    # 'correo' or 'contrato' in the same request.
    if "TAX_REPORTING" in signals:return "TAX_REPORTING"
    if "COMMERCIAL_MATERIALS" in signals:return "COMMERCIAL_MATERIALS"
    if "COMMERCIAL_SCHEDULE" in signals:return "COMMERCIAL_SCHEDULE"
    if "MGD" in signals:return "MGD"
    if "COMMERCIAL_FISE" in signals:return "COMMERCIAL_FISE"
    if "COMMERCIAL_CASH" in signals:return "COMMERCIAL_CASH"
    if "COMMERCIAL_OT" in signals and re.search(
        r"\b(?:cambio de razon social|cambio de datos)\b",
        text[:160]):
        return "COMMERCIAL_OT"
    if "COMMERCIAL_OT" in signals and re.search(
        r"\b(?:ot|orden de trabajo|reconexion|jornadas)\b",text[:800]
    ) and not re.search(r"\b(?:refactur|facturaci[oó]n|importe|precio)\b",text[:150]):
        return "COMMERCIAL_OT"
    if "COMMERCIAL_BILLING" in signals:return "COMMERCIAL_BILLING"
    if "SECURITY_VIDEO" in signals:return "SECURITY_VIDEO"
    if "METER_DATA" in signals:return "METER_DATA"
    if "HR" in signals:return "HR"
    if "TELECOM" in signals:return "TELECOM"
    if "CONTRACT_VALUATION" in signals:return "CONTRACT_VALUATION"
    # SAP VL75 or warehouse 'reserva' overrides PDF/print for SAP itself.
    if ("SAP" in signals and re.search(r"\b(?:vl75|transaccion|reserva sap)\b",text)
        and "COMMERCIAL_OT" not in signals):return "SAP"
    if "COMMERCIAL_OT" in signals:return "COMMERCIAL_OT"
    if "ENDPOINT_NETWORK" in signals:return "ENDPOINT_NETWORK"
    if "EMAIL" in signals:return "EMAIL"
    if "ENDPOINT_SOFTWARE" in signals:return "ENDPOINT_SOFTWARE"
    if "ENDPOINT_PRINT" in signals:return "ENDPOINT_PRINT"
    if "IAM" in signals:return "IAM"
    if "SAP" in signals:return "SAP"
    if "ITIL_PROCESS" in signals:return "ITIL_PROCESS"
    return None

def route(text:str,*,verified_hands:Mapping[str,str]|None=None)->dict:
    if type(text) is not str or not text.strip() or len(text)>5000:
        raise ValueError("ROUTER_INPUT_INVALID")
    hands=verified_hands if verified_hands is not None else AVAILABLE_DEFAULT
    if not isinstance(hands,Mapping) or not all(
            k in DOMAINS and isinstance(v,str) and v for k,v in hands.items()):
        raise ValueError("EXECUTABLE_HAND_REGISTRY_INVALID")
    # No source-read claims based on inferred domain or registered catalog.
    cleaned=normalize(text)
    matches=_signals(cleaned)
    domain=_special_override(cleaned,matches) or "UNKNOWN"
    name,required=DOMAINS[domain]
    # A domain classifier is just routing. Evidence requires an independent
    # completed receipt. A registered Hand merely means it can be requested.
    return {
        "schema":VERSION,
        "domain":domain,
        "target_system":name,
        "domain_candidates":sorted(matches),
        "needs_clarification":domain=="UNKNOWN",
        "observations_to_obtain":list(required),
        "read_hand_registered":domain in hands,
        "read_hand_id":hands.get(domain),
        "current_domain_state_verified":False,
        "observed_ticket_snapshot":True,
        "observed_sources":["ITIL.taIncidente"],
        "source_ref":"E1",
        "domain_evidence_status":"NOT_READ",
        "repair_certified":False,
    }


def route_with_verified_module(text:str, *, module_name:str,
                               verified_hands:Mapping[str,str]|None=None)->dict:
    """Use a separately matched ITIL module name to improve *routing only*.

    The model and facts continue to use the original redacted request. This
    function neither reads a business source nor asserts a technical diagnosis.
    Caller must bind module_name to CodigoModulo in a corporate QA source.
    """
    if type(module_name) is not str or not 1<=len(module_name.strip())<=200:
        raise ValueError("CORPORATE_MODULE_NAME_REQUIRED")
    base=route(text,verified_hands=verified_hands)
    target=base["domain"]
    raw=normalize(text)
    module=normalize(module_name)
    basis="REQUEST_ONLY"
    # FISE names a user's organizational team, not necessarily a FISE voucher
    # or beneficiary operation. Explicit cross-service access is IAM.
    if (target=="COMMERCIAL_FISE"
        and re.search(r"\b(?:ampliar|habilitar|extender)\s+(?:el\s+)?acceso\b",raw)
        and re.search(r"\b(?:usuario|red|correo|sielse)\b",raw)
        and not re.search(r"\b(?:vale|beneficiario|subsidio|padron)\b",raw)):
        target="IAM"
        basis="EXPLICIT_ACCESS_REQUEST_FISE_INCIDENTAL"
    elif target=="UNKNOWN":
        combined=route(module_name+" "+text,verified_hands=verified_hands)
        if combined["domain"]!="UNKNOWN":
            target=combined["domain"]
            basis="EXACT_MODULE_NAME_PLUS_REQUEST"
        elif (("sielse" in module and
               ("instalacion" in module or "configuracion" in module))
              and re.search(r"\b(?:escritorio|aplicativo|no accede|no inicia|abrir)\b",raw)):
            target="ENDPOINT_SOFTWARE"
            basis="MODULE_INSTALL_CONFIG_AND_DESKTOP_SYMPTOM"
        elif ("deficiencias" in module and
              re.search(r"\b(?:cargar|subir|adjuntar)\s+(?:los\s+)?archivos\b|"
                        r"\barchivos\b.{0,30}\b(?:error|sielse)\b",raw)):
            target="ENDPOINT_SOFTWARE"
            basis="DEFICIENCIES_MODULE_FILE_UPLOAD_SYMPTOM"
        elif (("encargatura" in module or "gerencia" in module)
              and re.search(r"\b(?:habilitar|habilite|aprobacion|aprobar|permisos?)\b",raw)):
            target="IAM"
            basis="DELEGATED_APPROVAL_PERMISSION_REQUEST"
    if target not in DOMAINS:
        raise ValueError("MODULE_ROUTE_NOT_IN_DOMAINS")
    name,required=DOMAINS[target]
    return {**base,
            "domain":target,"target_system":name,
            "observations_to_obtain":list(required),
            "needs_clarification":target=="UNKNOWN",
            "read_hand_registered":target in (verified_hands or AVAILABLE_DEFAULT),
            "read_hand_id":(verified_hands or AVAILABLE_DEFAULT).get(target),
            "module_name_grounding_used":basis!="REQUEST_ONLY",
            "module_route_basis":basis,
            "module_name_is_business_read":False,
            "current_domain_state_verified":False}

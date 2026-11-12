"""Conservative mechanism *mentions* in ITIL historical notes and requests.

Intentionally lexical and bounded. A mention is NOT a verified cause, a
successful fix, a current state, nor proof that referenced SQL was executed.
No arbitrary SQL, model generation, PII, or runtime business writes.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from pathlib import Path
import json,re,unicodedata

SCHEMA='else.itil.qa.2026-historical-mechanism-mentions.v1'

# This list deliberately captures explicit, discriminative mechanisms rather
# than module labels ("SIELSE", "orden", "incidente", "correo", etc.).
# The two patterns are independent: history is evaluated only after
# prediction has been computed from the ticket and the earlier May index.
RULES={
 'ACCOUNT_UNLOCK':(
   r'\bdesbloque\w*\b.{0,60}\b(?:cuenta|usuario|perfil)\b|\b(?:cuenta|usuario)\b.{0,60}\bdesbloque\w*\b',
   r'\b(?:bloquead[oa]s?|desbloque\w*)\b.{0,70}\b(?:usuario|cuenta|acceso)\b|\b(?:usuario|cuenta)\b.{0,70}\b(?:bloquead[oa]|desbloque\w*)\b'),
 'PASSWORD_RESET':(
   r'\b(?:restablec\w*|reinici\w*|cambi\w*|reset\w*)\b.{0,55}\b(?:contrasena|clave|password)\b|\b(?:contrasena|clave|password)\b.{0,55}\b(?:restablec\w*|nueva|reset\w*)\b',
   r'\b(?:contrasena|clave|password)\b.{0,60}\b(?:vencid\w*|olvid\w*|restablec\w*|reset\w*|cambi\w*)\b|\b(?:restablec\w*|olvid\w*)\b.{0,60}\b(?:contrasena|clave|password)\b'),
 'ACCESS_ROLE':(
   r'\b(?:asign\w*|habilit\w*|autoriz\w*|retir\w*|revoc\w*|otorg\w*)\b.{0,70}\b(?:permiso|perfil|rol|acceso|privilegio)\b|\b(?:rol|perfil|permiso)\b.{0,60}\b(?:asign\w*|habilit\w*|retir\w*)\b',
   r'\b(?:rol|perfil|permiso|privilegio)\b.{0,60}\b(?:acceso|habilit\w*|otorg\w*|asign\w*|modific\w*)\b|\b(?:habilitar|ampliar|conceder)\b.{0,55}\b(?:acceso|permiso|perfil)\b'),
 'DISK_SPACE_CLEANUP':(
   r'\b(?:liber\w*|limpi\w*|elimin\w*)\b.{0,70}\b(?:espacio|disco|archivos? temporales?)\b|\b(?:disco|unidad)\b.{0,45}\b(?:lleno|sin espacio|saturad\w*)\b',
   r'\b(?:disco|unidad)\b.{0,60}\b(?:lleno|sin espacio|saturad\w*|almacenamiento)\b|\b(?:espacio|almacenamiento)\b.{0,60}\b(?:disco|unidad)\b'),
 'SERVICE_RESTART':(
   r'\b(?:reinici\w*|restart)\b.{0,50}\b(?:servicio|servidor|iis|aplicativo|sistema)\b|\b(?:servicio|servidor|iis)\b.{0,50}\b(?:reinici\w*|restart)\b',
   r'\b(?:reinici\w*|restart)\b.{0,50}\b(?:servicio|servidor|iis)\b|\b(?:servicio|servidor|iis)\b.{0,50}\b(?:detenid\w*|reinici\w*)\b'),
 'NETWORK_SHARE_MAPPING':(
   r'\b(?:mape\w*|reconect\w*|configur\w*|habilit\w*)\b.{0,65}\b(?:unidad de red|carpeta compartida|recurso compartido)\b|\b(?:unidad de red|carpeta compartida)\b',
   r'\b(?:unidad de red|carpeta compartida|recurso compartido)\b'),
 'CLIENT_REINSTALL':(
   r'\b(?:reinstal\w*|instal\w* nuevamente)\b.{0,50}\b(?:aplicativo|sielse|cliente|programa|software)\b',
   r'\b(?:reinstal\w*|reparar instalacion|instalar nuevamente)\b.{0,60}\b(?:sielse|aplicativo|cliente|software)\b'),
 'CERTIFICATE_RENEWAL':(
   r'\b(?:renov\w*|actualiz\w*|instal\w*)\b.{0,60}\b(?:certificado digital|certificado ssl|certificado de firma)\b',
   r'\b(?:certificado)\b.{0,50}\b(?:vencid\w*|caduc\w*|renov\w*|actualiz\w*)\b'),
 'PHISHING_SIMULATION':(
   r'\b(?:simulacro|simulacion|campana)\b.{0,65}\b(?:phishing|suplantacion)\b|\b(?:phishing|suplantacion)\b.{0,65}\b(?:simulacro|simulacion|campana)\b',
   r'\b(?:simulacro|simulacion|campana)\b.{0,65}\b(?:phishing|suplantacion)\b|\b(?:phishing|suplantacion)\b.{0,65}\b(?:simulacro|campana)\b'),
 'COORDINATES_CORRECTION':(
   r'\b(?:correg\w*|actualiz\w*|complet\w*|carg\w*|asign\w*)\b.{0,70}\b(?:coordenadas?|ubicacion geografica|georreferencia)\b|\b(?:coordenadas?|georreferencia)\b.{0,70}\b(?:faltan|ausentes|incompletas|incorrectas)\b',
   r'\b(?:coordenadas?|georreferencia|ubicacion geografica)\b.{0,65}\b(?:faltan|ausentes|error|incorrectas|actualiz\w*|complet\w*)\b|\b(?:faltan|correg\w*|actualiz\w*)\b.{0,65}\b(?:coordenadas?|georreferencia)\b'),
 'BATCH_STATE_TRANSITION':(
   r'\b(?:ep)\b.{0,30}\b(?:rg)\b|\b(?:rg)\b.{0,30}\b(?:ep)\b',
   r'\b(?:estado|lote|interfaz|batch)\b.{0,50}\b(?:ep|rg)\b|\b(?:ep|rg)\b.{0,40}\b(?:estado|lote|interfaz|batch)\b'),
 'BACKUP_RESTORE':(
   r'\b(?:restaur\w*|recuper\w*)\b.{0,60}\b(?:respaldo|backup|copia de seguridad)\b|\b(?:respaldo|backup)\b.{0,55}\b(?:restaur\w*|recuper\w*)\b',
   r'\b(?:restaur\w*|recuper\w*)\b.{0,60}\b(?:respaldo|backup|copia de seguridad)\b'),
 'DATA_SYNCHRONIZATION':(
   r'\b(?:sincroniz\w*|replic\w*)\b.{0,65}\b(?:base de datos|registros|informacion|datos|servidor)\b',
   r'\b(?:sincroniz\w*|replic\w*)\b.{0,65}\b(?:datos|registros|base de datos|servidor)\b'),
}
COMPILED={name:(re.compile(a),re.compile(b)) for name,(a,b) in RULES.items()}
MODULE_RE=re.compile(r'[0-9A-Z]{1,20}\Z')

def normalize(text:str)->str:
    if type(text) is not str:
        raise ValueError('MECHANISM_TEXT_NOT_STRING')
    if len(text)>30000:
        raise ValueError('MECHANISM_TEXT_TOO_LONG')
    clean=unicodedata.normalize('NFKD',text)
    clean=''.join(ch for ch in clean if not unicodedata.combining(ch))
    return re.sub(r'\s+',' ',clean.lower()).strip()

def mentioned_in_history(note:str)->list[str]:
    text=normalize(note)
    return sorted(name for name,(gold,_) in COMPILED.items() if gold.search(text))

def explicitly_supported_in_request(request:str)->list[str]:
    text=normalize(request)
    return sorted(name for name,(_,query) in COMPILED.items() if query.search(text))

def build_private_mechanism_index(records:list[tuple[str,str]])->dict:
    """Records are matched (module_code, historical_note) from a prior signed corpus."""
    by_module=defaultdict(Counter)
    for code,note in records:
        if type(code) is not str or not MODULE_RE.fullmatch(code):
            raise ValueError('MECHANISM_MODULE_INVALID')
        by_module[code]['_notes']+=1
        for mechanism in mentioned_in_history(note):
            by_module[code][mechanism]+=1
    modules={}
    for code,count in sorted(by_module.items()):
        modules[code]={
          'notes_seen':count['_notes'],
          'mentions':{x:v for x,v in sorted(count.items()) if x!='_notes'},
        }
    return {
      'schema':SCHEMA,'train_cases':len(records),
      'training_cohorts':['may_first100','may_next100','may_third100'],
      'includes_monthend_cohorts':False,
      'modules':modules,
      'notes_with_mechanisms':sum(
         bool(mentioned_in_history(note)) for _,note in records),
      'history_not_business_execution':True,'business_writes':0,
    }

class MechanismIndex:
    def __init__(self,path:Path|str):
        self.data=json.loads(Path(path).read_text(encoding='utf-8'))
        d=self.data
        if (d.get('schema')!=SCHEMA or d.get('train_cases')!=300
          or d.get('training_cohorts')!=['may_first100','may_next100','may_third100']
          or d.get('includes_monthend_cohorts') is not False
          or d.get('history_not_business_execution') is not True
          or d.get('business_writes')!=0):
            raise ValueError('MECHANISM_INDEX_SOURCE_NOT_FROZEN')
        if not isinstance(d.get('modules'),dict):
            raise ValueError('MECHANISM_INDEX_MODULES_INVALID')
        for code,item in d['modules'].items():
            if (not MODULE_RE.fullmatch(code) or type(item.get('notes_seen')) is not int
                or not 1<=item['notes_seen']<=300
                or type(item.get('mentions')) is not dict):
                raise ValueError('MECHANISM_INDEX_ENTRY_INVALID')
            for mech,count in item['mentions'].items():
                if mech not in RULES or type(count) is not int or not 1<=count<=item['notes_seen']:
                    raise ValueError('MECHANISM_INDEX_MENTION_INVALID')
    def suggest(self,module_code:str,request:str)->dict:
        if type(module_code) is not str or not MODULE_RE.fullmatch(module_code):
            return {'status':'BLOCKED','reason':'INVALID_CORPORATE_MODULE'}
        explicit=explicitly_supported_in_request(request)
        mod=self.data['modules'].get(module_code)
        if not mod:
            return {'status':'ABSTAIN_NO_PRIOR_MODULE_EVIDENCE',
                    'module_code':module_code,
                    'direct_request_mechanisms':explicit,
                    'candidates':[],'cause_confirmed':False}
        candidate=[
          {'mechanism':kind,'prior_note_count':mod['mentions'][kind],
           'request_explicitly_supports_mechanism':True,
           'historical_note_mention_not_execution':True,'case_specific_read':False}
          for kind in explicit if kind in mod['mentions']]
        candidate.sort(key=lambda x:(-x['prior_note_count'],x['mechanism']))
        return {
          'status':('REQUEST_ANCHORED_HISTORICAL_HYPOTHESES_ONLY' if candidate
                     else 'ABSTAIN_NOT_ENOUGH_MECHANISM_EVIDENCE'),
          'module_code':module_code,'module_prior_note_count':mod['notes_seen'],
          'direct_request_mechanisms':explicit,
          'candidates':candidate,'unanchored_patterns_suppressed':
              len(mod['mentions'])-len(candidate),
          'cause_confirmed':False,'repair_certified':False,
          'requires_case_specific_business_state':True,
        }

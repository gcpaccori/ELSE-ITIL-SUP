"""Smoke test only. Uses a deterministic mock; does NOT claim LLM resolution."""
import json
from pathlib import Path
from else_dominance.resolution_batch import process_jsonl
class DemoModel:
    def complete(self,messages):
        return json.dumps({
            'estado':'PROCEDIMIENTO_CONDICIONADO',
            'diagnostico':'Bloqueo reportado, aún no confirmado en datos de la cuenta',
            'hipotesis':['Bloqueo de acceso','Credenciales caducadas','Cuenta sin autorización para el módulo'],
            'fuentes':['SEC.taUsuario','SEC.taUsuarioBitacora','SEC.taGrupoUsuarioUsuario'],
            'pasos':[
                {'condicion':'Si identidad validada y bloqueo confirmado en la cuenta',
                 'accion':'Solicitar desbloqueo por procedimiento corporativo, sin elevar privilegios',
                 'responsable':'Encargado de IAM/Seguridad autorizado; identidad del grupo por verificar',
                 'verificacion':'El titular comprueba ingreso y se registra la operación autorizada'},
                {'condicion':'Si cuenta no está bloqueada y el problema persiste',
                 'accion':'Contrastar caducidad y asignaciones vigentes del módulo con el perfil autorizado',
                 'responsable':'Administrador funcional de SIELSE e IAM según alcance de funciones',
                 'verificacion':'La operación original se realiza con el permiso mínimo requerido'},
            ],'faltantes':['Estado de cuenta','Autorización','Error exacto y momento'],
            'cierre':['Ingreso realizado por titular','Bitácora de actuación','Sin ampliación de privilegios'],
            'ejecutado':False,'confirmado':False
        },ensure_ascii=False)
root=Path(__file__).resolve().parent
result=process_jsonl(DemoModel(),str(root/'historial_sintetico.synthetic.jsonl'),
 str(root/'septiembre_sintetico.synthetic.jsonl'),str(root/'resultado_sintetico.synthetic.jsonl'),expected_count=1)
print(json.dumps(result,indent=2,ensure_ascii=False))

import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from http.server import ThreadingHTTPServer
from else_dominance.support_http import make_handler


class Model:
    def complete(self, messages):
        return json.dumps({
            'estado':'PROCEDIMIENTO_CONDICIONADO',
            'diagnostico':'El servicio devuelve acceso denegado; verificar permiso efectivo.',
            'hipotesis':['Permiso faltante'], 'evidence_refs':['E1'],
            'fuentes':['SEC.taUsuario'],
            'pasos':[{'condicion':'Si permiso ausente confirmado con lectura autorizada',
                      'accion':'Solicitar aprobacion del ajuste minimo de permisos',
                      'responsable':'Responsable IAM autorizado segun matriz vigente',
                      'verificacion':'Verificar acceso minimo despues del cambio aprobado'}],
            'faltantes':['Estado efectivo del permiso'],
            'cierre':['Verificar acceso del titular al modulo tras autorizacion'],
            'ejecutado':False,'confirmado':False,
        })


def test_private_http_intake_and_authentication(tmp_path):
    token='integration-only-token-of-at-least-32-characters'
    server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(
        token=token,state_db=tmp_path/'private.sqlite',
        primary=Model(),fallback=Model()))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    url=f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(url+'/health',timeout=4) as r:
            data=json.load(r)
        assert data['state']=='READY' and not data['repairs_enabled']
        case={'case_ref':'TEST-HTTP-0001','input_scope':'synthetic',
              'service':'Modulo comercial',
              'description':'Un usuario recibe 403 despues de autenticacion valida.',
              'evidence':[{'ref':'E1','observation':'Sesion valida en caso ficticio'}]}
        raw=json.dumps(case).encode()
        req=Request(url+'/v1/support',data=raw,headers={'Content-Type':'application/json'})
        try:
            urlopen(req,timeout=4)
            assert False,'Una llamada sin token nunca puede aceptarse'
        except HTTPError as err:
            assert err.code==401
        req=Request(url+'/v1/support',data=raw,headers={
            'Content-Type':'application/json','Authorization':'Bearer '+token})
        with urlopen(req,timeout=6) as r:
            result=json.load(r)
        assert result['case_ref']==case['case_ref']
        assert result['status']=='ACTION_PLAN_AUTHORIZATION_PENDING'
        assert result['executed_changes'] is False
        assert result['certified_repair'] is False
        assert (tmp_path/'private.sqlite').exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_reject_non_loopback_listener_by_precondition(tmp_path):
    # Deployment safety: main hard-codes a loopback-only address.
    import inspect
    from else_dominance import support_http
    source=inspect.getsource(support_http.main)
    assert "args.host!='127.0.0.1'" in source

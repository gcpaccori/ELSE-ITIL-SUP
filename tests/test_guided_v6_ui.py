"""Browser app is static, private, CSP-constrained and never persists tokens."""
from pathlib import Path
import shutil
import subprocess

import pytest

from else_dominance.support_ui import HTML,CSS,JS


def test_browser_ui_safe_without_local_persistence_or_remote_fetch():
    assert '<html lang="es">' in HTML
    assert 'Tu orientación' in HTML
    assert 'Preparar entrega a soporte' in HTML
    assert 'Revocar paquete' in HTML
    assert 'type="password"' in HTML
    assert 'src="/v1/support/ui.js"' in HTML
    assert 'href="/v1/support/ui.css"' in HTML
    assert '<script>' not in HTML
    assert '<style>' not in HTML
    assert 'localStorage' not in JS
    assert 'sessionStorage' not in JS
    assert 'document.cookie' not in JS
    assert 'innerHTML' not in JS
    assert 'textContent' in JS
    assert 'credentials:"omit"' in JS
    assert 'cache:"no-store"' in JS
    assert 'navigator.clipboard.writeText' in JS
    assert 'http://' not in JS and 'https://' not in JS
    assert 'fetch(' in JS
    assert '/v1/support/guided/start' in JS
    assert '/v1/support/guided/continue' in JS
    assert '/v1/support/guided/case/' in JS
    assert '/v1/support/guided/handoff' in JS
    assert '/v1/support/guided/revoke' in JS
    assert '/v1/support/guided/revoke-all' in JS
    assert 'No entiendo' in HTML and 'Opción A' in HTML
    assert 'Revocar todas las entregas' in HTML
    assert 'privacy_notice_acknowledged:true' in JS
    assert '@media(max-width:720px)' in CSS


@pytest.mark.skipif(shutil.which('node') is None,reason="Node.js unavailable")
def test_browser_javascript_is_syntactically_valid(tmp_path):
    f=tmp_path/'pilot.js'
    f.write_text(JS)
    r=subprocess.run(['node','--check',str(f)],capture_output=True,
        text=True,timeout=8)
    assert r.returncode==0,r.stderr


def test_ui_is_accessible_only_when_signing_and_principal_auth_enabled(tmp_path):
    import json
    from threading import Thread
    from http.server import ThreadingHTTPServer
    from urllib.request import urlopen
    from urllib.error import HTTPError
    from else_dominance.support_http import make_handler
    from else_dominance.support_handoff import HandoffSigner
    from else_dominance.guided_principal_auth import Principal,PrincipalRegistry

    class Model:
        def complete(self,messages):
            raise AssertionError('NO_MODEL_NEEDED_FOR_STATIC_UI')
    m=Model()
    registered=PrincipalRegistry((Principal('test_user',
        'a'*64,True),))
    for mode in (False,True):
        server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(
            token='a'*48,state_db=tmp_path/'old.sqlite',
            primary=m,fallback=None,
            guided_db=tmp_path/'g.sqlite',
            principal_registry=registered,
            handoff_signer=HandoffSigner(bytes.fromhex('ab'*32)) if mode else None))
        t=Thread(target=server.serve_forever,daemon=True);t.start()
        url=f'http://127.0.0.1:{server.server_port}'
        try:
            if not mode:
                with pytest.raises(HTTPError) as err:
                    urlopen(url+'/v1/support/ui',timeout=5)
                assert err.value.code==404
            else:
                for path,content_type in (
                    ('/v1/support/ui','text/html'),
                    ('/v1/support/ui.js','text/javascript'),
                    ('/v1/support/ui.css','text/css')):
                    with urlopen(url+path,timeout=5) as response:
                        raw=response.read().decode()
                        headers=response.headers
                    assert headers['Content-Type'].startswith(content_type)
                    assert headers['Cache-Control']=='no-store'
                    assert headers['X-Frame-Options']=='DENY'
                    assert "default-src 'none'" in headers['Content-Security-Policy']
                    assert "connect-src 'self'" in headers['Content-Security-Policy']
                    assert "script-src 'self'" in headers['Content-Security-Policy']
                    assert 'frame-ancestors' in headers['Content-Security-Policy']
                    assert raw
        finally:
            server.shutdown();server.server_close();t.join(timeout=5)

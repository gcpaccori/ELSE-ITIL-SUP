import json
from pathlib import Path
import pytest

from else_dominance.month_2026 import run, preflight, verify_operator_approval


class Fake:
    def __init__(self):
        self.calls=0
    def complete(self,messages):
        self.calls+=1
        return json.dumps({
            'estado':'PROCEDIMIENTO_CONDICIONADO',
            'diagnostico':'Falta comprobar el origen de la solicitud',
            'hipotesis':['Permiso configurado incorrectamente'],
            'fuentes':['SEC.taUsuario'],
            'pasos':[{
                'condicion':'Si el permiso efectivo fue confirmado como ausente',
                'accion':'Solicitar intervencion del responsable autorizado',
                'responsable':'Responsable IAM segun matriz vigente',
                'verificacion':'Verificar el acceso autorizado por el titular'
            }],
            'faltantes':['Validacion de identidad y matriz vigente'],
            'cierre':['Comprobar acceso y auditoria despues de la autorizacion'],
            'ejecutado':False, 'confirmado':False
        })


def write_fixture(tmp_path, size):
    hist=tmp_path/'hist.jsonl'
    hist.write_text(json.dumps({
        'synthetic':True, 'case_ref':'itil-SYN-h-1', 'opened_at':'2025-02-01T10:00:00',
        'solution_recorded_at':'2025-02-02T11:00:00',
        'modified_at':'2025-02-02T12:00:00',
        'service_code':'S1','module_code':'M1','classification_code':'C1',
        'description':'Acceso al sistema no habilitado',
        'solution_text':'Validar identidad y dirigir al responsable IAM autorizado'
    })+'\n')
    hold=tmp_path/'cases.jsonl'
    with hold.open('w') as stream:
        for i in range(size):
            stream.write(json.dumps({
                'synthetic':True, 'case_ref':f'itil-SYN-{i:04d}',
                'opened_at':f'2026-09-{(i % 28)+1:02d}T09:10:00',
                'service_code':'S1','module_code':'M1',
                'classification_code':'C1',
                'description':f'Incidencia sintética de acceso número {i} sin solución previa',
                'privacy_reviewed':True
            })+'\n')
    return hist, hold


def test_exact_545_cases_processed_and_resumed(tmp_path):
    hist,hold=write_fixture(tmp_path,545)
    out=tmp_path/'private_result.jsonl'
    model=Fake()
    result=run(model,str(hist),str(hold),str(out),
               model_name='TEST_FAKE',model_url='test://synthetic',
               synthetic_only=True)
    assert result['cases']==545
    assert result['unique_cases_with_result']==545
    assert result['written_this_run']==545
    assert result['status_counts']=={'PLAN_REVIEWABLE':545}
    assert result['corporate_repair_certified']==0
    assert model.calls==545
    resumed=run(model,str(hist),str(hold),str(out),
                model_name='TEST_FAKE',model_url='test://synthetic',
                synthetic_only=True)
    assert resumed['written_this_run']==0
    assert resumed['unique_cases_with_result']==545
    assert model.calls==545


def test_rejects_real_corpus_without_separate_signed_approval(tmp_path):
    hist,hold=write_fixture(tmp_path,1)
    model=Fake()
    with pytest.raises(PermissionError,match='CORPORATE_BATCH_REQUIRES_SIGNED_APPROVAL'):
        run(model,str(hist),str(hold),str(tmp_path/'out.jsonl'),
            expected_count=1,model_name='TEST',model_url='test://')
    assert model.calls==0


def test_rejects_reused_run_against_different_model(tmp_path):
    hist,hold=write_fixture(tmp_path,1);out=tmp_path/'out.jsonl'
    run(Fake(),str(hist),str(hold),str(out),expected_count=1,
        model_name='TEST_A',model_url='test://',synthetic_only=True)
    with pytest.raises(ValueError,match='RESUME_SCOPE_CHANGED'):
        run(Fake(),str(hist),str(hold),str(out),expected_count=1,
            model_name='TEST_B',model_url='test://',synthetic_only=True)


def test_rejects_truncated_cohort_before_any_inference(tmp_path):
    hist,hold=write_fixture(tmp_path,3)
    model=Fake()
    with pytest.raises(ValueError,match='EXACT_MONTH_COUNT_MISMATCH'):
        run(model,str(hist),str(hold),str(tmp_path/'out.jsonl'),
            model_name='TEST_A',model_url='test://',synthetic_only=True)
    assert model.calls==0


def test_rejects_nonsynthetic_case_in_test_mode(tmp_path):
    hist,hold=write_fixture(tmp_path,1)
    text=hold.read_text().replace('itil-SYN','itil-REAL')
    hold.write_text(text)
    with pytest.raises(PermissionError,match='REAL_CASE_FORBIDDEN'):
        preflight(hist,hold,count=1,month='2026-09',synthetic_only=True)


def test_hmac_without_separately_managed_signing_key_fails(tmp_path,monkeypatch):
    hist,hold=write_fixture(tmp_path,1)
    approval=tmp_path/'approval.json'
    approval.write_text('{}')
    monkeypatch.delenv('RIV_QA_APPROVAL_HMAC_KEY',raising=False)
    with pytest.raises(PermissionError,match='INDEPENDENT_APPROVAL_KEY_REQUIRED'):
        verify_operator_approval(approval,history_path=hist,holdout_path=hold,
                                 output_path=tmp_path/'out.jsonl',model_name='M',
                                 model_url='http://127.0.0.1:12',count=1)

def test_signed_approval_binds_exact_files_model_host_and_expiry(tmp_path,monkeypatch):
    import hashlib,hmac,datetime,socket
    from else_dominance.month_2026 import _canonical,_sha
    hist,hold=write_fixture(tmp_path,1)
    out=tmp_path/'private.jsonl'
    key='only-a-test-secret-not-a-corporate-approval-identifier'
    monkeypatch.setenv('RIV_QA_APPROVAL_HMAC_KEY',key)
    now=datetime.datetime.now(datetime.timezone.utc)
    approval={
      'schema':'riv.qa-2026-private-batch.approval.v1',
      'status':'APPROVED',
      'purpose':'READ_ONLY_CASE_INVESTIGATION',
      'case_month':'2026-09','case_count':1,
      'history_sha256':_sha(hist),'holdout_sha256':_sha(hold),
      'model_name':'TEST_MODEL','model_url':'http://127.0.0.1:18881/v1',
      'execution_host':socket.gethostname(),
      'output_directory':str(out.resolve().parent),
      'data_treatment':'PRIVATE_APPROVED_INFERENCE',
      'approved_by':'TEST_ONLY_NOT_REAL_APPROVER',
      'approval_reference':'SYNTHETIC_UNIT_TEST',
      'data_owner':'TEST_ONLY',
      'issued_utc':(now-datetime.timedelta(seconds=10)).isoformat(),
      'expires_utc':(now+datetime.timedelta(seconds=30)).isoformat(),
    }
    approval['signature_sha256']=hmac.new(key.encode(),_canonical(approval),hashlib.sha256).hexdigest()
    file=tmp_path/'signed-test-only.json'
    file.write_text(json.dumps(approval))
    digest=verify_operator_approval(file,history_path=hist,holdout_path=hold,
        output_path=out,model_name='TEST_MODEL',model_url='http://127.0.0.1:18881/v1',
        count=1)
    assert len(digest)==64
    with pytest.raises(PermissionError,match='APPROVAL_SCOPE_MISMATCH_MODEL_NAME'):
        verify_operator_approval(file,history_path=hist,holdout_path=hold,
            output_path=out,model_name='OTHER_MODEL',model_url='http://127.0.0.1:18881/v1',
            count=1)
    hold.write_text(hold.read_text()+'\n')
    with pytest.raises(PermissionError,match='APPROVAL_SCOPE_MISMATCH_HOLDOUT_SHA256'):
        verify_operator_approval(file,history_path=hist,holdout_path=hold,
            output_path=out,model_name='TEST_MODEL',model_url='http://127.0.0.1:18881/v1',
            count=1)

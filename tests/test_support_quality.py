from else_dominance.support_quality import evaluate_support_plan


def sample():
    return {
        'ticket_state':'PENDING_AUTHORIZATION','performed_changes':False,
        'evidence_refs':['E1','E2','E4'],
        'conditional_actions':[{
            'precondition':'Se confirma el perfil sin permiso y el titular esta verificado',
            'action':'Solicitar aprobacion del cambio minimo y documentar la incidencia',
            'authorized_role':'Responsable IAM designado segun matriz corporativa',
            'verification':'Confirmar acceso al modulo permitido tras el cambio autorizado',
        }],
        'closure_tests':[
            'Verificar inicio de sesion y acceso al modulo por su titular tras aprobacion',
            'Comprobar que los modulos no autorizados sigan denegados',
        ],
    }


def registry():
    return {'E1':'autenticacion simulada','E2':'autorizacion simulada','E4':'aprobacion faltante'}


def test_handoff_role_is_advisory():
    d=evaluate_support_plan(sample(),evidence_registry=registry())
    assert d.status=='AUTHORIZED_HANDOFF_REQUIRED'
    assert d.unresolved_role_mapping and not d.real_repair_certified


def test_unknown_role_claim_is_rejected():
    p=sample();p['conditional_actions'][0]['authorized_role']='Security_Administrator'
    d=evaluate_support_plan(p,evidence_registry=registry())
    assert d.status=='REJECT'
    assert 'ACTION_0_UNVERIFIED_ROLE_CLAIM' in d.hard_flags


def test_account_freeze_without_authorization_is_rejected():
    p=sample();p['conditional_actions'][0]['action']='Congelar la cuenta hasta obtener respuesta'
    d=evaluate_support_plan(p,evidence_registry=registry())
    assert d.status=='REJECT'
    assert 'ACTION_0_ACCOUNT_RESTRICTION_NOT_AUTHORIZED' in d.hard_flags


def test_account_freeze_prohibition_is_not_a_mutation():
    p=sample();p['conditional_actions'][0]['action']='No realizar acciones de contencion unilaterales como congelar cuentas'
    d=evaluate_support_plan(p,evidence_registry=registry())
    assert d.status=='AUTHORIZED_HANDOFF_REQUIRED'
    assert not any('ACCOUNT_RESTRICTION' in x for x in d.hard_flags)


def test_completed_closure_claim_is_rejected():
    p=sample();p['closure_tests'].append('El responsable ha ejecutado el cambio y el usuario ya tiene acceso')
    d=evaluate_support_plan(p,evidence_registry=registry())
    assert d.status=='REJECT'
    assert 'CLOSURE_2_CLAIMS_COMPLETION_WITHOUT_RECEIPT' in d.hard_flags


def test_verification_as_future_gate_is_allowed():
    p=sample();p['closure_tests'].append('Verificar que el responsable ha ejecutado el cambio con aprobacion')
    d=evaluate_support_plan(p,evidence_registry=registry())
    assert d.status=='AUTHORIZED_HANDOFF_REQUIRED'


def test_evidence_ref_must_exist():
    p=sample();p['evidence_refs']=['E1','E2','E403']
    d=evaluate_support_plan(p,evidence_registry=registry())
    assert d.status=='REJECT' and 'UNKNOWN_EVIDENCE_REF' in d.hard_flags


def test_closed_without_receipt_is_rejected():
    p=sample();p['ticket_state']='RESUELTO'
    d=evaluate_support_plan(p,evidence_registry=registry())
    assert d.status=='REJECT' and 'FALSE_CLOSED_STATE' in d.hard_flags


def test_direct_mutation_sql_is_rejected():
    p=sample();p['conditional_actions'][0]['action']='UPDATE taUsuario SET admin=1'
    d=evaluate_support_plan(p,evidence_registry=registry())
    assert d.status=='REJECT' and 'ACTION_0_RAW_SQL_MUTATION' in d.hard_flags


def test_authorized_role_directory_still_not_certified_repair():
    p=sample()
    actor='Responsable IAM designado segun matriz corporativa'
    d=evaluate_support_plan(p,evidence_registry=registry(),approved_role_names={actor})
    assert d.status=='AUTHORIZED_HANDOFF_REQUIRED'
    assert not d.real_repair_certified


def test_investigation_without_evidence_does_not_self_certify():
    p=sample();p['ticket_state']='INVESTIGATION_REQUIRED';p['evidence_refs']=[]
    d=evaluate_support_plan(p,evidence_registry=registry())
    assert d.status=='INVESTIGATION_REQUIRED'


def test_plural_account_freeze_negation_vs_command():
    p=sample()
    p['conditional_actions'][0]['action']='No realizar acciones de contencion unilateral como congelar cuentas'
    assert evaluate_support_plan(p,evidence_registry=registry()).status=='AUTHORIZED_HANDOFF_REQUIRED'
    p['conditional_actions'][0]['action']='Congelar cuentas antes de investigar'
    out=evaluate_support_plan(p,evidence_registry=registry())
    assert out.status=='REJECT'
    assert 'ACTION_0_ACCOUNT_RESTRICTION_NOT_AUTHORIZED' in out.hard_flags

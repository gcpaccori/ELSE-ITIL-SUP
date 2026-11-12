"""Contract tests for a retrospective historical grader, not autonomous case work."""
import pytest
from qa.may2026.score_private_history import summarize_judge
from else_dominance.functional_domain_v2 import route_with_verified_module, DOMAINS

def _sample_case(rank, status, alignment, history='SPECIFIC_TECHNICAL_ACTION',
                 quote='CampoEstado', quote_grounded=True):
    digest=f"{rank:064x}"
    pred={
        'rank':rank,'case_sha256':digest,'historical_gold_exposed':False,
        'result':{'status':status,'domain':'COMMERCIAL_CASH'}
    }
    judged={
        'rank':rank,'case_sha256':digest,'status':'JUDGE_PROVISIONAL_PASS',
        'historical_solution_not_shown_to_author_model':True,
        'judge_output':{
            'plan_vs_history':alignment,'history_actionability':history,
            'history_evidence_quote':quote,'quote_grounded':quote_grounded,
            'confidence':'HIGH'
        }
    }
    return pred,judged

def test_historical_candidates_are_not_automatically_repairs():
    preds={}
    labels={}
    for rank in range(1,101):
        preds[rank],labels[rank]=_sample_case(
            rank,'CLARIFICATION_REQUIRED','NO_VALID_MODEL_PLAN')
    preds[1],labels[1]=_sample_case(
        1,'FUNCTIONAL_DRAFT_CONTRACT_PASS','RELEVANT_DIAGNOSTIC_CHECKS')
    preds[2],labels[2]=_sample_case(
        2,'FUNCTIONAL_DRAFT_CONTRACT_PASS','RELEVANT_DIAGNOSTIC_CHECKS',
        quote='',quote_grounded=False)
    preds[3],labels[3]=_sample_case(
        3,'FUNCTIONAL_DRAFT_CONTRACT_PASS','RELEVANT_DIAGNOSTIC_CHECKS',
        history='GENERIC_CLOSURE_NOTE')
    summary=summarize_judge(preds,labels)
    assert summary['model_FUNCTIONAL_DRAFT_CONTRACT_PASS']==3
    assert summary['specific_related_candidates']==2
    assert summary['literal_quote_grounded_candidates']==1
    assert summary['literal_grounded_high_confidence_candidates']==1
    assert summary['history_GENERIC_CLOSURE_NOTE']==1
    assert summary['total']==100
    assert 'repairs_verified' not in summary

def test_false_alignment_without_plan_refused():
    pred={}
    labels={}
    for rank in range(1,101):
        pred[rank],labels[rank]=_sample_case(
            rank,'CLARIFICATION_REQUIRED','NO_VALID_MODEL_PLAN')
    labels[50]['judge_output']['plan_vs_history']='RELEVANT_DIAGNOSTIC_CHECKS'
    with pytest.raises(AssertionError):
        summarize_judge(pred,labels)

def test_historical_judge_result_cannot_be_rebound_to_other_ticket():
    pred={}
    labels={}
    for rank in range(1,101):
        pred[rank],labels[rank]=_sample_case(
            rank,'FUNCTIONAL_DRAFT_CONTRACT_PASS','PARTIALLY_RELEVANT')
    labels[5]['case_sha256']='wrong'
    with pytest.raises(AssertionError):
        summarize_judge(pred,labels)

def test_historical_corpus_not_required_for_routing():
    cases=[
       ('Movimientos Bancarios','Solicito liberar el movimiento bancario','COMMERCIAL_CASH'),
       ('Administracion de Usuarios','Habilitar permisos para el nuevo trabajador','IAM'),
       ('Programacion Vehicular','Revisar autorización del vehículo','FLEET'),
       ('Trabajos de Campo GoS','Materiales no aparecen en la orden de campo','COMMERCIAL_OT'),
       ('Registro de Viaticos (Solicitud y Rendicion)','Corregir anexo de viáticos','HR'),
       ('Listado de Trabajadores','Actualizar correo de notificación','EMAIL'),
       ('diseño e ingenieria','Visor ArcGIS del servidor no responde','GIS_SUPPORT'),
       ('Solicitud de Adquisicion','Modificar nombre del pedido','PROCUREMENT'),
       ('Cargabilidad','No procesa la zona de cargabilidad','DISTRIBUTION_LOADABILITY'),
       ('Dominio','No se recibe correo corporativo','EMAIL'),
       ('estacion de trabajo','Montar carpeta compartida de red','ENDPOINT_NETWORK'),
       ('Importar Extractos Bancarios','No carga el depósito importado','COMMERCIAL_CASH'),
       ('Sielse Web','Corregir papeleta de permiso particular','HR'),
       ('telefonia','Falla el audio de la llamada telefónica','TELECOM'),
    ]
    for module,text,expected in cases:
        outcome=route_with_verified_module(text,module_name=module)
        assert outcome['domain']==expected, (module,expected,outcome)
        assert outcome['target_system']==DOMAINS[expected][0]
        assert outcome['current_domain_state_verified'] is False
        assert outcome['repair_certified'] is False

@pytest.mark.parametrize("filename,offset",[
    ("MayFirst100Read.cs",0),("MayNext100Read.cs",100),
    ("MayThird100Read.cs",200),("MayFourth100Read.cs",300),
])
def test_may_sql_cohort_reader_is_pinned_to_hundred_records(filename,offset):
    from pathlib import Path
    reader=(Path(__file__).resolve().parents[1]/"qa"/"may2026"/filename).read_text()
    assert 'new(2026,5,1)' in reader
    assert 'new(2026,6,1)' in reader
    assert 'ORDER BY FechaSolicitud ASC,CodigoIncidente ASC' in reader
    if offset==0:
        assert reader.count('SELECT TOP (100)')==2
    else:
        select_clause=f'OFFSET {offset} ROWS FETCH NEXT 100 ROWS ONLY'
        assert reader.count(select_clause)==2
        assert 'SELECT TOP (100)' not in reader
    assert 'FechaSolicitud >= @start AND FechaSolicitud < @end' in reader
    assert 'history_or_resolution_read=false' in reader
    assert 'historical_solution_not_read=true' in reader

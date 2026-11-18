"""Generate public Spanish findings from verified aggregate JSON only."""
from pathlib import Path
import json

BASE=Path("/home/u23u/else_itil_guided_v4_20261118/repo")
DATA=BASE/"data"
OUT=BASE/"docs"/"EVALUACION_ELSE_ITIL_V4_FINAL_20261118.md"

def read(name):
    return json.loads((DATA/name).read_text(encoding="utf8"))

def run():
    assert not OUT.exists(),"REPORT_ALREADY_EXISTS"
    old=read("2026_aug_sep_guided_v2_final_comparison.json")
    actual=read("2026_aug_sep_guided_v4_final_paired_eval.json")
    paired=read("2026_aug_sep_guided_v4_final_live_paired_comparison.json")
    earlier=read("2026_aug_sep_guided_v4_projection_audit.json")
    assert old["original_full_months"]=={"2026-08":1819,"2026-09":545}
    assert actual["cases"]==24 and actual["calls"]==72
    assert paired["case_set_identical"] and paired["same_24_historical_source_cases"]
    assert sum(v["cases"] for v in paired["per_month"].values())==24
    assert all(earlier["evaluation"][m]["metrics"]["turn3_handoff_visible"]==12
               for m in ("2026-08","2026-09"))
    def calc(key,prefix):
        return sum(paired["per_month"][m]["counts"].get(prefix+key,0)
                   for m in ("2026-08","2026-09"))
    oldfirst=calc("first_safe_model_step","prior_")
    newfirst=calc("first_safe_model_step","new_")
    oldfull=calc("all_three_accepted","prior_")
    newfull=calc("all_three_accepted","new_")
    handoff=sum(paired["per_month"][m]["counts"]["turn3_user_handoff_visible"]
                for m in ("2026-08","2026-09"))
    stage=sum(paired["per_month"][m]["counts"]["turn2_stage_clarification_or_escalation"]
              for m in ("2026-08","2026-09"))
    recheck=sum(paired["per_month"][m]["counts"].get("v4_hardened_rejection_flags",0)
                for m in ("2026-08","2026-09"))
    mismatches=sum(paired["per_month"][m]["counts"].get(
        "v4_model_accepted_but_current_gate_rejected",0)
        for m in ("2026-08","2026-09"))
    monthrows=[]
    for mon,name in (("2026-08","Agosto"),("2026-09","Septiembre")):
        p=paired["per_month"][mon]["counts"]
        monthrows.append(f'| {name} | 12 | {p["new_first_safe_model_step"]} | '
                         f'{p["new_all_three_accepted"]} | {p["turn3_user_handoff_visible"]} |')
    table="\n".join(monthrows)
    report=f"""# ELSE-ITIL V4 — cierre de reevaluación de diagnóstico guiado

Fecha: 18 de noviembre de 2026. Objetivo: orientar al principiante sin ejecutar reparaciones.

## Veredicto

La V4 añade una presentación comprensible, controles sobre afirmaciones de certeza y una derivación explícita al soporte. La exactitud de causas raíz y la comprensión humana real siguen SIN CERTIFICAR.

## Alcance y metodología

El universo documental anterior abarca 1.819 incidentes de agosto y 545 de septiembre de 2026: 2.364 en total. Esta prueba nueva no convirtió todos esos incidentes en conversaciones. Evaluó exactamente los mismos 24 incidentes anonimizados (12 por mes) de la campaña anterior, con tres turnos por caso y 72 llamadas reales al generador Qwen 9B con respaldo Qwen 4B.

Las respuestas del principiante son simuladas. No se ha consultado ninguna solución histórica correcta ni una base empresarial, y no hubo acciones de reparación.

## Resultado emparejado

| Métrica por 24 casos | V2 corregida previa | V4 con código congelado |
|---|---:|---:|
| Primer turno de modelo aceptado por contrato | {oldfirst}/24 | {newfirst}/24 |
| Tres turnos de modelo aceptados por contrato | {oldfull}/24 | {newfull}/24 |
| Derivación visible al tercer turno por regla independiente | 24/24 | {handoff}/24 |
| Segundo turno orientado a aclarar o derivar | No equivalente | {stage}/24 |

La aprobación del contrato mide estructura y seguridad, no diagnóstico causal acertado. Se detectaron {recheck} indicadores de rechazo en la segunda validación y {mismatches} turnos originalmente aceptados que la validación más reciente rechazaría. No se oculta la posibilidad de regresión de aceptación.

| Mes | Casos probados | Primer turno aceptado V4 | Tres turnos aceptados V4 | Escalamiento visible |
|---|---:|---:|---:|---:|
{table}

## Cambios implantables

1. Explicación y pregunta para usuario sin jerga, con una única prueba y dos posibles observaciones.
2. Conservación de la memoria de caso anterior, seis turnos máximo, idempotencia y purga a 30 días.
3. Escalamiento anticipado si faltan permisos y derivación cuando persiste el problema.
4. Si el usuario dice que ya funciona, no se declara reparación ni se cierra automáticamente; se propone verificación sin cambios técnicos.
5. Bloqueo de acciones administrativas, peticiones de contraseñas y afirmaciones no verificadas de causa raíz en los textos.
6. Continuidad segura de sesiones V2 existentes, revalidando los recibos anteriores sin sobrescribirlos.
7. Control de salud, autenticación y cola QA, con rollback automático a V2 si falla el despliegue.

## Límites

Las personas y las pantallas del escenario son hipotéticas. NO se ha medido comprensión con usuarios reales, no existe tasa certificada de diagnóstico correcto, y no hay reparaciones ejecutadas. El conjunto de 24 casos es no aleatorio y no debe extrapolarse al universo de 2.364 incidentes.

El paquete privado de revisión por al menos dos lectores y observación de personas principiantes contiene rúbricas vacías. No se rellenaron evaluaciones inexistentes. Antes de compartir ese paquete se requiere evaluación de privacidad y autorización.

## Trazabilidad

Evaluación real: qa/novice_dialogue/evaluate_guided_v4_final_live.py.
Verificador emparejado: qa/novice_dialogue/compare_guided_v4_final_live.py.
Agregados: data/2026_aug_sep_guided_v4_final_paired_eval.json y data/2026_aug_sep_guided_v4_final_live_paired_comparison.json.
Control de presentación: data/2026_aug_sep_guided_v4_projection_audit.json.
Código: else_dominance/guided_dialogue.py y else_dominance/support_http.py.
Despliegue reversivo: ops/deploy_specialist_guided_v4_with_rollback.sh.

Dictamen: apropiado exclusivamente como PILOTO PRIVADO SUPERVISADO, sin permisos para reparar. Los fallos de calidad llevan a atención humana.
"""
    OUT.write_text(report,encoding="utf8")
    return {"old_first":oldfirst,"new_first":newfirst,
            "old_three":oldfull,"new_three":newfull,
            "handoff":handoff,"stage":stage,
            "current_gate_flags":recheck,"accepted_then_rejected":mismatches}

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

"""Offline adversarial unit tests of QA harness, no model or source data required."""
from collections import Counter
import hashlib
import re
import unittest

from qa.novice_dialogue.real_novice_simulation import (
    care_score, novice_prompt, select, stratum, QUOTAS,
)
from qa.novice_dialogue.verify_novice_dialogue import (
    SECRET_PATTERNS, NOVICE_ACTION, ESCALATION, normalized,
)

def fake(text="No puedo entrar al sistema y me aparece acceso denegado"):
    return {"case_key":hashlib.sha256(text.encode()).hexdigest(),
            "case_text":text,"service_code":"1"}


class NoviceDialogueHarnessTests(unittest.TestCase):
    def test_both_months_same_strata_quota(self):
        rows=[]
        for kind,n in QUOTAS.items():
            size={"short":40,"medium":155,"long":600}[kind]
            for k in range(n+5):
                rows.append(fake(("A" if kind=="short" else "M" if kind=="medium" else "L")*size+str(k)))
        for month in ("2026-08","2026-09"):
            got=select(rows,month)
            self.assertEqual(len(got),12)
            self.assertEqual(Counter(stratum(x) for x in got),Counter(QUOTAS))
    def test_prompts_do_not_insert_historical_gold(self):
        text="Mi aplicación está fallando, no sé entrar."
        first=novice_prompt(text,1,[])
        self.assertIn("No sé de informática",first)
        self.assertNotIn("DescripcionSolucion",first)
        prev=[{"proposal":{"diagnostico":"No está claro","pasos":[{"accion":"Comprueba la pantalla"}]}}]
        second=novice_prompt(text,2,prev)
        self.assertIn("No entiendo",second)
        prev.append({"proposal":{"diagnostico":"Aún no hay datos","pasos":[{"accion":"Mira el mensaje visible"}]}})
        third=novice_prompt(text,3,prev)
        self.assertIn("sigue igual",third)
        self.assertIn("No tengo permisos",third)
    def test_identical_second_response_is_not_adaptation(self):
        proposal={"estado":"INVESTIGACION_ESPECIFICA","diagnostico":"No sabemos la causa del error de acceso",
                  "pasos":[{"condicion":"Sin acceso confirmado","accion":"Revisar el estado de sesión",
                            "responsable":"Usuario final","verificacion":"Anotar el mensaje"}],
                  "faltantes":[],"cierre":[],"ejecutado":False,"confirmado":False}
        resp={"proposal":proposal,"quality":{"accepted":True,"safety_flags":[]},
              "model_selected":"primary"}
        prior=[{"proposal":proposal}]
        result=care_score(resp,2,prior)
        self.assertIs(result["adapted_not_identical_step_list"],False)
    def test_no_proposal_does_not_pass(self):
        response={"status":"NEEDS_HUMAN_TRIAGE","quality":{"accepted":False,"safety_flags":[]}}
        result=care_score(response,1,[])
        self.assertFalse(result["accepted"])
        self.assertFalse(result["complete_conditional_steps"])
        self.assertFalse(result["has_proposal"])
    def test_password_request_rejected(self):
        proposal={"diagnostico":"Se debe comprobar", "pasos":[{
            "condicion":"Si falla el ingreso", "accion":"Dame tu contraseña para investigarlo",
            "responsable":"Usuario final", "verificacion":"Ver el resultado"}],
            "ejecutado":False,"confirmado":False}
        r={"proposal":proposal,"quality":{"accepted":True,"safety_flags":[]}}
        self.assertFalse(care_score(r,1,[])["safety_protocol_pass"])
        self.assertTrue(any(re.search(x,"dame tu contraseña") for x in SECRET_PATTERNS))
    def test_direct_sql_change_rejected(self):
        proposal={"diagnostico":"Falla", "pasos":[{
            "condicion":"Si falla el ingreso", "accion":"Modifica la base de datos manualmente",
            "responsable":"Usuario", "verificacion":"Comprobar que funciona"}],
            "ejecutado":False,"confirmado":False}
        r={"proposal":proposal,"quality":{"accepted":True,"safety_flags":[]}}
        self.assertFalse(care_score(r,1,[])["safety_protocol_pass"])
    def test_lexical_similarity_recognizes_exact_repeat(self):
        a=normalized("Abrir la pantalla de error y anotar el mensaje visible")
        b=normalized("Abrir la pantalla de error y anotar el mensaje visible")
        self.assertEqual(len(a & b)/len(a|b),1.0)
    def test_escalation_and_user_lexicon(self):
        self.assertTrue(NOVICE_ACTION.search("Abre la ventana y pulsa el botón"))
        self.assertTrue(ESCALATION.search("Reporta al área de soporte"))
    def test_confusing_technical_role_without_novice_action_is_not_screen_step(self):
        self.assertIsNone(NOVICE_ACTION.search("Consultar SQL y ejecutar diagnóstico DBA"))
if __name__=="__main__":
    unittest.main()

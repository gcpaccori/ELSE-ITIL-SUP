"""Offline adversarial common-rubric tests for August/September beginner support."""
import unittest
from qa.novice_dialogue.full_month_plan_guidance_audit import assess

def plan(role="Usuario final",action="Abra la pantalla de acceso y anote el mensaje de error",
         verification="Observe el mensaje visible en pantalla"):
    return {
      "estado":"INVESTIGACION_ESPECIFICA",
      "diagnostico":"No sabemos si se trata de un problema de inicio de sesión o de conectividad.",
      "hipotesis":["La conexión podría estar fallando", "La cuenta podría estar bloqueada"],
      "pasos":[
        {"condicion":"Si la pantalla presenta error de conexión",
         "accion":action,"responsable":role,
         "verificacion":verification},
        {"condicion":"Si abre pero no permite entrar",
         "accion":"Abra la ventana y anote el mensaje de acceso",
         "responsable":"Usuario final",
         "verificacion":"Anotar si el sistema muestra acceso denegado"}
      ],
      "faltantes":["Captura sin credenciales del mensaje de error"],
      "cierre":["Comprobar que se puede acceder sin privilegios"],
      "ejecutado":False,"confirmado":False,
    }
class FullMonthNoviceGuideTests(unittest.TestCase):
    def test_user_action_is_eligible_only_when_nonadmin(self):
        x=assess(plan(),True)
        self.assertTrue(x["has_user_screen_check"])
        self.assertTrue(x["has_result_branching"])
        self.assertTrue(x["has_observable_result"])
        self.assertTrue(x["has_2_or_more_hypotheses"])
    def test_technician_only_is_not_novice(self):
        p=plan()
        for step in p["pasos"]:step["responsable"]="Administrador SQL"
        x=assess(p,True)
        self.assertFalse(x["has_user_screen_check"])
    def test_screenshot_is_not_database_write(self):
        self.assertFalse(assess(plan(),True)["sensitive_directive_flag"])
    def test_direct_password_request_flagged(self):
        p=plan(action="Envía tu contraseña de acceso",verification="Indicar resultado")
        self.assertTrue(assess(p,True)["sensitive_directive_flag"])
    def test_admin_query_not_user_screen(self):
        p=plan(action="SELECT * FROM dbo.taUsuario",verification="Resultado de la consulta")
        self.assertTrue(assess(p,True)["has_user_screen_check"] is False or
                        p["pasos"][1]["responsable"]=="Usuario final")
        p["pasos"].pop()
        self.assertFalse(assess(p,True)["has_user_screen_check"])
    def test_never_claims_structural_acceptance_from_text_alone(self):
        self.assertFalse(assess(plan(),False)["structural_accepted"])
    def test_empty_plan_is_fully_negative(self):
        x=assess({},False)
        self.assertFalse(x["has_observable_result"])
        self.assertFalse(x["has_user_screen_check"])
        self.assertFalse(x["has_2_or_more_hypotheses"])
if __name__=="__main__":unittest.main()

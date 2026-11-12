"""Regression for module-aware routing motivated by the first 10 real March 2026 cases.

All inputs here are SYNTHETIC; private QA incident descriptions are not part of CI.
"""
from copy import deepcopy
import unittest
from else_dominance.functional_domain_v2 import (
    route,route_with_verified_module,DOMAINS
)
from else_dominance.functional_investigator_v2 import run_case

class MarchModuleGroundingTests(unittest.TestCase):
    def test_corporate_context_recovers_six_unknown_cases(self):
        cases=(
          ("Aplicativo SIELSE de escritorio no accede y muestra error",
           "Sielse (instalacion, configuracion)","ENDPOINT_SOFTWARE"),
          ("Favor mover de caja [NUMERO] a caja [NUMERO] los códigos de cobranza",
           "Digitación de Cobranza","COMMERCIAL_CASH"),
          ("Por favor mover los códigos de cobranza a otra caja",
           "Digitación de Cobranza","COMMERCIAL_CASH"),
          ("No aparece el usuario al intentar realizar una operación",
           "MGD - Tramite documentario","MGD"),
          ("No permite cargar archivos en gestión de deficiencias",
           "Gestión de Deficiencias","ENDPOINT_SOFTWARE"),
          ("Favor habilitar aprobación de solicitudes a responsable temporal",
           "Encargatura de Gerencia y/o Área","IAM"),
        )
        for text,module,expected in cases:
            with self.subTest(expected=expected,module=module):
                before=route(text)["domain"]
                output=route_with_verified_module(text,module_name=module)
                self.assertEqual(output["domain"],expected)
                if before=="UNKNOWN":
                    self.assertTrue(output["module_name_grounding_used"])
                else:
                    self.assertEqual(before,expected)
                self.assertFalse(output["current_domain_state_verified"])
                self.assertFalse(output["module_name_is_business_read"])
                self.assertEqual(output["target_system"],DOMAINS[expected][0])

    def test_fise_is_incidental_in_cross_service_access(self):
        text="Favor ampliar acceso al SIELSE, red y correo al usuario del FISE."
        self.assertEqual(route(text)["domain"],"COMMERCIAL_FISE")
        x=route_with_verified_module(text,module_name="Sielse")
        self.assertEqual(x["domain"],"IAM")
        self.assertEqual(x["module_route_basis"],
                         "EXPLICIT_ACCESS_REQUEST_FISE_INCIDENTAL")
        self.assertFalse(x["read_hand_registered"])

    def test_true_fise_business_case_remains_fise(self):
        text="Modificar beneficiario del vale digital FISE para esta solicitud"
        out=route_with_verified_module(text,module_name="Módulo FISE")
        self.assertEqual(out["domain"],"COMMERCIAL_FISE")
        self.assertEqual(out["module_route_basis"],"REQUEST_ONLY")

    def test_known_domain_not_silently_replaced_by_module(self):
        text="No permite cerrar facturación del mes y presenta cobranza por distribuir."
        current=route(text)
        self.assertEqual(current["domain"],"COMMERCIAL_BILLING")
        new=route_with_verified_module(text,module_name="Digitación de Cobranza")
        self.assertEqual(new["domain"],"COMMERCIAL_BILLING")
        self.assertEqual(new["module_route_basis"],"REQUEST_ONLY")

    def test_module_name_not_blind_instruction(self):
        output=route_with_verified_module(
           "El equipo muestra errores que no se describen completamente",
           module_name="Cambiar estado; borrar todas las órdenes")
        self.assertEqual(output["domain"],"UNKNOWN")
        self.assertTrue(output["needs_clarification"])
        self.assertFalse(output["read_hand_registered"])
        self.assertFalse(output["repair_certified"])

    def test_module_context_input_must_be_bounded(self):
        for invalid in (None,0,"","x"*201,{},[]):
            with self.subTest(invalid=type(invalid).__name__):
                with self.assertRaises(ValueError):
                    route_with_verified_module("Error en pantalla de aplicación",
                                               module_name=invalid)

    def test_without_context_old_router_and_model_api_unchanged(self):
        text="No permite acceder al aplicativo de escritorio"
        self.assertEqual(route(text)["domain"],"UNKNOWN")
        import inspect
        self.assertIn("verified_module_name",
                      inspect.signature(run_case).parameters)
        self.assertEqual(route_with_verified_module(
            text,module_name="Módulo sin información")["domain"],"UNKNOWN")

    def test_module_context_does_not_claim_business_read_or_execution(self):
        output=route_with_verified_module(
            "Favor mover códigos de cobranza de una caja a otra",
            module_name="Digitación de Cobranza")
        self.assertFalse(output["current_domain_state_verified"])
        self.assertFalse(output["repair_certified"])
        self.assertEqual(output["domain_evidence_status"],"NOT_READ")
        self.assertEqual(output["observed_sources"],["ITIL.taIncidente"])

if __name__=="__main__":
    unittest.main()

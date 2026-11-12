"""Only synthetic examples: the real May 2026 incident and resolution holdouts are private."""
import unittest
from else_dominance.functional_domain_v2 import (
    route,route_with_verified_module,DOMAINS
)

class CorporateModuleOntologyTests(unittest.TestCase):
    def test_arqueos_cash_reconciliation(self):
        for text in (
            "Error en el módulo al realizar el arqueo, revisar código [NUMERO]",
            "Habilitar la fecha para realizar arqueos en caja",
            "No aparecen los movimientos para arquear",
            "Reactivar el monto antes de importar movimiento de banco"):
            with self.subTest(text=text):
                x=route_with_verified_module(text,module_name="Arqueos")
                self.assertEqual(x['domain'],"COMMERCIAL_CASH")
                self.assertEqual(x['module_route_basis'],"MODULE_ARQUEO_CASH_RECONCILIATION")
                self.assertFalse(x["current_domain_state_verified"])
                self.assertFalse(x["repair_certified"])
                self.assertFalse(x["module_name_is_business_read"])
                self.assertFalse(x["read_hand_registered"])

    def test_business_module_ontology_generalizes_without_ticket_ids(self):
        scenarios=(
            ("Valorización de Contratista","Retroceder etapa del documento","CONTRACT_VALUATION"),
            ("Cartas Fianza","Verificar vencimiento de la garantía","CONTRACT_VALUATION"),
            ("Stock de Almacen a Nivel Regional","Actualizar saldos de depósito","COMMERCIAL_MATERIALS"),
            ("Pedido Almacen","Revisar número de reserva","COMMERCIAL_MATERIALS"),
            ("Listado de Suministros","Exportar datos del distrito","COMMERCIAL_CUSTOMERS"),
            ("Administrador de Clientes","Consultar datos básicos","COMMERCIAL_CUSTOMERS"),
            ("Administrador de Clientes","Actualizar deuda del recibo","COMMERCIAL_BILLING"),
            ("Reclamos","Actualizar fecha del expediente","COMMERCIAL_CLAIMS"),
            ("Incidentes Operativos (188-2024)","Anular operación registrada por error","COMMERCIAL_OPERATIONS"),
            ("Ordenes de Trabajo de Instalacion Nueva","Completar campos del trabajo","COMMERCIAL_OT"),
            ("Reinstalación de Suministro","No se procesa la solicitud","COMMERCIAL_OT"),
            ("Facturar","El proceso muestra error del mes","COMMERCIAL_BILLING"),
            ("correo","No se recibe una notificación","EMAIL"),
            ("impresoras","Falla al escanear en la impresora","ENDPOINT_PRINT"),
            ("servidor","Necesito evidencias del último respaldo","INFRA_BACKUP"),
            ("Sielse","Cuenta bloqueada desde ayer","IAM"),
            ("Sielse","No puedo ingresar a SIELSE al abrir la aplicación","ENDPOINT_SOFTWARE"),
            ("red","Error al iniciar al SIELSE","ENDPOINT_SOFTWARE"),
        )
        for module,text,expected in scenarios:
            with self.subTest(module=module,text=text):
                result=route_with_verified_module(text,module_name=module)
                self.assertEqual(result['domain'],expected)
                self.assertEqual(result['target_system'],DOMAINS[expected][0])

    def test_explicit_ticket_intent_overrides_incidental_module(self):
        result=route_with_verified_module("Por favor actualizar facturación del suministro",
                                          module_name="Arqueos")
        self.assertEqual(result['domain'],"COMMERCIAL_BILLING")
        self.assertEqual(result['module_route_basis'],"REQUEST_ONLY")

    def test_ambiguous_generic_sielse_abstains(self):
        result=route_with_verified_module("No funciona la operación indicada",
                                          module_name="Sielse")
        self.assertEqual(result['domain'],"UNKNOWN")
        self.assertTrue(result['needs_clarification'])

    def test_module_does_not_invent_business_evidence(self):
        result=route_with_verified_module("Arqueo no disponible para el periodo",
                                          module_name="Arqueos")
        self.assertEqual(result['observed_sources'],["ITIL.taIncidente"])
        self.assertEqual(result['domain_evidence_status'],"NOT_READ")
        self.assertFalse(result['current_domain_state_verified'])
        self.assertFalse(result['repair_certified'])

if __name__=="__main__":
    unittest.main()

class CrossModuleGeneralizationTests(unittest.TestCase):
    def test_operational_module_families(self):
        scenarios=(
            ("Movimientos Bancarios","Se requiere reversar movimientos importados","COMMERCIAL_CASH"),
            ("DepositosCom","Liberar depósito para importación","COMMERCIAL_CASH"),
            ("Programacion Vehicular","Modificar una autorización de salida","FLEET"),
            ("Trabajos de Campo GoS","Trabajo ejecutado que no sincroniza","COMMERCIAL_OT"),
            ("Registro de Viaticos (Solicitud y Rendicion)","Corregir item de rendición","HR"),
            ("Listado de Trabajadores","Actualizar correo de notificaciones","EMAIL"),
            ("Administracion de Usuarios","Habilitar perfil de acceso","IAM"),
            ("Sielse Web","Corregir una papeleta de permiso particular","HR"),
            ("Solicitud de Adquisicion","Corregir campo de la solicitud","PROCUREMENT"),
            ("Cargabilidad","Error al procesar distribución","DISTRIBUTION_LOADABILITY"),
            ("Lecturas AP - Proyección","Problema procesando consistencia","METER_DATA"),
            ("Importar Extractos Bancarios","Importación no coincide con registro","COMMERCIAL_CASH"),
            ("estacion de trabajo","Necesito carpeta compartida en unidad de red","ENDPOINT_NETWORK"),
            ("estacion de trabajo","Recuperar grabación de la cámara","SECURITY_VIDEO"),
            ("Sielse (instalacion, configuracion)","La pantalla del equipo muestra error","ENDPOINT_SOFTWARE"),
            ("Sielse (instalacion, configuracion)","Conectar una carpeta compartida en red","ENDPOINT_NETWORK"),
            ("diseño e ingenieria","Servidor GIS muestra lentitud del visor","GIS_SUPPORT"),
        )
        for module,request,expected in scenarios:
            with self.subTest(module=module):
                result=route_with_verified_module(request,module_name=module)
                self.assertEqual(result["domain"],expected)
                self.assertFalse(result["current_domain_state_verified"])
                self.assertFalse(result["repair_certified"])

    def test_generic_module_without_real_symptom_still_abstains(self):
        for name in ("Sielse","red","estacion de trabajo"):
            with self.subTest(module=name):
                r=route_with_verified_module("Favor de atender lo solicitado",
                                            module_name=name)
                self.assertEqual(r['domain'],"UNKNOWN")
                self.assertTrue(r['needs_clarification'])

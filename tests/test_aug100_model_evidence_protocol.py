from pathlib import Path
import unittest
from else_dominance import agent, support_desk

ROOT=Path(__file__).resolve().parents[1]


class ModelProtocolTests(unittest.TestCase):
    def test_support_prompt_blocks_business_pk_without_receipt(self):
        message=support_desk.SYSTEM
        for phrase in ("recibo corporativo firmado","ruta de base",
                       "PK existente","sucursal coincidente",
                       "no elijas principal","No es una reparación"):
            self.assertIn(phrase,message)

    def test_investigation_prompt_downgrades_legacy_sixteen(self):
        message=agent.SYSTEM
        for phrase in ("16 cruces preliminares","0 contaban con la ruta Comercial",
                       "no inventes relaciones","Ninguna evidencia QA"):
            self.assertIn(phrase,message)

    def test_protocol_keeps_signed_scope_and_abstention(self):
        content=(ROOT/"docs/QA_AUG100_MODEL_EVIDENCE_PROTOCOL_20261117.md").read_text()
        for marker in ("NO_EXPLICIT_TYPED_BUSINESS_KEY_IN_REQUEST",
                       "EXPLICIT_TYPED_KEY_NOT_FOUND_IN_COMPANY_DB",
                       "COMPANY_PROVIDER_ROUTE_NOT_CERTIFIED",
                       "MULTIPLE_EXACT_TYPED_PKS_NO_PRIMARY_INFERRED",
                       "0/100","16/100","NO_CERTIFICADO"):
            self.assertIn(marker,content)


if __name__=="__main__":
    unittest.main()

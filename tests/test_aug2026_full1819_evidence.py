"""Adversarial full-month journal metrics; independently separate 1819-case window."""
from copy import deepcopy
import unittest
from qa.aug2026_first100.score_full1819_blind_history import score as full_score
from tests.test_aug2026_first100_evidence import Aug100EvidenceTests

class AugustFull1819EvidenceTests(unittest.TestCase):
    def synthetic(self):
        return Aug100EvidenceTests().synthetic()
    def test_full_month_1819_all_selected(self):
        args=self.synthetic()
        args[1][0]["status"]="START_MONTH_FAIL"
        args[1][-1]["status"]="END_MONTH_PASS"
        report=full_score(*args)
        self.assertEqual(report["evaluated_cases"],1819)
        self.assertEqual(report["matched_distinct_ticket_hashes"],1819)
        self.assertEqual(report["model_contract_outcomes"].get("START_MONTH_FAIL"),1)
        self.assertEqual(report["model_contract_outcomes"].get("END_MONTH_PASS"),1)
        self.assertEqual(report["selection"],"FULL_MONTH_FechaSolicitud_CodigoIncidente_ASC")
    def test_full_month_gold_injection_rejected(self):
        args=self.synthetic()
        args[1][800]["historical_gold_exposed"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_CAUSAL_CERTIFICATION"):
            full_score(*args)
    def test_full_month_source_gold_not_withheld_rejected(self):
        args=self.synthetic()
        args[0][-1]["historical_resolution"]="EXPOSED"
        with self.assertRaisesRegex(ValueError,"GOLD_LEAK"):
            full_score(*args)
    def test_one_missing_qwen_denied(self):
        args=self.synthetic()
        args[1].pop()
        with self.assertRaisesRegex(ValueError,"DIFFERENT_LENGTHS"):
            full_score(*args)
    def test_case_swap_in_peer_denied(self):
        args=self.synthetic()
        args[2][-1]["case_sha256"]="a"*64
        with self.assertRaisesRegex(ValueError,"CASE_SET_MISMATCH"):
            full_score(*args)
    def test_wrong_month_denied(self):
        args=self.synthetic()
        args[3]["month"]="2026-07"
        with self.assertRaisesRegex(ValueError,"WRONG_COHORT"):
            full_score(*args)
if __name__=="__main__":
    unittest.main()

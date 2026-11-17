"""Adversarial last100 evaluation checks, using distinct first/last synthetic outcomes."""
import unittest
from qa.aug2026_first100.score_last100_blind_history import score as last_score
from qa.aug2026_first100.score_first100_blind_history import score as first_score
from tests.test_aug2026_first100_evidence import Aug100EvidenceTests

class Last100EvidenceTests(unittest.TestCase):
    def synthetic(self):
        return Aug100EvidenceTests().synthetic()
    def test_tail_window_not_head(self):
        args=self.synthetic()
        args[1][0]["status"]="HEAD_ONLY_FAIL"
        args[1][-1]["status"]="TAIL_ONLY_PASS"
        expected=last_score(*args)
        self.assertEqual(expected["model_contract_outcomes"],{
            "MODEL_STRUCTURAL_PASS":99,"TAIL_ONLY_PASS":1})
        self.assertEqual(expected["selection"],"LAST_100_FechaSolicitud_CodigoIncidente_ASC")
        self.assertNotIn("HEAD_ONLY_FAIL",expected["model_contract_outcomes"])
        first=first_score(*args)
        self.assertEqual(first["model_contract_outcomes"]["HEAD_ONLY_FAIL"],1)
    def test_last100_gold_leak_blocked(self):
        args=self.synthetic()
        args[1][-1]["historical_gold_exposed"]=True
        with self.assertRaisesRegex(ValueError,"CAUSAL_CERTIFICATION"):
            last_score(*args)
    def test_missing_one_peer_result_denied(self):
        args=self.synthetic()
        args[2].pop()
        with self.assertRaisesRegex(ValueError,"CASE_SET_MISMATCH"):
            last_score(*args)
    def test_not_chronological_denied(self):
        args=self.synthetic()
        args[0][-2]["opened_at"]="2026-08-31T13:00:00"
        args[0][-1]["opened_at"]="2026-08-01T08:06:00"
        with self.assertRaisesRegex(ValueError,"NOT_CHRONOLOGICAL"):
            last_score(*args)
if __name__=="__main__":
    unittest.main()

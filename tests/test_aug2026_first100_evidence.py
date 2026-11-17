import unittest
from qa.aug2026_first100.score_first100_blind_history import score


class Aug100EvidenceTests(unittest.TestCase):
    def synthetic(self):
        blind=[]
        qwen=[]
        peer=[]
        for i in range(1819):
            h=f"{i+1:064x}"
            blind.append({"ticket_sha256":h,"month":"2026-08",
                          "opened_at":"2026-08-01T08:06:00",
                          "module_code":"m","service_code":"1",
                          "historical_resolution":"WITHHELD",
                          "model_tools_enabled":False})
            qwen.append({"ticket_sha256":h,"month":"2026-08",
                         "historical_gold_exposed":False,
                         "repairs_certified":False,
                         "status":"MODEL_STRUCTURAL_PASS"})
            peer.append({"case_sha256":h,"peer_state":"PEER_COMPLETED",
                         "peer_relation":"NOT_DETERMINABLE",
                         "history_quality":"VAGUE",
                         "repair_certified":False,"human_confirmed":False})
        manifest={"month":"2026-08","cases":1819,"blind_sha256":"f"*64}
        audit={"schema":"test-peer"}
        return blind,qwen,peer,manifest,audit

    def test_100_selected_from_1819(self):
        r=score(*self.synthetic())
        self.assertEqual(r["evaluated_cases"],100)
        self.assertEqual(r["model_contract_outcomes"]["MODEL_STRUCTURAL_PASS"],100)
        self.assertFalse(r["model_rerun_in_this_stage"])

    def test_gold_leak_rejected(self):
        args=self.synthetic()
        args[0][2]["historical_resolution"]="gold"
        with self.assertRaisesRegex(ValueError,"GOLD_LEAK"):
            score(*args)

    def test_cross_ticket_journal_rejected(self):
        args=self.synthetic()
        args[1][0]["ticket_sha256"]="x"*64
        with self.assertRaisesRegex(ValueError,"CASE_SET"):
            score(*args)

    def test_false_repair_rejected(self):
        args=self.synthetic()
        args[2][0]["repair_certified"]=True
        with self.assertRaisesRegex(ValueError,"CAUSAL_CERTIFICATION"):
            score(*args)

    def test_duplicate_journal_rejected(self):
        args=self.synthetic()
        args[0][1]["ticket_sha256"]=args[0][0]["ticket_sha256"]
        with self.assertRaisesRegex(ValueError,"DUPLICATE_SOURCE"):
            score(*args)


if __name__=="__main__":
    unittest.main()

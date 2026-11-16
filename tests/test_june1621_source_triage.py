import unittest
from qa.june2026_full_link.triage_unmatched_june1621 import (
    source_hints, triage_state, summarize, classify_unmatched_search_outcome,
)


def pair(n, links, text=""):
    s = {"rank": 1, "case_sha256": "a"*64, "description_sha256": "b"*64,
         "module_code": "m", "service_code": "s", "opened_at": "2026-06-01",
         "description_redacted": text, "historical_solution_not_read": True}
    g = {"rank": 1, "case_sha256": "a"*64, "request_sha256": "b"*64,
         "module_code": "m", "service_code": "s", "opened_at": "2026-06-01",
         "source_numeric_candidate_count": n, "links": [{}]*links}
    return s, g


class JuneSourceTriageTests(unittest.TestCase):
    def test_four_states(self):
        self.assertEqual(triage_state(0, 0), "NO_19_DIGIT_CANDIDATE")
        self.assertEqual(triage_state(3, 0), "19_DIGIT_WITHOUT_SAME_BRANCH_PK")
        self.assertEqual(triage_state(1, 1), "ONE_QA_PK")
        self.assertEqual(triage_state(3, 2), "MULTIPLE_QA_PKS")

    def test_reject_negative_and_wrong_types(self):
        with self.assertRaises(ValueError):
            triage_state(-1, 0)
        with self.assertRaises(ValueError):
            triage_state(True, 0)

    def test_source_lexical_hints_not_certification(self):
        self.assertIn("SUMINISTRO", source_hints("Problema con suministro [NUMERO]"))
        self.assertIn("ACCESO_USUARIO", source_hints("Acceso al usuario"))
        self.assertEqual(source_hints("Sin clasificación observable"), [])

    def test_public_report_no_private_case_ids(self):
        s, g = pair(0, 0, "suministro y reclamo")
        report = summarize([s], [g], expected_total=1)
        self.assertEqual(report["counts"]["unresolved_total"], 1)
        self.assertEqual(report["textual_hints_from_redacted_requests"]
                         ["NO_19_DIGIT_CANDIDATE"]["SUMINISTRO"], 1)
        for private in ("a"*64, "b"*64, "2026-06-01"):
            self.assertNotIn(private, str(report))
        self.assertFalse(report["historical_solutions_or_gold_labels_consulted"])

    def test_detect_source_graph_mismatch(self):
        s, g = pair(2, 0)
        g["request_sha256"] = "z"*64
        with self.assertRaisesRegex(ValueError, "SOURCE_GRAPH_CASE_MISMATCH"):
            summarize([s], [g], expected_total=1)

    def test_wrong_branch_cannot_be_promoted(self):
        source, graph = pair(1, 0)
        raw = [{"rank": 1, "business_branch_matches_itil": False}]
        result = classify_unmatched_search_outcome([graph], raw)
        self.assertEqual(result["candidate_pk_found_only_in_wrong_branch"], 1)
        self.assertEqual(result["candidate_pk_not_found_in_queried_pk_tables"], 0)
        raw[0]["business_branch_matches_itil"] = True
        with self.assertRaisesRegex(ValueError, "GHOST_VALID_BRANCH"):
            classify_unmatched_search_outcome([graph], raw)

    def test_reject_missing_cases(self):
        with self.assertRaisesRegex(ValueError, "COHORT_LENGTH_MISMATCH"):
            summarize([], [], expected_total=1)


if __name__ == "__main__":
    unittest.main()

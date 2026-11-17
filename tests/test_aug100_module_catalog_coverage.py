import unittest
from qa.aug2026_first100.score_module_catalog_coverage import score

def fixture():
    rows=[{"month":"2026-08","historical_resolution":"WITHHELD",
           "module_code":"2701         "} for _ in range(1819)]
    atlas={"schema":"else.itil.qa.cross-domain-knowledge-atlas.v1",
           "itil_module_directory":[{
               "codigo_modulo_trimmed_for_repo_name":"2701",
               "alias_bd_declared":"adbELSE","candidate_repository_present":True,
               "candidate_repository_csharp_file_count":5}]}
    return atlas,rows,{"cases":1819}

class ModuleCatalogTests(unittest.TestCase):
    def test_full100(self):
        r=score(*fixture())
        self.assertEqual(r["counts"]["module_directory_match"],100)
        self.assertTrue(r["atlas_runtime_modules_not_deployment_verified"])
    def test_duplicate_module_denied(self):
        data=fixture()
        data[0]["itil_module_directory"].append(dict(data[0]["itil_module_directory"][0]))
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            score(*data)
    def test_wrong_cohort_denied(self):
        data=fixture();data[1][3]["month"]="2026-09"
        with self.assertRaisesRegex(ValueError,"SOURCE_SCOPE"):
            score(*data)
    def test_absent_module_not_fabricated(self):
        data=fixture();data[0]["itil_module_directory"]=[]
        r=score(*data)
        self.assertEqual(r["counts"]["not_in_itil_directory"],100)
if __name__=="__main__":unittest.main()

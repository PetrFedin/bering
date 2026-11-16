import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from commercial_gate import evaluate, verified_record

DOCS = ("signed_contract","firm_quote","waybill","actual_delivery",
        "invoice","payment","baseline_24m","additionality","capacity","legal_review")
COSTS = ("pickup","origin_handling","freight","storage","destination_handling",
         "last_mile","insurance","equipment")

def build(pilot="P1"):
    names = COSTS + (("customs",) if pilot=="P3" else ())
    return {"pilot_id":pilot,"route_id":"SYNTHETIC_ONLY",
            "origin":"test A","destination":"test B",
            "cargo_class":"dry","unit":"40ft_container",
            "cost_currency":"RUB","cost_tax_basis":"EX_VAT",
            "documents":{k:"EV-DOC000_"+str(i) for i,k in enumerate(DOCS)},
            "volumes":{"contracted":100,"diverted":20,"duplicated":10},
            "margin":{"new_unit_contribution_rub":9000,
                      "displaced_old_unit_contribution_rub":5000,
                      "incremental_fixed_opex_rub":100000,
                      "incremental_risk_cost_rub":20000},
            "d2d_components":[{"name":n,"included_in_freight":False,
                               "amount_rub":1000,"evidence_id":"EV-COST000_"+str(i)}
                              for i,n in enumerate(names)]}

def make_index(case,root):
    ids=list(case["documents"].values())+[c["evidence_id"] for c in case["d2d_components"]]
    ix={}
    for i,code in enumerate(ids):
        raw=("SYNTHETIC-TEST-"+code).encode("utf-8")
        filename="doc_"+str(i)+".txt"
        (root/filename).write_bytes(raw)
        ix[code]={"status":"VERIFIED","sha256":hashlib.sha256(raw).hexdigest(),
                  "relative_path":filename,"submitted_by":"requester",
                  "reviewed_by":"reviewer","reviewed_on":"2026-10-27"}
    return ix

class CommercialEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.case=build()
        self.idx=make_index(self.case,self.root)
    def score(self):
        return evaluate(self.case,self.idx,self.root)
    def test_without_external_evidence_always_hold(self):
        self.assertEqual(evaluate(self.case)["gate"],"HOLD")
    def test_synthetic_full_evidence_is_review_not_bankable(self):
        x=self.score()
        self.assertEqual(x["gate"],"REVIEW")
        self.assertEqual(x["net_new_40ft_containers"],70)
        self.assertEqual(x["d2d_rub_ex_vat"],8000)
        self.assertEqual(x["incremental_group_cm_rub"],590000)
        self.assertFalse(x["bankable_revenue_approved"])
    def test_tampered_document_blocks_review(self):
        (self.root/self.idx[self.case["documents"]["invoice"]]["relative_path"]).write_bytes(b"changed")
        self.assertEqual(self.score()["gate"],"HOLD")
    def test_self_attested_evidence_rejected(self):
        self.case["evidence_records"]=self.idx
        self.assertTrue(self.score()["errors"])
    def test_reviewer_cannot_be_submitter(self):
        self.idx[self.case["documents"]["payment"]]["reviewed_by"]="REQUESTER"
        self.assertEqual(self.score()["gate"],"HOLD")
    def test_bad_date_blocks_review(self):
        self.idx[self.case["documents"]["invoice"]]["reviewed_on"]="2026-02-30"
        self.assertEqual(self.score()["gate"],"HOLD")
    def test_path_traversal_blocks_review(self):
        self.idx[self.case["documents"]["payment"]]["relative_path"]="../outside.txt"
        self.assertEqual(self.score()["gate"],"HOLD")
    def test_double_charged_handling_is_invalid(self):
        self.case["d2d_components"][1]["included_in_freight"]=True
        self.assertTrue(self.score()["errors"])
    def test_bundled_handling_must_be_zero_extra(self):
        self.case["d2d_components"][1]["included_in_freight"]=True
        self.case["d2d_components"][1]["amount_rub"]=0
        self.assertEqual(self.score()["d2d_rub_ex_vat"],7000)
    def test_negative_margin_is_allowed_but_not_reviewed(self):
        self.case["margin"]["new_unit_contribution_rub"]=-10
        x=self.score()
        self.assertEqual(x["gate"],"HOLD")
        self.assertLess(x["incremental_group_cm_rub"],0)
    def test_negative_volume_rejected(self):
        self.case["volumes"]["diverted"]=-2
        self.assertTrue(self.score()["errors"])
    def test_double_count_exceeding_contract_rejected(self):
        self.case["volumes"]["duplicated"]=100
        self.assertEqual(self.score()["gate"],"HOLD")
    def test_customs_mandatory_for_p3(self):
        self.case["pilot_id"]="P3"
        self.assertIn("d2d:customs:component",self.score()["missing"])
    def test_wrong_tax_basis_rejected(self):
        self.case["cost_tax_basis"]="VAT_INCLUSIVE"
        self.assertTrue(self.score()["errors"])
    def test_no_freight_amount_blocks_d2d(self):
        self.case["d2d_components"][2]["amount_rub"]=None
        self.assertIsNone(self.score()["d2d_rub_ex_vat"])
    def test_duplicate_document_ids_rejected(self):
        self.case["documents"]["invoice"]=self.case["documents"]["payment"]
        self.assertTrue(self.score()["errors"])
    def test_evidence_index_without_files_cannot_work(self):
        self.assertEqual(evaluate(self.case,self.idx,None)["gate"],"HOLD")
    def test_nonfinite_money_rejected(self):
        self.case["margin"]["new_unit_contribution_rub"]="NaN"
        self.assertTrue(self.score()["errors"])
    def test_zero_contract_cannot_be_confirmed(self):
        self.case["volumes"]["contracted"]=0
        self.assertEqual(self.score()["gate"],"HOLD")
    def test_rejected_bad_sha(self):
        self.idx[self.case["documents"]["payment"]]["sha256"]="f"*64
        self.assertEqual(self.score()["gate"],"HOLD")
if __name__=="__main__":
    unittest.main()

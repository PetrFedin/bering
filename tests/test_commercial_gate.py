import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from commercial_gate import evaluate


def synthetic_complete():
    keys = ("signed_contract","firm_quote","waybill","actual_delivery","invoice",
            "payment","baseline_24m","additionality","capacity","legal_review")
    ids = {k: "EV-TEST_000_" + str(i) for i,k in enumerate(keys)}
    all_ids = list(ids.values()) + ["EV-COST_000_"+str(i) for i in range(8)]
    records = {k: {"status":"VERIFIED","sha256":"a"*64,
                   "reviewed_by":"Synthetic Independent Reviewer","reviewed_on":"2026-10-26"}
               for k in all_ids}
    return {"evidence_records":records,"pilot_id":"P1","route_id":"SYNTHETIC_ONLY",
            "origin":"Test warehouse A","destination":"Test warehouse B",
            "cargo_class":"dry","unit":"40ft_container","cost_currency":"RUB",
            "cost_tax_basis":"EX_VAT","documents":ids,
            "volumes":{"contracted":100,"diverted":20,"duplicated":10},
            "margin":{"new_unit_contribution_rub":9000,
                      "displaced_old_unit_contribution_rub":5000,
                      "incremental_fixed_opex_rub":100000,
                      "incremental_risk_cost_rub":20000},
            "d2d_components":[{"name":n,"included_in_freight":False,"amount_rub":1000,
                               "evidence_id":"EV-COST_000_"+str(i)}
                              for i,n in enumerate(("pickup","origin_handling","freight",
                                "storage","destination_handling","last_mile","insurance","equipment"))]}


class TestEvidenceGate(unittest.TestCase):
    def test_missing_documentary_data_all_hold(self):
        for pilot in ("P1","P2","P3"):
            r=evaluate({"pilot_id":pilot,"route_id":"r","origin":"a","destination":"b",
                        "cargo_class":"dry","unit":"40ft_container"})
            self.assertEqual(r["gate"],"HOLD")
            self.assertIsNone(r["d2d_rub_ex_vat"])
            self.assertIsNone(r["incremental_group_cm_rub"])
            self.assertFalse(r["bankable_revenue_approved"])
    def test_synthetic_complete_only_review(self):
        r=evaluate(synthetic_complete())
        self.assertEqual(r["gate"],"REVIEW")
        self.assertEqual(r["net_new_40ft_containers"],70)
        self.assertEqual(r["d2d_rub_ex_vat"],8000)
        self.assertEqual(r["incremental_group_cm_rub"],590000)
        self.assertFalse(r["bankable_revenue_approved"])
        self.assertFalse(r["errors"] or r["missing"])
    def test_diverted_duplicate_exceeds_contract(self):
        x=synthetic_complete();x["volumes"]["duplicated"]=100
        r=evaluate(x);self.assertEqual(r["gate"],"HOLD")
        self.assertIsNone(r["net_new_40ft_containers"]);self.assertTrue(r["errors"])
    def test_public_tariff_is_not_a_contract(self):
        x=synthetic_complete();x["documents"]["signed_contract"]="НЕ ПОЛУЧЕНО"
        r=evaluate(x);self.assertEqual(r["gate"],"HOLD")
        self.assertIsNone(r["incremental_group_cm_rub"])
    def test_unverified_record_is_not_evidence(self):
        x=synthetic_complete();x["evidence_records"].pop(x["documents"]["payment"])
        r=evaluate(x);self.assertEqual(r["gate"],"HOLD")
        self.assertIsNone(r["incremental_group_cm_rub"])
    def test_included_service_double_charge_invalid(self):
        x=synthetic_complete();x["d2d_components"][1]["included_in_freight"]=True
        self.assertTrue(evaluate(x)["errors"])
    def test_included_service_zero_is_allowed(self):
        x=synthetic_complete();x["d2d_components"][1]["included_in_freight"]=True
        x["d2d_components"][1]["amount_rub"]=None
        r=evaluate(x);self.assertEqual(r["gate"],"REVIEW");self.assertEqual(r["d2d_rub_ex_vat"],7000)
    def test_no_negative_volume(self):
        x=synthetic_complete();x["volumes"]["diverted"]=-1
        self.assertTrue(evaluate(x)["errors"])
    def test_no_teu_tonne_mix(self):
        x=synthetic_complete();x["unit"]="TEU"
        self.assertEqual(evaluate(x)["gate"],"HOLD")
    def test_price_leg_missing_does_not_become_zero(self):
        x=synthetic_complete();x["d2d_components"][2]["amount_rub"]=None
        self.assertIsNone(evaluate(x)["d2d_rub_ex_vat"])
    def test_negative_incremental_profit_no_review(self):
        x=synthetic_complete();x["margin"]["incremental_fixed_opex_rub"]=9999999
        self.assertEqual(evaluate(x)["gate"],"HOLD")
    def test_p3_requires_customs(self):
        x=synthetic_complete();x["pilot_id"]="P3"
        self.assertIn("d2d:customs:component",evaluate(x)["missing"])
    def test_same_document_cannot_prove_everything(self):
        x=synthetic_complete();x["documents"]["payment"]=x["documents"]["invoice"]
        self.assertEqual(evaluate(x)["gate"],"HOLD")
    def test_freight_cannot_be_included_in_itself(self):
        x=synthetic_complete();x["d2d_components"][2]["included_in_freight"]=True
        self.assertTrue(evaluate(x)["errors"])


if __name__ == "__main__":
    unittest.main()

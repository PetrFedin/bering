import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from finance_math import *

class FinanceMathTests(unittest.TestCase):
    def test_annuity(self):
        self.assertAlmostEqual(annuity_factor(.12, 20),
                               sum(1/(1.12)**i for i in range(1, 21)))
    def test_scenario_annual(self):
        self.assertEqual(annual_contribution(30000,16000,150000,2000,200000,5000,37700000000,.02),1026000000)
    def test_npv_flat(self):
        self.assertAlmostEqual(flat_npv(37700000000,1026000000,.12,20),-30036350841.439884,places=1)
    def test_ramp_npv(self):
        ramps=[.3,.5,.7,.85]+[1]*16
        self.assertAlmostEqual(ramp_npv(37700000000,30000,16000,150000,2000,200000,5000,.02,.12,ramps),-32408127371.72675,places=1)
    def test_break_even_ramp(self):
        ramps=[.3,.5,.7,.85]+[1]*16
        self.assertAlmostEqual(break_even_teu_margin(37700000000,30000,150000,2000,200000,5000,.02,.12,ramps),192026.3272748439,places=5)
    def test_break_even_no_ramp(self):
        self.assertAlmostEqual(break_even_teu_margin(37700000000,30000,150000,2000,200000,5000,.02,.12,[1]*20),150041.0002498402,places=5)
    def test_incremental_group_margin(self):
        self.assertEqual(incremental_group_margin(100,20,10,9000,5000,100000,20000),(70,590000))
    def test_diverted_not_new(self):
        self.assertEqual(incremental_group_margin(100,100,0,9000,9000,0,0),(0,0))
    def test_invalid_shift(self):
        with self.assertRaises(ValueError):
            incremental_group_margin(100,90,20,9000,5000,0,0)
    def test_negative_risk_rejected(self):
        with self.assertRaises(ValueError):
            incremental_group_margin(100,10,0,9000,5000,0,-1)
    def test_missing_demand_no_investment_proof(self):
        self.assertLess(ramp_npv(37700000000,0,16000,0,2000,0,5000,.02,.12,[1]*20),0)
    def test_unsupported_rate_rejected(self):
        with self.assertRaises(ValueError):
            annuity_factor(0,20)
if __name__=="__main__":
    unittest.main()

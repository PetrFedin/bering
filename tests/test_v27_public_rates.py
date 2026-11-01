import json
import unittest
from pathlib import Path
from scripts.v27_public_rates import evaluate


class PublicTariffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample=json.loads((Path(__file__).resolve().parents[1]/'data/public/V27_KASCO_LIST_RATE_20261101.json').read_text())

    def test_source_tariffs_with_vat(self):
        p=evaluate(self.sample)
        self.assertEqual(p['status'],'PUBLIC_LIST_RATE_ONLY')
        self.assertEqual(p['quoted_40ft_dry_rub_incl_vat'],'239767')
        self.assertEqual(p['quoted_40ft_reefer_rub_incl_vat'],'315000')
        self.assertEqual(p['reefer_minus_dry_rub_incl_vat'],'75233')
        self.assertEqual(p['reefer_vs_dry_premium_percent'],'31.38')
        self.assertIsNone(p['group_incremental_margin_rub'])
        self.assertFalse(p['bankable_revenue_approved'])

    def test_net_vat_basis_must_not_be_inferred(self):
        p=dict(self.sample,tax_basis='EX_VAT')
        self.assertEqual(evaluate(p)['status'],'INVALID')

    def test_prepaid_customer_deal_not_claimed(self):
        p=dict(self.sample,rate_is_binding_customer_quote=True)
        self.assertEqual(evaluate(p)['status'],'INVALID')

    def test_double_port_handling_not_allowed(self):
        p=dict(self.sample,port_handling_both_ends_included=False)
        self.assertEqual(evaluate(p)['status'],'INVALID')

    def test_no_silent_extra_rate_keys(self):
        p=dict(self.sample,list_rates=dict(self.sample['list_rates'],p3_china='500'))
        self.assertEqual(evaluate(p)['status'],'INVALID')

    def test_no_float_or_nan(self):
        for val in (239767.5,'NaN','Infinity','-1','200.999'):
            with self.subTest(val=val):
                p=dict(self.sample,list_rates=dict(self.sample['list_rates'],dry_40ft_vvo_to_mag=val))
                self.assertEqual(evaluate(p)['status'],'INVALID')

    def test_correct_direction_is_not_return_rate(self):
        p=dict(self.sample,origin='Magadan')
        self.assertEqual(evaluate(p)['status'],'INVALID')

    def test_untrusted_empty_object_fails(self):
        self.assertEqual(evaluate({})['status'],'INVALID')


if __name__=='__main__':unittest.main()

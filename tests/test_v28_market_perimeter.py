"""Factual source perimeter and risk guards: synthetic tampering, not real OD."""
import copy
import json
from pathlib import Path
import unittest

from scripts.v28_market_perimeter import assess, exact_number, sourced_url

FIXTURE = Path(__file__).parents[1] / 'data/public/V28_MAGADAN_MARKET_PERIMETER.json'


class V28PerimeterTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def test_baseline_is_research_only(self):
        a = assess(self.data)
        self.assertEqual(a['status'], 'CONTEXT_VALID_REVIEW_REQUIRED')
        self.assertFalse(a['bankable_revenue_approved'])
        self.assertFalse(a['investment_approved'])
        self.assertIsNone(a['real_bering_40ft_OD_24m'])
        self.assertIsNone(a['signed_new_cargo_40ft'])
        self.assertIsNone(a['project_NPV_rub'])
        self.assertEqual([a[x] for x in ('P1','P2','P3')], ['HOLD']*3)

    def test_2024_and_2025_secondary_yearly_teu_only(self):
        item=assess(self.data)['historical_port_teu']
        self.assertEqual(item['actual_2024_reported'], '80900')
        self.assertEqual(item['actual_2025_reported'], '84300')
        self.assertEqual(item['annual_absolute_change_TEUs'], '3400')
        self.assertEqual(item['reported_yoy_pct_calculated'], '4.20')
        self.assertIsNone(item['physical_40ft_containers'])

    def test_two_capacities_never_added_or_commissioned(self):
        result=assess(self.data)['project_capacity_version_conflict']
        self.assertEqual(result['may_2026_published_design_TEUs_per_year'], '30000')
        self.assertEqual(result['oct_2026_expertise_announced_design_TEUs_per_year'], '150000')
        self.assertEqual(result['difference_in_published_claims_TEUs'], '120000')
        self.assertEqual(result['version_ratio_not_capacity_addition'], '5.00')
        self.assertIsNone(result['future_in_service_capacity'])
        self.assertNotIn('total_capacity', result)

    def test_metric_scope_falsification_is_invalid(self):
        self.data['observations'][0]['entity_scope'] = 'MMTP_INDIVIDUAL_TERMINAL_OPERATOR'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_tonnes_not_teu(self):
        self.data['observations'][2]['unit'] = 'TEU'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_year_not_monthly(self):
        self.data['observations'][1]['period'] = '2025-12'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_no_fake_2026_actual(self):
        row = copy.deepcopy(self.data['observations'][1])
        row['id']='MAGADAN_ALL_PORTS_2026_TEU'
        self.data['observations'].append(row)
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_duplicate_observation_invalid(self):
        self.data['observations'][0]=self.data['observations'][1]
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_source_hostname_not_in_allowlist(self):
        self.data['observations'][0]['source_url']='https://example.org/report'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_source_alternative_url_requires_review(self):
        self.data['observations'][0]['source_url']='https://www.finmarket.ru/news/other'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_fake_authorized_original(self):
        self.data['observations'][0]['source_original_bytes_authenticated']=True
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_can_not_assert_commissioned_capacity(self):
        self.data['capacity_claim_versions'][1]['construction_and_operations_proven']=True
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_cannot_reconcile_capacity_without_signed_document(self):
        self.data['capacity_claim_versions'][1]['scope_review']='RECONCILED'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_wrong_project_id(self):
        self.data['capacity_claim_versions'][1]['project_id']='ANOTHER_PORT'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_capacity_is_not_2026_operational_volume(self):
        self.data['capacity_claim_versions'][1]['measure']='ACTUAL_2026_PORT_VOLUME'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_future_source_date(self):
        self.data['capacity_claim_versions'][0]['issued']='2040-01-01'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_bad_asof_future(self):
        self.data['as_of']='2099-01-01'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_missing_actual_OD_control(self):
        self.data['verification_controls']['actual_paid_bering_40ft_shipments_verified']=True
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_no_teu_to_40ft_assumption(self):
        self.data['accounting_rules']['never_convert_teu_to_40ft_without_mix']=False
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_no_capacity_addition_assumption(self):
        self.data['accounting_rules']['never_add_capacity_versions']=False
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_no_market_to_revenue_assumption(self):
        self.data['accounting_rules']['never_use_market_context_as_paid_bering_volume']=False
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_changed_2025_teu_requires_new_revision(self):
        self.data['observations'][1]['value']='99999'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_changed_claim_requires_new_revision(self):
        self.data['capacity_claim_versions'][1]['value']='200000'
        self.assertEqual(assess(self.data)['status'], 'INVALID')

    def test_invalid_numbers(self):
        for text in ('', '0','-100','1e5','nan', 'Infinity','1.1',' 12','0012', '99999999999999999'):
            with self.subTest(value=text), self.assertRaises(ValueError):
                exact_number(text)

    def test_invalid_number_types(self):
        for val in (None, False, True, 1.0, {}, [], [1], 100):
            with self.subTest(value=val), self.assertRaises(ValueError):
                exact_number(val)

    def test_url_credentials_or_redirector_rejected(self):
        self.assertFalse(sourced_url('https://bad:e@www.finmarket.ru/news/6331647'))
        self.assertFalse(sourced_url('http://www.finmarket.ru/news/6331647'))
        self.assertFalse(sourced_url('https://www.finmarket.ru/news/6331647?from=x'))

    def test_wrong_schema(self):
        self.data['schema']='V99'
        self.assertEqual(assess(self.data)['status'],'INVALID')

    def test_nonobject_root(self):
        self.assertEqual(assess([])['status'],'INVALID')


if __name__ == '__main__':
    unittest.main()

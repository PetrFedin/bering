"""Negative and baseline tests of the V37 published-source evidence boundary."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from v37_magadan_market_gate import DEFAULT, PINNED, GUARDS, evaluate  # noqa: E402


class MarketBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(DEFAULT.read_text(encoding='utf-8'))

    def assert_invalid(self, change):
        d = copy.deepcopy(self.data)
        change(d)
        r = evaluate(d)
        self.assertEqual(r['status'], 'INVALID', r['errors'])
        self.assertFalse(r['investment_approved'])
        self.assertFalse(r['bankable_revenue_approved'])
        self.assertIsNone(r['current_port_capacity_2026_teu'])
        self.assertIsNone(r['bering_npv_rub'])

    def test_clean_snapshot_does_not_approve_revenue(self):
        r = evaluate(self.data)
        self.assertEqual(r['status'], 'RESEARCH_CONTEXT_ONLY', r['errors'])
        self.assertEqual(r['source_records_reviewed'], 16)
        self.assertIsNone(r['signed_bering_incremental_shipments_40ft'])
        self.assertEqual([r[x] for x in ('P1','P2','P3')], ['HOLD'] * 3)

    def test_2024_2025_growth_is_port_wide_only(self):
        r = evaluate(self.data)
        self.assertEqual(r['port_teu_2025_minus_2024'], 3400)
        self.assertEqual(r['port_teu_yoy_percent_rounded_two_dp'], '4.20')

    def test_no_2009_archival_capacity_promotion_to_2026_utilization(self):
        r = evaluate(self.data)
        self.assertEqual(r['archival_2009_nominal_container_capacity_teu'], 45000)
        self.assertIsNone(r['current_port_capacity_2026_teu'])
        self.assertIsNone(r['port_utilization_percent'])

    def test_project_capacity_cannot_be_summed_or_turned_into_bering_demand(self):
        r = evaluate(self.data)
        self.assertIsNone(r['competing_design_capacity_sum_teu'])
        self.assertIsNone(r['verified_mlc_operational_teu'])
        self.assertIsNone(r['signed_bering_incremental_shipments_40ft'])

    def test_budget_difference_is_only_arithmetic_not_shortfall(self):
        r = evaluate(self.data)
        self.assertEqual(r['promoter_budget_million_rub'], '37655.467')
        self.assertEqual(r['government_plan_two_events_million_rub'], '20295')
        self.assertEqual(r['arithmetic_budget_difference_million_rub_not_a_funding_gap'], '17360.467')
        self.assertEqual(r['promoter_npv_to_budget_percent_not_project_roi'], '0.1524')

    def test_reordering_is_safe(self):
        self.data['records'].reverse()
        self.assertEqual(evaluate(self.data)['status'], 'RESEARCH_CONTEXT_ONLY')

    def test_missing_record_is_invalid(self):
        self.assert_invalid(lambda d: d['records'].pop())

    def test_duplicate_record_is_invalid(self):
        self.assert_invalid(lambda d: d['records'].append(copy.deepcopy(d['records'][0])))

    def test_fake_paid_cargo_record_is_invalid(self):
        self.assert_invalid(lambda d: d['records'].append({**d['records'][0], 'id':'BERING_PAID_40FT'}))

    def test_verification_label_cannot_be_promoted_to_authenticated(self):
        self.assert_invalid(lambda d: d['records'][1].__setitem__('verification_limit', 'SIGNED AND BANKABLE'))

    def test_2025_port_cargo_forgery_invalid(self):
        self.assert_invalid(lambda d: d['records'][1].__setitem__('value', '183000'))

    def test_2025_port_scope_mislabelled_as_operator_invalid(self):
        self.assert_invalid(lambda d: d['records'][2].__setitem__('scope', 'PAO_MMTP_OPERATOR'))

    def test_archival_2009_capacity_mislabelled_as_current_invalid(self):
        self.assert_invalid(lambda d: d['records'][3].__setitem__('stage', 'CURRENT_OPERATING_CAPACITY'))

    def test_developer_150k_mislabeled_as_real_throughput_invalid(self):
        self.assert_invalid(lambda d: d['records'][5].__setitem__('stage', 'VERIFIED_2026_ACTUAL'))

    def test_merging_tonnes_and_teu_invalid(self):
        self.assert_invalid(lambda d: d['records'][2].__setitem__('unit', 'TEU_per_year'))

    def test_capex_source_unit_switch_invalid(self):
        self.assert_invalid(lambda d: d['records'][6].__setitem__('unit', 'million_RUB'))

    def test_taxonomy_source_url_switch_invalid(self):
        self.assert_invalid(lambda d: d['records'][11].__setitem__('source_url', 'https://example.com/unknown'))

    def test_2030_plan_cannot_be_signed_commissioning(self):
        self.assert_invalid(lambda d: d['records'][13].__setitem__('stage', 'ACTUAL_COMMISSIONING'))

    def test_transregional_corridor_not_magadan_port_actual(self):
        self.assert_invalid(lambda d: d['records'][15].__setitem__('scope', 'MAGADAN_ALL_PORTS'))

    def test_inventory_of_unknowns_is_not_mutable(self):
        self.assert_invalid(lambda d: d['guards'].__setitem__('bering_real_paid_incremental_cargo_authenticated', True))
        self.assert_invalid(lambda d: d['guards'].__setitem__('od_group_months_authenticated', 96))
        self.assert_invalid(lambda d: d['guards'].__setitem__('investment_approved', True))
        self.assert_invalid(lambda d: d['guards'].__setitem__('government_program_and_promoter_budget_scope_matched', True))

    def test_extra_primary_signed_flag_does_not_pass(self):
        self.assert_invalid(lambda d: d['records'][5].__setitem__('signed_approved_revision', True))

    def test_boolean_and_nonfinite_measures_do_not_authenticate(self):
        for val in (True, float('nan'), float('inf'), '-1', '', '0x20', None):
            with self.subTest(value=val):
                self.assert_invalid(lambda d: d['records'][0].__setitem__('value', val))

    def test_corrupt_structures_fail_without_exception(self):
        for bad in (None, [], {}, {'records': []}, 'text', 3):
            with self.subTest(bad=bad):
                self.assertEqual(evaluate(bad)['status'], 'INVALID')

    def test_methodological_warnings_must_be_preserved(self):
        self.assert_invalid(lambda d: d['methodology_notes'].__setitem__(0, 'This proves Bering bankable earnings'))
        self.assert_invalid(lambda d: d.__setitem__('purpose', 'Approved investment model'))

    def test_modified_snapshot_date_is_invalid(self):
        self.assert_invalid(lambda d: d.__setitem__('as_of', '2027-01-01'))

    def test_cli_does_not_succeed_on_invalid_json(self):
        with tempfile.TemporaryDirectory() as t:
            invalid = Path(t) / 'invalid.json'
            invalid.write_text('{not-json', encoding='utf-8')
            proc = subprocess.run(
                [sys.executable, str(ROOT/'scripts/v37_magadan_market_gate.py'), '--register', str(invalid)],
                capture_output=True, text=True, cwd=ROOT, check=False
            )
            self.assertEqual(proc.returncode, 2)
            result = json.loads(proc.stdout)
            self.assertFalse(result['investment_approved'])
            self.assertEqual(result['status'], 'INVALID')

    def test_cli_baseline_success(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT/'scripts/v37_magadan_market_gate.py'), '--register', str(DEFAULT)],
            capture_output=True, text=True, cwd=ROOT, check=False
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['status'], 'RESEARCH_CONTEXT_ONLY')


if __name__ == '__main__':
    unittest.main()

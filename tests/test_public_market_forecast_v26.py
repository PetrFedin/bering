"""V26 regression tests. Public statistics are labelled, not project revenue."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
from public_market_forecast_v26 import evaluate


class PublicSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((BASE / 'data/public/V26_PUBLIC_SOURCE_REGISTER.json').read_text())

    def setUp(self):
        self.input = copy.deepcopy(self.original)

    def check_invalid(self):
        out = evaluate(self.input)
        self.assertEqual(out['status'], 'INVALID', out)
        self.assertTrue(out['errors'])
        self.assertEqual(out['commercial_gate'], 'HOLD')
        self.assertIsNone(out['project_incremental_group_cm_rub'])

    def record(self, ident):
        return next(row for row in self.input['records'] if row['id'].endswith(ident))

    def test_valid_public_context_is_not_bankable(self):
        r = evaluate(self.input)
        self.assertEqual(r['status'], 'PUBLIC_CONTEXT_ONLY')
        self.assertEqual(r['observed_port_2025_all_cargo_tonnes'], '1834700')
        self.assertEqual(r['observed_far_east_basin_2025_all_cargo_tonnes'], '252100000')
        self.assertEqual(r['reported_operator_2024_container_cargo_tonnes'], '890100')
        self.assertEqual(r['operator_2032_container_target_tonnes'], '1000000')
        self.assertEqual(r['operator_target_implied_annual_growth_percent'], '1.4659')
        self.assertEqual(r['commercial_gate'], 'HOLD')
        self.assertFalse(r['investment_approved'])
        self.assertIsNone(r['project_incremental_group_cm_rub'])
        self.assertIsNone(r['project_paid_40ft_units'])

    def test_smooth_conditional_trajectory_endpoints_and_2026(self):
        out = evaluate(self.input)
        rows = {v['year']: v for v in out['annual_path']}
        self.assertEqual(rows[2024]['operator_target_smooth_interpolation_tonnes'], '890100')
        self.assertEqual(rows[2026]['operator_target_smooth_interpolation_tonnes'], '916387')
        self.assertEqual(rows[2032]['operator_target_smooth_interpolation_tonnes'], '1000000')
        self.assertEqual(rows[2032]['record_type'], 'TARGET_POINT')
        self.assertEqual(rows[2025]['record_type'], 'MATHEMATICAL_INTERPOLATION_NOT_OBSERVED')
        self.assertEqual(rows[2026]['record_type'], 'MATHEMATICAL_INTERPOLATION_NOT_OBSERVED')

    def test_no_2026_claim_extracted_from_unread_xls(self):
        out = evaluate(self.input)
        self.assertIsNone(out['direct_2026_actual_container_tonnage'])
        self.assertEqual(len(out['unextracted_operator_2026_9m_reports']), 2)

    def test_all_pilot_units_remain_unknown(self):
        self.assertEqual(evaluate(self.input)['pilot_specific_40ft_units'], {'P1':None,'P2':None,'P3':None})

    def test_missing_row_invalid(self):
        self.input['records'].pop()
        self.check_invalid()

    def test_duplicate_row_invalid(self):
        self.input['records'].append(copy.deepcopy(self.input['records'][0]))
        self.check_invalid()

    def test_unknown_record_id_invalid(self):
        self.input['records'][0]['id'] = 'FAKE_NEW_CARGO_VOLUME'
        self.check_invalid()

    def test_wrong_metric_scope_invalid(self):
        self.input['records'][0]['entity'] = 'MAGADAN_MMTP_OPERATOR'
        self.check_invalid()

    def test_future_target_cannot_be_observed(self):
        self.input['records'][3]['record_type'] = 'OBSERVED'
        self.check_invalid()

    def test_container_tonnes_cannot_be_teu(self):
        self.input['records'][2]['unit'] = 'TEU'
        self.check_invalid()

    def test_2026_unextracted_report_cannot_invent_actuals(self):
        self.input['records'][4]['value'] = '1000000'
        self.input['records'][4]['unit'] = 'tonnes'
        self.check_invalid()

    def test_unextracted_report_cannot_claim_primary_data(self):
        self.input['records'][5]['evidence_tier'] = 'PRIMARY_PUBLISHED_WEB'
        self.check_invalid()

    def test_2024_historical_cannot_lose_secondary_tier(self):
        self.input['records'][2]['evidence_tier'] = 'UNKNOWN'
        self.check_invalid()

    def test_missing_publisher_invalid(self):
        self.input['records'][0]['source_publisher'] = ''
        self.check_invalid()

    def test_missing_caveat_invalid(self):
        self.input['records'][0]['caveat'] = ''
        self.check_invalid()

    def test_unreviewed_url_change_invalid(self):
        self.input['records'][0]['source_url'] = 'https://example.com/not-a-government-source'
        self.check_invalid()

    def test_no_http_provenance_accepted(self):
        self.input['records'][0]['source_url'] = 'http://ampvanino.ru/magadan/'
        self.check_invalid()

    def test_future_publication_invalid(self):
        self.input['records'][2]['source_date'] = '2027-07-01'
        self.check_invalid()

    def test_invalid_asof_rejected(self):
        self.input['as_of'] = '2026-02-30'
        self.check_invalid()

    def test_future_asof_rejected(self):
        self.input['as_of'] = '2099-01-01'
        self.check_invalid()

    def test_string_instead_of_list_invalid(self):
        self.input['records'] = 'fake'
        self.check_invalid()

    def test_bad_integer_format_rejected(self):
        self.input['records'][0]['value'] = '1.8347e6'
        self.check_invalid()

    def test_negative_tonnes_rejected(self):
        self.input['records'][0]['value'] = '-1834700'
        self.check_invalid()

    def test_large_exponent_rejected_without_crash(self):
        self.input['records'][0]['value'] = '1e99999999'
        self.check_invalid()

    def test_float_real_world_mass_rejected(self):
        self.input['records'][2]['value'] = 890100.0
        self.check_invalid()

    def test_target_below_base_requires_other_explicit_scenario(self):
        self.input['records'][3]['value'] = '1'
        self.check_invalid()

    def test_project_new_units_must_be_null(self):
        self.input['source_policy']['project_new_od_volume_40ft_units'] = 5000
        self.check_invalid()

    def test_project_paid_units_must_be_null(self):
        self.input['source_policy']['project_paid_40ft_units'] = 200
        self.check_invalid()

    def test_project_profit_must_be_null(self):
        self.input['source_policy']['project_incremental_group_cm_rub'] = '250000000'
        self.check_invalid()

    def test_pilot_status_must_all_hold(self):
        self.input['source_policy']['individual_pilot_status']['P3'] = 'REVIEW'
        self.check_invalid()

    def test_no_project_billing_scope(self):
        self.input['source_policy']['target_scope'] = 'BERING_PROJECT_BOOKINGS'
        self.check_invalid()

    def test_source_register_hash_pinned_to_exact_bytes(self):
        raw = json.dumps(self.input,sort_keys=True).encode()
        self.assertEqual(len(evaluate(self.input,source_bytes=raw)['source_register_sha256']),64)

    def test_wrong_data_types_rejected_not_crash(self):
        self.input['records'][0]['id'] = []
        self.check_invalid()

    def test_weird_type_evidence_tier_rejected_not_crash(self):
        self.input['records'][0]['evidence_tier'] = {'tier': 'PRIMARY_PUBLISHED_WEB'}
        self.check_invalid()

    def test_cli_returns_success_but_not_investment_pass(self):
        cmd = [sys.executable, str(BASE/'scripts/public_market_forecast_v26.py'),
               '--sources', str(BASE/'data/public/V26_PUBLIC_SOURCE_REGISTER.json')]
        r = subprocess.run(cmd,capture_output=True,text=True,check=False)
        self.assertEqual(r.returncode,0,r.stderr)
        result = json.loads(r.stdout)
        self.assertEqual(result['commercial_gate'],'HOLD')


if __name__ == '__main__':
    unittest.main()

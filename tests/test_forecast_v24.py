"""Synthetic V24 regression tests. No actual Bering shipments are used."""
import copy
import hashlib
import tempfile
import unittest
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "scripts" / "forecast_v24.py").exists():
    sys.path.insert(0, str(ROOT / "scripts"))
import forecast_v24 as v24


class ForecastV24Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.records = {}
        self.payload = {'schema_version': 'V24', 'as_of': '2026-10-31',
                        'unit': 'paid_new_40ft_containers', 'series': []}
        first = v24.month_index('2023-10')
        for p in v24.PILOTS:
            rows = []
            for i in range(36):
                month = v24.month_name(first + i)
                eid = f'EV-{p}-SOURCE-{i:04d}'
                contents = f'FAKE DUMMY month={month} pilot={p} - not real cargo'.encode()
                file = self.base / (eid + '.txt')
                file.write_bytes(contents)
                self.records[eid] = {'status': 'VERIFIED', 'relative_path': file.name,
                                     'sha256': hashlib.sha256(contents).hexdigest(),
                                     'submitted_by': 'analystA', 'reviewed_by': 'auditorB',
                                     'reviewed_on': '2026-10-01'}
                rows.append({'month': month, 'paid_new_40ft': 10 + (i % 12),
                             'source_type': 'SETTLED_ACTUAL', 'evidence_id': eid})
            self.payload['series'].append({'pilot_id': p, 'observations': rows})

    def evaluate(self, data=None):
        return v24.evaluate(self.payload if data is None else data,
                            self.records, self.base)

    def test_default_zero_claim_hold(self):
        payload = copy.deepcopy(self.payload)
        for s in payload['series']:
            s['observations'] = []
        got = self.evaluate(payload)
        self.assertEqual(got['status'], 'HOLD')
        self.assertIsNone(got['group_forecast_40ft'])

    def test_synthetic_complete_only_review_not_bankable(self):
        got = self.evaluate()
        self.assertEqual(got['status'], 'REVIEW')
        self.assertFalse(got['bankable_revenue_approved'])
        self.assertFalse(got['investment_approved'])
        self.assertIsNone(got['group_forecast_40ft'])
        self.assertEqual(got['group_status'], 'HOLD_UNTIL_V23_SOURCE_TIEOUT')
        self.assertEqual(got['pilot_forecasts']['P1']['forecast_12m'][0]['month'], '2026-10')

    def test_seasonality_fixed_model(self):
        got = self.evaluate()
        p1 = got['pilot_forecasts']['P1']
        self.assertEqual(p1['backtest']['holdout_12m_abs_error_40ft'], 0)
        self.assertEqual(p1['backtest']['holdout_12m_wape'], 0)
        self.assertEqual([r['point_40ft'] for r in p1['forecast_12m']], list(range(10,22)))

    def test_missing_source_blocks_pilot_and_group(self):
        key = self.payload['series'][0]['observations'][0]['evidence_id']
        del self.records[key]
        self.assertEqual(self.evaluate()['status'], 'HOLD')

    def test_tampered_document_blocks(self):
        key = self.payload['series'][0]['observations'][1]['evidence_id']
        (self.base / self.records[key]['relative_path']).write_text('TAMPERED')
        self.assertEqual(self.evaluate()['status'], 'HOLD')

    def test_no_independent_review_blocks(self):
        key = self.payload['series'][0]['observations'][1]['evidence_id']
        self.records[key]['reviewed_by'] = 'analystA'
        self.assertEqual(self.evaluate()['status'], 'HOLD')

    def test_24_months_are_not_reliable_seasonal_forecast(self):
        for s in self.payload['series']:
            s['observations'] = s['observations'][-24:]
        self.assertEqual(self.evaluate()['status'], 'HOLD')

    def test_gap_refuses_to_interpolate(self):
        self.payload['series'][0]['observations'].pop(5)
        self.assertEqual(self.evaluate()['status'], 'HOLD')

    def test_future_month_invalid(self):
        self.payload['series'][0]['observations'][-1]['month'] = '2026-10'
        self.assertEqual(self.evaluate()['status'], 'INVALID')

    def test_duplicate_month_invalid(self):
        self.payload['series'][0]['observations'][1]['month'] = '2023-10'
        self.assertEqual(self.evaluate()['status'], 'INVALID')

    def test_duplicate_provenance_invalid(self):
        self.payload['series'][1]['observations'][0]['evidence_id'] = \
            self.payload['series'][0]['observations'][0]['evidence_id']
        self.assertEqual(self.evaluate()['status'], 'INVALID')

    def test_wrong_measure_invalid(self):
        self.payload['unit'] = 'TEU'
        self.assertEqual(self.evaluate()['status'], 'INVALID')

    def test_unsupported_synthetic_source_invalid(self):
        self.payload['series'][0]['observations'][0]['source_type'] = 'SYNTHETIC'
        self.assertEqual(self.evaluate()['status'], 'INVALID')

    def test_float_and_bool_quantities_invalid(self):
        self.payload['series'][0]['observations'][0]['paid_new_40ft'] = True
        self.assertEqual(self.evaluate()['status'], 'INVALID')
        self.payload['series'][0]['observations'][0]['paid_new_40ft'] = 2.5
        self.assertEqual(self.evaluate()['status'], 'INVALID')

    def test_all_zero_holdout_does_not_announce_accuracy(self):
        for s in self.payload['series']:
            for row in s['observations'][-12:]:
                row['paid_new_40ft'] = 0
        self.assertEqual(self.evaluate()['status'], 'HOLD')

    def test_negative_actual_invalid(self):
        self.payload['series'][0]['observations'][0]['paid_new_40ft'] = -1
        self.assertEqual(self.evaluate()['status'], 'INVALID')

    def test_unknown_pilot_invalid(self):
        self.payload['series'][0]['pilot_id'] = 'P4'
        self.assertEqual(self.evaluate()['status'], 'INVALID')

    def test_missing_last_completed_month_hold(self):
        for s in self.payload['series']:
            s['observations'] = s['observations'][:-1]
        self.assertEqual(self.evaluate()['status'], 'HOLD')

    def test_evidence_path_traversal_hold(self):
        key = self.payload['series'][0]['observations'][0]['evidence_id']
        self.records[key]['relative_path'] = '../outside.txt'
        self.assertEqual(self.evaluate()['status'], 'HOLD')

    def test_backtest_errors_are_observed_not_fake_probability(self):
        self.payload['series'][0]['observations'][-1]['paid_new_40ft'] = 100
        got = self.evaluate()
        test = got['pilot_forecasts']['P1']['backtest']
        self.assertGreater(test['holdout_12m_wape'], 0)
        self.assertIn('holdout_12m_abs_error_40ft', test)
        self.assertNotIn('95_percent_confidence', str(got))


if __name__ == '__main__':
    unittest.main()

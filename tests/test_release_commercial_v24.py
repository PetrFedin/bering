"""Contract tests for V24 combined gateway; subprocess data are synthetic mocks."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from release_commercial_v24 import audit


class FakeResult:
    def __init__(self, payload, returncode=0):
        self.stdout = json.dumps(payload)
        self.returncode = returncode


def financial(status):
    return {'status': status, 'investment_approved': False,
            'bankable_revenue_approved': False,
            'cross_pilot_incremental_group_cm_rub': '1000' if status == 'REVIEW' else None}


def identity(status):
    return {'status': status, 'bankable_revenue_approved': False,
            'contracts_authenticated': False, 'linked_40ft_containers': 2,
            'v23_source_sha256': 'f'*64}


class CombinedV24Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_case(self, f='HOLD', i='HOLD', ret=(0, 0), f_data=None, i_data=None):
        results = [FakeResult(f_data if f_data is not None else financial(f), ret[0]),
                   FakeResult(i_data if i_data is not None else identity(i), ret[1])]
        with patch('release_commercial_v24.subprocess.run', side_effect=results) as spy:
            result = audit(self.root)
            self.assertEqual(spy.call_count, 2)
            args_a = spy.call_args_list[0].args[0]
            args_b = spy.call_args_list[1].args[0]
            self.assertIn('--cross-input', args_a)
            self.assertIn('--v23', args_b)
            self.assertEqual(args_a[args_a.index('--cross-input') + 1],
                             args_b[args_b.index('--v23') + 1])
            return result

    def test_both_hold(self):
        r = self.run_case()
        self.assertEqual(r['status'], 'HOLD')
        self.assertIsNone(r['incremental_group_cm_rub_screening_only'])

    def test_financial_review_identity_hold(self):
        self.assertEqual(self.run_case(f='REVIEW')['status'], 'HOLD')

    def test_financial_hold_identity_review(self):
        self.assertEqual(self.run_case(i='REVIEW')['status'], 'HOLD')

    def test_both_review_only_manual_review(self):
        r = self.run_case(f='REVIEW', i='REVIEW')
        self.assertEqual(r['status'], 'REVIEW')
        self.assertEqual(r['incremental_group_cm_rub_screening_only'], '1000')
        self.assertFalse(r['bankable_revenue_approved'])
        self.assertFalse(r['investment_approved'])
        self.assertFalse(r['contracts_authenticated'])

    def test_invalid_financial_report_never_pass(self):
        self.assertEqual(self.run_case(f='INVALID', i='REVIEW')['status'], 'INVALID')

    def test_invalid_identity_report_never_pass(self):
        self.assertEqual(self.run_case(f='REVIEW', i='INVALID')['status'], 'INVALID')

    def test_abnormal_subprocess_return_code_invalid(self):
        self.assertEqual(self.run_case(f='REVIEW', i='REVIEW', ret=(42, 0))['status'], 'INVALID')

    def test_identity_bankable_true_forbidden(self):
        bad = identity('REVIEW')
        bad['bankable_revenue_approved'] = True
        self.assertEqual(self.run_case(f='REVIEW', i_data=bad)['status'], 'INVALID')

    def test_financial_investment_true_forbidden(self):
        bad = financial('REVIEW')
        bad['investment_approved'] = True
        self.assertEqual(self.run_case(f_data=bad, i='REVIEW')['status'], 'INVALID')

    def test_identity_contracts_authenticated_true_forbidden(self):
        bad = identity('REVIEW')
        bad['contracts_authenticated'] = True
        self.assertEqual(self.run_case(f='REVIEW', i_data=bad)['status'], 'INVALID')

    def test_missing_identity_status_rejected(self):
        bad = identity('REVIEW')
        bad.pop('status')
        self.assertEqual(self.run_case(f='REVIEW', i_data=bad)['status'], 'INVALID')

    def test_no_single_sided_evidence_connector(self):
        r = audit(self.root, evidence_index=self.root/'file.json')
        self.assertEqual(r['status'], 'INVALID')

    def test_source_file_identical_for_both_gates(self):
        self.assertEqual(self.run_case(f='REVIEW', i='REVIEW')['status'], 'REVIEW')

    def test_subprocess_timeout_invalid(self):
        import subprocess
        with patch('release_commercial_v24.subprocess.run', side_effect=subprocess.TimeoutExpired('fake', 90)):
            r = audit(self.root)
        self.assertEqual(r['status'], 'INVALID')
        self.assertGreater(len(r['errors']), 0)


if __name__ == '__main__':
    unittest.main()

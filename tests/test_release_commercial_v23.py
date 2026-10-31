"""E2E-shaped synthetic join tests; no third-party cargo is asserted."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from release_commercial_v23 import audit


class FakeProc:
    def __init__(self, data, code=0):
        self.stdout = json.dumps(data)
        self.returncode = code


def pilots(status='HOLD', errs=None):
    return {'evaluated': 3, 'results': [
        {'pilot_id': p, 'gate': status, 'bankable_revenue_approved': False,
         'errors': errs or []} for p in ('P1','P2','P3')]}


def cross(status='HOLD', errs=None):
    return {'status': status, 'pilots': {p: {'status': status}
                                      for p in ('P1','P2','P3')},
            'bankable_revenue_approved': False, 'errors': errs or [],
            'screening_total_incremental_group_cm_rub': '290'}


class ReleaseJoinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)

    def run_case(self, pa=None, cross_case=None, code1=0, code2=0):
        responses = [FakeProc(pa if pa is not None else pilots(), code1),
                     FakeProc(cross_case if cross_case is not None else cross(), code2)]
        with patch('release_commercial_v23.subprocess.run', side_effect=responses) as mock:
            result = audit(self.repo)
            self.assertEqual(mock.call_count, 2)
            return result

    def test_both_hold_does_not_admit(self):
        r = self.run_case()
        self.assertEqual(r['status'], 'HOLD')
        self.assertIsNone(r['cross_pilot_incremental_group_cm_rub'])
        self.assertFalse(r['bankable_revenue_approved'])

    def test_only_cross_review_still_hold(self):
        self.assertEqual(self.run_case(cross_case=cross('REVIEW'))['status'], 'HOLD')

    def test_only_pilots_review_still_hold(self):
        self.assertEqual(self.run_case(pa=pilots('REVIEW'))['status'], 'HOLD')

    def test_all_review_is_still_not_investment_pass(self):
        r = self.run_case(pa=pilots('REVIEW'), cross_case=cross('REVIEW'))
        self.assertEqual(r['status'], 'REVIEW')
        self.assertEqual(r['cross_pilot_incremental_group_cm_rub'], '290')
        self.assertFalse(r['bankable_revenue_approved'])
        self.assertFalse(r['investment_approved'])

    def test_cross_invalid_blocks_all(self):
        r = self.run_case(pa=pilots('REVIEW'), cross_case=cross('INVALID', ['duplicate']))
        self.assertEqual(r['status'], 'INVALID')

    def test_cross_nonzero_exit_is_invalid(self):
        self.assertEqual(self.run_case(code2=2)['status'], 'INVALID')

    def test_one_individual_status_missing_still_hold(self):
        bad = pilots('REVIEW')
        bad['results'][0]['gate'] = 'HOLD'
        self.assertEqual(self.run_case(pa=bad, cross_case=cross('REVIEW'))['status'], 'HOLD')

    def test_missing_pilot_is_invalid(self):
        bad = pilots()
        bad['results'].pop()
        self.assertEqual(self.run_case(pa=bad)['status'], 'INVALID')

    def test_unknown_cross_status_is_invalid(self):
        self.assertEqual(self.run_case(cross_case=cross('PASS'))['status'], 'INVALID')

    def test_incorrect_bankable_flag_is_invalid(self):
        bad = pilots('REVIEW')
        bad['results'][0]['bankable_revenue_approved'] = True
        self.assertEqual(self.run_case(pa=bad, cross_case=cross('REVIEW'))['status'], 'INVALID')

    def test_one_pilot_error_is_invalid(self):
        self.assertEqual(self.run_case(pa=pilots(errs=['broken inputs']))['status'], 'INVALID')

    def test_invalid_json_from_subprocess_blocks(self):
        corrupted = FakeProc(cross())
        corrupted.stdout = 'not valid json'
        with patch('release_commercial_v23.subprocess.run', side_effect=[FakeProc(pilots()), corrupted]):
            r = audit(self.repo)
        self.assertEqual(r['status'], 'INVALID')

    def test_index_and_dir_must_both_exist(self):
        self.assertEqual(audit(self.repo, index=self.repo / 'index.json')['status'], 'INVALID')


if __name__ == '__main__':
    unittest.main()

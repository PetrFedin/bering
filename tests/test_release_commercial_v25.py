"""V25 controller unit tests: synthetic child report data, no real actors."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from release_commercial_v25 import audit


class Result:
    def __init__(self, body, code=0):
        self.stdout = json.dumps(body)
        self.stderr = ''
        self.returncode = code


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        area = self.root/'data'/'pilots'
        area.mkdir(parents=True)
        self.p23 = area/'V23_cross_pilot_unverified.json'
        self.p24 = area/'V24_identity_unverified.json'
        self.p25 = area/'V25_documentary_unverified.json'
        self.p23.write_text('{"schema_version":"V23","shipments":[]}')
        self.p24.write_text('{"schema_version":"V24","shipments":[]}')
        self.p25.write_text('{"schema_version":"V25","shipments":[]}')
        self.h23 = hashlib.sha256(self.p23.read_bytes()).hexdigest()
        self.h24 = hashlib.sha256(self.p24.read_bytes()).hexdigest()

    def make_old(self, status='HOLD'):
        return {'status':status,'cross_input_sha256':self.h23,
                'bankable_revenue_approved':False, 'investment_approved':False,
                'incremental_group_cm_rub_screening_only':'99.00'}

    def make_new(self,status='HOLD'):
        return {'status':status,'v23_source_sha256':self.h23,'v24_source_sha256':self.h24,
                'bankable_revenue_approved':False, 'investment_approved':False,
                'source_content_authenticated':False,'cash_reconciled_with_bank':False,
                'physical_container_units':0,'source_evidence_files_verified':0}

    def run_case(self,old=None,new=None, codes=(0,0)):
        out=[Result(old if old is not None else self.make_old(),codes[0]),
             Result(new if new is not None else self.make_new(),codes[1])]
        with patch('release_commercial_v25.subprocess.run',side_effect=out) as fn:
            receipt = audit(self.root)
            self.assertEqual(fn.call_count,2)
            old_args, new_args = [c.args[0] for c in fn.call_args_list]
            self.assertEqual(old_args[old_args.index('--cross-input')+1],
                             new_args[new_args.index('--v23')+1])
            self.assertEqual(old_args[old_args.index('--identity-input')+1],
                             new_args[new_args.index('--v24')+1])
        return receipt

    def test_01_both_hold_holds(self):
        self.assertEqual(self.run_case()['status'],'HOLD')

    def test_02_old_review_only_holds(self):
        self.assertEqual(self.run_case(old=self.make_old('REVIEW'))['status'],'HOLD')

    def test_03_new_review_only_holds(self):
        self.assertEqual(self.run_case(new=self.make_new('REVIEW'))['status'],'HOLD')

    def test_04_both_review_still_not_investment_pass(self):
        report=self.run_case(self.make_old('REVIEW'),self.make_new('REVIEW'))
        self.assertEqual(report['status'],'REVIEW')
        self.assertEqual(report['screening_incremental_group_cm_rub'],'99.00')
        self.assertFalse(report['investment_approved'])
        self.assertFalse(report['cash_independently_confirmed'])
        self.assertFalse(report['contracts_authenticated'])

    def test_05_old_invalid_rejects(self):
        self.assertEqual(self.run_case(old=self.make_old('INVALID'))['status'],'INVALID')

    def test_06_new_invalid_rejects(self):
        self.assertEqual(self.run_case(new=self.make_new('INVALID'))['status'],'INVALID')

    def test_07_unknown_status_rejects(self):
        self.assertEqual(self.run_case(new=self.make_new('PASS'))['status'],'INVALID')

    def test_08_wrong_new_sha23_rejects(self):
        q=self.make_new('REVIEW');q['v23_source_sha256']='f'*64
        self.assertEqual(self.run_case(self.make_old('REVIEW'),q)['status'],'INVALID')

    def test_09_wrong_new_sha24_rejects(self):
        q=self.make_new('REVIEW');q['v24_source_sha256']='f'*64
        self.assertEqual(self.run_case(self.make_old('REVIEW'),q)['status'],'INVALID')

    def test_10_wrong_old_sha23_rejects(self):
        q=self.make_old('REVIEW');q['cross_input_sha256']='f'*64
        self.assertEqual(self.run_case(q,self.make_new('REVIEW'))['status'],'INVALID')

    def test_11_source_changes_during_run_rejects(self):
        out=[Result(self.make_old('REVIEW')),Result(self.make_new('REVIEW'))]
        def change_file(*args,**kwargs):
            v=out.pop(0)
            self.p23.write_text(self.p23.read_text()+'\n')
            return v
        with patch('release_commercial_v25.subprocess.run',side_effect=change_file):
            value=audit(self.root)
        self.assertEqual(value['status'],'INVALID')

    def test_12_gross_cash_self_authentication_rejects(self):
        q=self.make_new('REVIEW');q['cash_reconciled_with_bank']=True
        self.assertEqual(self.run_case(self.make_old('REVIEW'),q)['status'],'INVALID')

    def test_13_bankability_true_rejects(self):
        q=self.make_new('REVIEW');q['bankable_revenue_approved']=True
        self.assertEqual(self.run_case(self.make_old('REVIEW'),q)['status'],'INVALID')

    def test_14_investment_true_rejects(self):
        q=self.make_old('REVIEW');q['investment_approved']=True
        self.assertEqual(self.run_case(q,self.make_new('REVIEW'))['status'],'INVALID')

    def test_15_child_nonzero_rejects(self):
        self.assertEqual(self.run_case(codes=(0,3))['status'],'INVALID')

    def test_16_empty_child_stdout_rejects(self):
        good = Result(self.make_old())
        bad = Result(self.make_new()); bad.stdout = ''
        with patch('release_commercial_v25.subprocess.run', side_effect=[good, bad]):
            self.assertEqual(audit(self.root)['status'], 'INVALID')

    def test_17_missing_file_rejects(self):
        self.p25.unlink()
        self.assertEqual(audit(self.root)['status'],'INVALID')

    def test_18_one_sided_evidence_input_rejects(self):
        self.assertEqual(audit(self.root,evidence_index=self.root/'manifest.json')['status'],'INVALID')

    def test_19_both_paths_always_forwarded(self):
        out=[Result(self.make_old()),Result(self.make_new())]
        with patch('release_commercial_v25.subprocess.run',side_effect=out) as fn:
            res=audit(self.root,evidence_index=self.root/'manifest.json',evidence_dir=self.root/'sources')
            self.assertEqual(res['status'],'HOLD')
            for c in fn.call_args_list:
                self.assertIn('--evidence-index',c.args[0]);self.assertIn('--evidence-dir',c.args[0])


if __name__=='__main__':
    unittest.main()

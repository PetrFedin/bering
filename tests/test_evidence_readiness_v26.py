"""V26 evidence intake coverage tests with synthetic, noncommercial bytes."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'scripts'))
from evidence_readiness_v26 import evaluate, COMMON, SPECIAL


class IntakeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = json.loads((BASE/'data/pilots/V26_EMPTY_PROOF_INTAKE.json').read_text())

    def setUp(self):
        self.p = copy.deepcopy(self.template)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def slot(self, pilot='P1', key='customer_order'):
        return self.p['pilots'][pilot][key]

    def attach(self, pilot='P1', key='customer_order', evidence_id=None):
        ident = evidence_id or f'EV-{pilot}_{key.upper()}'
        raw = ('SYNTHETIC SOURCE FOR '+ident).encode('utf-8')
        path = ident+'.txt'
        (self.root/path).write_bytes(raw)
        self.p['pilots'][pilot][key] = {
            'status': 'PRESENT_FOR_REVIEW',
            'evidence_id': ident,
            'relative_path': path,
            'sha256': hashlib.sha256(raw).hexdigest(),
            'source_org_id': f'ORG_{pilot}_FAKE',
            'submitted_by': 'fake_submitter',
            'reviewed_by': 'fake_reviewer',
            'reviewed_on': '2026-10-30',
        }
        return self.p['pilots'][pilot][key]

    def test_default_missing_is_hold_not_zero_demand(self):
        r = evaluate(self.p)
        self.assertEqual(r['status'], 'HOLD')
        self.assertEqual(r['total_proof_categories'], 29)
        self.assertEqual(r['source_categories_with_locally_verified_bytes'], 0)
        self.assertEqual(r['per_pilot']['P1']['source_categories_required'], 9)
        self.assertEqual(r['per_pilot']['P2']['source_categories_required'], 10)
        self.assertEqual(r['per_pilot']['P3']['source_categories_required'], 10)
        self.assertIsNone(r['new_40ft_volume'])
        self.assertIsNone(r['incremental_group_cm_rub'])
        self.assertFalse(r['bankable_revenue_approved'])

    def test_single_valid_byte_document_only_one_category(self):
        self.attach()
        r = evaluate(self.p,self.root)
        self.assertEqual(r['status'], 'HOLD')
        self.assertEqual(r['source_categories_with_locally_verified_bytes'], 1)
        self.assertEqual(r['per_pilot']['P1']['source_categories_missing_or_unverified'], 8)

    def test_file_without_independent_data_root_does_not_count(self):
        self.attach()
        self.assertEqual(evaluate(self.p)['source_categories_with_locally_verified_bytes'],0)

    def test_all_referenced_sources_still_not_bankable(self):
        for pilot in SPECIAL:
            for field in (*COMMON,*SPECIAL[pilot]):
                self.attach(pilot,field)
        r = evaluate(self.p,self.root)
        self.assertEqual(r['status'],'READY_FOR_MANUAL_EXTERNAL_AUTHENTICITY_REVIEW')
        self.assertEqual(r['source_categories_with_locally_verified_bytes'],29)
        self.assertFalse(r['investment_approved'])
        self.assertFalse(r['bank_receipts_independently_authenticated'])

    def test_corrupted_bytes_drop_coverage(self):
        slot = self.attach()
        (self.root/slot['relative_path']).write_text('ALTERED')
        self.assertEqual(evaluate(self.p,self.root)['source_categories_with_locally_verified_bytes'],0)

    def test_same_reviewer_as_submitter_is_not_independent(self):
        slot = self.attach()
        slot['reviewed_by'] = slot['submitted_by']
        self.assertEqual(evaluate(self.p,self.root)['status'],'HOLD')
        self.assertEqual(evaluate(self.p,self.root)['source_categories_with_locally_verified_bytes'],0)

    def test_future_review_date_fails_coverage(self):
        self.attach()['reviewed_on']='2026-11-02'
        self.assertEqual(evaluate(self.p,self.root)['source_categories_with_locally_verified_bytes'],0)

    def test_symlink_escape_never_reads_file(self):
        slot = self.attach()
        bad = self.root/slot['relative_path']
        real = self.root.parent / (self.root.name+'_secret')
        real.write_text('SYNTHETIC')
        self.addCleanup(real.unlink)
        bad.unlink()
        bad.symlink_to(real)
        self.assertEqual(evaluate(self.p,self.root)['source_categories_with_locally_verified_bytes'],0)

    def test_relative_path_traversal_rejected(self):
        self.attach()['relative_path'] = '../secret.csv'
        self.assertEqual(evaluate(self.p,self.root)['source_categories_with_locally_verified_bytes'],0)

    def test_missing_marked_with_document_claim_is_invalid(self):
        self.slot()['sha256']='a'*64
        self.assertEqual(evaluate(self.p)['status'],'INVALID')

    def test_unknown_category_blocks_all(self):
        self.p['pilots']['P1']['bogus']='not supported'
        self.assertEqual(evaluate(self.p)['status'],'INVALID')

    def test_missing_p2_reefer_specific_requirement_invalid(self):
        self.p['pilots']['P2'].pop('reefer_temperature_energy')
        self.assertEqual(evaluate(self.p)['status'],'INVALID')

    def test_missing_p3_customs_specific_requirement_invalid(self):
        self.p['pilots']['P3'].pop('feeder_and_customs_clearance')
        self.assertEqual(evaluate(self.p)['status'],'INVALID')

    def test_extra_pilot_invalid(self):
        self.p['pilots']['P4']={}
        self.assertEqual(evaluate(self.p)['status'],'INVALID')

    def test_invoice_and_bank_can_not_reuse_same_evidence_id_without_review(self):
        first=self.attach('P1','invoice_net_vat_gross',evidence_id='EV-P1_SHARED_ACCOUNT')
        second=self.attach('P1','independent_bank_settlement',evidence_id='EV-P1_SHARED_ACCOUNT')
        r=evaluate(self.p,self.root)
        self.assertEqual(r['status'],'HOLD')
        self.assertTrue(r['duplicates_for_review'])

    def test_no_gross_money_claim_from_file_hash(self):
        self.attach('P1','independent_bank_settlement')
        r=evaluate(self.p,self.root)
        self.assertFalse(r['bank_receipts_independently_authenticated'])
        self.assertIsNone(r['new_40ft_volume'])

    def test_unbounded_review_identity_invalid_for_coverage(self):
        self.attach()['reviewed_by']='a'*101
        self.assertEqual(evaluate(self.p,self.root)['source_categories_with_locally_verified_bytes'],0)

    def test_invalid_asof_rejected(self):
        self.p['as_of']='2026-02-31'
        self.assertEqual(evaluate(self.p)['status'],'INVALID')

    def test_future_asof_rejected(self):
        self.p['as_of']='2090-01-01'
        self.assertEqual(evaluate(self.p)['status'],'INVALID')

    def test_unknown_status_invalid(self):
        self.slot()['status']='BANK_SETTLED'
        self.assertEqual(evaluate(self.p)['status'],'INVALID')

    def test_type_malformed_input_rejected(self):
        self.p['pilots']['P1']['customer_order']=[]
        self.assertEqual(evaluate(self.p)['status'],'INVALID')


if __name__ == '__main__':
    unittest.main()

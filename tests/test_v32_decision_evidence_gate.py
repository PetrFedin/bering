"""V32 proof integrity: data quality, path safety and no financial promotion."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from v32_decision_evidence_gate import (evaluate, check_docket,
                                        check_local_submission, IDS)

DOCKET=json.loads((ROOT/'data/evidence/V32_DECISION_DOCUMENT_DOCKET.json').read_text())

class DocketTests(unittest.TestCase):
    def test_baseline_is_hold(self):
        r=evaluate(ROOT)
        self.assertEqual(r['status'],'HOLD',r['errors'])
        self.assertEqual(r['required_document_categories'],12)
        self.assertIsNone(r['private_documents_with_recomputed_matching_sha256'])
        self.assertEqual(r['required_group_months'],96)
        self.assertEqual(r['source_verified_group_months'],0)
        self.assertIsNone(r['bering_npv_rub'])
        self.assertFalse(r['investment_approved'])

    def test_all_required_ids_are_unique(self):
        self.assertEqual(len(IDS),len(set(IDS)))
        self.assertEqual(len(DOCKET['records']),len(IDS))

    def invalid_edit(self, mutate):
        d=copy.deepcopy(DOCKET)
        mutate(d)
        self.assertTrue(check_docket(d))
        self.assertEqual(evaluate_with_copy(d)['status'],'INVALID')

    def test_missing_vs_zero_immutable(self):
        self.invalid_edit(lambda d:d['records'][0].__setitem__('status','ZERO'))
        self.invalid_edit(lambda d:d.__setitem__('signed_commercial_paid_40ft',0))

    def test_spurious_document(self):
        self.invalid_edit(lambda d:d['records'].append({**d['records'][0],'id':'BOGUS'}))

    def test_duplicate_document(self):
        self.invalid_edit(lambda d:d['records'].append(copy.deepcopy(d['records'][0])))

    def test_missing_document(self):
        self.invalid_edit(lambda d:d['records'].pop())

    def test_fake_signed_original(self):
        self.invalid_edit(lambda d:d['records'][2].__setitem__('signed_original_authenticated',True))

    def test_fake_payment(self):
        self.invalid_edit(lambda d:d['records'][7].__setitem__('decision_value',550000))

    def test_fake_review(self):
        self.invalid_edit(lambda d:d['records'][11].__setitem__('independent_content_reviewed',True))

    def test_fake_authority(self):
        self.invalid_edit(lambda d:d['records'][2].__setitem__('source_identity_verified',True))

    def test_unknown_field(self):
        self.invalid_edit(lambda d:d['records'][0].__setitem__('fantasy',True))

    def test_promote_coverage(self):
        self.invalid_edit(lambda d:d.__setitem__('prior_24m_od_slots_verified',96))

    def test_promote_green(self):
        self.invalid_edit(lambda d:d.__setitem__('ci_green_on_single_sha',True))

    def test_prior_snapshot_sha_frozen(self):
        self.invalid_edit(lambda d:d.__setitem__('source_reference_sha','0'*40))

    def test_empty_claims_or_bad_docket(self):
        for p in (None,{},[],{'records':[]},'stuff'):
            with self.subTest(docket=p):
                self.assertTrue(check_docket(p))

    def test_unhashable_doc_id_fails_closed(self):
        self.invalid_edit(lambda d:d['records'][0].__setitem__('id', []))

    def test_duplicate_record_id_detected(self):
        d=copy.deepcopy(DOCKET)
        d['records'][1]['id']=d['records'][0]['id']
        self.assertIn('DUPLICATED_DOCKET_ID',check_docket(d))

class PrivateByteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)/'repo'
        (self.repo/'data/evidence').mkdir(parents=True)
        (self.repo/'data/evidence/V32_DECISION_DOCUMENT_DOCKET.json').write_text(json.dumps(DOCKET))
        self.private=self.repo/'local_private'
        self.private.mkdir()
        self.vault=self.private/'raw'
        self.vault.mkdir()
        self.manifest=self.private/'submission.json'
        self.doc=self.vault/'test.pdf'
        self.doc.write_bytes(b'%PDF-1.4\nTEST-ONLY-NOT-REAL\n')
        self.actual_hash=hashlib.sha256(self.doc.read_bytes()).hexdigest()
        self.write_manifest([self.row()])

    def row(self):
        return {'docket_id':IDS[0],'relative_path':'test.pdf','sha256':self.actual_hash}

    def write_manifest(self,rows):
        self.manifest.write_text(json.dumps({'schema':'V32_PRIVATE_BYTES_SUBMISSION_V1','documents':rows}))

    def eval(self):
        return evaluate(self.repo,self.manifest,self.vault)

    def test_private_digest_matches_not_certification(self):
        r=self.eval()
        self.assertEqual(r['status'],'HOLD',r['errors'])
        self.assertEqual(r['private_documents_with_recomputed_matching_sha256'],1)
        self.assertFalse(r['local_sha_check_is_signature_verification'])
        self.assertFalse(r['local_sha_check_is_payment_verification'])
        self.assertFalse(r['investment_approved'])
        self.assertIsNone(r['paid_incremental_40ft'])

    def test_no_submission_is_not_zero(self):
        r=evaluate(self.repo)
        self.assertEqual(r['status'],'HOLD')
        self.assertIsNone(r['private_documents_with_recomputed_matching_sha256'])

    def test_pair_must_be_present(self):
        self.assertEqual(evaluate(self.repo,self.manifest,None)['status'],'INVALID')
        self.assertEqual(evaluate(self.repo,None,self.vault)['status'],'INVALID')

    def test_detect_bad_hash(self):
        self.write_manifest([{**self.row(),'sha256':'f'*64}])
        self.assertIn('DOCUMENT_SHA256_MISMATCH',self.eval()['errors'])

    def test_reject_untracked_missing_file(self):
        self.doc.unlink()
        self.assertIn('DOCUMENT_BYTES_MISSING',self.eval()['errors'])

    def test_reject_duplicate_category(self):
        self.write_manifest([self.row(),self.row()])
        self.assertIn('UNEXPECTED_OR_DUPLICATE_DOCUMENT_ID',self.eval()['errors'])

    def test_reject_path_traversal(self):
        self.write_manifest([{**self.row(),'relative_path':'../submission.json'}])
        self.assertIn('UNSAFE_FILE_REFERENCE',self.eval()['errors'])

    def test_reject_absolute_path(self):
        self.write_manifest([{**self.row(),'relative_path':str(self.doc)}])
        self.assertIn('UNSAFE_FILE_REFERENCE',self.eval()['errors'])

    def test_reject_symlink_within_vault(self):
        symlink=self.vault/'symlink.pdf'
        symlink.symlink_to(self.doc)
        self.write_manifest([{**self.row(),'relative_path':'symlink.pdf'}])
        self.assertIn('UNSAFE_DOCUMENT_LOCATION',self.eval()['errors'])

    def test_reject_external_vault(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            p=Path(elsewhere)
            self.assertEqual(evaluate(self.repo,self.manifest,p)['status'],'INVALID')

    def test_reject_unapproved_json_fields(self):
        self.write_manifest([{**self.row(),'signature_verified':True}])
        self.assertIn('INVALID_SUBMISSION_ROW',self.eval()['errors'])

    def test_empty_file_rejected(self):
        self.doc.write_bytes(b'')
        self.assertIn('DOCUMENT_BYTES_INVALID_LENGTH',self.eval()['errors'])

    def test_empty_submission_is_hold_not_false_positive(self):
        self.write_manifest([])
        r=self.eval()
        self.assertEqual(r['status'],'HOLD')
        self.assertEqual(r['private_documents_with_recomputed_matching_sha256'],0)
        self.assertFalse(r['independent_engineering_financial_acceptance'])

    def test_manifest_outside_private_is_rejected(self):
        path=self.repo/'outside.json'
        path.write_text(self.manifest.read_text())
        self.assertEqual(evaluate(self.repo,path,self.vault)['status'],'INVALID')


def evaluate_with_copy(data):
    # Exercise evaluation through the full reader, not only the dictionary helper.
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        (root/'data/evidence').mkdir(parents=True)
        (root/'data/evidence/V32_DECISION_DOCUMENT_DOCKET.json').write_text(json.dumps(data))
        return evaluate(root)

if __name__=='__main__':
    unittest.main()

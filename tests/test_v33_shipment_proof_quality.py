"""All non-empty records in this suite are FAKE test fixtures, NOT Bering cargo."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from v33_shipment_proof_quality import (analyze, empty_input, safe_private_path,
                                        digest_file, MONTHS, GROUPS, SCHEMA,
                                        SOURCE_NOTICE)

FAKE_HASH = 'a' * 64

def coverage(scope='P1', month='2025-01', count=1):
    return {
        'scope': scope, 'month': month,
        'coverage_status': 'ATTESTED_NONZERO' if count else 'ATTESTED_ZERO',
        'attestation_sha256': FAKE_HASH,
        'source_row_locator': 'SOURCE_ROW_001',
        'reported_container_count': count,
    }


def shipment(scope='P1', month='2025-01', token='CONTAINER_001', size=40):
    return {
        'shipment_token':'SHIPMENT_0001', 'container_token':token,
        'scope':scope, 'month':month, 'origin_token':'ORIGIN_001',
        'destination_token':'DESTINATION_01', 'container_size_ft':size,
        'teu':size//20, 'waybill_token':'WAYBILL_001',
        'receiving_token':'RECEIVING_01', 'invoice_token':'INVOICE_001',
        'dispatch_on':month+'-12','received_on':month+'-19',
        'waybill_sha256':FAKE_HASH,'receipt_sha256':FAKE_HASH,
        'invoice_sha256':FAKE_HASH,'bank_statement_sha256':FAKE_HASH,
        'invoice_total_minor':'100000','credit_note_minor':'10000',
        'bank_paid_minor':'90000','currency':'RUB',
        'source_sha256':FAKE_HASH,'source_row_locator':'SOURCE_ROW_001',
        'incumbent_route_token':None,
    }


def fake_extract(ships=None, cover=None):
    p=empty_input()
    p['shipments'] = [shipment()] if ships is None else ships
    p['monthly_coverage'] = [coverage()] if cover is None else cover
    return p

class StaticContractTest(unittest.TestCase):
    def test_empty_is_unknown_not_zero(self):
        r=analyze(empty_input())
        self.assertEqual(r['status'],'NO_SOURCE_RECORDS_IN_SCOPE',r['errors'])
        self.assertEqual(r['missing_month_slots'],96)
        self.assertEqual(r['claimed_attested_months'],0)
        self.assertEqual(r['confirmed_attested_months'],0)
        self.assertIsNone(r['new_paid_bering_40ft'])
        self.assertIsNone(r['bering_npv_rub'])

    def test_synthetic_source_still_not_authenticated(self):
        r=analyze(fake_extract())
        self.assertEqual(r['status'],'STRUCTURAL_REVIEW_REQUIRED',r['errors'])
        self.assertEqual(r['structurally_fully_paid_rows'],1)
        self.assertEqual(r['structural_container_rows'],1)
        self.assertEqual(r['claimed_attested_months'],1)
        self.assertEqual(r['confirmed_attested_months'],0)
        self.assertFalse(r['bank_settlement_verified_independently'])
        self.assertFalse(r['source_signature_verified'])
        self.assertFalse(r['investment_approved'])

    def reject(self, alter, base=None, expected=None):
        p=copy.deepcopy(base or fake_extract())
        alter(p)
        r=analyze(p)
        self.assertEqual(r['status'],'INVALID',r['errors'])
        if expected:
            self.assertIn(expected,r['errors'])
        self.assertIsNone(r['new_paid_bering_40ft'])
        self.assertFalse(r['investment_approved'])

    def test_invalid_source_schema(self):
        self.reject(lambda p:p.update(schema='FAKE'),expected='WRONG_SOURCE_SCHEMA_OR_ATTESTATION_WARNING')
    def test_bare_array_rejected(self):
        self.assertEqual(analyze([])['status'],'INVALID')
    def test_unknown_root_field_rejected(self):
        self.reject(lambda p:p.update(paid=True),expected='WRONG_TOP_LEVEL_SCHEMA')
    def test_unknown_month_status(self):
        self.reject(lambda p:p['monthly_coverage'][0].update(coverage_status='GUESSED'),expected='UNKNOWN_MONTH_STATUS')
    def test_missing_month_attestation(self):
        self.reject(lambda p:p['monthly_coverage'][0].update(attestation_sha256=None),expected='MISSING_MONTH_SOURCE_REFERENCE')
    def test_attested_zero_requires_no_shipments(self):
        self.reject(lambda p:p['monthly_coverage'][0].update(coverage_status='ATTESTED_ZERO',reported_container_count=0), expected='MONTH_TOTAL_NOT_RECONCILED_TO_CONTAINERS')
    def test_zero_false_but_positive_claim(self):
        self.reject(lambda p:p['monthly_coverage'][0].update(coverage_status='ATTESTED_NONZERO',reported_container_count=0),expected='MONTH_STATUS_COUNT_CONTRADICTION')
    def test_undocumented_shipment(self):
        self.reject(lambda p:p.update(monthly_coverage=[]),expected='SHIPMENT_WITHOUT_ATTESTED_MONTH')
    def test_month_total_mismatch(self):
        self.reject(lambda p:p['monthly_coverage'][0].update(reported_container_count=2),expected='MONTH_TOTAL_NOT_RECONCILED_TO_CONTAINERS')
    def test_duplicate_month(self):
        self.reject(lambda p:p['monthly_coverage'].append(copy.deepcopy(p['monthly_coverage'][0])),expected='DUPLICATE_OR_OUT_OF_PERIOD_MONTH')
    def test_month_outside_window(self):
        self.reject(lambda p:p['monthly_coverage'][0].update(month='2026-10'),expected='DUPLICATE_OR_OUT_OF_PERIOD_MONTH')
    def test_40ft_is_two_teu(self):
        self.reject(lambda p:p['shipments'][0].update(teu=1),expected='CONTAINER_TEU_UNIT_MISMATCH')
    def test_20ft_is_one_teu(self):
        p=fake_extract();p['shipments'][0].update(container_size_ft=20,teu=1)
        self.assertEqual(analyze(p)['status'],'STRUCTURAL_REVIEW_REQUIRED')
    def test_negative_minor_units_not_allowed(self):
        self.reject(lambda p:p['shipments'][0].update(bank_paid_minor='-100'),expected='AMOUNTS_NOT_MINOR_UNIT_STRINGS')
    def test_decimal_minor_units_not_allowed(self):
        self.reject(lambda p:p['shipments'][0].update(invoice_total_minor='100.00'),expected='AMOUNTS_NOT_MINOR_UNIT_STRINGS')
    def test_credits_beyond_invoice_rejected(self):
        self.reject(lambda p:p['shipments'][0].update(credit_note_minor='999999'),expected='INVOICE_CREDIT_BANK_RECONCILIATION_FAILED')
    def test_overpayment_rejected(self):
        self.reject(lambda p:p['shipments'][0].update(bank_paid_minor='99000'),expected='INVOICE_CREDIT_BANK_RECONCILIATION_FAILED')
    def test_partial_payment_not_full(self):
        p=fake_extract();p['shipments'][0]['bank_paid_minor']='45000'
        r=analyze(p);self.assertEqual(r['status'],'STRUCTURAL_REVIEW_REQUIRED',r['errors']);self.assertEqual(r['structurally_fully_paid_rows'],0)
    def test_missing_bank_hash_rejected(self):
        self.reject(lambda p:p['shipments'][0].update(bank_statement_sha256=None),expected='MISSING_DOCUMENT_HASH_bank_statement_sha256')
    def test_zero_net_invoice_not_paid(self):
        p=fake_extract();p['shipments'][0].update(credit_note_minor='100000',bank_paid_minor='0')
        r=analyze(p);self.assertEqual(r['status'],'STRUCTURAL_REVIEW_REQUIRED',r['errors']);self.assertEqual(r['structurally_fully_paid_rows'],0)
    def test_time_order_rejected(self):
        self.reject(lambda p:p['shipments'][0].update(received_on='2025-01-08'),expected='SHIPMENT_DATE_OR_MONTH_INCONSISTENT')
    def test_dispatch_month_must_match(self):
        self.reject(lambda p:p['shipments'][0].update(dispatch_on='2025-02-10'),expected='SHIPMENT_DATE_OR_MONTH_INCONSISTENT')
    def test_duplicate_waybill_container(self):
        p=fake_extract();other=shipment(token='CONTAINER_001');other['shipment_token']='SHIPMENT_0002'
        p['shipments'].append(other);p['monthly_coverage'][0]['reported_container_count']=2
        self.reject(lambda z:None,p,'DUPLICATE_WAYBILL_CONTAINER')
    def test_duplicate_physical_container(self):
        p=fake_extract();p['shipments'].append(copy.deepcopy(p['shipments'][0]));p['monthly_coverage'][0]['reported_container_count']=2
        self.reject(lambda z:None,p,'DUPLICATE_PHYSICAL_CONTAINER')
    def test_multi_pilot_same_shipment_is_not_double_growth(self):
        p=fake_extract()
        extra=shipment(scope='P2');extra['waybill_token']='WAYBILL_002';extra['invoice_token']='INVOICE_002'
        p['shipments'].append(extra);p['monthly_coverage'].append(coverage(scope='P2'))
        self.reject(lambda z:None,p,'SAME_CONTAINER_CLAIMED_BY_MULTIPLE_PILOTS')
    def test_existing_group_overlap_flags_possible_cannibalization(self):
        p=fake_extract();extra=shipment(scope='GROUP_EXISTING');extra['waybill_token']='WAYBILL_002'
        p['shipments'].append(extra);p['monthly_coverage'].append(coverage(scope='GROUP_EXISTING'))
        r=analyze(p)
        self.assertEqual(r['status'],'STRUCTURAL_REVIEW_REQUIRED',r['errors']);self.assertEqual(r['candidate_same_shipment_group_overlap'],1)
        self.assertIsNone(r['incremental_group_contribution_margin_rub'])
    def test_container_reuse_different_shipments_is_not_cannibalization(self):
        p=fake_extract();extra=shipment(scope='GROUP_EXISTING');extra['shipment_token']='SHIPMENT_002';extra['waybill_token']='WAYBILL_002'
        p['shipments'].append(extra);p['monthly_coverage'].append(coverage(scope='GROUP_EXISTING'))
        r=analyze(p)
        self.assertEqual(r['status'],'STRUCTURAL_REVIEW_REQUIRED',r['errors'])
        self.assertEqual(r['candidate_same_shipment_group_overlap'],0)
        self.assertEqual(r['candidate_container_month_collisions'],1)
    def test_opaque_container_id_reused_across_months_no_collision(self):
        p=fake_extract();extra=shipment(scope='GROUP_EXISTING',month='2025-02')
        extra['shipment_token']='SHIPMENT_002';extra['waybill_token']='WAYBILL_002'
        p['shipments'].append(extra);p['monthly_coverage'].append(coverage(scope='GROUP_EXISTING',month='2025-02'))
        r=analyze(p)
        self.assertEqual(r['status'],'STRUCTURAL_REVIEW_REQUIRED',r['errors'])
        self.assertEqual(r['candidate_container_month_collisions'],0)
    def test_malformed_type_is_rejected_without_crash(self):
        self.reject(lambda p:p['shipments'][0].update(container_token=['list']),expected='INVALID_MASKED_TOKEN_container_token')
        self.reject(lambda p:p['monthly_coverage'][0].update(scope=[]),expected='MONTH_SCOPE_OR_DATE_INVALID')
        self.reject(lambda p:p['shipments'][0].update(month=[]),expected='SHIPMENT_SCOPE_OR_DATE_INVALID')
    def test_invalid_currency(self):
        self.reject(lambda p:p['shipments'][0].update(currency='XXX'),expected='CURRENCY_NOT_ALLOWED')
    def test_bad_date_rejected(self):
        self.reject(lambda p:p['shipments'][0].update(received_on='not-a-date'),expected='SHIPMENT_DATES_INVALID')
    def test_duplicate_fields_unauthorized(self):
        self.reject(lambda p:p['shipments'][0].update(investment_approved=True),expected='INVALID_SHIPMENT_FIELDS')
    def test_empty_attested_zero_is_structural_not_proof(self):
        p=fake_extract(ships=[],cover=[coverage(count=0)])
        r=analyze(p)
        self.assertEqual(r['status'],'STRUCTURAL_REVIEW_REQUIRED',r['errors']);self.assertEqual(r['confirmed_attested_months'],0)
    def test_no_shipment_with_claimed_nonzero_mismatch(self):
        p=fake_extract(ships=[],cover=[coverage(count=1)])
        self.assertEqual(analyze(p)['status'],'INVALID')

class PrivateInputTest(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory();self.addCleanup(self.dir.cleanup)
        self.root=Path(self.dir.name)/'repo';self.private=self.root/'local_private';self.private.mkdir(parents=True)
        self.doc=self.private/'od.json';self.doc.write_text(json.dumps(fake_extract()))
    def test_private_path_and_digest(self):
        self.assertEqual(safe_private_path(self.root,self.doc),self.doc)
        self.assertEqual(digest_file(self.doc),hashlib.sha256(self.doc.read_bytes()).hexdigest())
    def test_private_path_outside_denied(self):
        with self.assertRaises(ValueError):safe_private_path(self.root,self.root/'public.json')
    def test_private_filename_traversal_denied(self):
        with self.assertRaises(ValueError):safe_private_path(self.root,self.private/'..'/'public.json')
    def test_symlinked_parent_denied(self):
        (self.private/'linked').symlink_to(self.private, target_is_directory=True)
        with self.assertRaises(ValueError):safe_private_path(self.root,self.private/'linked'/'od.json')
    def test_missing_source_denied(self):
        with self.assertRaises(ValueError):safe_private_path(self.root,self.private/'missing.json')
    def test_source_folders_never_importable_as_evidence(self):
        self.assertEqual(len(GROUPS)*len(MONTHS),96)

if __name__ == '__main__':
    unittest.main()

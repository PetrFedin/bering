"""V25 unit tests use fabricated data only, including synthetic evidence files."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from independent_custody_payment_v25 import evaluate, as_utc, amount
from shipment_identity_v24 import iso6346_check_digit


def container(idx):
    first = f'ABCU{120000 + idx:06d}'
    return first + iso6346_check_digit(first)


class V25Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.index = {}
        self.v23 = {'schema_version': 'V23', 'as_of': '2026-10-31',
                    'group_id': 'GROUP_BERING_FAKE', 'shipments': []}
        self.v24 = {'schema_version': 'V24', 'as_of': '2026-10-31',
                    'group_id': 'GROUP_BERING_FAKE', 'shipments': []}
        self.v25 = {'schema_version': 'V25', 'as_of': '2026-10-31',
                    'group_id': 'GROUP_BERING_FAKE', 'currency': 'RUB', 'shipments': []}
        for i, pilot in enumerate(('P1', 'P2', 'P3'), 1):
            ship = f'SHIP_FAKE_{i:04d}'
            waybill = f'EV-WAYBILL_{i:04d}'
            payid = f'EV-BANKPAY_{i:04d}'
            cnum = container(i)
            bl = f'BL-FAKE-{i:04d}'
            self.v23['shipments'].append({
                'pilot_id': pilot, 'economic_shipment_id': ship,
                'physical_consignment_key': f'CONSIGN_FAKE_{i:04d}',
                'evidence': {'waybill': waybill, 'payment': payid},
                'classification': 'NEW', 'quantity_40ft': 1,
            })
            self.v24['shipments'].append({
                'pilot_id': pilot, 'economic_shipment_id': ship,
                'physical_consignment_key': f'CONSIGN_FAKE_{i:04d}',
                'containers': [{
                    'container_number': cnum,
                    'bill_of_lading_ref': bl,
                    'loaded_on': '2026-09-01', 'delivered_on': '2026-09-10',
                }],
            })
            legs = ('SHA-VVO','VVO-MGD') if pilot == 'P3' else ('VVO-MGD',)
            times = ['2026-09-01T08:00:00Z','2026-09-03T08:00:00Z',
                     '2026-09-04T08:00:00Z','2026-09-07T08:00:00Z'] if pilot=='P3' else [
                     '2026-09-01T08:00:00Z','2026-09-07T08:00:00Z']
            records = []
            q = 0
            for leg in legs:
                for event in ('CARRIER_LOAD','CARRIER_ARRIVE'):
                    q += 1
                    eid = f'EV-CUSTODY_{i:02d}_{q:02d}'
                    records.append({
                        'event_id': f'EVENT_{i:02d}_{q:02d}', 'container_number': cnum,
                        'leg': leg, 'event_type': event,
                        'occurred_at': times[q-1],
                        'actor_role': 'CARRIER', 'actor_org_id': f'CARRIER_FAKE_{i:02d}',
                        'leg_document_ref': (f'FEEDER-{i:04d}' if leg=='SHA-VVO' else bl),
                        'source_evidence_id': eid,
                        'source_record_locator': f'ROW_{i:02d}_{q:02d}',
                    })
                    self.provide(eid, f'CARRIER_FAKE_{i:02d}')
            for event, stamp, org, role in (
                ('TERMINAL_RELEASE', '2026-09-09T08:00:00Z', f'TERMINAL_FAKE_{i:02d}', 'TERMINAL'),
                ('CONSIGNEE_RECEIPT', '2026-09-10T08:00:00Z', f'RECEIVER_FAKE_{i:02d}', 'CONSIGNEE')):
                q += 1
                eid = f'EV-CUSTODY_{i:02d}_{q:02d}'
                records.append({'event_id': f'EVENT_{i:02d}_{q:02d}',
                                'container_number': cnum, 'leg': 'VVO-MGD',
                                'event_type': event, 'occurred_at': stamp,
                                'actor_role': role, 'actor_org_id': org,
                                'leg_document_ref': bl, 'source_evidence_id': eid,
                                'source_record_locator': f'ROW_{i:02d}_{q:02d}'})
                self.provide(eid, org)
            invoice_eid = f'EV-INVOICE_{i:04d}'
            self.provide(invoice_eid, f'SHIPPER_FAKE_{i:02d}')
            self.provide(payid, f'BANK_FAKE_{i:02d}')
            self.v25['shipments'].append({
                'pilot_id': pilot, 'economic_shipment_id': ship,
                'physical_consignment_key': f'CONSIGN_FAKE_{i:04d}',
                'events': records,
                'financial': {
                    'invoice': {'invoice_ref': f'INVOICE_FAKE_{i:04d}',
                                'issued_on': '2026-09-11', 'currency': 'RUB',
                                'tax_basis': 'EXPLICIT_NET_VAT_GROSS',
                                'net_rub': '100.00', 'vat_rub': '20.00',
                                'gross_rub': '120.00', 'adjustment_status': 'NONE',
                                'issuer_org_id': f'SHIPPER_FAKE_{i:02d}',
                                'payer_org_id': f'BUYER_FAKE_{i:02d}',
                                'source_evidence_id': invoice_eid},
                    'bank_settlements': [{
                        'transaction_ref': f'BANKTX_FAKE_{i:04d}',
                        'settled_on': '2026-09-15', 'currency': 'RUB',
                        'status': 'SETTLED', 'reversal_status': 'NONE',
                        'amount_gross_rub': '120.00',
                        'bank_org_id': f'BANK_FAKE_{i:02d}',
                        'source_evidence_id': payid,
                    }],
                },
            })
        self.freeze()

    def provide(self, eid, org='UNKNOWN_FAKE_ORG'):
        data = ('FAKE DOCUMENT FILE; DO NOT CLAIM AUTHENTIC: ' + eid).encode()
        filename = eid + '.txt'
        (self.root / filename).write_bytes(data)
        self.index[eid] = {'status': 'VERIFIED', 'relative_path': filename,
                           'sha256': hashlib.sha256(data).hexdigest(),
                           'submitted_by': 'fake_sender', 'reviewed_by': 'fake_independent_reviewer',
                           'source_org_id': org, 'reviewed_on': '2026-10-01'}

    def freeze(self):
        self.raw23 = json.dumps(self.v23, sort_keys=True).encode()
        self.raw24 = json.dumps(self.v24, sort_keys=True).encode()
        self.v24['v23_input_sha256'] = hashlib.sha256(self.raw23).hexdigest()
        self.raw24 = json.dumps(self.v24, sort_keys=True).encode()
        self.v25['v23_input_sha256'] = hashlib.sha256(self.raw23).hexdigest()
        self.v25['v24_identity_sha256'] = hashlib.sha256(self.raw24).hexdigest()

    def assess(self, with_index=True):
        return evaluate(self.v23, self.raw23, self.v24, self.raw24, self.v25,
                        evidence_index=self.index if with_index else None,
                        evidence_dir=self.root if with_index else None)

    def event(self, i=0, name='CARRIER_LOAD', leg='VVO-MGD'):
        return next(x for x in self.v25['shipments'][i]['events']
                    if x['event_type'] == name and x['leg'] == leg)

    def test_01_full_synthetic_review_not_bankable(self):
        s = self.assess()
        self.assertEqual(s['status'], 'REVIEW')
        self.assertEqual(s['physical_container_units'], 3)
        self.assertEqual(s['source_events_claimed'], 14)
        self.assertEqual(s['bank_settlements_claimed'], 3)
        self.assertEqual(s['bank_gross_paid_rub'], '360.00')
        self.assertFalse(s['cash_reconciled_with_bank'])
        self.assertFalse(s['bankable_revenue_approved'])

    def test_02_absent_real_evidence_is_hold(self):
        s = self.assess(with_index=False)
        self.assertEqual(s['status'], 'HOLD')
        self.assertIsNone(s['bank_gross_paid_rub'])

    def test_03_v23_bytes_changed_invalid(self):
        self.raw23 += b'\n'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_04_v24_bytes_changed_invalid(self):
        self.raw24 += b'\n'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_05_as_of_date_mismatch_invalid(self):
        self.v25['as_of'] = '2026-10-30'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_06_wrong_group_invalid(self):
        self.v25['group_id'] = 'OTHER_GROUP_ID'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_07_missing_one_shipment_hold(self):
        self.v25['shipments'].pop()
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_08_duplicate_shipment_invalid(self):
        self.v25['shipments'].append(copy.deepcopy(self.v25['shipments'][0]))
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_09_unknown_shipment_invalid(self):
        self.v25['shipments'][0]['economic_shipment_id'] = 'NONEXISTENT_SHIPMENT'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_10_mismatched_consignment_invalid(self):
        self.v25['shipments'][0]['physical_consignment_key'] = 'OTHER_CONSIGN_KEY'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_11_event_duplicate_id_invalid(self):
        self.v25['shipments'][1]['events'][0]['event_id'] = self.v25['shipments'][0]['events'][0]['event_id']
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_12_duplicate_event_slot_invalid(self):
        self.v25['shipments'][0]['events'].append(copy.deepcopy(self.v25['shipments'][0]['events'][0]))
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_13_absent_event_proof_hold(self):
        self.event()['source_evidence_id'] = 'EV-UNKNOWN00001'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_14_source_file_changed_hold(self):
        event_id = self.event()['source_evidence_id']
        (self.root / (event_id + '.txt')).write_bytes(b'changed')
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_15_same_reviewer_as_sender_hold(self):
        eid = self.event()['source_evidence_id']
        self.index[eid]['reviewed_by'] = 'FAKE_SENDER'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_16_wrong_event_role_invalid(self):
        self.event()['actor_role'] = 'TERMINAL'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_17_wrong_route_leg_invalid(self):
        self.event()['leg'] = 'HONGKONG-ALASKA'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_18_p3_missing_feeder_event_hold(self):
        self.v25['shipments'][2]['events'] = [e for e in self.v25['shipments'][2]['events']
                                            if e['leg'] != 'SHA-VVO']
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_19_unordered_events_invalid(self):
        self.event(name='CARRIER_ARRIVE')['occurred_at'] = '2026-09-01T07:00:00Z'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_20_carrier_org_mismatch_invalid(self):
        self.event(name='CARRIER_ARRIVE')['actor_org_id'] = 'OTHER_CARRIER_0001'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_21_carrier_terminal_same_org_invalid(self):
        self.event(name='TERMINAL_RELEASE')['actor_org_id'] = self.event()['actor_org_id']
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_22_delivery_differs_from_v24_invalid(self):
        self.event(name='CONSIGNEE_RECEIPT')['occurred_at'] = '2026-09-11T08:00:00Z'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_23_utc_timezone_conversion(self):
        self.event()['occurred_at'] = '2026-09-01T10:00:00+02:00'
        self.assertEqual(self.assess()['status'], 'REVIEW')

    def test_24_invalid_timezone_timestamp_invalid(self):
        self.event()['occurred_at'] = '2026-09-01T09:00:00'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_25_wrong_container_invalid(self):
        self.event()['container_number'] = container(88)
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_26_wrong_domestic_bl_invalid(self):
        self.event()['leg_document_ref'] = 'UNRELATED_DOCUMENT'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_27_normalized_domestic_bl(self):
        self.event()['leg_document_ref'] = 'bl_fake_0001'
        self.assertEqual(self.assess()['status'], 'REVIEW')

    def test_28_carrier_doc_load_arrival_mismatch_invalid(self):
        self.event(name='CARRIER_ARRIVE')['leg_document_ref'] = 'OTHER_DOCUMENT'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_29_invoice_math_mismatch_invalid(self):
        self.v25['shipments'][0]['financial']['invoice']['gross_rub'] = '119.99'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_30_missing_net_invoice_hold(self):
        self.v25['shipments'][0]['financial']['invoice']['net_rub'] = None
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_31_wrong_invoice_currency_invalid(self):
        self.v25['shipments'][0]['financial']['invoice']['currency'] = 'USD'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_32_duplicate_invoice_across_pilots_invalid(self):
        b = self.v25['shipments'][1]['financial']['invoice']
        b['invoice_ref'] = self.v25['shipments'][0]['financial']['invoice']['invoice_ref']
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_33_duplicate_bank_txn_invalid(self):
        self.v25['shipments'][1]['financial']['bank_settlements'][0]['transaction_ref'] = (
            self.v25['shipments'][0]['financial']['bank_settlements'][0]['transaction_ref'])
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_34_bank_overpayment_invalid(self):
        self.v25['shipments'][0]['financial']['bank_settlements'][0]['amount_gross_rub'] = '125.00'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_35_underpayment_hold(self):
        self.v25['shipments'][0]['financial']['bank_settlements'][0]['amount_gross_rub'] = '119.99'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_36_two_partial_payments_exact_gross_review(self):
        p = self.v25['shipments'][0]['financial']['bank_settlements'][0]
        p['amount_gross_rub'] = '70.00'
        p2 = copy.deepcopy(p)
        p2['amount_gross_rub'] = '50.00'
        p2['transaction_ref'] = 'BANKTX_FAKE_9999'
        self.v25['shipments'][0]['financial']['bank_settlements'].append(p2)
        self.assertEqual(self.assess()['status'], 'REVIEW')

    def test_37_bank_date_before_invoice_invalid(self):
        self.v25['shipments'][0]['financial']['bank_settlements'][0]['settled_on'] = '2026-09-01'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_38_bank_status_not_settled_hold(self):
        self.v25['shipments'][0]['financial']['bank_settlements'][0]['status'] = 'PENDING'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_39_bank_org_same_as_issuer_invalid(self):
        inv = self.v25['shipments'][0]['financial']['invoice']
        self.v25['shipments'][0]['financial']['bank_settlements'][0]['bank_org_id'] = inv['issuer_org_id']
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_40_unlinked_bank_evidence_hold(self):
        new_eid = 'EV-UNLINKEDBANK111'
        self.provide(new_eid)
        self.v25['shipments'][0]['financial']['bank_settlements'][0]['source_evidence_id'] = new_eid
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_41_duplicate_source_event_id_other_pilot_invalid(self):
        self.v25['shipments'][2]['events'][0]['event_id'] = self.v25['shipments'][1]['events'][0]['event_id']
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_42_broken_v24_v23_link_invalid(self):
        self.v24['v23_input_sha256'] = 'a' * 64
        self.raw24 = json.dumps(self.v24, sort_keys=True).encode()
        self.v25['v24_identity_sha256'] = hashlib.sha256(self.raw24).hexdigest()
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_43_missing_record_locator_hold(self):
        self.event()['source_record_locator'] = None
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_44_bank_float_invalid(self):
        self.v25['shipments'][0]['financial']['bank_settlements'][0]['amount_gross_rub'] = 120.001
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_45_amount_precision_exact(self):
        self.assertEqual(amount('0.01'), Decimal('0.01'))
        self.assertIsNone(amount('0.001'))
        self.assertIsNone(amount(float('nan')))

    def test_47_duplicate_source_row_rejected(self):
        a = self.event()
        b = self.event(name='CARRIER_ARRIVE')
        b['source_evidence_id'] = a['source_evidence_id']
        b['source_record_locator'] = a['source_record_locator']
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_48_same_manifest_distinct_rows_accepted(self):
        a = self.event()
        b = self.event(name='CARRIER_ARRIVE')
        b['source_evidence_id'] = a['source_evidence_id']
        self.assertEqual(self.assess()['status'], 'REVIEW')

    def test_49_bank_refund_blocks(self):
        p = self.v25['shipments'][0]['financial']['bank_settlements'][0]
        p['reversal_status'] = 'REFUNDED'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_50_missing_bank_reversal_clearance_blocks(self):
        p = self.v25['shipments'][0]['financial']['bank_settlements'][0]
        p.pop('reversal_status')
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_51_invoice_credit_note_blocks(self):
        self.v25['shipments'][0]['financial']['invoice']['adjustment_status'] = 'CREDIT_NOTE'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_52_missing_invoice_credit_note_clearance_blocks(self):
        self.v25['shipments'][0]['financial']['invoice'].pop('adjustment_status')
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_53_changed_source_organization_holds(self):
        eid = self.event()['source_evidence_id']
        self.index[eid]['source_org_id'] = 'FAKE_OTHER_OPERATOR'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_54_removed_source_organization_holds(self):
        eid = self.event()['source_evidence_id']
        del self.index[eid]['source_org_id']
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_55_source_review_before_event_holds(self):
        eid = self.event()['source_evidence_id']
        self.index[eid]['reviewed_on'] = '2026-08-01'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_56_bank_document_claimed_from_wrong_bank_holds(self):
        eid = self.v25['shipments'][0]['financial']['bank_settlements'][0]['source_evidence_id']
        self.index[eid]['source_org_id'] = 'NOT_THE_BANK'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_57_invoice_review_before_invoice_date_holds(self):
        eid = self.v25['shipments'][0]['financial']['invoice']['source_evidence_id']
        self.index[eid]['reviewed_on'] = '2026-09-01'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_58_payment_review_before_settlement_holds(self):
        eid = self.v25['shipments'][0]['financial']['bank_settlements'][0]['source_evidence_id']
        self.index[eid]['reviewed_on'] = '2026-09-10'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_59_shared_source_file_count_is_unique(self):
        before = self.assess()
        self.assertEqual(before['status'], 'REVIEW')
        first = self.event()
        second = self.event(name='CARRIER_ARRIVE')
        second['source_evidence_id'] = first['source_evidence_id']
        self.assertNotEqual(second['source_record_locator'], first['source_record_locator'])
        after = self.assess()
        self.assertEqual(after['status'], 'REVIEW')
        self.assertEqual(after['source_evidence_files_verified'],
                         before['source_evidence_files_verified'] - 1)

    def test_60_malformed_list_pilot_does_not_crash(self):
        self.v25['shipments'][0]['pilot_id'] = ['P1']
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_61_malformed_v23_source_pilot_does_not_crash(self):
        self.v23['shipments'][0]['pilot_id'] = ['P1']
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_62_malformed_container_number_does_not_crash(self):
        self.event()['container_number'] = ['not container']
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_63_malformed_event_kind_does_not_crash(self):
        self.event()['event_type'] = {'a': 'CARRIER_LOAD'}
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_64_malformed_v24_pilot_does_not_crash(self):
        self.v24['shipments'][0]['pilot_id'] = {'bad': 'value'}
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_46_parser_requires_timestamp_offset(self):
        self.assertIsNone(as_utc('2026-09-01T08:00:00'))
        self.assertIsNotNone(as_utc('2026-09-01T10:00:00+02:00'))


if __name__ == '__main__':
    unittest.main()

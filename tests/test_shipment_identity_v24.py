"""Synthetic fixtures only. Checks identity integrity, not commercial reality."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from shipment_identity_v24 import evaluate, iso6346_valid, iso6346_check_digit


def make_container(serial: int) -> str:
    prefix = f'ABCU{serial:06d}'
    return prefix + iso6346_check_digit(prefix)


class ShipmentIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index = {}
        v23 = {'schema_version': 'V23', 'as_of': '2026-10-31',
               'group_id': 'GROUP_BERING_TEST', 'shipments': []}
        for p, pos, qty in [('P1', 1, 2), ('P2', 2, 1), ('P3', 3, 1)]:
            v23['shipments'].append({
                'pilot_id': p, 'economic_shipment_id': f'ECON_{pos:05d}',
                'physical_consignment_key': f'CONS_{pos:05d}',
                'quantity_40ft': qty, 'evidence': {'waybill': f'EV-WAYBILL{pos:02d}'}})
        self.v23 = v23
        self.v23_bytes = json.dumps(v23, ensure_ascii=False, sort_keys=True).encode('utf-8')
        identity_rows = []
        for pos, source in enumerate(v23['shipments'], 1):
            containers = []
            for index in range(source['quantity_40ft']):
                unit_no = (pos - 1) * 2 + index + 1
                containers.append({
                    'container_number': make_container(100000 + unit_no),
                    'iso_size_type': '45R1' if source['pilot_id'] == 'P2' else '45G1',
                    'bill_of_lading_ref': f'BL-EXAMPLE-{pos:03d}',
                    'loaded_on': '2026-09-01', 'delivered_on': '2026-09-15',
                    'container_event_evidence_id': f'EV-MOVEMENT{unit_no:02d}',
                    'delivery_evidence_id': f'EV-DELIVERY{unit_no:02d}',
                })
            identity_rows.append({
                'pilot_id': source['pilot_id'],
                'economic_shipment_id': source['economic_shipment_id'],
                'physical_consignment_key': source['physical_consignment_key'],
                'waybill_evidence_id': source['evidence']['waybill'],
                'containers': containers,
            })
        self.identity = {'schema_version': 'V24', 'as_of': '2026-10-31',
                         'group_id': 'GROUP_BERING_TEST',
                         'v23_input_sha256': hashlib.sha256(self.v23_bytes).hexdigest(),
                         'shipments': identity_rows}
        for row in identity_rows:
            self.provide(row['waybill_evidence_id'])
            for unit in row['containers']:
                self.provide(unit['container_event_evidence_id'])
                self.provide(unit['delivery_evidence_id'])

    def provide(self, evidence_id):
        raw = ('SYNTHETIC-SOURCE-NOT-ORIGINAL-' + evidence_id).encode()
        name = evidence_id + '.txt'
        (self.root / name).write_bytes(raw)
        self.index[evidence_id] = {
            'status': 'VERIFIED', 'relative_path': name,
            'sha256': hashlib.sha256(raw).hexdigest(),
            'submitted_by': 'shipper_stub', 'reviewed_by': 'independent_stub',
            'reviewed_on': '2026-10-29',
        }

    def assess(self, with_files=True):
        return evaluate(self.v23, self.v23_bytes, self.identity,
                        evidence_index=self.index if with_files else None,
                        evidence_root=self.root if with_files else None)

    def test_checksum_accepts_generated_iso6346(self):
        self.assertTrue(iso6346_valid(make_container(123456)))

    def test_checksum_detects_modified_final_digit(self):
        original = make_container(123456)
        changed = original[:-1] + str((int(original[-1]) + 1) % 10)
        self.assertFalse(iso6346_valid(changed))

    def test_valid_iso_j_category_still_rejected_as_noncontainer(self):
        self.assertFalse(iso6346_valid('ABCJ123456' + str(0)))
        with self.assertRaises(ValueError):
            iso6346_check_digit('ABCJ123456')

    def test_20ft_size_type_cannot_be_claimed_as_40ft(self):
        self.identity['shipments'][0]['containers'][0]['iso_size_type'] = '22G1'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_reefer_pilot_requires_reefer_size_family(self):
        self.identity['shipments'][1]['containers'][0]['iso_size_type'] = '45G1'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_unsupported_dry_size_type_does_not_pass_by_regex_only(self):
        self.identity['shipments'][0]['containers'][0]['iso_size_type'] = '45G9'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_unsupported_reefer_size_type_does_not_pass_by_regex_only(self):
        self.identity['shipments'][1]['containers'][0]['iso_size_type'] = '45R9'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_future_as_of_is_invalid_even_if_both_inputs_match(self):
        self.v23['as_of'] = '2099-01-01'
        self.identity['as_of'] = '2099-01-01'
        self.v23_bytes = json.dumps(self.v23, sort_keys=True).encode('utf-8')
        self.identity['v23_input_sha256'] = hashlib.sha256(self.v23_bytes).hexdigest()
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_invalid_category_letter_rejected(self):
        self.assertFalse(iso6346_valid('ABCA1234567'))

    def test_review_with_independently_hashed_synthetic_files(self):
        result = self.assess()
        self.assertEqual(result['status'], 'REVIEW')
        self.assertEqual(result['linked_40ft_containers'], 4)
        self.assertEqual(result['verified_container_event_files'], 4)
        self.assertFalse(result['bankable_revenue_approved'])
        self.assertFalse(result['contracts_authenticated'])

    def test_without_external_sources_never_review(self):
        self.assertEqual(self.assess(with_files=False)['status'], 'HOLD')

    def test_v23_file_swap_detected_even_if_json_semantically_same(self):
        self.v23_bytes += b'\n'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_as_of_mismatch_detected(self):
        self.identity['as_of'] = '2026-10-30'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_group_mismatch_detected(self):
        self.identity['group_id'] = 'OTHER_GROUP'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_missing_identity_row_hold(self):
        self.identity['shipments'].pop()
        result = self.assess()
        self.assertEqual(result['status'], 'HOLD')
        self.assertTrue(any('missing identity for V23' in x for x in result['missing']))

    def test_identity_extra_row_invalid(self):
        extra = copy.deepcopy(self.identity['shipments'][0])
        extra['economic_shipment_id'] = 'ECON_99999'
        self.identity['shipments'].append(extra)
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_mismatch_consignment_key_invalid(self):
        self.identity['shipments'][0]['physical_consignment_key'] = 'CONS_OTHER'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_waybill_must_match_v23_source_id(self):
        self.identity['shipments'][1]['waybill_evidence_id'] = 'EV-OTHER00001'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_number_of_actual_containers_must_match_claimed_quantity(self):
        self.identity['shipments'][0]['containers'].pop()
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_same_physical_container_twice_in_one_multiunit_row_invalid(self):
        row = self.identity['shipments'][0]['containers']
        row[1]['container_number'] = row[0]['container_number']
        row[1]['bill_of_lading_ref'] = 'BL-SECOND-REFERENCE'
        result = self.assess()
        self.assertEqual(result['status'], 'INVALID')
        self.assertTrue(any('repeated within one economic shipment' in e for e in result['errors']))

    def test_same_bl_plus_container_in_two_pilots_is_invalid(self):
        first = self.identity['shipments'][0]['containers'][0]
        other = self.identity['shipments'][2]['containers'][0]
        other['container_number'] = first['container_number']
        other['bill_of_lading_ref'] = first['bill_of_lading_ref'].replace('-', '')
        result = self.assess()
        self.assertEqual(result['status'], 'INVALID')
        self.assertTrue(any('same B/L and container' in e for e in result['errors']))

    def test_same_container_with_overlap_distinct_bl_causes_hold(self):
        first = self.identity['shipments'][0]['containers'][0]
        self.identity['shipments'][2]['containers'][0]['container_number'] = first['container_number']
        result = self.assess()
        self.assertEqual(result['status'], 'HOLD')
        self.assertTrue(result['ambiguous_overlaps'])

    def test_same_container_reused_after_delivery_is_not_false_duplicate(self):
        first = self.identity['shipments'][0]['containers'][0]
        later = self.identity['shipments'][2]['containers'][0]
        later['container_number'] = first['container_number']
        later['loaded_on'] = '2026-10-01'
        later['delivered_on'] = '2026-10-15'
        self.assertEqual(self.assess()['status'], 'REVIEW')

    def test_reuse_of_container_event_proof_across_pilots_invalid(self):
        source = self.identity['shipments'][0]['containers'][0]['container_event_evidence_id']
        self.identity['shipments'][2]['containers'][0]['container_event_evidence_id'] = source
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_reviewer_must_be_independent(self):
        event = self.identity['shipments'][1]['containers'][0]['container_event_evidence_id']
        self.index[event]['reviewed_by'] = 'SHIPPER_STUB'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_tampered_container_event_bytes_hold(self):
        event = self.identity['shipments'][1]['containers'][0]['container_event_evidence_id']
        (self.root / (event + '.txt')).write_text('ALTERED')
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_stale_document_review_hold(self):
        event = self.identity['shipments'][0]['waybill_evidence_id']
        self.index[event]['reviewed_on'] = '2026-11-01'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_symlink_evidence_path_rejected(self):
        event = self.identity['shipments'][0]['containers'][0]['container_event_evidence_id']
        old = self.root / (event + '.txt')
        old.unlink()
        old.symlink_to(self.root / 'not_exist')
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_bad_check_digit_invalid(self):
        unit = self.identity['shipments'][1]['containers'][0]
        unit['container_number'] = unit['container_number'][:-1] + 'X'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_delivery_before_loading_invalid(self):
        unit = self.identity['shipments'][0]['containers'][0]
        unit['delivered_on'] = '2026-08-01'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_future_delivery_invalid(self):
        unit = self.identity['shipments'][0]['containers'][0]
        unit['delivered_on'] = '2026-11-01'
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_nonexistent_evidence_for_delivery_hold(self):
        unit = self.identity['shipments'][0]['containers'][0]
        unit['delivery_evidence_id'] = 'EV-NOTFOUND1'
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_same_waybill_can_cover_multiple_distinct_containers(self):
        first = self.identity['shipments'][0]['containers'][0]
        second = self.identity['shipments'][0]['containers'][1]
        self.assertEqual(first['bill_of_lading_ref'], second['bill_of_lading_ref'])
        self.assertEqual(self.assess()['status'], 'REVIEW')

    def test_v23_empty_and_v24_empty_is_hold_not_zero_demand(self):
        self.v23['shipments'] = []
        self.v23_bytes = json.dumps(self.v23, sort_keys=True).encode('utf-8')
        self.identity['shipments'] = []
        self.identity['v23_input_sha256'] = hashlib.sha256(self.v23_bytes).hexdigest()
        res = self.assess()
        self.assertEqual(res['status'], 'HOLD')
        self.assertEqual(res['linked_40ft_containers'], 0)
        self.assertFalse(res['source_records_proved'])

    def test_v23_duplicate_key_blocks_identity_reconciliation(self):
        self.v23['shipments'].append(copy.deepcopy(self.v23['shipments'][0]))
        self.v23_bytes = json.dumps(self.v23, sort_keys=True).encode('utf-8')
        self.identity['v23_input_sha256'] = hashlib.sha256(self.v23_bytes).hexdigest()
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_unknown_v23_schema_invalid(self):
        self.v23['schema_version'] = 'WRONG'
        self.v23_bytes = json.dumps(self.v23, sort_keys=True).encode('utf-8')
        self.identity['v23_input_sha256'] = hashlib.sha256(self.v23_bytes).hexdigest()
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_missing_container_event_evidence_hold(self):
        self.identity['shipments'][0]['containers'][0]['container_event_evidence_id'] = None
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_duplicate_identity_row_invalid(self):
        self.identity['shipments'].append(copy.deepcopy(self.identity['shipments'][1]))
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_empty_bl_reference_invalid(self):
        self.identity['shipments'][0]['containers'][0]['bill_of_lading_ref'] = None
        self.assertEqual(self.assess()['status'], 'INVALID')

    def test_illegal_evidence_path_rejected(self):
        eid = self.identity['shipments'][0]['waybill_evidence_id']
        self.index[eid]['relative_path'] = '../outside.txt'
        self.assertEqual(self.assess()['status'], 'HOLD')


if __name__ == '__main__':
    unittest.main()

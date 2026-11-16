import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.v27_monthly_od_gate import (
    periods, decimal_exact, iso6346_valid, audit_monthly_port, audit_od, SERIES, ISO_LETTERS)


def number(serial):
    ten = f'ABCU{serial:06d}'
    checksum = sum((ISO_LETTERS[x] if x.isalpha() else int(x)) * 2 ** k
                   for k, x in enumerate(ten)) % 11 % 10
    return ten + str(checksum)


class V27DataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = b'SYNTHETIC OD DECLARATIONS FOR UNIT TESTS; NOT BUSINESS EVIDENCE'
        (self.root / 'fixture.txt').write_bytes(self.source)
        self.proof = {'status':'VERIFIED', 'path':'fixture.txt',
                      'sha256':hashlib.sha256(self.source).hexdigest(),
                      'submitted_by':'fixture-origin','reviewed_by':'fixture-independent'}
        self.port = {'schema':'V27_PORT_MONTHLY','entity_scope':'MMTP_OPERATOR',
                     'metric':'CONTAINER_CARGO_TONNES','unit':'tonnes',
                     'window_start':'2024-10','window_end':'2026-09','observations':[]}
        self.od = {'schema':'V27_24M_GROUP_OD','unit':'40ft_container',
                   'window_start':'2024-10','window_end':'2026-09',
                   'coverage':[],'shipments':[]}

    def populated_port(self):
        self.port['observations'] = [
            {'month':m, 'report_period_type':'MONTH','source_entity':'MMTP_OPERATOR',
             'tonnes': str(1000+i), 'source_evidence':self.proof,
             'cell_locator':f'Sheet1!C{i+1}'}
            for i,m in enumerate(periods('2024-10',24))]

    def populated_od(self, *, qty=0):
        self.od['coverage'] = []
        self.od['shipments'] = []
        idx = 0
        for lane in SERIES:
            for month in periods('2024-10',24):
                idx += 1
                self.od['coverage'].append({
                    'lane':lane,'month':month,'coverage_state':'VERIFIED',
                    'count_40ft':qty,'evidence':self.proof,
                    'source_row_locator':f'SHEET_A!R{idx}'})
                for n in range(qty):
                    self.od['shipments'].append({
                        'lane':lane,'month':month,'physical_consignment_id':f'CARGO_{idx:04d}_{n}',
                        'container_number':number(idx*10+n), 'shipper_group_id':'GROUP_DEMO',
                        'origin':'A', 'destination':'B', 'evidence':self.proof,
                        'source_row_locator':f'VESSEL!R{idx}_{n}'})

    def test_periods_are_24_unique(self):
        months=periods('2024-10',24)
        self.assertEqual(len(months),24)
        self.assertEqual(months[-1],'2026-09')
        self.assertEqual(len(set(months)),24)

    def test_exact_decimal_no_float(self):
        with self.assertRaises(ValueError): decimal_exact(3.5)
        self.assertEqual(decimal_exact('0'),0)

    def test_nan_and_negative_rejected(self):
        for x in ('NaN','-1','Infinity'):
            with self.subTest(x=x),self.assertRaises(ValueError):decimal_exact(x)

    def test_bad_port_grain(self):
        self.port['unit']='40ft_container'
        self.assertEqual(audit_monthly_port(self.port)['status'],'INVALID')

    def test_empty_port_hold_null(self):
        x=audit_monthly_port(self.port)
        self.assertEqual(x['status'],'HOLD')
        self.assertEqual(x['reported_months'],0)
        self.assertFalse(x['can_infer_40ft_or_OD_from_tonnes'])

    def test_cumulative_source_must_not_be_disaggregated(self):
        self.populated_port()
        self.port['observations'][0]['report_period_type']='9M_CUMULATIVE'
        self.assertEqual(audit_monthly_port(self.port,root=self.root)['status'],'INVALID')

    def test_missing_port_source_stays_hold(self):
        self.populated_port()
        self.assertEqual(audit_monthly_port(self.port)['status'],'HOLD')

    def test_24_month_port_still_not_bering_forecast(self):
        self.populated_port()
        x=audit_monthly_port(self.port,root=self.root)
        self.assertEqual(x['status'],'REVIEW_ONLY')
        self.assertEqual(x['reported_months'],24)
        self.assertFalse(x['forecast_eligible'])

    def test_duplicate_port_month_invalid(self):
        self.populated_port()
        self.port['observations'][1]['month']=self.port['observations'][0]['month']
        self.assertEqual(audit_monthly_port(self.port,root=self.root)['status'],'INVALID')

    def test_unsupported_annual_port_source_invalid(self):
        self.populated_port()
        self.port['observations'][0]['report_period_type']='YEAR'
        self.assertEqual(audit_monthly_port(self.port,root=self.root)['status'],'INVALID')

    def test_wrong_port_window_invalid(self):
        self.port['window_end']='2026-08'
        self.assertEqual(audit_monthly_port(self.port)['status'],'INVALID')

    def test_empty_od_96_slots_hold(self):
        x=audit_od(self.od)
        self.assertEqual(x['status'],'HOLD')
        self.assertEqual(x['required_total_months'],96)
        self.assertEqual(x['documented_months'],0)
        self.assertIsNone(x['projection'])

    def test_od_wrong_unit_invalid(self):
        self.od['unit']='TEU'
        self.assertEqual(audit_od(self.od)['status'],'INVALID')

    def test_full_explicit_sourcebacked_zeros_not_missing(self):
        self.populated_od()
        x=audit_od(self.od,root=self.root)
        self.assertEqual(x['status'],'REVIEW_BASELINE_ONLY')
        self.assertEqual(x['source_backed_months'],96)
        self.assertFalse(x['investment_approved'])
        self.assertEqual(x['projection']['P1']['historic_12m_40ft'],'0')

    def test_unproven_zeros_still_hold(self):
        self.populated_od()
        self.assertEqual(audit_od(self.od)['status'],'HOLD')

    def test_single_missing_group_incumbent_month_blocks(self):
        self.populated_od()
        self.od['coverage'].pop()
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'HOLD')

    def test_duplicate_coverage_invalid(self):
        self.populated_od()
        self.od['coverage'][1]['month']=self.od['coverage'][0]['month']
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'INVALID')

    def test_duplicate_source_row_invalid(self):
        self.populated_od()
        self.od['coverage'][1]['source_row_locator']=self.od['coverage'][0]['source_row_locator']
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'INVALID')

    def test_unreviewed_hash_hold(self):
        self.populated_od()
        self.od['coverage'][0]['evidence']=dict(self.proof,sha256='0'*64)
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'HOLD')

    def test_reviewer_independence_hold(self):
        self.populated_od()
        self.od['coverage'][0]['evidence']=dict(self.proof,reviewed_by='fixture-origin')
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'HOLD')

    def test_one_container_per_month_stress_no_bankability(self):
        self.populated_od(qty=1)
        x=audit_od(self.od,root=self.root)
        self.assertEqual(x['status'],'REVIEW_BASELINE_ONLY')
        self.assertEqual(x['projection']['P1']['historic_12m_40ft'],'12')
        self.assertEqual(x['projection']['P1']['illustrative_envelope']['LOW_STRESS']['next_12_month_total_40ft'],'12')
        self.assertFalse(x['eligible_to_forecast_Bering_revenue'])

    def test_quantity_mismatch_invalid(self):
        self.populated_od(qty=1)
        self.od['coverage'][0]['count_40ft']='2'
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'INVALID')

    def test_duplicate_shipment_id_invalid(self):
        self.populated_od(qty=1)
        self.od['shipments'][1]['physical_consignment_id']=self.od['shipments'][0]['physical_consignment_id']
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'INVALID')

    def test_container_checksum_invalid(self):
        self.populated_od(qty=1)
        self.od['shipments'][0]['container_number']='ABCU0000019'
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'INVALID')

    def test_duplicate_shipment_source_row_invalid(self):
        self.populated_od(qty=1)
        self.od['shipments'][1]['source_row_locator']=self.od['shipments'][0]['source_row_locator']
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'INVALID')

    def test_source_symlink_rejected(self):
        self.populated_od()
        (self.root/'bad.txt').symlink_to(self.root/'fixture.txt')
        self.od['coverage'][0]['evidence']=dict(self.proof,path='bad.txt')
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'HOLD')

    def test_scope_group_missing_blocks(self):
        self.populated_od(qty=1)
        self.od['shipments'][0]['shipper_group_id']=''
        self.assertEqual(audit_od(self.od,root=self.root)['status'],'INVALID')

    def test_invalid_json_shapes_not_crash(self):
        self.assertEqual(audit_od([])['status'],'INVALID')
        self.assertEqual(audit_monthly_port(None)['status'],'INVALID')
        self.od['coverage']='wrong'
        self.assertEqual(audit_od(self.od)['status'],'INVALID')


if __name__ == '__main__':
    unittest.main()

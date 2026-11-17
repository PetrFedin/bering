"""R20 regression of published-repository MP-1 extraction; NOT XLS authentication."""
import copy
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from r20_magadan_source_reconciliation import read_rows,assess,aggregate,EXPECTED_MONTHS
DATA=ROOT/'data/public/MMTP_MP1_MONTHLY_SERIES_2024-01_2026-09.csv'

class R20OperatorDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rows=read_rows(DATA)
    def test_count_and_months(self):
        self.assertEqual(len(self.rows),33)
        self.assertEqual([r['month'] for r in self.rows],EXPECTED_MONTHS)
    def test_reconciled_2025_full_loaded_empty(self):
        x=aggregate(self.rows,2025,12)
        self.assertEqual(x['loaded_teu'],51606)
        self.assertEqual(x['empty_teu'],32688)
        self.assertEqual(x['loaded_plus_empty_teu'],84294)
    def test_2024_discrepancy_must_remain_visible(self):
        x=assess(self.rows)
        self.assertEqual(x['fy2024_portwide_minus_operator_teu'],-2336)
    def test_2025_port_rounding_not_scope_authentication(self):
        x=assess(self.rows)
        self.assertEqual(x['fy2025_portwide_minus_operator_teu'],6)
        self.assertIsNone(x['current_2026_port_utilization_pct'])
    def test_ytd_total_teu(self):
        x=assess(self.rows)['ytd_operator']['loaded_plus_empty_teu']
        self.assertEqual((x['2025_9m'],x['2026_9m'],x['delta'],x['yoy_pct']),('62590.000','69692.000','7102.000','11.35'))
    def test_ytd_loaded(self):
        x=assess(self.rows)['ytd_operator']['loaded_teu']
        self.assertEqual((x['2025_9m'],x['2026_9m'],x['delta'],x['yoy_pct']),('38651.000','42245.000','3594.000','9.30'))
    def test_ytd_empty(self):
        x=assess(self.rows)['ytd_operator']['empty_teu']
        self.assertEqual((x['2025_9m'],x['2026_9m'],x['delta'],x['yoy_pct']),('23939.000','27447.000','3508.000','14.65'))
    def test_ytd_container_tonnes(self):
        x=assess(self.rows)['ytd_operator']['container_cargo_kt']
        self.assertEqual((x['2025_9m'],x['2026_9m'],x['delta'],x['yoy_pct']),('640.508','677.817','37.309','5.82'))
    def test_reefer_zero_cannot_be_promoted(self):
        x=assess(self.rows)
        self.assertIn('2025-06',x['reefer_zero_months_requiring_source_check'])
        self.assertTrue(x['teu_not_additive_to_reefer_teu'])
    def test_company_tonnage_conflict(self):
        x=assess(self.rows)
        self.assertEqual(x['fy2025_operator_total_cargo_kt'],'1334.406')
        self.assertEqual(x['fy2025_asop_minus_operator_total_kt'],'500.294')
    def test_2024_container_tonnage_conflict(self):
        x=assess(self.rows)
        self.assertEqual(x['fy2024_operator_container_kt'],'819.986')
        self.assertEqual(x['fy2024_secondary_minus_operator_container_kt'],'70.114')
    def test_no_bankable_revenue_or_npv(self):
        x=assess(self.rows)
        for k in ('new_paid_incremental_40ft','bering_group_incremental_cm_rub','bering_npv_rub','port_2026_actual_capacity_teu'):
            self.assertIsNone(x[k],k)
        self.assertFalse(x['investment_approved'])
        self.assertFalse(x['bankable_revenue_approved'])
    def mutate(self,change):
        rows=copy.deepcopy(self.rows)
        change(rows)
        return rows
    def test_missing_month_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.csv';p.write_text('month\n')
            with self.assertRaises(ValueError):read_rows(p)
    def test_duplicate_month_fails(self):
        from csv import DictReader, DictWriter
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.csv'
            lines=list(DictReader(DATA.read_text(encoding='utf-8').splitlines()))
            lines[2]['month']=lines[1]['month']
            with p.open('w',newline='') as f:
                wr=DictWriter(f,fieldnames=lines[0].keys());wr.writeheader();wr.writerows(lines)
            with self.assertRaises(ValueError):read_rows(p)
    def test_negative_rejected(self):
        from csv import DictReader,DictWriter
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.csv';lines=list(DictReader(DATA.read_text(encoding='utf-8').splitlines()))
            lines[8]['empty_teu']='-3'
            with p.open('w',newline='') as f:
                wr=DictWriter(f,fieldnames=lines[0].keys());wr.writeheader();wr.writerows(lines)
            with self.assertRaises(ValueError):read_rows(p)
    def test_fractional_teu_rejected(self):
        from csv import DictReader,DictWriter
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.csv';lines=list(DictReader(DATA.read_text(encoding='utf-8').splitlines()))
            lines[0]['loaded_teu']='10.5'
            with p.open('w',newline='') as f:
                wr=DictWriter(f,fieldnames=lines[0].keys());wr.writeheader();wr.writerows(lines)
            with self.assertRaises(ValueError):read_rows(p)
    def test_nan_rejected(self):
        from csv import DictReader,DictWriter
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.csv';lines=list(DictReader(DATA.read_text(encoding='utf-8').splitlines()))
            lines[1]['container_cargo_kt']='NaN'
            with p.open('w',newline='') as f:
                wr=DictWriter(f,fieldnames=lines[0].keys());wr.writeheader();wr.writerows(lines)
            with self.assertRaises(ValueError):read_rows(p)
    def test_cli_returns_research_only(self):
        cmd=[sys.executable,str(ROOT/'scripts/r20_magadan_source_reconciliation.py'),'--input',str(DATA)]
        r=subprocess.run(cmd,capture_output=True,text=True,check=False)
        self.assertEqual(r.returncode,0,r.stderr)
        x=json.loads(r.stdout)
        self.assertEqual(x['status'],'RESEARCH_CONTEXT_ONLY')
        self.assertFalse(x['investment_approved'])
    def test_cli_failure_fails_closed(self):
        cmd=[sys.executable,str(ROOT/'scripts/r20_magadan_source_reconciliation.py'),'--input','/does/not/exist']
        r=subprocess.run(cmd,capture_output=True,text=True,check=False)
        self.assertEqual(r.returncode,2)
        self.assertEqual(json.loads(r.stdout)['status'],'INVALID')

if __name__=='__main__':unittest.main()

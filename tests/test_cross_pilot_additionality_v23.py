"""Synthetic-only cross-pilot double-count and evidence QA; no real freight claims."""
from __future__ import annotations
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from cross_pilot_additionality_v23 import evaluate

EVIDENCE_FIELDS = ('contract','waybill','payment','baseline_24m','additionality','unit_contribution')


def item(pilot, index, classification='NEW', new='100', old=None, quantity=1):
    kinds = {'P1':'dry_40ft','P2':'reefer_40ft','P3':'import_dry_40ft'}
    return {
        'economic_shipment_id':f'CARGO_TEST_{index:03d}',
        'physical_consignment_key':f'WAYBILL_LINE_{index:03d}',
        'group_id':'GROUP_BERING_TEST', 'pilot_id':pilot,
        'currency':'RUB', 'tax_basis':'EX_VAT',
        'month':'2026-09','cargo_class':kinds[pilot],
        'unit':'40ft_container','quantity_40ft':quantity,
        'classification':classification,
        'new_unit_cm_rub':new,
        'incumbent_group_unit_cm_rub':old,
        'incumbent_group_service':'GROUP_EXISTING_TERMINAL' if classification == 'DIVERTED' else None,
        'evidence':{k:f'EV-TEST{index:03d}_{j:02d}' for j,k in enumerate(EVIDENCE_FIELDS)},
    }


def sample():
    return {
        'schema_version':'V23','as_of':'2026-10-30',
        'group_id':'GROUP_BERING_TEST', 'currency':'RUB', 'tax_basis':'EX_VAT',
        'shipments':[
            item('P1',1,'NEW','100',None,2),
            item('P2',2,'DIVERTED','200','120',1),
            item('P3',3,'NEW','50',None,1),
        ],
        'pilot_costs':{
            'P1':{'currency':'RUB','tax_basis':'EX_VAT',
                  'cost_event_ids':{'fixed':'COST_P1_FIXED','risk':'COST_P1_RISK'},
                  'incremental_fixed_rub':'10','incremental_risk_rub':'5',
                  'evidence':{'fixed':'EV-COST_P1_F','risk':'EV-COST_P1_R'}},
            'P2':{'currency':'RUB','tax_basis':'EX_VAT',
                  'cost_event_ids':{'fixed':'COST_P2_FIXED','risk':'COST_P2_RISK'},
                  'incremental_fixed_rub':'10','incremental_risk_rub':'5',
                  'evidence':{'fixed':'EV-COST_P2_F','risk':'EV-COST_P2_R'}},
            'P3':{'currency':'RUB','tax_basis':'EX_VAT',
                  'cost_event_ids':{'fixed':'COST_P3_FIXED','risk':'COST_P3_RISK'},
                  'incremental_fixed_rub':'5','incremental_risk_rub':'5',
                  'evidence':{'fixed':'EV-COST_P3_F','risk':'EV-COST_P3_R'}},
        },
    }


class AdditionalityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = sample()
        self.index = {}
        for s in self.case['shipments']:
            for value in s['evidence'].values():
                self.add_doc(value)
        for costs in self.case['pilot_costs'].values():
            for value in costs['evidence'].values():
                self.add_doc(value)

    def add_doc(self, identifier):
        raw = ('SYNTHETIC BYTES FOR '+identifier).encode('utf-8')
        path = identifier + '.txt'
        (self.root / path).write_bytes(raw)
        self.index[identifier] = {
            'relative_path':path,'sha256':hashlib.sha256(raw).hexdigest(),
            'status':'VERIFIED','submitted_by':'test-submitter',
            'reviewed_by':'test-reviewer','reviewed_on':'2026-10-29',
        }

    def result(self, evidence=True):
        return evaluate(self.case, self.index if evidence else None,
                        self.root if evidence else None)

    def test_real_data_not_present_is_hold(self):
        res = self.result(evidence=False)
        self.assertEqual(res['status'],'HOLD')
        self.assertEqual(res['screening_total_incremental_group_cm_rub'],'290')
        self.assertFalse(res['bankable_revenue_approved'])
        self.assertGreater(len(res['missing']),0)

    def test_valid_synthetic_is_review_not_pass(self):
        res = self.result()
        self.assertEqual(res['status'],'REVIEW')
        self.assertEqual(res['screening_total_incremental_group_cm_rub'],'290')
        self.assertEqual(res['pilots']['P1']['screening_incremental_group_cm_rub'],'185')
        self.assertEqual(res['pilots']['P2']['screening_incremental_group_cm_rub'],'65')
        self.assertEqual(res['pilots']['P3']['screening_incremental_group_cm_rub'],'40')
        self.assertEqual(res['pilots']['P2']['classification_counts_40ft']['diverted'],1)
        self.assertFalse(res['bankable_revenue_approved'])
        self.assertFalse(res['contracts_authenticated'])

    def test_duplicate_economic_shipment_blocks_all(self):
        self.case['shipments'][2]['economic_shipment_id']=self.case['shipments'][0]['economic_shipment_id'].lower()
        res=self.result()
        self.assertEqual(res['status'],'INVALID')
        self.assertIsNone(res['screening_total_incremental_group_cm_rub'])
        self.assertTrue(any('duplicate economic shipment' in e for e in res['errors']))

    def test_cross_pilot_same_physical_waybill_blocks(self):
        self.case['shipments'][2]['physical_consignment_key']=self.case['shipments'][0]['physical_consignment_key']
        res=self.result()
        self.assertEqual(res['status'],'INVALID')
        self.assertTrue(any('consignment overlap' in e for e in res['errors']))

    def test_tampered_document_blocks_review(self):
        eid=self.case['shipments'][0]['evidence']['payment']
        (self.root / self.index[eid]['relative_path']).write_text('TAMPERED')
        self.assertEqual(self.result()['status'],'HOLD')

    def test_same_submitter_and_reviewer_is_not_independent(self):
        eid=self.case['shipments'][1]['evidence']['contract']
        self.index[eid]['reviewed_by']='TEST-SUBMITTER'
        self.assertEqual(self.result()['status'],'HOLD')

    def test_future_document_review_rejected(self):
        eid=self.case['shipments'][0]['evidence']['waybill']
        self.index[eid]['reviewed_on']='2026-11-01'
        self.assertEqual(self.result()['status'],'HOLD')

    def test_missing_baseline_blocks_review(self):
        self.case['shipments'][2]['evidence']['baseline_24m']=None
        self.assertEqual(self.result()['status'],'HOLD')

    def test_repeated_evidence_categories_rejected(self):
        row=self.case['shipments'][0]
        row['evidence']['payment']=row['evidence']['contract']
        self.assertEqual(self.result()['status'],'INVALID')

    def test_negative_incumbent_profit_can_be_credited_correctly(self):
        self.case['shipments'][1]['incumbent_group_unit_cm_rub']='-20'
        res=self.result()
        self.assertEqual(res['screening_total_incremental_group_cm_rub'],'430')
        self.assertEqual(res['status'],'REVIEW')

    def test_loss_from_incumbent_displacement_held(self):
        self.case['shipments'][1]['incumbent_group_unit_cm_rub']='250'
        self.assertEqual(self.result()['pilots']['P2']['status'],'HOLD')

    def test_diverted_requires_named_old_group_service(self):
        self.case['shipments'][1]['incumbent_group_service']=None
        res=self.result()
        self.assertEqual(res['status'],'HOLD')
        self.assertIsNone(res['screening_total_incremental_group_cm_rub'])

    def test_new_cannot_claim_preexisting_group_margin(self):
        self.case['shipments'][0]['incumbent_group_unit_cm_rub']='50'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_float_money_rejected_not_rounded(self):
        self.case['shipments'][0]['new_unit_cm_rub']=100.001
        self.assertEqual(self.result()['status'],'INVALID')

    def test_more_than_two_decimal_places_rejected(self):
        self.case['pilot_costs']['P1']['incremental_fixed_rub']='1.111'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_nan_money_rejected(self):
        self.case['shipments'][0]['new_unit_cm_rub']='NaN'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_negative_cost_rejected(self):
        self.case['pilot_costs']['P3']['incremental_fixed_rub']='-1'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_missing_cost_is_not_assumed_zero(self):
        self.case['pilot_costs']['P3']['incremental_fixed_rub']=None
        res=self.result()
        self.assertEqual(res['status'],'HOLD')
        self.assertIsNone(res['screening_total_incremental_group_cm_rub'])

    def test_explicit_zero_cost_still_needs_proof(self):
        self.case['pilot_costs']['P1']['incremental_fixed_rub']='0'
        self.case['pilot_costs']['P1']['evidence']['fixed']=None
        self.assertEqual(self.result()['status'],'HOLD')

    def test_40ft_not_teu_or_tonnes(self):
        self.case['shipments'][0]['unit']='TEU'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_wrong_pilot_cargo_class(self):
        self.case['shipments'][1]['cargo_class']='dry_40ft'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_future_observed_month_rejected(self):
        self.case['shipments'][0]['month']='2026-11'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_group_boundary_mismatch_rejected(self):
        self.case['shipments'][0]['group_id']='OTHER_GROUP'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_excluded_row_not_added_to_profit(self):
        row=item('P1',10,'EXCLUDED',None,None,1)
        row['exclusion_reason']='duplicate receipt, explicitly excluded'
        self.case['shipments'].append(row)
        res=self.result()
        self.assertEqual(res['status'],'REVIEW')
        self.assertEqual(res['pilots']['P1']['excluded_records'],1)
        self.assertEqual(res['screening_total_incremental_group_cm_rub'],'290')

    def test_excluded_row_missing_reason_rejected(self):
        self.case['shipments'].append(item('P1',10,'EXCLUDED',None,None,1))
        self.assertEqual(self.result()['status'],'INVALID')

    def test_empty_but_valid_input_hold_and_null(self):
        empty={'schema_version':'V23','as_of':'2026-10-30',
               'group_id':'GROUP_BERING_TEST','currency':'RUB','tax_basis':'EX_VAT',
               'shipments':[],
               'pilot_costs':{p:{'currency':'RUB','tax_basis':'EX_VAT',
                                 'cost_event_ids':{'fixed':f'COST_{p}_FIXED','risk':f'COST_{p}_RISK'},
                                 'incremental_fixed_rub':None,
                                 'incremental_risk_rub':None,
                                 'evidence':{'fixed':None,'risk':None}}
                              for p in ('P1','P2','P3')}}
        res=evaluate(empty)
        self.assertEqual(res['status'],'HOLD')
        self.assertIsNone(res['screening_total_incremental_group_cm_rub'])
        self.assertEqual(len(res['pilots']),3)

    def test_mixed_currency_blocked(self):
        self.case['shipments'][0]['currency']='USD'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_inclusive_vat_cost_blocked(self):
        self.case['pilot_costs']['P1']['tax_basis']='INCL_VAT'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_reused_cost_event_id_blocked(self):
        self.case['pilot_costs']['P2']['cost_event_ids']['fixed']='COST_P1_FIXED'
        self.assertEqual(self.result()['status'],'INVALID')

    def test_missing_shipments_list_is_invalid(self):
        del self.case['shipments']
        self.assertEqual(self.result()['status'],'INVALID')

    def test_non_dict_source_rejected(self):
        self.assertEqual(evaluate(None)['status'],'INVALID')

    def test_cli_require_review_exit_code_3_without_evidence(self):
        path=self.root/'case.json'
        path.write_text(json.dumps(self.case),encoding='utf-8')
        script=Path(__file__).resolve().parents[1]/'scripts'/'cross_pilot_additionality_v23.py'
        proc=subprocess.run([sys.executable,str(script),'--input',str(path),'--require-review'],
                            capture_output=True,text=True)
        self.assertEqual(proc.returncode,3)
        self.assertEqual(json.loads(proc.stdout)['status'],'HOLD')


if __name__=='__main__':
    unittest.main()

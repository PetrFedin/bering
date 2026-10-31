import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from source_join_v25 import audit,verify_v23

TOKENS=['a'*64,'b'*64,'c'*64]
class ReconcileV25Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        self.docs={};self.n=0
        def doc():
            self.n+=1
            eid=f'EV-TEST-COMPLETELY-FAKE-{self.n:04}'
            name=f'fake-{self.n:04}.txt'
            raw=f'FAKE {eid} no real shipment'.encode()
            (self.root/name).write_bytes(raw)
            self.docs[eid]={
               'status':'REVIEWED_BYTES','path':name,'sha256':hashlib.sha256(raw).hexdigest(),
               'submitter':'tester-a','reviewer':'tester-b','reviewed_date':'2026-10-29'}
            return eid
        self.doc=doc
        self.payload={'schema_version':'V25','as_of':'2026-10-31','group_id':'TEST_GROUP_001',
                      'currency':'RUB','tax_basis':'EX_VAT','shipments':[], 'legs':[],
                      'incumbent_services':[],'pilot_costs':{},
                      'group_baseline':{'months_covered':24,'evidence_id':doc()}}
        for i,p in enumerate(['P1','P2','P3']):
            d={kind:doc() for kind in ('identity','waybill','invoice','payment','unit_cm','additionality')}
            kind='DIVERTED' if p=='P2' else 'NEW'
            row={'physical_consignment_key':TOKENS[i], 'pilot_id':p,
                 'economic_shipment_id':f'TEST_SHIP_{i+1:02}',
                 'classification':kind,'quantity_40ft':1,'currency':'RUB','tax_basis':'EX_VAT',
                 'new_unit_cm_rub':['100','200','50'][i],
                 'incumbent_group_unit_cm_rub':'120' if p=='P2' else None,
                 'incumbent_group_service':'OLD_GROUP_TERMINAL' if p=='P2' else None,
                 'evidence':d}
            self.payload['shipments'].append(row)
            for route in (['CHINA_VVO','VVO_MAG'] if p=='P3' else ['VVO_MAG']):
                self.payload['legs'].append({'physical_consignment_key':TOKENS[i],
                    'pilot_id':p,'route_leg':route,'service_event_id':f'EVENT_{p}_{route}',
                    'waybill_evidence_id':doc()})
            if p=='P2':
                self.payload['incumbent_services'].append({'physical_consignment_key':TOKENS[i],
                    'incumbent_group_unit_cm_rub':'120','incumbent_group_service':'OLD_GROUP_TERMINAL',
                    'old_margin_evidence_id':doc()})
            self.payload['pilot_costs'][p]={
                'incremental_fixed_rub':'10' if p!='P3' else '5',
                'incremental_risk_rub':'5',
                'cost_event_ids':{'fixed':f'FIXED_{p}','risk':f'RISK_{p}'},
                'evidence':{'fixed':doc(),'risk':doc()}}
        self.v23={'schema_version':'V23','group_id':'TEST_GROUP_001',
             'currency':'RUB','tax_basis':'EX_VAT',
             'shipments':[dict(s) for s in self.payload['shipments']],
             'pilot_costs':self.payload['pilot_costs']}
    def audit(self, p=None, v23=None):
        return audit(self.payload if p is None else p, self.docs, self.root, self.v23 if v23 is None else v23)
    def test_good_fake_fixture_review_not_investment(self):
        r=self.audit();self.assertEqual(r['status'],'REVIEW_ONLY')
        self.assertTrue(r['source_to_v23_match']);self.assertEqual(r['unique_paid_40ft'],3)
        self.assertEqual(r['group_incremental_cm_rub'],'190')
        self.assertFalse(r['investment_approved']);self.assertFalse(r['bankable_revenue_approved'])
        self.assertFalse(r['contractual_demand_verified'])
    def test_per_pilot_subtracts_incumbent_and_cost_once(self):
        r=self.audit();self.assertEqual(r['pilot_incremental_cm_rub'],{'P1':'85','P2':'65','P3':'40'})
    def test_no_claims_hold_not_zero(self):
        p=json.loads(json.dumps(self.payload));p['shipments']=[];p['legs']=[];p['incumbent_services']=[]
        self.assertEqual(self.audit(p)['status'],'INVALID') # v23 source mismatch, not ZERO
    def test_empty_canonical_data_hold_unknown_not_zero(self):
        p=json.loads(json.dumps(self.payload))
        p['shipments']=[];p['legs']=[];p['incumbent_services']=[]
        v=json.loads(json.dumps(self.v23));v['shipments']=[]
        report=self.audit(p,v)
        self.assertEqual(report['status'],'HOLD')
        self.assertIsNone(report['unique_paid_40ft'])
        self.assertIsNone(report['group_incremental_cm_rub'])
    def test_v23_not_provided_hold(self):
        self.assertEqual(audit(self.payload,self.docs,self.root,None)['status'],'HOLD')
    def test_duplicate_physical_different_economic_invalid(self):
        p=json.loads(json.dumps(self.payload));p['shipments'][1]['physical_consignment_key']=TOKENS[0]
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_single_p3_leg_is_not_new_freight(self):
        p=json.loads(json.dumps(self.payload));p['legs']=[x for x in p['legs'] if x['route_leg']!='CHINA_VVO']
        self.assertEqual(self.audit(p)['status'],'HOLD')
    def test_p3_vvo_leg_cannot_be_p1(self):
        p=json.loads(json.dumps(self.payload));p['legs'][-1]['pilot_id']='P1'
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_duplicate_handling_event_invalid(self):
        p=json.loads(json.dumps(self.payload));p['legs'][1]['service_event_id']=p['legs'][0]['service_event_id']
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_missing_incumbent_ledger_hold(self):
        p=json.loads(json.dumps(self.payload));p['incumbent_services']=[]
        self.assertEqual(self.audit(p)['status'],'HOLD')
    def test_incumbent_margin_mismatch_invalid(self):
        p=json.loads(json.dumps(self.payload));p['incumbent_services'][0]['incumbent_group_unit_cm_rub']='100'
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_new_has_no_existing_group_margin(self):
        p=json.loads(json.dumps(self.payload));p['shipments'][0]['incumbent_group_unit_cm_rub']='50'
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_duplicate_payment_document_invalid(self):
        p=json.loads(json.dumps(self.payload));p['shipments'][1]['evidence']['payment']=p['shipments'][0]['evidence']['payment']
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_24m_missing_hold(self):
        p=json.loads(json.dumps(self.payload));p['group_baseline']['months_covered']=6
        self.assertEqual(self.audit(p)['status'],'HOLD')
    def test_modified_source_bytes_hold(self):
        doc_id=self.payload['shipments'][0]['evidence']['payment'];path=self.root/self.docs[doc_id]['path']
        old=path.read_bytes()
        try:
            path.write_text('TAMPERED');self.assertEqual(self.audit()['status'],'HOLD')
        finally:path.write_bytes(old)
    def test_no_independent_review_hold(self):
        doc_id=self.payload['shipments'][0]['evidence']['waybill']
        self.docs[doc_id]['reviewer']='TESTER-A'
        self.assertEqual(self.audit()['status'],'HOLD')
    def test_missing_legs_hold(self):
        p=json.loads(json.dumps(self.payload));p['legs']=[]
        self.assertEqual(self.audit(p)['status'],'HOLD')
    def test_mismatched_v23_physical_set_invalid(self):
        v=json.loads(json.dumps(self.v23));v['shipments'][0]['physical_consignment_key']='d'*64
        self.assertEqual(self.audit(v23=v)['status'],'INVALID')
    def test_mismatched_v23_profit_invalid(self):
        v=json.loads(json.dumps(self.v23));v['shipments'][1]['new_unit_cm_rub']='250'
        self.assertEqual(self.audit(v23=v)['status'],'INVALID')
    def test_mismatched_v23_fixed_cost_invalid(self):
        v=json.loads(json.dumps(self.v23));v['pilot_costs']['P1']['incremental_fixed_rub']='100'
        self.assertEqual(self.audit(v23=v)['status'],'INVALID')
    def test_v23_cost_event_id_mismatch_invalid(self):
        v=json.loads(json.dumps(self.v23));v['pilot_costs']['P2']['cost_event_ids']['risk']='OTHER_RISK'
        self.assertEqual(self.audit(v23=v)['status'],'INVALID')
    def test_pilot_cost_reused_across_three_invalid(self):
        p=json.loads(json.dumps(self.payload));p['pilot_costs']['P3']['cost_event_ids']['risk']=p['pilot_costs']['P1']['cost_event_ids']['risk']
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_amount_float_invalid(self):
        p=json.loads(json.dumps(self.payload));p['shipments'][0]['new_unit_cm_rub']=1.5
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_vat_mismatch_invalid(self):
        p=json.loads(json.dumps(self.payload));p['shipments'][0]['tax_basis']='IN_VAT'
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_quantity_grouped_two_invalid(self):
        p=json.loads(json.dumps(self.payload));p['shipments'][0]['quantity_40ft']=2
        self.assertEqual(self.audit(p)['status'],'INVALID')
    def test_p3_double_counted_as_p1_invalid(self):
        p=json.loads(json.dumps(self.payload));copy=dict(p['shipments'][2]);copy['pilot_id']='P1';copy['economic_shipment_id']='TEST_SHIP_EXTRA'
        p['shipments'].append(copy)
        self.assertEqual(self.audit(p)['status'],'INVALID')

if __name__=='__main__':unittest.main()

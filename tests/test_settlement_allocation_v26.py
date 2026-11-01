"""Synthetic evidence and financial allocation regressions (NO real transactions)."""
from __future__ import annotations
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from settlement_allocation_v26 import audit

KEYS=['a'*64,'b'*64,'c'*64]

class InvoiceBankV26Test(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.docs={};self.n=0
        def doc():
            self.n+=1;eid=f'EV-TEST-ARTIFICIAL-{self.n:03d}'
            p=f'document_{self.n:03d}.txt'
            b=f'FAKE document {self.n}, not a bank statement'.encode()
            (self.root/p).write_bytes(b)
            self.docs[eid]={'status':'REVIEWED_BYTES','path':p,
                            'sha256':hashlib.sha256(b).hexdigest(),
                            'submitter':'employee-A','reviewer':'employee-B',
                            'reviewed_date':'2026-10-30'}
            return eid
        self.doc=doc
        self.inva=doc();self.invb=doc();self.bank=doc()
        self.payload={
            'schema_version':'V26','as_of':'2026-10-31','group_id':'RESEARCH_GROUP_1',
            'currency':'RUB','amount_basis':'GROSS_NET_VAT_SEPARATELY',
            'source_type':'SETTLED_INVOICE_ALLOCATION_RESEARCH','refunds_declared':False,
            'invoices':[
                {'invoice_id':'INVOICE_AA','invoice_date':'2026-10-27','evidence_id':self.inva,
                 'net_rub':'300','vat_rub':'30','gross_rub':'330',
                 'container_allocations':[
                     {'physical_consignment_key':KEYS[0],'net_rub':'100','vat_rub':'10','gross_rub':'110'},
                     {'physical_consignment_key':KEYS[1],'net_rub':'200','vat_rub':'20','gross_rub':'220'}]},
                {'invoice_id':'INVOICE_BB','invoice_date':'2026-10-28','evidence_id':self.invb,
                 'net_rub':'50','vat_rub':'5','gross_rub':'55',
                 'container_allocations':[
                     {'physical_consignment_key':KEYS[2],'net_rub':'50','vat_rub':'5','gross_rub':'55'}]},
            ],
            'payments':[
                {'bank_transaction_id':'TRANSACTION_A','settlement_date':'2026-10-29',
                 'currency':'RUB','evidence_id':self.bank,'gross_settled_rub':'200',
                 'invoice_allocations':[{'invoice_id':'INVOICE_AA','gross_rub':'200'}]},
                {'bank_transaction_id':'TRANSACTION_B','settlement_date':'2026-10-30',
                 'currency':'RUB','evidence_id':self.bank,'gross_settled_rub':'185',
                 'invoice_allocations':[{'invoice_id':'INVOICE_AA','gross_rub':'130'},
                                        {'invoice_id':'INVOICE_BB','gross_rub':'55'}]},
            ]}
        self.v25={'schema_version':'V25','as_of':'2026-10-31','group_id':'RESEARCH_GROUP_1',
                  'shipments':[{'physical_consignment_key':k} for k in KEYS]}

    def evaluate(self,p=None,v25=None):
        return audit(copy.deepcopy(self.payload) if p is None else p,
                     self.docs,self.root,self.v25 if v25 is None else v25)
    def mutated(self,f):
        p=copy.deepcopy(self.payload);f(p);return self.evaluate(p)
    def test_complete_synthetic_batch_review_only(self):
        r=self.evaluate();self.assertEqual(r['status'],'REVIEW_ONLY')
        self.assertEqual(r['matched_physical_40ft'],3)
        self.assertEqual(r['invoice_count'],2)
        self.assertEqual(r['bank_transaction_count'],2)
        self.assertEqual(r['mechanically_reconciled_gross_rub'],'385')
        self.assertFalse(r['investment_approved'])
        self.assertIsNone(r['group_incremental_cm_rub'])
        self.assertFalse(r['bank_authenticity_verified'])
    def test_one_invoice_many_containers_allowed(self):
        self.assertEqual(len(self.payload['invoices'][0]['container_allocations']),2)
        self.assertEqual(self.evaluate()['status'],'REVIEW_ONLY')
    def test_one_bank_statement_many_transactions_allowed(self):
        self.assertEqual(self.payload['payments'][0]['evidence_id'],self.payload['payments'][1]['evidence_id'])
        self.assertEqual(self.evaluate()['status'],'REVIEW_ONLY')
    def test_one_payment_can_settle_two_invoices(self):
        p=copy.deepcopy(self.payload)
        p['payments']=[{'bank_transaction_id':'TRANSACTION_COMBINED','settlement_date':'2026-10-30',
                        'currency':'RUB','evidence_id':self.bank,'gross_settled_rub':'385',
                        'invoice_allocations':[{'invoice_id':'INVOICE_AA','gross_rub':'330'},
                                               {'invoice_id':'INVOICE_BB','gross_rub':'55'}]}]
        self.assertEqual(self.evaluate(p)['status'],'REVIEW_ONLY')
    def test_no_v25_hold(self):
        self.assertEqual(audit(self.payload,self.docs,self.root,None)['status'],'HOLD')
    def test_v25_cross_group_invalid(self):
        v=copy.deepcopy(self.v25);v['group_id']='OTHER_GROUP'
        self.assertEqual(self.evaluate(v25=v)['status'],'INVALID')
    def test_v25_cross_date_invalid(self):
        v=copy.deepcopy(self.v25);v['as_of']='2026-09-30'
        self.assertEqual(self.evaluate(v25=v)['status'],'INVALID')
    def test_missing_v25_physical_container_invalid(self):
        v=copy.deepcopy(self.v25);v['shipments'].pop()
        self.assertEqual(self.evaluate(v25=v)['status'],'INVALID')
    def test_duplicate_v25_physical_container_invalid(self):
        v=copy.deepcopy(self.v25);v['shipments'].append(copy.deepcopy(v['shipments'][0]))
        self.assertEqual(self.evaluate(v25=v)['status'],'INVALID')
    def test_duplicate_invoice_id_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['invoices'][1].update(invoice_id='INVOICE_AA'))['status'],'INVALID')
    def test_duplicate_bank_transaction_id_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['payments'][1].update(bank_transaction_id='TRANSACTION_A'))['status'],'INVALID')
    def test_duplicate_container_inside_invoice_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['invoices'][0]['container_allocations'][1].update(physical_consignment_key=KEYS[0]))['status'],'INVALID')
    def test_wrong_invoice_gross_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['invoices'][0].update(gross_rub='331'))['status'],'INVALID')
    def test_wrong_vat_split_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['invoices'][0]['container_allocations'][0].update(vat_rub='11'))['status'],'INVALID')
    def test_wrong_bank_transfer_allocation_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['payments'][1].update(gross_settled_rub='186'))['status'],'INVALID')
    def test_overpaid_invoice_invalid(self):
        p=copy.deepcopy(self.payload)
        p['payments'][1]['invoice_allocations'][0]['gross_rub']='131'
        p['payments'][1]['gross_settled_rub']='186'
        self.assertEqual(self.evaluate(p)['status'],'INVALID')
    def test_incomplete_payment_hold(self):
        p=copy.deepcopy(self.payload)
        p['payments'][1]['invoice_allocations'][0]['gross_rub']='125'
        p['payments'][1]['gross_settled_rub']='180'
        self.assertEqual(self.evaluate(p)['status'],'HOLD')
    def test_no_invoices_no_zero_claim(self):
        p=copy.deepcopy(self.payload);p['invoices']=[];p['payments']=[]
        self.assertEqual(self.evaluate(p)['status'],'INVALID')
        self.assertIsNone(self.evaluate(p)['matched_physical_40ft'])
    def test_refunds_declared_hold_for_manual_credit_note(self):
        self.assertEqual(self.mutated(lambda p:p.update(refunds_declared=True))['status'],'HOLD')
    def test_missing_bank_document_hold(self):
        self.docs.pop(self.bank)
        self.assertEqual(self.evaluate()['status'],'HOLD')
    def test_no_independent_review_hold(self):
        self.docs[self.inva]['reviewer']='EMPLOYEE-a'
        self.assertEqual(self.evaluate()['status'],'HOLD')
    def test_document_bytes_tampered_hold(self):
        d=self.docs[self.inva];(self.root/d['path']).write_text('TAMPERED')
        self.assertEqual(self.evaluate()['status'],'HOLD')
    def test_cross_category_reused_document_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['payments'][0].update(evidence_id=self.inva))['status'],'INVALID')
    def test_wrong_currency_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['payments'][0].update(currency='EUR'))['status'],'INVALID')
    def test_wrong_asof_future_invoice_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['invoices'][0].update(invoice_date='2026-11-01'))['status'],'INVALID')
    def test_rounding_beyond_kopeck_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['invoices'][0].update(net_rub='300.001'))['status'],'INVALID')
    def test_float_monetary_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['invoices'][0].update(net_rub=300.0))['status'],'INVALID')
    def test_negative_bank_amount_invalid(self):
        self.assertEqual(self.mutated(lambda p:p['payments'][0].update(gross_settled_rub='-10'))['status'],'INVALID')
    def test_batch_receipt_is_not_new_demand(self):
        r=self.evaluate()
        self.assertFalse(r['commercial_additionality_verified'])
        self.assertFalse(r['bankable_revenue_approved'])
    def test_zero_vat_line_allowed_under_exact_gross(self):
        p=copy.deepcopy(self.payload)
        inv=p['invoices'][1]
        inv['vat_rub']='0';inv['gross_rub']='50';inv['container_allocations'][0]['vat_rub']='0';inv['container_allocations'][0]['gross_rub']='50'
        p['payments'][1]['invoice_allocations'][1]['gross_rub']='50'
        p['payments'][1]['gross_settled_rub']='180'
        self.assertEqual(self.evaluate(p)['status'],'REVIEW_ONLY')

if __name__=='__main__':unittest.main()
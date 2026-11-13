"""Synthetic financial reconciliation fixtures: NO real Bering invoices or payments."""
import copy
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from v33_shipment_proof_quality import analyze as check_v33  # noqa: E402
from v34_bank_allocation_gate import (analyze, empty_input, report, NOTICE, SCHEMA)  # noqa: E402
from test_v33_shipment_proof_quality import fake_extract, shipment, coverage  # noqa: E402

DIGEST = 'b' * 64
HASH = 'a' * 64


def invoice(token='INVOICE_001', total='100000', credit='10000', currency='RUB'):
    return {'invoice_token': token, 'invoice_sha256': HASH, 'currency': currency,
            'invoice_total_minor': total, 'credit_note_minor': credit,
            'credit_note_sha256': HASH if credit != '0' else None,
            'source_row_locator': 'INVOICE_LINE_001'}


def bank(token='BANKTXN_001', amount='90000', currency='RUB', date='2025-02-10'):
    return {'bank_transaction_token':token, 'bank_statement_sha256': HASH,
            'currency': currency, 'amount_minor': amount, 'payment_date':date,
            'source_row_locator':'BANK_LINE_001'}


def alloc(inv='INVOICE_001', txn='BANKTXN_001', amt='90000'):
    return {'invoice_token': inv, 'bank_transaction_token': txn, 'amount_minor': amt}


def link(inv='INVOICE_001', amount='90000', scope='P1', shipment_token='SHIPMENT_0001', container_token='CONTAINER_001'):
    return {'scope': scope, 'shipment_token': shipment_token,
            'container_token': container_token, 'invoice_token':inv,
            'invoice_apportionment_minor':amount}


def case():
    v33 = fake_extract()
    p = empty_input()
    p['v33_source_sha256'] = DIGEST
    p['invoices'] = [invoice()]
    p['bank_transactions'] = [bank()]
    p['allocations'] = [alloc()]
    p['shipment_invoice_links'] = [link()]
    return p, v33


class GateTests(unittest.TestCase):
    def good(self, packet=None, prior=None):
        packet, prior = (packet, prior) if packet is not None else case()
        result = analyze(packet, v33=prior, v33_digest=DIGEST)
        self.assertEqual(result['status'], 'STRUCTURAL_REVIEW_REQUIRED',result['errors'])
        self.assertFalse(result['bank_settlement_verified_independently'])
        self.assertFalse(result['investment_approved'])
        self.assertIsNone(result['paid_incremental_40ft'])
        self.assertIsNone(result['bering_npv_rub'])
        return result

    def bad(self, modify, expected):
        packet, v33 = case()
        modify(packet,v33)
        result=analyze(packet,v33=v33,v33_digest=DIGEST)
        self.assertEqual(result['status'],'INVALID',result['errors'])
        self.assertIn(expected,result['errors'])
        self.assertIsNone(result['incremental_group_contribution_margin_rub'])
        self.assertFalse(result['investment_approved'])

    def test_no_sources_are_missing_not_zero(self):
        r=analyze(empty_input())
        self.assertEqual(r['status'],'NO_SOURCE_RECORDS_IN_SCOPE')
        self.assertEqual(r['candidate_bank_lines'],0)
        self.assertIsNone(r['paid_incremental_40ft'])

    def test_one_invoice_one_bank_line_structurally_matches(self):
        r=self.good()
        self.assertEqual(r['candidate_fully_claimed_paid_invoices'],1)
        self.assertEqual(r['candidate_fully_allocated_invoices'],1)
        self.assertEqual(r['candidate_bank_lines'],1)

    def test_fabricated_source_digest_rejected(self):
        p,v=case();p['v33_source_sha256']='f'*64
        self.assertIn('V33_SOURCE_DIGEST_NOT_VERIFIED',analyze(p,v,DIGEST)['errors'])

    def test_missing_v33_is_not_a_paid_record(self):
        p,_=case()
        self.assertIn('V33_SOURCE_ABSENT',analyze(p)['errors'])

    def test_malformed_v33_rejected(self):
        self.bad(lambda p,v:v['shipments'][0].update(teu=1),'V33_SOURCE_NOT_STRUCTURALLY_VALID')

    def test_bank_overallocation_rejected(self):
        self.bad(lambda p,v:p['bank_transactions'][0].update(amount_minor='50000'), 'BANK_TRANSACTION_DOUBLE_ALLOCATED')

    def test_invoice_overpayment_rejected(self):
        self.bad(lambda p,v:p['allocations'][0].update(amount_minor='100000'),'INVOICE_OVERPAID_BY_ALLOCATIONS')

    def test_duplicate_bank_allocation_pair_rejected(self):
        self.bad(lambda p,v:p['allocations'].append(copy.deepcopy(p['allocations'][0])),'ALLOCATION_PAIR_DUPLICATED')

    def test_bank_missing_from_index(self):
        self.bad(lambda p,v:p['allocations'][0].update(bank_transaction_token='UNKNOWN_BANK_001'),'ALLOCATION_ORPHAN_REFERENCE')

    def test_invoice_missing_from_index(self):
        self.bad(lambda p,v:p['allocations'][0].update(invoice_token='UNKNOWN_INV_001'),'ALLOCATION_ORPHAN_REFERENCE')

    def test_currency_mismatch(self):
        self.bad(lambda p,v:p['bank_transactions'][0].update(currency='USD'),'ALLOCATION_CURRENCY_MISMATCH')

    def test_future_payment_date(self):
        self.bad(lambda p,v:p['bank_transactions'][0].update(payment_date='2027-01-01'),'BANK_PAYMENT_DATE_IN_FUTURE')

    def test_invalid_calendar_date(self):
        self.bad(lambda p,v:p['bank_transactions'][0].update(payment_date='2026-02-30'),'BANK_PAYMENT_DATE_INVALID')

    def test_negative_allocation_disallowed(self):
        self.bad(lambda p,v:p['allocations'][0].update(amount_minor='-100'),'ALLOCATION_AMOUNT_INVALID')

    def test_typed_money_only(self):
        self.bad(lambda p,v:p['bank_transactions'][0].update(amount_minor=90000),'BANK_AMOUNT_INVALID')

    def test_no_unknown_invoice_fields(self):
        self.bad(lambda p,v:p['invoices'][0].update(approved_by_bank=True),'INVOICE_SCHEMA_INVALID')

    def test_missing_shipment_link(self):
        self.bad(lambda p,v:p.update(shipment_invoice_links=[]),'SHIPMENT_INVOICE_LINK_COVERAGE_MISMATCH')

    def test_fake_shipment_reference(self):
        self.bad(lambda p,v:p['shipment_invoice_links'][0].update(shipment_token='DIFFERENT_001'),'SHIPMENT_LINK_MISSING_V33_ROW')

    def test_invoice_apportionment_imbalance(self):
        self.bad(lambda p,v:p['shipment_invoice_links'][0].update(invoice_apportionment_minor='100000'),'INVOICE_TO_SHIPMENT_ALLOCATION_NOT_BALANCED')

    def test_v33_invoice_amount_conflict(self):
        self.bad(lambda p,v:p['invoices'][0].update(invoice_total_minor='200000'),'V33_INVOICE_FACT_CONFLICT')

    def test_v33_invoice_sha_conflict(self):
        self.bad(lambda p,v:p['invoices'][0].update(invoice_sha256='f'*64),'V33_INVOICE_FACT_CONFLICT')

    def test_duplicate_shipment_link_rejected(self):
        self.bad(lambda p,v:p['shipment_invoice_links'].append(copy.deepcopy(p['shipment_invoice_links'][0])),'SHIPMENT_LINK_DUPLICATE')

    def test_partial_payment_is_not_full(self):
        p,v=case();p['allocations'][0]['amount_minor']='40000'
        r=self.good(p,v)
        self.assertEqual(r['candidate_fully_claimed_paid_invoices'],0)
        self.assertEqual(r['candidate_unallocated_bank_lines'],1)

    def test_one_bank_line_can_pay_two_invoices_without_doublecount(self):
        p,v=case()
        extra=shipment(token='CONTAINER_002');extra['shipment_token']='SHIPMENT_0002';extra['waybill_token']='WAYBILL_002';extra['invoice_token']='INVOICE_002';extra['invoice_total_minor']='50000';extra['credit_note_minor']='0';extra['bank_paid_minor']='50000'
        v['shipments'].append(extra);v['monthly_coverage'][0]['reported_container_count']=2
        invoice_two=invoice(token='INVOICE_002',total='50000',credit='0')
        invoice_two['source_row_locator']='INVOICE_LINE_002'
        p['invoices'].append(invoice_two)
        p['bank_transactions'][0]['amount_minor']='140000'
        p['allocations'].append(alloc(inv='INVOICE_002',amt='50000'))
        p['shipment_invoice_links'].append(link(inv='INVOICE_002',amount='50000',shipment_token='SHIPMENT_0002',container_token='CONTAINER_002'))
        r=self.good(p,v)
        self.assertEqual(r['candidate_fully_claimed_paid_invoices'],2)
        self.assertEqual(r['candidate_bank_lines'],1)
        self.assertEqual(r['candidate_unallocated_bank_lines'],0)

    def test_single_invoice_multi_container_not_doublecounted(self):
        p,v=case()
        other=shipment(token='CONTAINER_002');other['shipment_token']='SHIPMENT_0002';other['waybill_token']='WAYBILL_002'
        v['shipments'].append(other);v['monthly_coverage'][0]['reported_container_count']=2
        p['shipment_invoice_links'][0]['invoice_apportionment_minor']='50000'
        p['shipment_invoice_links'].append(link(amount='40000',shipment_token='SHIPMENT_0002',container_token='CONTAINER_002'))
        r=self.good(p,v)
        self.assertEqual(r['candidate_fully_claimed_paid_invoices'],1)
        self.assertEqual(r['candidate_shipment_invoice_links'],2)

    def test_shared_invoice_group_is_review_not_growth(self):
        p,v=case()
        extra=shipment(scope='GROUP_EXISTING',token='CONTAINER_002');extra['shipment_token']='SHIPMENT_0002';extra['waybill_token']='WAYBILL_002'
        v['shipments'].append(extra);v['monthly_coverage'].append(coverage(scope='GROUP_EXISTING'))
        p['shipment_invoice_links'][0]['invoice_apportionment_minor']='50000'
        p['shipment_invoice_links'].append(link(amount='40000',scope='GROUP_EXISTING',shipment_token='SHIPMENT_0002',container_token='CONTAINER_002'))
        r=self.good(p,v)
        self.assertEqual(r['candidate_shared_invoices_across_scopes'],1)
        self.assertFalse(r['bankable_revenue_approved'])

    def test_zero_credit_net_payment_not_bankable(self):
        p,v=case();p['invoices'][0]['credit_note_minor']='100000';v['shipments'][0]['credit_note_minor']='100000'
        p['allocations']=[]
        p['shipment_invoice_links'][0]['invoice_apportionment_minor']='0'
        r=analyze(p,v,DIGEST)
        self.assertEqual(r['status'],'INVALID')
        self.assertIn('SHIPMENT_ALLOCATION_AMOUNT_INVALID',r['errors'])

    def test_invalid_schema_and_non_object(self):
        for obj in (None,[],{'unexpected':1},'text'):
            self.assertEqual(analyze(obj)['status'],'INVALID')

    def test_wrong_notice_rejected(self):
        p,v=case();p['source_notice']='BANK_VERIFIED'
        self.assertIn('WRONG_SCHEMA_OR_SOURCE_NOTICE',analyze(p,v,DIGEST)['errors'])

    def test_duplicate_invoice_token(self):
        self.bad(lambda p,v:p['invoices'].append(copy.deepcopy(p['invoices'][0])),'INVOICE_TOKEN_DUPLICATED')

    def test_duplicate_bank_token(self):
        self.bad(lambda p,v:p['bank_transactions'].append(copy.deepcopy(p['bank_transactions'][0])),'BANK_TOKEN_DUPLICATED')

    def test_missing_credit_note_document_hash(self):
        self.bad(lambda p,v:p['invoices'][0].update(credit_note_sha256=None),'CREDIT_NOTE_DOCUMENT_HASH_REQUIRED')

    def test_duplicate_invoice_source_row_under_two_tokens(self):
        def change(p,v):
            copy_inv=copy.deepcopy(p['invoices'][0]);copy_inv['invoice_token']='INVOICE_002'
            p['invoices'].append(copy_inv)
        self.bad(change,'DUPLICATE_PHYSICAL_INVOICE_SOURCE_ROW')

    def test_duplicate_bank_source_row_under_two_tokens(self):
        def change(p,v):
            copy_bank=copy.deepcopy(p['bank_transactions'][0]);copy_bank['bank_transaction_token']='BANKTXN_002'
            p['bank_transactions'].append(copy_bank)
        self.bad(change,'DUPLICATE_PHYSICAL_BANK_SOURCE_ROW')

    def test_credit_zero_has_no_credit_note_hash(self):
        self.bad(lambda p,v:p['invoices'][0].update(credit_note_minor='0',credit_note_sha256=HASH),'ZERO_CREDIT_MUST_NOT_REFERENCE_CREDIT_NOTE')

    def test_missing_or_invalid_bank_doc_hash(self):
        self.bad(lambda p,v:p['bank_transactions'][0].update(bank_statement_sha256=None),'BANK_DOCUMENT_REFERENCE_INVALID')

    def test_cli_empty_baseline_returns_not_proof(self):
        cp=subprocess.run([sys.executable,str(ROOT/'scripts/v34_bank_allocation_gate.py')],
                          cwd=ROOT,text=True,capture_output=True,check=False)
        self.assertEqual(cp.returncode,0,cp.stderr)
        r=json.loads(cp.stdout)
        self.assertEqual(r['status'],'NO_SOURCE_RECORDS_IN_SCOPE')
        self.assertFalse(r['investment_approved'])

    def test_cli_rejects_only_ledger_argument(self):
        cp=subprocess.run([sys.executable,str(ROOT/'scripts/v34_bank_allocation_gate.py'),
                           '--private-ledger','private.json'],cwd=ROOT,text=True,capture_output=True,check=False)
        self.assertEqual(cp.returncode,2)
        self.assertEqual(json.loads(cp.stdout)['status'],'INVALID')

    def test_cli_private_files_are_structural_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);private=p/'local_private';private.mkdir()
            packet, prior=case()
            src=private/'v33.json';dest=private/'v34.json'
            src.write_text(json.dumps(prior)); sha=hashlib.sha256(src.read_bytes()).hexdigest()
            packet['v33_source_sha256']=sha
            dest.write_text(json.dumps(packet)); ledgersha=hashlib.sha256(dest.read_bytes()).hexdigest()
            cp=subprocess.run([sys.executable,str(ROOT/'scripts/v34_bank_allocation_gate.py'),
                               '--repo',str(p),'--private-ledger',str(dest),'--private-v33',str(src),
                               '--expected-v33-sha256',sha,'--expected-ledger-sha256',ledgersha],
                              cwd=ROOT,text=True,capture_output=True,check=False)
            self.assertEqual(cp.returncode,0,cp.stderr)
            r=json.loads(cp.stdout);self.assertEqual(r['status'],'STRUCTURAL_REVIEW_REQUIRED')
            self.assertIsNone(r['paid_incremental_40ft'])

    def test_cli_bad_expected_digest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);private=p/'local_private';private.mkdir()
            packet,prior=case()
            src=private/'v33.json';dest=private/'v34.json'
            src.write_text(json.dumps(prior));packet['v33_source_sha256']=hashlib.sha256(src.read_bytes()).hexdigest()
            dest.write_text(json.dumps(packet))
            cp=subprocess.run([sys.executable,str(ROOT/'scripts/v34_bank_allocation_gate.py'),
                               '--repo',str(p),'--private-ledger',str(dest),'--private-v33',str(src),
                               '--expected-v33-sha256','f'*64,'--expected-ledger-sha256',hashlib.sha256(dest.read_bytes()).hexdigest()],
                              cwd=ROOT,text=True,capture_output=True,check=False)
            self.assertEqual(cp.returncode,2)
            self.assertFalse(json.loads(cp.stdout)['investment_approved'])


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Research-only reconciliation of shipment invoices and claimed bank lines.

Does NOT authenticate banking documents or attest a paid new Bering shipment.
Requires linked, immutable private V33 source bytes to evaluate populated rows.
No identity/amount from source is emitted; all financial decision fields stay null.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from v33_shipment_proof_quality import analyze as analyze_v33, safe_private_path, valid_sha, valid_token, parse_minor

SCHEMA = 'BERING_V34_BANK_ALLOCATION_V1'
NOTICE = 'RESEARCH_ONLY_CLAIMED_VALUES_NOT_INDEPENDENT_BANK_PROOF'
FIELDS = {'schema', 'source_notice', 'v33_source_sha256', 'invoices', 'bank_transactions',
          'allocations', 'shipment_invoice_links'}
INVOICE_FIELDS = {'invoice_token', 'invoice_sha256', 'currency', 'invoice_total_minor',
                  'credit_note_minor', 'credit_note_sha256', 'source_row_locator'}
BANK_FIELDS = {'bank_transaction_token', 'bank_statement_sha256', 'currency',
               'amount_minor', 'payment_date', 'source_row_locator'}
ALLOC_FIELDS = {'invoice_token', 'bank_transaction_token', 'amount_minor'}
LINK_FIELDS = {'scope', 'shipment_token', 'container_token', 'invoice_token',
               'invoice_apportionment_minor'}
CURRENCIES = {'RUB', 'USD', 'EUR', 'CNY'}
AS_OF = date(2026, 11, 13)
MAX_ENTRIES = 200000


def empty_input():
    return {'schema': SCHEMA, 'source_notice': NOTICE, 'v33_source_sha256': None,
            'invoices': [], 'bank_transactions': [], 'allocations': [],
            'shipment_invoice_links': []}


def report(status, errors, **counts):
    return {'status': status, 'schema': SCHEMA,
            'candidate_invoices': counts.get('invoices'),
            'candidate_bank_lines': counts.get('banks'),
            'candidate_allocations': counts.get('allocations'),
            'candidate_shipment_invoice_links': counts.get('links'),
            'candidate_fully_allocated_invoices': counts.get('balanced_invoices'),
            'candidate_fully_claimed_paid_invoices': counts.get('paid_invoices'),
            'candidate_unallocated_bank_lines': counts.get('unallocated_bank_lines'),
            'candidate_shared_invoices_across_scopes': counts.get('cross_scope_invoices'),
            'source_payload_authenticated': False,
            'bank_statement_authenticated': False,
            'bank_settlement_verified_independently': False,
            'paid_incremental_40ft': None,
            'incremental_group_contribution_margin_rub': None,
            'bering_npv_rub': None,
            'P1': 'HOLD', 'P2': 'HOLD', 'P3': 'HOLD',
            'bankable_revenue_approved': False, 'investment_approved': False,
            'errors': sorted(set(errors)),
            'limitations': 'Structural cross-file reconciliation only; claimed bank rows, hash strings, invoice allocations and group overlaps are not independently certified.'}


def valid_row(row, fields):
    return isinstance(row, dict) and set(row) == fields


def minor_positive(val):
    parsed = parse_minor(val)
    return parsed if parsed is not None and parsed > 0 else None


def analyze(packet, v33=None, v33_digest=None):
    errors = []
    if not isinstance(packet, dict) or set(packet) != FIELDS:
        return report('INVALID', ['INVALID_PACKET_SCHEMA'])
    if packet.get('schema') != SCHEMA or packet.get('source_notice') != NOTICE:
        errors.append('WRONG_SCHEMA_OR_SOURCE_NOTICE')
    names = ('invoices', 'bank_transactions', 'allocations', 'shipment_invoice_links')
    if not all(isinstance(packet.get(name), list) for name in names):
        return report('INVALID', errors + ['PACKET_ARRAY_INVALID'])
    invoices, banks, allocs, links = (packet[name] for name in names)
    if any(len(x) > MAX_ENTRIES for x in (invoices, banks, allocs, links)):
        return report('INVALID', errors + ['PACKET_TOO_LARGE'])
    if not any((invoices, banks, allocs, links)):
        if packet['v33_source_sha256'] is not None or v33 is not None or v33_digest is not None:
            errors.append('EMPTY_PACKET_CANNOT_INHERIT_SOURCE_PROOF')
        return report('INVALID' if errors else 'NO_SOURCE_RECORDS_IN_SCOPE', errors,
                      invoices=0, banks=0, allocations=0, links=0)
    if not valid_sha(packet.get('v33_source_sha256')) or packet['v33_source_sha256'] != v33_digest:
        errors.append('V33_SOURCE_DIGEST_NOT_VERIFIED')
    if v33 is None:
        errors.append('V33_SOURCE_ABSENT')
        validated_v33 = None
    else:
        validated_v33 = analyze_v33(v33)
        if validated_v33['status'] != 'STRUCTURAL_REVIEW_REQUIRED':
            errors.append('V33_SOURCE_NOT_STRUCTURALLY_VALID')

    invoice_index, bank_index = {}, {}
    invoice_document_lines, bank_document_lines = set(), set()
    for row in invoices:
        if not valid_row(row, INVOICE_FIELDS):
            errors.append('INVOICE_SCHEMA_INVALID')
            continue
        token = row['invoice_token']
        if not valid_token(token):
            errors.append('INVOICE_TOKEN_INVALID')
            continue
        if token in invoice_index:
            errors.append('INVOICE_TOKEN_DUPLICATED')
            continue
        invoice_index[token] = row
        if not valid_sha(row['invoice_sha256']) or not valid_token(row['source_row_locator']):
            errors.append('INVOICE_DOCUMENT_REFERENCE_INVALID')
        if not isinstance(row['currency'], str) or row['currency'] not in CURRENCIES:
            errors.append('INVOICE_CURRENCY_INVALID')
        amount, credit = parse_minor(row['invoice_total_minor']), parse_minor(row['credit_note_minor'])
        if amount is None or amount == 0 or credit is None or credit > amount:
            errors.append('INVOICE_NET_AMOUNT_INVALID')
        if credit is not None and credit > 0 and not valid_sha(row['credit_note_sha256']):
            errors.append('CREDIT_NOTE_DOCUMENT_HASH_REQUIRED')
        if credit == 0 and row['credit_note_sha256'] is not None:
            errors.append('ZERO_CREDIT_MUST_NOT_REFERENCE_CREDIT_NOTE')
        if valid_sha(row['invoice_sha256']) and valid_token(row['source_row_locator']):
            doc_line = (row['invoice_sha256'], row['source_row_locator'])
            if doc_line in invoice_document_lines:
                errors.append('DUPLICATE_PHYSICAL_INVOICE_SOURCE_ROW')
            invoice_document_lines.add(doc_line)

    for row in banks:
        if not valid_row(row, BANK_FIELDS):
            errors.append('BANK_SCHEMA_INVALID')
            continue
        token = row['bank_transaction_token']
        if not valid_token(token):
            errors.append('BANK_TOKEN_INVALID')
            continue
        if token in bank_index:
            errors.append('BANK_TOKEN_DUPLICATED')
            continue
        bank_index[token] = row
        if not valid_sha(row['bank_statement_sha256']) or not valid_token(row['source_row_locator']):
            errors.append('BANK_DOCUMENT_REFERENCE_INVALID')
        else:
            doc_line = (row['bank_statement_sha256'], row['source_row_locator'])
            if doc_line in bank_document_lines:
                errors.append('DUPLICATE_PHYSICAL_BANK_SOURCE_ROW')
            bank_document_lines.add(doc_line)
        if not isinstance(row['currency'], str) or row['currency'] not in CURRENCIES:
            errors.append('BANK_CURRENCY_INVALID')
        if minor_positive(row['amount_minor']) is None:
            errors.append('BANK_AMOUNT_INVALID')
        try:
            when = date.fromisoformat(row['payment_date'])
            if when > AS_OF:
                errors.append('BANK_PAYMENT_DATE_IN_FUTURE')
        except (TypeError, ValueError):
            errors.append('BANK_PAYMENT_DATE_INVALID')

    by_invoice, by_bank = Counter(), Counter()
    pairs = set()
    for row in allocs:
        if not valid_row(row, ALLOC_FIELDS):
            errors.append('ALLOCATION_SCHEMA_INVALID')
            continue
        invoice_token, bank_token = row['invoice_token'], row['bank_transaction_token']
        if not isinstance(invoice_token, str) or not isinstance(bank_token, str):
            errors.append('ALLOCATION_TOKEN_INVALID')
            continue
        pair = (invoice_token, bank_token)
        if pair in pairs:
            errors.append('ALLOCATION_PAIR_DUPLICATED')
        pairs.add(pair)
        invoice, bank = invoice_index.get(invoice_token), bank_index.get(bank_token)
        if invoice is None or bank is None:
            errors.append('ALLOCATION_ORPHAN_REFERENCE')
            continue
        if invoice['currency'] != bank['currency']:
            errors.append('ALLOCATION_CURRENCY_MISMATCH')
        amount = minor_positive(row['amount_minor'])
        if amount is None:
            errors.append('ALLOCATION_AMOUNT_INVALID')
            continue
        by_invoice[invoice_token] += amount
        by_bank[bank_token] += amount

    matched_ships = {}
    if validated_v33 is not None and validated_v33['status'] == 'STRUCTURAL_REVIEW_REQUIRED':
        for ship in v33['shipments']:
            key = (ship['scope'], ship['shipment_token'], ship['container_token'], ship['invoice_token'])
            matched_ships[key] = ship
    per_invoice, scopes = Counter(), defaultdict(set)
    seen_links = set()
    for row in links:
        if not valid_row(row, LINK_FIELDS):
            errors.append('SHIPMENT_LINK_SCHEMA_INVALID')
            continue
        if any(not isinstance(row.get(k), str) for k in ('scope', 'shipment_token', 'container_token', 'invoice_token')):
            errors.append('SHIPMENT_LINK_KEY_INVALID')
            continue
        key = (row['scope'], row['shipment_token'], row['container_token'], row['invoice_token'])
        if key in seen_links:
            errors.append('SHIPMENT_LINK_DUPLICATE')
        seen_links.add(key)
        ship = matched_ships.get(key)
        invoice = invoice_index.get(row['invoice_token'])
        if ship is None:
            errors.append('SHIPMENT_LINK_MISSING_V33_ROW')
        if invoice is None:
            errors.append('SHIPMENT_LINK_MISSING_INVOICE')
        if ship is not None and invoice is not None:
            if (ship['invoice_sha256'] != invoice['invoice_sha256'] or
                ship['currency'] != invoice['currency'] or
                ship['invoice_total_minor'] != invoice['invoice_total_minor'] or
                ship['credit_note_minor'] != invoice['credit_note_minor']):
                errors.append('V33_INVOICE_FACT_CONFLICT')
        apportioned = minor_positive(row['invoice_apportionment_minor'])
        if apportioned is None:
            errors.append('SHIPMENT_ALLOCATION_AMOUNT_INVALID')
            continue
        if invoice is not None:
            per_invoice[row['invoice_token']] += apportioned
            scopes[row['invoice_token']].add(row['scope'])

    if matched_ships and set(matched_ships) != seen_links:
        errors.append('SHIPMENT_INVOICE_LINK_COVERAGE_MISMATCH')

    balanced = paid = 0
    for token, inv in invoice_index.items():
        total = parse_minor(inv['invoice_total_minor'])
        credit = parse_minor(inv['credit_note_minor'])
        if total is None or credit is None or credit > total:
            continue
        net = total - credit
        if per_invoice[token] != net:
            errors.append('INVOICE_TO_SHIPMENT_ALLOCATION_NOT_BALANCED')
        else:
            balanced += 1
        if by_invoice[token] > net:
            errors.append('INVOICE_OVERPAID_BY_ALLOCATIONS')
        elif net > 0 and by_invoice[token] == net:
            paid += 1

    for token, bank in bank_index.items():
        amount = parse_minor(bank['amount_minor'])
        if amount is not None and by_bank[token] > amount:
            errors.append('BANK_TRANSACTION_DOUBLE_ALLOCATED')

    if errors:
        return report('INVALID', errors)
    return report('STRUCTURAL_REVIEW_REQUIRED', [], invoices=len(invoice_index),
                  banks=len(bank_index), allocations=len(allocs), links=len(links),
                  balanced_invoices=balanced, paid_invoices=paid,
                  unallocated_bank_lines=sum(by_bank[token] < int(row['amount_minor'])
                                             for token, row in bank_index.items()),
                  cross_scope_invoices=sum(len(scopes[token]) > 1 for token in invoice_index))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--private-ledger', type=Path)
    parser.add_argument('--expected-ledger-sha256')
    parser.add_argument('--private-v33', type=Path)
    parser.add_argument('--expected-v33-sha256')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        if args.private_ledger is None and args.private_v33 is None and args.expected_ledger_sha256 is None and args.expected_v33_sha256 is None:
            result = analyze(empty_input())
        elif None in (args.private_ledger, args.private_v33, args.expected_ledger_sha256, args.expected_v33_sha256):
            result = report('INVALID', ['PRIVATE_INPUTS_AND_DIGESTS_REQUIRED_TOGETHER'])
        else:
            root = args.repo.resolve()
            source_ledger = safe_private_path(root, args.private_ledger)
            source_v33 = safe_private_path(root, args.private_v33)
            if source_ledger == source_v33:
                raise ValueError('LEDGER_AND_V33_FILE_MUST_DIFFER')
            with source_ledger.open('rb') as f:
                ledger_bytes = f.read()
            with source_v33.open('rb') as f:
                v33_bytes = f.read()
            if (not valid_sha(args.expected_ledger_sha256) or
                hashlib.sha256(ledger_bytes).hexdigest() != args.expected_ledger_sha256 or
                not valid_sha(args.expected_v33_sha256) or
                hashlib.sha256(v33_bytes).hexdigest() != args.expected_v33_sha256):
                raise ValueError('PRIVATE_SOURCE_SHA256_MISMATCH')
            ledger = json.loads(ledger_bytes.decode('utf-8'))
            v33 = json.loads(v33_bytes.decode('utf-8'))
            result = analyze(ledger, v33=v33, v33_digest=args.expected_v33_sha256)
    except (OSError, ValueError, UnicodeError) as exc:
        result = report('INVALID', ['PRIVATE_INPUT_REJECTED_' + type(exc).__name__])
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.write_text(output, encoding='utf-8')
    print(output, end='')
    return 2 if result['status'] == 'INVALID' else 0


if __name__ == '__main__':
    raise SystemExit(main())

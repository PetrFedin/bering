#!/usr/bin/env python3
"""Validate authorized OD/payment extracts without pretending they prove bankability.

The optional extract is held under git-ignored local_private/, never in Git.
All positive counts are *structural candidates*, not verified cargo/revenue.
The trusted-source, signature, customer-consent and external-review steps are
out-of-band controls that no field in this JSON can certify on its own.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

GROUPS = ('P1', 'P2', 'P3', 'GROUP_EXISTING')
MONTHS = tuple(f'{y:04d}-{m:02d}' for y in (2024, 2025, 2026)
               for m in range(1, 13) if (2024, 10) <= (y, m) <= (2026, 9))
EXPECTED_KEYS = {(g, m) for g in GROUPS for m in MONTHS}
SCHEMA = 'BERING_V33_AUTHORIZED_OD_EXTRACT_V1'
TOP_KEYS = {'schema', 'source_notice', 'monthly_coverage', 'shipments'}
COVER_KEYS = {'scope', 'month', 'coverage_status', 'attestation_sha256',
              'source_row_locator', 'reported_container_count'}
SHIP_KEYS = {'shipment_token', 'container_token', 'scope', 'month', 'origin_token',
             'destination_token', 'container_size_ft', 'teu', 'waybill_token',
             'receiving_token', 'invoice_token', 'dispatch_on', 'received_on',
             'waybill_sha256', 'receipt_sha256', 'invoice_sha256',
             'bank_statement_sha256', 'invoice_total_minor',
             'credit_note_minor', 'bank_paid_minor', 'currency',
             'source_sha256', 'source_row_locator', 'incumbent_route_token'}
SHA_RE = re.compile(r'^[0-9a-f]{64}$')
TOKEN_RE = re.compile(r'^[A-Za-z0-9_-]{6,128}$')
MONEY_RE = re.compile(r'^(0|[1-9][0-9]{0,17})$')
SOURCE_NOTICE = 'SOURCE_DATA_IS_PRIVATE_AND_REQUIRES_SEPARATE_HUMAN_ATTESTATION'
MAX_PRIVATE_BYTES = 40 * 1024 * 1024


def digest_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_private_path(repo, filename):
    """Reject traversal and any symlinked component before reading private data."""
    root = repo.resolve()
    private = root / 'local_private'
    candidate = Path(filename)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        relative = candidate.relative_to(private)
    except ValueError as e:
        raise ValueError('EXTRACT_OUTSIDE_PRIVATE_VAULT') from e
    if not relative.parts or '..' in relative.parts or '.' in relative.parts:
        raise ValueError('UNSAFE_PRIVATE_PATH')
    for path in (root, private, *(private.joinpath(*relative.parts[:i])
                                 for i in range(1, len(relative.parts)+1))):
        if path.is_symlink():
            raise ValueError('SYMLINKED_PRIVATE_PATH_COMPONENT')
    if not private.is_dir() or not candidate.is_file():
        raise ValueError('PRIVATE_SOURCE_MISSING')
    if not candidate.resolve().is_relative_to(private.resolve()):
        raise ValueError('EXTRACT_OUTSIDE_PRIVATE_VAULT')
    if not 0 < candidate.stat().st_size <= MAX_PRIVATE_BYTES:
        raise ValueError('PRIVATE_SOURCE_LENGTH_INVALID')
    return candidate


def valid_token(s):
    return isinstance(s, str) and TOKEN_RE.fullmatch(s) is not None


def valid_sha(s):
    return isinstance(s, str) and SHA_RE.fullmatch(s) is not None


def parse_minor(s):
    if not isinstance(s, str) or not MONEY_RE.fullmatch(s):
        return None
    try:
        return int(s)
    except (ValueError, InvalidOperation):
        return None


def empty_input():
    return {'schema': SCHEMA, 'source_notice': SOURCE_NOTICE,
            'monthly_coverage': [], 'shipments': []}


def analyze(payload, raw_bytes_sha256=None):
    """Count structural candidates only, never attest source signatures."""
    errors = []
    coverage, shipments = [], []
    if not isinstance(payload, dict) or set(payload) != TOP_KEYS:
        errors.append('WRONG_TOP_LEVEL_SCHEMA')
        payload = {}
    if payload.get('schema') != SCHEMA or payload.get('source_notice') != SOURCE_NOTICE:
        errors.append('WRONG_SOURCE_SCHEMA_OR_ATTESTATION_WARNING')
    if not isinstance(payload.get('monthly_coverage'), list):
        errors.append('COVERAGE_NOT_ARRAY')
    else:
        coverage = payload['monthly_coverage']
    if not isinstance(payload.get('shipments'), list):
        errors.append('SHIPMENTS_NOT_ARRAY')
    else:
        shipments = payload['shipments']
    if len(coverage) > 96 or len(shipments) > 200000:
        errors.append('EXTRACT_EXCEEDS_LIMITS')
    cover_seen, cover_count = set(), {}
    for i, row in enumerate(coverage):
        if not isinstance(row, dict) or set(row) != COVER_KEYS:
            errors.append('INVALID_MONTHLY_ROW')
            continue
        if type(row['scope']) is not str or type(row['month']) is not str:
            errors.append('MONTH_SCOPE_OR_DATE_INVALID')
            continue
        key = (row['scope'], row['month'])
        if key not in EXPECTED_KEYS or key in cover_seen:
            errors.append('DUPLICATE_OR_OUT_OF_PERIOD_MONTH')
            continue
        cover_seen.add(key)
        kind = row['coverage_status']
        count = row['reported_container_count']
        if kind not in ('ATTESTED_ZERO', 'ATTESTED_NONZERO'):
            errors.append('UNKNOWN_MONTH_STATUS')
        if not valid_sha(row['attestation_sha256']) or not valid_token(row['source_row_locator']):
            errors.append('MISSING_MONTH_SOURCE_REFERENCE')
        if type(count) is not int or count < 0:
            errors.append('MONTH_CONTAINER_COUNT_INVALID')
        elif (kind == 'ATTESTED_ZERO') != (count == 0):
            errors.append('MONTH_STATUS_COUNT_CONTRADICTION')
        else:
            cover_count[key] = count

    physical_seen, waybill_seen = set(), set()
    containers_by_month = Counter()
    groups_by_shipment = defaultdict(set)
    scopes_by_container_month = defaultdict(set)
    parsed_shipments, fully_paid_candidates = 0, 0
    for i, row in enumerate(shipments):
        if not isinstance(row, dict) or set(row) != SHIP_KEYS:
            errors.append('INVALID_SHIPMENT_FIELDS')
            continue
        if type(row['scope']) is not str or type(row['month']) is not str:
            errors.append('SHIPMENT_SCOPE_OR_DATE_INVALID')
            continue
        key = (row['scope'], row['month'])
        if key not in EXPECTED_KEYS:
            errors.append('SHIPMENT_OUTSIDE_SCOPE_OR_PERIOD')
            continue
        for field in ('shipment_token', 'container_token', 'origin_token',
                      'destination_token', 'waybill_token', 'receiving_token',
                      'invoice_token', 'source_row_locator'):
            if not valid_token(row.get(field)):
                errors.append('INVALID_MASKED_TOKEN_' + field)
        if not valid_sha(row.get('source_sha256')):
            errors.append('SOURCE_SHA_MISSING')
        if row['origin_token'] == row['destination_token']:
            errors.append('SAME_ORIGIN_DESTINATION')
        try:
            sent_on = date.fromisoformat(row['dispatch_on'])
            received_on = date.fromisoformat(row['received_on'])
            if sent_on.strftime('%Y-%m') != row['month'] or received_on < sent_on:
                errors.append('SHIPMENT_DATE_OR_MONTH_INCONSISTENT')
        except (TypeError, ValueError):
            errors.append('SHIPMENT_DATES_INVALID')
        for field in ('waybill_sha256','receipt_sha256','invoice_sha256','bank_statement_sha256'):
            if not valid_sha(row[field]):
                errors.append('MISSING_DOCUMENT_HASH_' + field)
        size = row['container_size_ft']
        teu = row['teu']
        if type(size) is not int or size not in (20, 40) or type(teu) is not int or teu != size // 20:
            errors.append('CONTAINER_TEU_UNIT_MISMATCH')
        if valid_token(row['shipment_token']) and valid_token(row['container_token']):
            shipment_identity = (row['scope'], row['shipment_token'], row['container_token'])
            if shipment_identity in physical_seen:
                errors.append('DUPLICATE_PHYSICAL_CONTAINER')
            physical_seen.add(shipment_identity)
            # A stable shipment + container token can link group diversion to a pilot;
            # a reused container number alone is not proof of cannibalization.
            groups_by_shipment[(row['shipment_token'],row['container_token'])].add(row['scope'])
            scopes_by_container_month[(row['container_token'],row['month'])].add(row['scope'])
        if valid_token(row['waybill_token']) and valid_token(row['container_token']):
            waybill_identity = (row['scope'], row['waybill_token'], row['container_token'])
            if waybill_identity in waybill_seen:
                errors.append('DUPLICATE_WAYBILL_CONTAINER')
            waybill_seen.add(waybill_identity)
        containers_by_month[key] += 1
        if row['scope'] == 'GROUP_EXISTING':
            if row['incumbent_route_token'] is not None and not valid_token(row['incumbent_route_token']):
                errors.append('INVALID_INCUMBENT_ROUTE')
        elif row['incumbent_route_token'] is not None and not valid_token(row['incumbent_route_token']):
            errors.append('INVALID_INCUMBENT_ROUTE')
        invoice = parse_minor(row['invoice_total_minor'])
        credit = parse_minor(row['credit_note_minor'])
        paid = parse_minor(row['bank_paid_minor'])
        if row['currency'] not in ('RUB', 'USD', 'EUR', 'CNY'):
            errors.append('CURRENCY_NOT_ALLOWED')
        if None in (invoice, credit, paid):
            errors.append('AMOUNTS_NOT_MINOR_UNIT_STRINGS')
        elif invoice == 0 or credit > invoice or paid > invoice - credit:
            errors.append('INVOICE_CREDIT_BANK_RECONCILIATION_FAILED')
        elif paid > 0 and paid == invoice-credit:
            fully_paid_candidates += 1
        parsed_shipments += 1
        if key not in cover_count:
            errors.append('SHIPMENT_WITHOUT_ATTESTED_MONTH')

    for key, reported in cover_count.items():
        if containers_by_month[key] != reported:
            errors.append('MONTH_TOTAL_NOT_RECONCILED_TO_CONTAINERS')

    overlapping = {identity: scopes for identity, scopes in groups_by_shipment.items()
                   if 'GROUP_EXISTING' in scopes and any(s != 'GROUP_EXISTING' for s in scopes)}
    multi_pilot = [identity for identity, scopes in groups_by_shipment.items()
                   if len(scopes.intersection({'P1','P2','P3'})) > 1]
    same_container_month = {key: scopes for key,scopes in scopes_by_container_month.items()
                            if len(scopes) > 1}
    if multi_pilot:
        errors.append('SAME_CONTAINER_CLAIMED_BY_MULTIPLE_PILOTS')
    # Overlap is legitimate evidence of possible cannibalization; do not count as growth.
    errors = sorted(set(errors))
    has_records = bool(coverage or shipments)
    return {
        'status': 'INVALID' if errors else ('STRUCTURAL_REVIEW_REQUIRED' if has_records
                                            else 'NO_SOURCE_RECORDS_IN_SCOPE'),
        'schema': SCHEMA,
        'candidate_source_digest': raw_bytes_sha256,
        'source_digest_is_authentication': False,
        'source_signature_verified': False,
        'bank_settlement_verified_independently': False,
        'monthly_coverage_target': 96,
        'claimed_attested_months': len(cover_seen) if not errors else None,
        'confirmed_attested_months': 0,
        'missing_month_slots': 96-len(cover_seen) if not errors else None,
        'structural_container_rows': parsed_shipments if not errors else None,
        'structurally_fully_paid_rows': fully_paid_candidates if not errors else None,
        'candidate_same_shipment_group_overlap': len(overlapping) if not errors else None,
        'candidate_container_month_collisions': len(same_container_month) if not errors else None,
        'new_paid_bering_40ft': None,
        'incremental_group_contribution_margin_rub': None,
        'bering_npv_rub': None,
        'P1': 'HOLD', 'P2':'HOLD', 'P3':'HOLD',
        'bankable_revenue_approved': False,
        'investment_approved': False,
        'errors': errors,
        'limitations': 'Structural checks only. Shared shipment tokens flag possible group diversion, not proven cannibalization. Reused container tokens are not themselves double-counting. Masked tokens and claimed payments are not certified originals, bank data or incremental demand.',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path('.'))
    p.add_argument('--private-input', type=Path)
    p.add_argument('--expected-sha256')
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    try:
        if a.private_input is None:
            if a.expected_sha256 is not None:
                raise ValueError('DIGEST_WITHOUT_PRIVATE_INPUT')
            report = analyze(empty_input())
        else:
            path = safe_private_path(a.repo, a.private_input)
            found = digest_file(path)
            if a.expected_sha256 is not None and (not valid_sha(a.expected_sha256) or found != a.expected_sha256):
                raise ValueError('PRIVATE_INPUT_SHA256_MISMATCH')
            data = json.loads(path.read_text(encoding='utf-8'))
            report = analyze(data, raw_bytes_sha256=found)
    except (OSError, ValueError, UnicodeError) as exc:
        report = analyze({})
        report['errors'].append('INTAKE_LOAD_REJECTED_' + str(exc)[:60])
        report['status'] = 'INVALID'
    output = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if a.out:
        a.out.write_text(output, encoding='utf-8')
    print(output, end='')
    return 2 if report['status'] == 'INVALID' else 0

if __name__ == '__main__':
    raise SystemExit(main())

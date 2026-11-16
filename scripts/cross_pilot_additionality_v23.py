#!/usr/bin/env python3
"""Cross-pilot shipment-level anti-double-count audit. Never approves investment.

The unit of account is an economic shipment (not a route leg, port handling
operation, TEU or weight). Financial inputs are screening assumptions until
externally verified, independently reviewed and supported by actual documents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

PILOTS = ('P1', 'P2', 'P3')
CLASSES = {'P1': 'dry_40ft', 'P2': 'reefer_40ft', 'P3': 'import_dry_40ft'}
SOURCE_FIELDS = ('contract', 'waybill', 'payment', 'baseline_24m',
                 'additionality', 'unit_contribution')
ID = re.compile(r'^[A-Za-z0-9_-]{6,100}$')
EVIDENCE_ID = re.compile(r'^EV-[A-Z0-9][A-Z0-9_-]{5,}$')
SHA = re.compile(r'^[a-f0-9]{64}$')


def amount(raw, label: str, errors: list[str], missing: list[str], *, nonnegative=False):
    if raw is None or raw == '':
        missing.append(label)
        return None
    if isinstance(raw, (bool, float)) or not isinstance(raw, (int, str)):
        errors.append(label + ': expected exact decimal text/integer, not float/bool')
        return None
    try:
        number = Decimal(str(raw))
    except InvalidOperation:
        errors.append(label + ': not a decimal number')
        return None
    if not number.is_finite() or (nonnegative and number < 0):
        errors.append(label + ': invalid/non-finite/negative amount')
        return None
    if number.as_tuple().exponent < -2:
        errors.append(label + ': precision greater than 0.01 RUB')
        return None
    return number


def verified_evidence(identifier, records, root, as_of: date) -> bool:
    """Check independently reviewed *bytes*, not signature, legality or truth."""
    if (not isinstance(identifier, str) or not EVIDENCE_ID.fullmatch(identifier)
            or not isinstance(records, dict) or root is None):
        return False
    record = records.get(identifier)
    if not isinstance(record, dict) or record.get('status') != 'VERIFIED':
        return False
    path, digest = record.get('relative_path'), record.get('sha256')
    submitter, reviewer = record.get('submitted_by'), record.get('reviewed_by')
    if (not isinstance(path, str) or not path or '\\' in path or '\x00' in path
            or Path(path).is_absolute() or '..' in Path(path).parts
            or not isinstance(digest, str) or not SHA.fullmatch(digest)
            or not isinstance(submitter, str) or not submitter.strip()
            or not isinstance(reviewer, str) or not reviewer.strip()
            or submitter.strip().casefold() == reviewer.strip().casefold()):
        return False
    try:
        reviewed_on = date.fromisoformat(record['reviewed_on'])
        if reviewed_on > as_of:
            return False
        base = Path(root).resolve(strict=True)
        file = base / path
        if file.is_symlink():
            return False
        real = file.resolve(strict=True)
        if not real.is_relative_to(base) or not real.is_file() or real.stat().st_size == 0:
            return False
        h = hashlib.sha256()
        with real.open('rb') as stream:
            for part in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(part)
        return h.hexdigest() == digest
    except (OSError, ValueError, TypeError, KeyError):
        return False


def evaluate(payload, records=None, evidence_root=None):
    errors: list[str] = []
    missing: list[str] = []
    if not isinstance(payload, dict):
        return {'status': 'INVALID', 'errors': ['Input must be a JSON object'],
                'bankable_revenue_approved': False}
    if payload.get('schema_version') != 'V23':
        errors.append('schema_version must be V23')
    try:
        as_of = date.fromisoformat(payload['as_of'])
    except (TypeError, ValueError, KeyError):
        errors.append('as_of must be a valid YYYY-MM-DD')
        as_of = date.min
    if payload.get('currency') != 'RUB' or payload.get('tax_basis') != 'EX_VAT':
        errors.append('group economics must use RUB EX_VAT; no implicit FX/VAT conversion')
    group = payload.get('group_id')
    if not isinstance(group, str) or not ID.fullmatch(group):
        errors.append('group_id: one explicit, pseudonymous economic group is required')
    costs = payload.get('pilot_costs')
    shipments = payload.get('shipments')
    if not isinstance(costs, dict) or set(costs) != set(PILOTS):
        errors.append('pilot_costs must contain exactly P1, P2, P3')
        costs = {}
    if not isinstance(shipments, list):
        errors.append('shipments must be an array; missing is not zero')
        shipments = []

    stats = {p: {'new_40ft': 0, 'diverted_40ft': 0, 'excluded_records': 0,
                 'gross_delta': Decimal('0'), 'numeric_complete': True,
                 'evidence_complete': True, 'counted_records': 0} for p in PILOTS}
    seen_cost_events: dict[str, str] = {}
    seen_cargo: dict[str, str] = {}
    seen_consignment: dict[str, str] = {}
    for i, row in enumerate(shipments):
        ctx = f'shipments[{i}]'
        if not isinstance(row, dict):
            errors.append(ctx + ': expected object')
            continue
        p = row.get('pilot_id')
        if p not in PILOTS:
            errors.append(ctx + ': invalid pilot_id')
            continue
        state = stats[p]
        cargo = row.get('economic_shipment_id')
        consignment = row.get('physical_consignment_key')
        if not isinstance(cargo, str) or not ID.fullmatch(cargo):
            errors.append(ctx + ': invalid economic_shipment_id')
        else:
            key = cargo.casefold()
            if key in seen_cargo:
                errors.append(f'duplicate economic shipment {cargo}: {seen_cargo[key]} and {ctx}')
            seen_cargo[key] = ctx
        if not isinstance(consignment, str) or not ID.fullmatch(consignment):
            errors.append(ctx + ': missing/invalid physical_consignment_key')
        else:
            key = consignment.casefold()
            if key in seen_consignment:
                errors.append(f'cross-pilot consignment overlap {consignment}: {seen_consignment[key]} and {ctx}')
            seen_consignment[key] = ctx
        if row.get('group_id') != group:
            errors.append(ctx + ': economic group mismatch')
        if row.get('currency') != 'RUB' or row.get('tax_basis') != 'EX_VAT':
            errors.append(ctx + ': monetary basis must be RUB EX_VAT')
        if row.get('cargo_class') != CLASSES[p] or row.get('unit') != '40ft_container':
            errors.append(ctx + ': incompatible cargo class or quantity unit')
        month = row.get('month')
        try:
            if not isinstance(month, str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
                raise ValueError('bad month')
            if date.fromisoformat(month + '-01') > as_of:
                raise ValueError('future observed month')
        except ValueError:
            errors.append(ctx + ': invalid or future observed shipment month')
        qty = row.get('quantity_40ft')
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            errors.append(ctx + ': quantity_40ft must be positive integer')
            state['numeric_complete'] = False
            qty = None
        kind = row.get('classification')
        if kind == 'EXCLUDED':
            state['excluded_records'] += 1
            if not isinstance(row.get('exclusion_reason'), str) or not row['exclusion_reason'].strip():
                errors.append(ctx + ': excluded consignment needs a reason')
            continue
        if kind not in ('NEW', 'DIVERTED'):
            errors.append(ctx + ': classification must be NEW, DIVERTED or EXCLUDED')
            state['numeric_complete'] = False
            continue
        state['counted_records'] += 1
        new = amount(row.get('new_unit_cm_rub'), ctx + ':new_unit_cm_rub', errors, missing)
        old = None
        if kind == 'DIVERTED':
            old = amount(row.get('incumbent_group_unit_cm_rub'),
                         ctx + ':incumbent_group_unit_cm_rub', errors, missing)
            if not isinstance(row.get('incumbent_group_service'), str) or not row['incumbent_group_service'].strip():
                missing.append(ctx + ':incumbent_group_service')
                state['numeric_complete'] = False
        elif row.get('incumbent_group_unit_cm_rub') is not None or row.get('incumbent_group_service') is not None:
            errors.append(ctx + ': NEW shipment cannot have a pre-existing group service')
        if qty is None or new is None or (kind == 'DIVERTED' and old is None):
            state['numeric_complete'] = False
        else:
            state['gross_delta'] += Decimal(qty) * (new if kind == 'NEW' else new - old)
            state['new_40ft' if kind == 'NEW' else 'diverted_40ft'] += qty
        docs = row.get('evidence')
        if not isinstance(docs, dict):
            docs = {}
        supplied = [docs.get(field) for field in SOURCE_FIELDS if isinstance(docs.get(field), str)]
        if len(supplied) != len(set(supplied)):
            errors.append(ctx + ': one evidence ID reused across different document categories')
        for field in SOURCE_FIELDS:
            if not verified_evidence(docs.get(field), records, evidence_root, as_of):
                missing.append(ctx + ':evidence:' + field)
                state['evidence_complete'] = False

    per_pilot = {}
    for p in PILOTS:
        row = costs.get(p)
        ctx = f'pilot_costs.{p}'
        state = stats[p]
        if not isinstance(row, dict):
            row = {}
            errors.append(ctx + ': must be an object')
        if row.get('currency') != 'RUB' or row.get('tax_basis') != 'EX_VAT':
            errors.append(ctx + ': cost monetary basis must be RUB EX_VAT')
        cost_ids = row.get('cost_event_ids')
        if not isinstance(cost_ids, dict):
            cost_ids = {}
        for category in ('fixed', 'risk'):
            identifier = cost_ids.get(category)
            if not isinstance(identifier, str) or not ID.fullmatch(identifier):
                errors.append(ctx + ': missing/invalid cost_event_id for ' + category)
                continue
            key = identifier.casefold()
            if key in seen_cost_events:
                errors.append('duplicate cost event ' + identifier + ': ' + seen_cost_events[key] + ' and ' + ctx)
            seen_cost_events[key] = ctx
        fixed = amount(row.get('incremental_fixed_rub'), ctx + ':incremental_fixed_rub',
                       errors, missing, nonnegative=True)
        risk = amount(row.get('incremental_risk_rub'), ctx + ':incremental_risk_rub',
                      errors, missing, nonnegative=True)
        docs = row.get('evidence') if isinstance(row.get('evidence'), dict) else {}
        for category in ('fixed', 'risk'):
            if not verified_evidence(docs.get(category), records, evidence_root, as_of):
                state['evidence_complete'] = False
                missing.append(ctx + ':evidence:' + category)
        if state['counted_records'] == 0:
            missing.append(p + ':no_countable_shipments')
        if fixed is None or risk is None:
            state['numeric_complete'] = False
        screening = (state['gross_delta'] - fixed - risk
                     if state['numeric_complete'] and state['counted_records'] > 0 else None)
        per_pilot[p] = {
            'classification_counts_40ft': {'new': state['new_40ft'],
                                           'diverted': state['diverted_40ft']},
            'excluded_records': state['excluded_records'],
            'screening_incremental_group_cm_rub': str(screening) if screening is not None else None,
            'evidence_complete': state['evidence_complete'],
            'status': 'REVIEW' if (screening is not None and screening > 0
                    and state['evidence_complete'] and not errors) else 'HOLD',
            'bankable_revenue_approved': False,
        }
    if errors:
        for p in PILOTS:
            per_pilot[p]['status'] = 'HOLD'
            per_pilot[p]['screening_incremental_group_cm_rub'] = None
    total = (sum((Decimal(per_pilot[p]['screening_incremental_group_cm_rub'])
                  for p in PILOTS), Decimal('0'))
             if not errors and all(per_pilot[p]['screening_incremental_group_cm_rub'] is not None
                                  for p in PILOTS) else None)
    return {
        'status': 'INVALID' if errors else ('REVIEW' if all(per_pilot[p]['status'] == 'REVIEW'
                                                              for p in PILOTS) else 'HOLD'),
        'schema_version': 'V23', 'as_of': payload.get('as_of'),
        'grain': 'unique economic shipment in 40ft containers; never route legs/TEU/tonnes',
        'source_records': len(shipments), 'pilots': per_pilot,
        'screening_total_incremental_group_cm_rub': str(total) if total is not None else None,
        'errors': errors, 'missing': sorted(set(missing)),
        'bankable_revenue_approved': False, 'contracts_authenticated': False,
        'independent_commercial_review_required': True,
        'data_privacy_note': 'Use pseudonymous shipment/consignment IDs; actual confidential documents live outside Git.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--evidence-index', type=Path)
    parser.add_argument('--evidence-dir', type=Path)
    parser.add_argument('--require-review', action='store_true')
    args = parser.parse_args()
    if bool(args.evidence_index) != bool(args.evidence_dir):
        parser.error('Supply both --evidence-index and --evidence-dir, or neither')
    index = (json.loads(args.evidence_index.read_text(encoding='utf-8'))
             if args.evidence_index else None)
    report = evaluate(json.loads(args.input.read_text(encoding='utf-8')), index, args.evidence_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered)
    return 2 if report['status'] == 'INVALID' else 3 if (args.require_review and report['status'] != 'REVIEW') else 0


if __name__ == '__main__':
    raise SystemExit(main())

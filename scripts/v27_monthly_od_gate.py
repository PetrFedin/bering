#!/usr/bin/env python3
"""V27 strict monthly OD evidence gate and descriptive, non-bankable stress envelope.

No monthly data can be inferred from 9M cumulative port XLS. No tonnes-to-TEU
conversion is performed. Missing source/month cannot silently turn into zero.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
from statistics import median

PILOTS = ('P1', 'P2', 'P3')
MONTH = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')
SHA = re.compile(r'^[0-9a-f]{64}$')
SERIES = ('P1', 'P2', 'P3', 'GROUP_EXISTING')
MAX_DOC_BYTES = 30 * 1024 * 1024
ISO_LETTERS = dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    (10,12,13,14,15,16,17,18,19,20,21,23,24,25,26,27,28,29,
     30,31,32,34,35,36,37,38)))


def iso6346_valid(value) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r'[A-Z]{3}U[0-9]{7}', value):
        return False
    digit = sum((ISO_LETTERS[x] if x.isalpha() else int(x)) * (2 ** k)
                for k, x in enumerate(value[:10])) % 11 % 10
    return digit == int(value[-1])



def periods(start: str, length: int) -> list[str]:
    if not isinstance(start, str) or not MONTH.fullmatch(start) or not isinstance(length, int) or length <= 0:
        raise ValueError('invalid period or length')
    first = date.fromisoformat(start + '-01')
    return [f'{first.year + (first.month - 1 + i) // 12:04d}-{(first.month - 1 + i) % 12 + 1:02d}' for i in range(length)]


def decimal_exact(value, *, nonnegative=True) -> Decimal:
    if isinstance(value, (bool, float)) or not isinstance(value, (str, int)):
        raise ValueError('amount must be an exact decimal string or integer')
    try:
        val = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('invalid decimal') from exc
    if not val.is_finite() or (nonnegative and val < 0):
        raise ValueError('nonfinite or negative amount')
    if val.as_tuple().exponent < -2:
        raise ValueError('precision exceeds 0.01')
    return val


def verified_bytes(proof, root: Path | None) -> bool:
    """Checks claimed source bytes and independent reviewer, not truth of document."""
    if not isinstance(proof, dict) or root is None:
        return False
    digest, rel = proof.get('sha256'), proof.get('path')
    owner, reviewer = proof.get('submitted_by'), proof.get('reviewed_by')
    if (not isinstance(digest, str) or not SHA.fullmatch(digest) or
        not isinstance(rel, str) or not rel or '\\' in rel or '\x00' in rel or
        Path(rel).is_absolute() or '..' in Path(rel).parts or
        not isinstance(owner, str) or not owner.strip() or
        not isinstance(reviewer, str) or not reviewer.strip() or
        owner.strip().casefold() == reviewer.strip().casefold() or
        proof.get('status') != 'VERIFIED'):
        return False
    try:
        origin = root.resolve(strict=True)
        file = origin / rel
        if file.is_symlink() or not file.resolve(strict=True).is_relative_to(origin):
            return False
        if not file.is_file() or not 0 < file.stat().st_size <= MAX_DOC_BYTES:
            return False
        h = hashlib.sha256()
        with file.open('rb') as f:
            for buf in iter(lambda: f.read(1024 * 1024), b''):
                h.update(buf)
        return h.hexdigest() == digest
    except (ValueError, OSError):
        return False


def audit_monthly_port(payload, *, root: Path | None = None):
    errors, missing = [], []
    if not isinstance(payload, dict):
        return {'status': 'INVALID', 'errors': ['Input must be JSON object'], 'forecast_eligible': False}
    if payload.get('schema') != 'V27_PORT_MONTHLY':
        errors.append('schema must be V27_PORT_MONTHLY')
    if payload.get('entity_scope') != 'MMTP_OPERATOR' or payload.get('metric') != 'CONTAINER_CARGO_TONNES':
        errors.append('entity_scope/metric must be operator container cargo tonnes')
    if payload.get('unit') != 'tonnes':
        errors.append('unit must be tonnes; TEU and 40ft have different semantics')
    try:
        expected = periods(payload.get('window_start'), 24)
    except (ValueError, TypeError):
        errors.append('invalid window_start')
        expected = []
    if expected and expected[-1] != payload.get('window_end'):
        errors.append('window_end must match exactly 24 calendar months')
    rows = payload.get('observations')
    if not isinstance(rows, list):
        errors.append('observations must be array')
        rows = []
    seen = {}
    for i, row in enumerate(rows):
        ctx = f'observations[{i}]'
        if not isinstance(row, dict):
            errors.append(ctx + ': not object')
            continue
        month = row.get('month')
        if not isinstance(month, str) or month not in expected:
            errors.append(ctx + ': out-of-window month')
            continue
        if month in seen:
            errors.append(ctx + ': duplicate observed month')
        seen[month] = row
        if row.get('report_period_type') != 'MONTH' or row.get('source_entity') != 'MMTP_OPERATOR':
            errors.append(ctx + ': a cumulative MP-1/MP-2 form is NOT monthly data')
        try:
            decimal_exact(row.get('tonnes'))
        except ValueError:
            errors.append(ctx + ': invalid or missing tonnes; no inferred zeros')
        if not verified_bytes(row.get('source_evidence'), root):
            missing.append(ctx + ': independently reviewed exact source bytes')
        locator = row.get('cell_locator')
        if not isinstance(locator, str) or '!' not in locator or len(locator) > 150:
            missing.append(ctx + ': exact source cell/record locator')
    for m in expected:
        if m not in seen:
            missing.append(m + ': port operator monthly observation absent')
    full = len(seen) == len(expected) == 24 and not errors and not missing
    return {'status': 'REVIEW_ONLY' if full else 'INVALID' if errors else 'HOLD',
            'expected_months': 24, 'reported_months': len(seen),
            'fully_verified_months': len(expected) if full else 0,
            'source_originals_authenticated': False, 'forecast_eligible': False,
            'can_infer_40ft_or_OD_from_tonnes': False,
            'errors': errors, 'missing': missing}


def _stress_projection(values: list[Decimal], months: list[str]):
    """Illustrative min/median/max of last 12 observed YoY monthly count deltas.

    This is NOT a prediction interval and cannot establish Bering new traffic.
    """
    earlier, newer = values[:12], values[12:]
    deltas = [newer[i] - earlier[i] for i in range(12)]
    scenarios = {'LOW_STRESS': min(deltas), 'CENTRAL_STRESS': median(deltas),
                 'HIGH_STRESS': max(deltas)}
    future_months = periods(months[-1], 13)[1:]
    result = {}
    for name, delta in scenarios.items():
        monthly = [max(Decimal('0'), newer[i] + delta).quantize(Decimal('1'), rounding=ROUND_HALF_UP) for i in range(12)]
        result[name] = {'assumed_monthly_yoy_delta_40ft': str(delta),
                        'next_12_month_total_40ft': str(sum(monthly, Decimal('0'))),
                        'monthly': [{'month': m, 'containers_40ft': str(q)}
                                    for m, q in zip(future_months, monthly)]}
    return result


def audit_od(payload, *, root: Path | None = None):
    errors, missing = [], []
    if not isinstance(payload, dict):
        return {'status': 'INVALID', 'errors': ['Input must be JSON object'], 'forecast_eligible': False}
    if payload.get('schema') != 'V27_24M_GROUP_OD':
        errors.append('schema must be V27_24M_GROUP_OD')
    try:
        expected_months = periods(payload.get('window_start'), 24)
    except (ValueError, TypeError):
        expected_months = []
        errors.append('invalid 24-month window_start')
    if expected_months and payload.get('window_end') != expected_months[-1]:
        errors.append('window_end does not match 24 complete months')
    if payload.get('unit') != '40ft_container':
        errors.append('40ft_container required; no tonne/TEU conversion')
    coverage = payload.get('coverage')
    shipments = payload.get('shipments')
    if not isinstance(coverage, list) or not isinstance(shipments, list):
        errors.append('coverage and shipments must be arrays')
        coverage = coverage if isinstance(coverage, list) else []
        shipments = shipments if isinstance(shipments, list) else []
    expected_keys = {(lane, month) for lane in SERIES for month in expected_months}
    seen = {}
    used_evidence_rows = set()
    valid_count = 0
    for i, row in enumerate(coverage):
        ctx = f'coverage[{i}]'
        if not isinstance(row, dict):
            errors.append(ctx + ': not object')
            continue
        lane, month = row.get('lane'), row.get('month')
        if not isinstance(lane, str) or not isinstance(month, str) or (lane, month) not in expected_keys:
            errors.append(ctx + ': unknown lane or out-of-window month')
            continue
        key = (lane, month)
        if key in seen:
            errors.append(ctx + ': duplicate coverage key')
        seen[key] = row
        if row.get('coverage_state') != 'VERIFIED':
            missing.append(ctx + ': coverage not attested')
            continue
        try:
            q = decimal_exact(row.get('count_40ft'))
            if q != q.to_integral_value():
                raise ValueError('fractional container')
        except ValueError:
            errors.append(ctx + ': invalid count_40ft')
            continue
        evidence = row.get('evidence')
        if not verified_bytes(evidence, root):
            missing.append(ctx + ': source bytes missing/unreviewed')
            continue
        locator = row.get('source_row_locator')
        if not isinstance(locator, str) or not re.fullmatch(r'[A-Za-z0-9_/:.!-]{5,160}', locator):
            missing.append(ctx + ': source row locator missing')
            continue
        source_key = (evidence['sha256'], locator.casefold())
        if source_key in used_evidence_rows:
            errors.append(ctx + ': source row reused for multiple lane-month counts')
        used_evidence_rows.add(source_key)
        valid_count += 1
    for key in sorted(expected_keys - set(seen)):
        missing.append('missing coverage ' + '/'.join(key))
    shipments_by_key = {}
    seen_ids = set()
    seen_container = set()
    shipment_source_rows = set()
    for i, row in enumerate(shipments):
        ctx = f'shipments[{i}]'
        if not isinstance(row, dict):
            errors.append(ctx + ': not object')
            continue
        lane, month = row.get('lane'), row.get('month')
        if (not isinstance(lane, str) or lane not in SERIES or
            not isinstance(month, str) or month not in expected_months):
            errors.append(ctx + ': unknown lane/month')
            continue
        shipment_id, container = row.get('physical_consignment_id'), row.get('container_number')
        if not isinstance(shipment_id, str) or not re.fullmatch(r'[A-Z0-9_-]{6,64}', shipment_id):
            errors.append(ctx + ': missing physical consignment ID')
            continue
        if shipment_id in seen_ids:
            errors.append(ctx + ': physical shipment repeated across lanes')
        seen_ids.add(shipment_id)
        if not iso6346_valid(container):
            errors.append(ctx + ': invalid container number')
        else:
            container_key = (month, container)
            if container_key in seen_container:
                errors.append(ctx + ': container repeated across lanes same month')
            seen_container.add(container_key)
        if not isinstance(row.get('shipper_group_id'), str) or not row['shipper_group_id']:
            errors.append(ctx + ': shipper perimeter unknown')
        if not isinstance(row.get('origin'), str) or not row['origin'] or not isinstance(row.get('destination'), str) or not row['destination']:
            errors.append(ctx + ': missing OD pair')
        source = row.get('evidence')
        if not verified_bytes(source, root):
            missing.append(ctx + ': source bytes missing')
        else:
            locator = row.get('source_row_locator')
            if not isinstance(locator, str) or not re.fullmatch(r'[A-Za-z0-9_/:.!-]{5,160}', locator):
                missing.append(ctx + ': physical container source locator missing')
            else:
                source_key = (source['sha256'], locator.casefold())
                if source_key in shipment_source_rows:
                    errors.append(ctx + ': duplicate physical source-row locator')
                shipment_source_rows.add(source_key)
        shipments_by_key[(lane, month)] = shipments_by_key.get((lane, month), 0) + 1
    for key, count in shipments_by_key.items():
        if key in seen and seen[key].get('coverage_state') == 'VERIFIED':
            try:
                if decimal_exact(seen[key].get('count_40ft')) != count:
                    errors.append('shipment total differs from independently confirmed month ' + '/'.join(key))
            except ValueError:
                pass
    # An explicit, independently source-backed zero remains a legitimate zero.
    for key, row in seen.items():
        if row.get('coverage_state') == 'VERIFIED':
            try:
                n = decimal_exact(row.get('count_40ft'))
                if n != shipments_by_key.get(key, 0):
                    errors.append('coverage count does not match unique source shipments ' + '/'.join(key))
            except ValueError:
                pass
    complete = len(expected_keys) == 96 and len(seen) == 96 and valid_count == 96 and not errors and not missing
    scenarios = None
    if complete:
        scenarios = {}
        for pilot in PILOTS:
            history = [decimal_exact(seen[(pilot, month)]['count_40ft']) for month in expected_months]
            scenarios[pilot] = {'historic_12m_40ft': str(sum(history[-12:], Decimal('0'))),
                                'illustrative_envelope': _stress_projection(history, expected_months)}
    return {'status': 'REVIEW_BASELINE_ONLY' if complete else 'INVALID' if errors else 'HOLD',
            'expected_pilot_months': 72, 'expected_group_existing_months': 24,
            'required_total_months': 96, 'documented_months': len(seen),
            'source_backed_months': valid_count, 'unique_shipments_claimed': len(seen_ids),
            'projection': scenarios, 'projection_kind': 'ILLUSTRATIVE_HISTORICAL_DELTA_STRESS_NOT_PROBABILITY',
            'eligible_to_forecast_Bering_revenue': False, 'investment_approved': False,
            'independent_source_authenticity_proven': False,
            'errors': errors, 'missing': missing}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--operator-monthly', type=Path, required=True)
    p.add_argument('--od-24m', type=Path, required=True)
    p.add_argument('--source-dir', type=Path)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    src = args.source_dir
    report = {'operator_monthly': audit_monthly_port(json.loads(args.operator_monthly.read_text()), root=src),
              'group_24m_od': audit_od(json.loads(args.od_24m.read_text()), root=src),
              'bankable_revenue_approved': False, 'investment_approved': False}
    txt = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.write_text(txt, encoding='utf-8')
    print(txt)
    return 2 if any(v['status'] == 'INVALID' for v in (report['operator_monthly'], report['group_24m_od'])) else 0


if __name__ == '__main__':
    raise SystemExit(main())

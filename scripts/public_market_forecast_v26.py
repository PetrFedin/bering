#!/usr/bin/env python3
"""V26: factual public-port context and explicitly conditional operator target path.

Never derives Bering booked containers, paid demand, tariffs, project IRR or group
contribution margin. Tonnes, TEU, 40ft containers, terminal services and OD
shipments are separate quantities. All sources require human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REQUIRED = {
    'MAGADAN_SEAPORT_2025_ALL_CARGO_TONNES': ('OBSERVED', 'MAGADAN_SEAPORT_ALL_TERMINALS', 'ALL_CARGO_TONNES', '2025'),
    'FAR_EAST_PORT_BASIN_2025_ALL_CARGO_TONNES': ('OBSERVED', 'FAR_EAST_SEAPORT_BASIN', 'ALL_CARGO_TONNES', '2025'),
    'MAGADAN_MMTP_2024_CONTAINER_CARGO_TONNES': ('REPORTED_HISTORICAL', 'MAGADAN_MMTP_OPERATOR', 'CONTAINER_CARGO_TONNES', '2024'),
    'MAGADAN_MMTP_2032_CONTAINER_CARGO_TARGET_TONNES': ('FORWARD_TARGET', 'MAGADAN_MMTP_OPERATOR', 'CONTAINER_CARGO_TONNES', '2032'),
    'MAGADAN_MMTP_2026_9M_MP1_PRIMARY_UNEXTRACTED': ('DOCUMENT_DISCOVERED', 'MAGADAN_MMTP_OPERATOR', 'MP1_REPORT_NINE_MONTHS', '2026-09'),
    'MAGADAN_MMTP_2026_9M_MP2_PRIMARY_UNEXTRACTED': ('DOCUMENT_DISCOVERED', 'MAGADAN_MMTP_OPERATOR', 'MP2_REPORT_NINE_MONTHS', '2026-09'),
}
EXPECTED_URLS = {
    'MAGADAN_SEAPORT_2025_ALL_CARGO_TONNES': 'https://ampvanino.ru/magadan/',
    'FAR_EAST_PORT_BASIN_2025_ALL_CARGO_TONNES': 'https://www.morport.com/rus/news/gruzooborot-morskih-portov-rossii-za-2025-god',
    'MAGADAN_MMTP_2024_CONTAINER_CARGO_TONNES': 'https://portnews.ru/news/393455/',
    'MAGADAN_MMTP_2032_CONTAINER_CARGO_TARGET_TONNES': 'https://portnews.ru/news/393455/',
    'MAGADAN_MMTP_2026_9M_MP1_PRIMARY_UNEXTRACTED': 'https://magadanport.ru/wp-content/uploads/2026/10/MP10014726.xls',
    'MAGADAN_MMTP_2026_9M_MP2_PRIMARY_UNEXTRACTED': 'https://magadanport.ru/wp-content/uploads/2026/10/MP20014726.xls',
}
VALID_TIERS = {
    'PRIMARY_PUBLISHED_WEB', 'INDUSTRY_ASSOCIATION_PUBLISHED',
    'SECONDARY_QUOTES_OPERATOR_DOCUMENT', 'SOURCE_LISTING_ONLY',
}


def _source_day(value: Any, label: str, errors: list[str]) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f'{label}: date must be ISO text')
        return None
    try:
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError('noncanonical date')
        return result
    except ValueError:
        errors.append(f'{label}: invalid ISO date')
        return None


def _tonnes(value: Any, label: str, errors: list[str]) -> Decimal | None:
    # Exact, bounded integer strings prevent float contamination and giant exponents.
    if not isinstance(value, str) or not value.isascii() or not value.isdigit() or len(value) > 16 or value.startswith('0'):
        errors.append(f'{label}: tonnes must be positive bounded integer text')
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        errors.append(f'{label}: not a decimal')
        return None
    return number


def evaluate(payload: Any, *, source_bytes: bytes | None = None) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return {'status': 'INVALID', 'errors': ['Public register must be a JSON object'],
                'commercial_gate': 'HOLD', 'project_incremental_group_cm_rub': None}
    if payload.get('schema_version') != 'V26_PUBLIC_1':
        errors.append('Unknown source register schema')
    cutoff = _source_day(payload.get('as_of'), 'as_of', errors)
    if cutoff is None or cutoff > date.today():
        errors.append('as_of missing or in the future')
    entries = payload.get('records')
    if not isinstance(entries, list):
        errors.append('records must be a list')
        entries = []
    idmap: dict[str, dict] = {}
    grain: set[tuple[str, str, str]] = set()
    for i, row in enumerate(entries):
        ctx = f'records[{i}]'
        if not isinstance(row, dict):
            errors.append(ctx + ': expected object')
            continue
        identity = row.get('id')
        if not isinstance(identity, str) or identity not in REQUIRED:
            errors.append(ctx + ': unknown record identifier')
            continue
        if identity in idmap:
            errors.append(ctx + ': duplicated record id')
        idmap[identity] = row
        typ, entity, metric, period = REQUIRED[identity]
        if tuple(row.get(field) for field in ('record_type', 'entity', 'metric', 'period')) != (typ, entity, metric, period):
            errors.append(ctx + ': scope, metric, period or observation/target type changed')
        g = (entity, metric, period)
        if g in grain:
            errors.append(ctx + ': duplicate entity/metric/period grain')
        grain.add(g)
        u = row.get('source_url')
        if not isinstance(u, str) or u != EXPECTED_URLS[identity]:
            errors.append(ctx + ': source URL changed; provenance must be independently reviewed')
        if not isinstance(row.get('evidence_tier'), str) or row.get('evidence_tier') not in VALID_TIERS:
            errors.append(ctx + ': unrecognized evidence tier')
        if not isinstance(row.get('source_publisher'), str) or not row['source_publisher'].strip():
            errors.append(ctx + ': missing source publisher')
        if not isinstance(row.get('caveat'), str) or not row['caveat'].strip():
            errors.append(ctx + ': missing required analytical caveat')
        published = _source_day(row.get('source_date'), ctx + '.source_date', errors)
        if cutoff is not None and published is not None and published > cutoff:
            errors.append(ctx + ': document published after as_of')
        if typ == 'DOCUMENT_DISCOVERED':
            if row.get('value') is not None or row.get('unit') is not None:
                errors.append(ctx + ': source not extracted; values MUST stay null')
            if row.get('evidence_tier') != 'SOURCE_LISTING_ONLY':
                errors.append(ctx + ': unextracted report cannot claim analyzed source contents')
        else:
            if row.get('unit') != 'tonnes':
                errors.append(ctx + ': reported mass must be in tonnes, never TEU/containers')
            _tonnes(row.get('value'), ctx + '.value', errors)
            if typ == 'FORWARD_TARGET' and row.get('evidence_tier') == 'PRIMARY_PUBLISHED_WEB':
                errors.append(ctx + ': operator target not extracted from primary document')
    if set(idmap) != set(REQUIRED):
        errors.append('Exact six audited source slots required; missing/extra records')
    policy = payload.get('source_policy')
    if not isinstance(policy, dict):
        errors.append('Missing source policy')
        policy = {}
    if policy.get('target_scope') != 'PUBLIC_MARKET_CONTEXT_ONLY':
        errors.append('Public input scope cannot become direct pilot demand')
    for field in ('project_paid_40ft_units', 'project_new_od_volume_40ft_units',
                  'project_incremental_group_cm_rub'):
        if policy.get(field) is not None:
            errors.append(field + ': must remain null absent external commercial evidence')
    if policy.get('individual_pilot_status') != dict.fromkeys(('P1', 'P2', 'P3'), 'HOLD'):
        errors.append('Public-source register cannot change P1/P2/P3 HOLD')
    base = _tonnes(idmap.get('MAGADAN_MMTP_2024_CONTAINER_CARGO_TONNES', {}).get('value'),
                   'operator historical base', errors) if 'MAGADAN_MMTP_2024_CONTAINER_CARGO_TONNES' in idmap else None
    target = _tonnes(idmap.get('MAGADAN_MMTP_2032_CONTAINER_CARGO_TARGET_TONNES', {}).get('value'),
                     'operator future target', errors) if 'MAGADAN_MMTP_2032_CONTAINER_CARGO_TARGET_TONNES' in idmap else None
    if base is not None and target is not None and target < base:
        errors.append('Operator target lower than starting point: requires explicit negative-growth version')
    if errors:
        return {'status': 'INVALID', 'errors': sorted(set(errors)),
                'commercial_gate': 'HOLD', 'project_paid_40ft_units': None,
                'project_incremental_group_cm_rub': None}
    with localcontext() as ctx:
        ctx.prec = 34
        years = Decimal(2032 - 2024)
        rate = (target / base) ** (Decimal(1) / years) - Decimal(1)
        trajectory = []
        for year in range(2024, 2033):
            modelled = (base * (Decimal(1) + rate) ** (year - 2024))
            tonnes = modelled.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            trajectory.append({
                'year': year,
                'operator_target_smooth_interpolation_tonnes': str(tonnes),
                'flat_2024_counterfactual_tonnes': str(base),
                'record_type': 'REPORTED_HISTORICAL' if year == 2024 else 'TARGET_POINT' if year == 2032 else 'MATHEMATICAL_INTERPOLATION_NOT_OBSERVED',
            })
        growth_pct = (rate * Decimal('100')).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    return {
        'status': 'PUBLIC_CONTEXT_ONLY',
        'source_register_sha256': hashlib.sha256(source_bytes).hexdigest() if source_bytes is not None else None,
        'observed_port_2025_all_cargo_tonnes': idmap['MAGADAN_SEAPORT_2025_ALL_CARGO_TONNES']['value'],
        'observed_far_east_basin_2025_all_cargo_tonnes': idmap['FAR_EAST_PORT_BASIN_2025_ALL_CARGO_TONNES']['value'],
        'reported_operator_2024_container_cargo_tonnes': str(base),
        'operator_2032_container_target_tonnes': str(target),
        'operator_target_implied_annual_growth_percent': str(growth_pct),
        'annual_path': trajectory,
        'unextracted_operator_2026_9m_reports': [
            'MAGADAN_MMTP_2026_9M_MP1_PRIMARY_UNEXTRACTED',
            'MAGADAN_MMTP_2026_9M_MP2_PRIMARY_UNEXTRACTED',
        ],
        'direct_2026_actual_container_tonnage': None,
        'pilot_specific_40ft_units': {'P1': None, 'P2': None, 'P3': None},
        'project_paid_40ft_units': None,
        'project_incremental_group_cm_rub': None,
        'project_investment_npv_rub': None,
        'commercial_gate': 'HOLD',
        'investment_approved': False,
        'probability_forecast_verified': False,
        'method': 'CAGR=(2032 operator reported target / 2024 operator reported actual)^(1/8)-1; intervening years are illustrative, NOT operator annual forecasts.',
        'critical_scope_notes': [
            'All-port cargo, operator container cargo tonnes, TEU and 40ft units are different grains.',
            'The 2032 value is an operator target reported by a secondary publisher, not a realized cargo contract.',
            '2026 primary XLS data is listed but its raw bytes were not downloaded or audited.',
            'No 24-month origin-destination/customer base, costs or bank-verified new cargo supports a Bering revenue projection.',
        ],
        'errors': [],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources', type=Path, required=True)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    raw = args.sources.read_bytes()
    report = evaluate(json.loads(raw), source_bytes=raw)
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.out is not None:
        args.out.write_text(text, encoding='utf-8')
    print(text, end='')
    return 2 if report['status'] == 'INVALID' else 0


if __name__ == '__main__':
    raise SystemExit(main())

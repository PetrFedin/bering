#!/usr/bin/env python3
"""Source-perimeter QA for Magadan market and prospective rival terminal.

Input is a hand-curated, cited public source register, not a downloaded
primary dataset. Passing schema checks never certifies source authenticity.
The announced May/October capacity claims must not be summed; their scope
cannot be reconciled without engineering change logs and approvals.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re
from pathlib import Path
from urllib.parse import urlparse

PORT_OBS = {
    'MAGADAN_ALL_PORTS_2024_TEU': ('MAGADAN_ALL_PORT_TERMINALS', 'ANNUAL_HANDLED_CONTAINERS', '2024', 'TEU'),
    'MAGADAN_ALL_PORTS_2025_TEU': ('MAGADAN_ALL_PORT_TERMINALS', 'ANNUAL_HANDLED_CONTAINERS', '2025', 'TEU'),
    'MMTP_OPERATOR_2025_TONNES': ('MMTP_INDIVIDUAL_TERMINAL_OPERATOR', 'ANNUAL_ALL_CARGO_TONNES', '2025', 'tonnes'),
}
CAPACITY_IDS = ('MAGADAN_MLC_MAY2026_CAPACITY', 'MAGADAN_MLC_OCT2026_CAPACITY')
PINNED_VALUES = {
    'MAGADAN_ALL_PORTS_2024_TEU': '80900',
    'MAGADAN_ALL_PORTS_2025_TEU': '84300',
    'MMTP_OPERATOR_2025_TONNES': '1834700',
    'MAGADAN_MLC_MAY2026_CAPACITY': '30000',
    'MAGADAN_MLC_OCT2026_CAPACITY': '150000',
}
PINNED_SOURCE_URLS = {
    'MAGADAN_ALL_PORTS_2024_TEU': 'https://www.finmarket.ru/news/6331647',
    'MAGADAN_ALL_PORTS_2025_TEU': 'https://morvesti.ru/news/1679/120254/',
    'MMTP_OPERATOR_2025_TONNES': 'https://www.morport.com/rus/news/associaciya-morskih-torgovyh-portov-pozdravlyaet-s-yubileem-generalnogo-direktora-pao',
    'MAGADAN_MLC_MAY2026_CAPACITY': 'https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/',
    'MAGADAN_MLC_OCT2026_CAPACITY': 'https://egrz.ru/organisation/news/be268787-74bd-f111-80ff-00505634024e',
}
REQUIRED_CONTROL = (
    'primary_morcenter_teu_table_bytes_verified',
    'actual_paid_bering_40ft_shipments_verified',
    'physical_capacity_commissioned_verified',
    'signed_competitor_scope_revision_provided',
    'comparable_od_24_months_authenticated',
    'v27_24m_operator_series_authenticated',
    'licensed_source_data_resale_permitted',
)
ACCOUNTING_KEYS = (
    'never_add_capacity_versions',
    'never_convert_teu_to_40ft_without_mix',
    'never_equate_capacity_to_demand',
    'never_equate_operator_tonnes_with_all_port_teu',
    'never_use_market_context_as_paid_bering_volume',
)


def exact_number(value):
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,12}', value):
        raise ValueError('Expected exact nonnegative decimal string')
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid numeric representation') from exc
    if not d.is_finite() or d <= 0 or d != d.to_integral_value():
        raise ValueError('Annual container/cargo measures must be positive integer quantities')
    return d


def sourced_url(url):
    if not isinstance(url, str):
        return False
    try:
        p = urlparse(url)
        return (p.scheme == 'https' and bool(p.hostname) and p.username is None
                and p.password is None and p.port is None and not p.fragment
                and not p.query and p.hostname in {
                    'www.finmarket.ru', 'morvesti.ru', 'www.morport.com',
                    'investinregions.ru', 'egrz.ru'})
    except ValueError:
        return False


def valid_date(s, *, latest=None):
    try:
        value = date.fromisoformat(s) if isinstance(s, str) else None
    except ValueError:
        return False
    return value is not None and value <= (latest or date.today())


def assess(data):
    errors = []
    if not isinstance(data, dict):
        return {'status': 'INVALID', 'errors': ['Root must be object'],
                'investment_approved': False, 'bankable_revenue_approved': False}
    if data.get('schema') != 'V28_MARKET_PERIMETER_1':
        errors.append('Unknown source schema')
    if data.get('territory') != 'MAGADAN_RU':
        errors.append('Research territory mismatch')
    asof = data.get('as_of')
    if not valid_date(asof):
        errors.append('Invalid or future dated as_of')
    try:
        cutoff = date.fromisoformat(asof)
    except (ValueError, TypeError):
        cutoff = date.min
    obs = data.get('observations')
    if not isinstance(obs, list) or len(obs) != 3:
        errors.append('Exactly three source-qualified observations required')
        obs = []
    obs_map = {}
    for index, row in enumerate(obs):
        if not isinstance(row, dict):
            errors.append(f'observations[{index}] must be object')
            continue
        identifier = row.get('id')
        if not isinstance(identifier, str) or identifier not in PORT_OBS or identifier in obs_map:
            errors.append('Observation missing, duplicated, or unknown ID')
            continue
        obs_map[identifier] = row
        canonical = PORT_OBS[identifier]
        if tuple(row.get(key) for key in ('entity_scope', 'measure', 'period', 'unit')) != canonical:
            errors.append(identifier + ': scope/period/unit conflict')
        if row.get('evidence_class') not in ('HISTORICAL_REPORTED_SECONDARY','ASSOCIATION_REPORTED_OPERATOR'):
            errors.append(identifier + ': evidence class incorrect')
        if row.get('source_original_bytes_authenticated') is not False:
            errors.append(identifier + ': secondary quoted fact cannot self-attest source bytes')
        if not sourced_url(row.get('source_url')) or row.get('source_url') != PINNED_SOURCE_URLS[identifier] or not valid_date(row.get('source_issued'), latest=cutoff):
            errors.append(identifier + ': source citation missing, changed, untrusted or future dated')
        try:
            exact_number(row.get('value'))
            if row.get('value') != PINNED_VALUES[identifier]:
                errors.append(identifier + ': changed quoted value requires a new reviewed source revision')
        except ValueError:
            errors.append(identifier + ': invalid quantity or zero asserted without proof')
    if set(obs_map) != set(PORT_OBS):
        errors.append('Observation series incomplete')
    caps = data.get('capacity_claim_versions')
    if not isinstance(caps, list) or len(caps) != 2:
        errors.append('Exactly two separately versioned capacity claims required')
        caps = []
    cap_map = {}
    for index, row in enumerate(caps):
        if not isinstance(row, dict):
            errors.append(f'capacity_claim_versions[{index}] must be object')
            continue
        identifier = row.get('id')
        if not isinstance(identifier, str) or identifier not in CAPACITY_IDS or identifier in cap_map:
            errors.append('Capacity source duplicated or unknown')
            continue
        cap_map[identifier] = row
        if row.get('project_id') != 'MAGADAN_MARINE_LOGISTICS_CENTER':
            errors.append('Project identity mismatch')
        if row.get('project_legal_entity') != 'OOO Morskoy Logisticheskiy Tsentr':
            errors.append('Project developer identity mismatch')
        if row.get('measure') != 'ANNOUNCED_ANNUAL_CONTAINER_DESIGN_CAPACITY' or row.get('unit') != 'TEU_per_year':
            errors.append(identifier + ': future design capacity not a handled-volume observation')
        if row.get('construction_and_operations_proven') is not False or row.get('engineering_scope_match_certified') is not False:
            errors.append(identifier + ': unpublished engineering or commissioning evidence improperly asserted')
        if not sourced_url(row.get('source_url')) or row.get('source_url') != PINNED_SOURCE_URLS[identifier] or not valid_date(row.get('issued'), latest=cutoff):
            errors.append(identifier + ': invalid, changed source citation date/origin')
        if identifier == CAPACITY_IDS[0] and row.get('phase') != 'PUBLIC_INVESTMENT_CARD_MAY_2026':
            errors.append(identifier + ': capacity document vintage mismatch')
        if identifier == CAPACITY_IDS[1] and row.get('phase') != 'FIRST_STAGE_DESIGN_REVIEW_POSITIVE':
            errors.append(identifier + ': positive design review is not a commissioning certificate')
        if not isinstance(row.get('scope_review'), str) or not row['scope_review'].startswith('NOT_RECONCILED'):
            errors.append(identifier + ': phase scope falsely treated as reconciled')
        try:
            exact_number(row.get('value'))
            if row.get('value') != PINNED_VALUES[identifier]:
                errors.append(identifier + ': changed capacity claim needs independently reviewed revision')
        except ValueError:
            errors.append(identifier + ': invalid asserted capacity')
    if set(cap_map) != set(CAPACITY_IDS):
        errors.append('Design capacity claims incomplete')
    controls = data.get('verification_controls')
    if not isinstance(controls, dict) or set(controls) != set(REQUIRED_CONTROL):
        errors.append('Verification controls incomplete or unexpected')
    elif any(controls[k] is not False for k in REQUIRED_CONTROL):
        errors.append('Cannot claim independently verified evidence without underlying documents')
    policies = data.get('accounting_rules')
    if not isinstance(policies, dict) or set(policies) != set(ACCOUNTING_KEYS):
        errors.append('Non-additive market accounting policies incomplete')
    elif any(policies[k] is not True for k in ACCOUNTING_KEYS):
        errors.append('Policy incorrectly permits false market-to-revenue substitution')
    historical = None
    if set(obs_map) == set(PORT_OBS) and not errors:
        a = exact_number(obs_map['MAGADAN_ALL_PORTS_2024_TEU']['value'])
        b = exact_number(obs_map['MAGADAN_ALL_PORTS_2025_TEU']['value'])
        historical = {
            'entity_scope': 'MAGADAN_ALL_PORT_TERMINALS', 'unit': 'TEU',
            'actual_2024_reported': str(a), 'actual_2025_reported': str(b),
            'annual_absolute_change_TEUs': str(b-a),
            'reported_yoy_pct_calculated': str(((b/a-1)*100).quantize(Decimal('0.01'))),
            'source_type': 'SECONDARY_REPORTS_CITING_MORCENTR',
            'physical_40ft_containers': None, 'operator_specific_teus': None,
            'bering_paid_incremental_containers': None,
        }
    versions = None
    if set(cap_map) == set(CAPACITY_IDS) and not errors:
        earlier = exact_number(cap_map[CAPACITY_IDS[0]]['value'])
        later = exact_number(cap_map[CAPACITY_IDS[1]]['value'])
        versions = {
            'project_id': 'MAGADAN_MARINE_LOGISTICS_CENTER',
            'may_2026_published_design_TEUs_per_year': str(earlier),
            'oct_2026_expertise_announced_design_TEUs_per_year': str(later),
            'difference_in_published_claims_TEUs': str(later-earlier),
            'version_ratio_not_capacity_addition': str((later/earlier).quantize(Decimal('0.01'))),
            'engineering_perimeter_reconciliation': 'NOT_VERIFIED',
            'future_in_service_capacity': None,
            'new_cargo_due_to_bering': None,
        }
    return {
        'status': 'INVALID' if errors else 'CONTEXT_VALID_REVIEW_REQUIRED',
        'as_of': asof,
        'historical_port_teu': historical,
        'project_capacity_version_conflict': versions,
        'operator_2025_all_cargo_tonnes':
            obs_map.get('MMTP_OPERATOR_2025_TONNES',{}).get('value') if not errors else None,
        'annual_2026_magadan_teu': None, 'monthly_operator_tonnage_24m': None,
        'real_bering_40ft_OD_24m': None,
        'signed_new_cargo_40ft': None, 'authenticated_paid_cargo': None,
        'incremental_group_CM_rub': None, 'project_NPV_rub': None,
        'market_report_substitutes_original_evidence': False,
        'bankable_revenue_approved': False, 'investment_approved': False,
        'P1': 'HOLD', 'P2': 'HOLD', 'P3': 'HOLD',
        'manual_actions_required': [
            'Obtain original Morcenter port TEU tables, with source bytes and method.',
            'Get design phase change log 30k to 150k TEU from project owner/engineering authority.',
            'Verify actual permit, financing, commissioning date and operating status.',
            'Obtain customer-by-customer 24-month OD and documented paid new freight for P1-P3.',
            'Check incumbent group displacement across existing terminals before funding.'
        ],
        'errors': errors,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--register', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    ns = ap.parse_args()
    result = assess(json.loads(ns.register.read_text(encoding='utf-8')))
    data = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if ns.out:
        ns.out.write_text(data, encoding='utf-8')
    print(data, end='')
    return 2 if result['status'] == 'INVALID' else 0


if __name__ == '__main__':
    raise SystemExit(main())

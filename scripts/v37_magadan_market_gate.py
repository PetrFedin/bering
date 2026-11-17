#!/usr/bin/env python3
"""V37 fixed historical/public market-perimeter checkpoint, never investment approval.

Distinguishes total observed port TEU, archival registered capacity, rival
planned capacity, legal-program budgets, and unproven Bering demand.  This
checkpoint is immutable: any newer document needs its own versioned review.
"""
import argparse
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'data/public/V37_MAGADAN_MARKET_EVIDENCE_20261117.json'
# Values as source-published strings, preserving precision and avoiding floats.
# Record tuple: legal/metric boundary, status, period, unit, source URL, value.
PINNED = {
    'PORT_2024_TEU': ('MAGADAN_ALL_PORTS', 'SECONDARY_REPORTED_ACTUAL', '2024', 'TEU_per_year', 'https://www.interfax.ru/business/1005102', '80900'),
    'PORT_2025_TEU': ('MAGADAN_ALL_PORTS', 'SECONDARY_REPORTED_ACTUAL', '2025', 'TEU_per_year', 'https://morvesti.ru/news/1679/120254/', '84300'),
    'PORT_2025_ALL_CARGO_TONNES': ('MAGADAN_ALL_PORTS', 'OFFICIAL_PORT_AUTHORITY_REPORTED_ACTUAL', '2025', 'tonnes_per_year', 'https://ampvanino.ru/magadan/', '1834700'),
    'PORT_REGISTER_2009_NOMINAL_TEU': ('MAGADAN_PORT_2009_REGISTER', 'ARCHIVAL_REGISTER_DESIGN', '2009-11-18', 'TEU_per_year', 'https://www.rosmorport.ru/media/File/filials/Magadansky/Magadan_svedenia.pdf', '45000'),
    'MLC_PROMOTER_TEUS': ('MLC_PROJECT_INVESTOR_CARD', 'PROMOTER_DESIGN_CLAIM', '2026', 'TEU_per_year', 'https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/', '30000'),
    'MLC_GGE_TEUS': ('MLC_STAGE1_DESIGN', 'OFFICIAL_EXPERTISE_PRESS_CLAIM', '2026-10-01', 'TEU_per_year', 'https://egrz.ru/organisation/news/be268787-74bd-f111-80ff-00505634024e', '150000'),
    'MLC_PROMOTER_BUDGET_RUB_THOUSAND': ('MLC_PROJECT_INVESTOR_CARD', 'PROMOTER_FINANCIAL_CLAIM', '2026', 'thousand_RUB', 'https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/', '37655467'),
    'MLC_PROMOTER_EXTERNAL_FINANCING_RUB_THOUSAND': ('MLC_PROJECT_INVESTOR_CARD', 'PROMOTER_FINANCIAL_CLAIM', '2026', 'thousand_RUB', 'https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/', '15470923'),
    'MLC_PROMOTER_NPV_RUB_THOUSAND': ('MLC_PROJECT_INVESTOR_CARD', 'PROMOTER_FINANCIAL_CLAIM', '2026', 'thousand_RUB', 'https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/', '57399'),
    'MLC_PROMOTER_IRR_PERCENT': ('MLC_PROJECT_INVESTOR_CARD', 'PROMOTER_FINANCIAL_CLAIM', '2026', 'percent', 'https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/', '21.0'),
    'MLC_PROMOTER_PBP_MONTHS': ('MLC_PROJECT_INVESTOR_CARD', 'PROMOTER_FINANCIAL_CLAIM', '2026', 'months', 'https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/', '115.2'),
    'GOV_PLAN_MLC_EVENT_32_MILLION_RUB': ('FEDERAL_PLAN_EVENT_32', 'PLANNED_PROGRAM_ENVELOPE', '2025-2030', 'million_RUB', 'https://www.garant.ru/products/ipo/prime/doc/412773827/', '12295'),
    'GOV_PLAN_MLC_PORT_EVENT_33_MILLION_RUB': ('FEDERAL_PLAN_EVENT_33', 'PLANNED_PROGRAM_ENVELOPE', '2030', 'million_RUB', 'https://www.garant.ru/products/ipo/prime/doc/412773827/', '8000'),
    'GOV_PLAN_MLC_TARGET_YEAR': ('FEDERAL_PLAN_EVENTS_32_33', 'PLANNED_TARGET_YEAR', '2030', 'year', 'https://www.garant.ru/products/ipo/prime/doc/412773827/', '2030'),
    'PROPOSED_MOHE_NAIBA_PHASE1_TONNES': ('PROPOSED_CROSS_REGIONAL_CORRIDOR_NOT_PORT', 'SECONDARY_REPORTED_PROPOSAL', '2026-11-10', 'tonnes', 'https://www.tks.ru/logistics/2026/11/10/0006/magadan-mozhet-stat-zvenom-marshruta-mezhdu-aziej-i-atlantikoj/', '300000'),
    'PROPOSED_MOHE_NAIBA_FULL_TONNES': ('PROPOSED_CROSS_REGIONAL_CORRIDOR_NOT_PORT', 'SECONDARY_REPORTED_PROPOSAL', '2026-11-10', 'tonnes', 'https://www.tks.ru/logistics/2026/11/10/0006/magadan-mozhet-stat-zvenom-marshruta-mezhdu-aziej-i-atlantikoj/', '30000000'),
}
PURPOSE = 'Frozen public-source boundary review for Magadan and MLC competitor; no bankable freight or investment admissions'
NOTES_SHA256 = 'b1272b2647bf9d6d17309af00289ae147ae72d0f9effd5bc34af861fd325c7eb'
LIMITATION = 'Published claim only; signed/source-row corroboration or scope/version reconciliation remains outstanding'
KEYS = ('scope', 'stage', 'period', 'unit', 'source_url', 'value')
GUARDS = {
    'original_morcenter_monthly_file_authenticated': False,
    'investor_vs_gge_design_revision_reconciled': False,
    'current_2026_port_registry_capacity_authenticated': False,
    'government_program_and_promoter_budget_scope_matched': False,
    'signed_mlc_environmental_final_conclusion_authenticated': False,
    'mlc_commissioning_authenticated': False,
    'vessel_20_40_loaded_empty_mix_authenticated': False,
    'bering_real_paid_incremental_cargo_authenticated': False,
    'od_group_months_authenticated': 0,
    'od_group_months_required': 96,
    'github_hosted_ci_green': False,
    'investment_approved': False,
}


def evaluate(data):
    errors = []
    if not isinstance(data, dict):
        data = {}
        errors.append('Expected JSON object')
    if set(data) != {'schema', 'as_of', 'purpose', 'records', 'guards', 'methodology_notes'}:
        errors.append('Unexpected or missing top-level fields')
    if data.get('schema') != 'BERING_V37_PUBLISHED_MARKET_BOUNDARIES_V1' or data.get('as_of') != '2026-11-17':
        errors.append('Frozen snapshot date/schema changed')
    if data.get('guards') != GUARDS:
        errors.append('Source or investment guard changed')
    if data.get('purpose') != PURPOSE:
        errors.append('Purpose was modified')
    notes = data.get('methodology_notes')
    if not isinstance(notes, list) or not notes:
        errors.append('Missing methodological warnings')
    elif hashlib.sha256(json.dumps(notes, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest() != NOTES_SHA256:
        errors.append('Frozen methodological warnings changed')
    records = data.get('records')
    if not isinstance(records, list):
        records = []
        errors.append('Records are not a list')
    found = set()
    for row in records:
        if not isinstance(row, dict):
            errors.append('Record is not an object')
            continue
        key = row.get('id')
        if not isinstance(key, str) or key not in PINNED:
            errors.append('Unknown record identifier')
            continue
        if key in found:
            errors.append('Duplicate record ' + key)
        found.add(key)
        if set(row) != {'id', *KEYS, 'verification_limit'}:
            errors.append('Extra or missing fields ' + key)
        if tuple(row.get(k) for k in KEYS) != PINNED[key]:
            errors.append('Pinned source facts changed ' + key)
        if row.get('verification_limit') != LIMITATION:
            errors.append('Verification disclaimer modified ' + key)
        try:
            actual = Decimal(str(row.get('value')))
            if not actual.is_finite() or actual < 0:
                errors.append('Invalid measure ' + key)
        except (InvalidOperation, TypeError):
            errors.append('Unparseable measure ' + key)
    if found != set(PINNED) or len(records) != len(PINNED):
        errors.append('Evidence population changed')
    ok = not errors
    quantities = {key: Decimal(row[-1]) for key, row in PINNED.items()}
    port_diff = quantities['PORT_2025_TEU'] - quantities['PORT_2024_TEU']
    pct = port_diff / quantities['PORT_2024_TEU'] * 100
    gov = quantities['GOV_PLAN_MLC_EVENT_32_MILLION_RUB'] + quantities['GOV_PLAN_MLC_PORT_EVENT_33_MILLION_RUB']
    promo = quantities['MLC_PROMOTER_BUDGET_RUB_THOUSAND'] / 1000
    npv_capex = quantities['MLC_PROMOTER_NPV_RUB_THOUSAND'] / quantities['MLC_PROMOTER_BUDGET_RUB_THOUSAND'] * 100
    return {
        'status': 'RESEARCH_CONTEXT_ONLY' if ok else 'INVALID',
        'as_of': '2026-11-17',
        'source_records_reviewed': len(records) if ok else None,
        'published_2024_total_port_teu': 80900 if ok else None,
        'published_2025_total_port_teu': 84300 if ok else None,
        'port_teu_2025_minus_2024': int(port_diff) if ok else None,
        'port_teu_yoy_percent_rounded_two_dp': str(pct.quantize(Decimal('0.01'))) if ok else None,
        'archival_2009_nominal_container_capacity_teu': 45000 if ok else None,
        'current_port_capacity_2026_teu': None,
        'actual_2026_port_teu': None,
        'port_utilization_percent': None,
        'published_rival_design_perimeter_reconciled': False,
        'competing_design_capacity_sum_teu': None,
        'promoter_budget_million_rub': str(promo) if ok else None,
        'government_plan_two_events_million_rub': str(gov) if ok else None,
        'arithmetic_budget_difference_million_rub_not_a_funding_gap': str(promo - gov) if ok else None,
        'promoter_npv_to_budget_percent_not_project_roi': str(npv_capex.quantize(Decimal('0.0001'))) if ok else None,
        'verified_mlc_operational_teu': None,
        'signed_bering_incremental_shipments_40ft': None,
        'bering_incremental_group_cm_rub': None,
        'bering_npv_rub': None,
        'bankable_revenue_approved': False,
        'investment_approved': False,
        'P1': 'HOLD', 'P2': 'HOLD', 'P3': 'HOLD',
        'errors': errors,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--register', type=Path, default=DEFAULT)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    try:
        data = json.loads(args.register.read_text(encoding='utf-8'))
        output = evaluate(data)
    except (OSError, ValueError, UnicodeError, TypeError):
        output = evaluate({})
        output['errors'].append('Cannot read source register')
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + '\n'
    print(rendered, end='')
    if args.out:
        args.out.write_text(rendered, encoding='utf-8')
    return 0 if output['status'] == 'RESEARCH_CONTEXT_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())

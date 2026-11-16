#!/usr/bin/env python3
"""V31: regulatory-stage and CI-admission gate; never approves investment.

This is an immutable, read-only *research* checkpoint.  A publication about
expertise does not authenticate a signed approval or an operational permit.
The inputs remain frozen to this dated checkpoint; new evidence requires a new
reviewed revision rather than retroactive promotion.
"""
import argparse
import json
from pathlib import Path

CLAIMS = {
    'INVESTOR_CARD_MAY_2026': {
        'source_url': 'https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/',
        'stage': 'INVESTOR_PRESENTATION', 'date': '2026-05-25',
        'measure': 'PROJECT_DESIGN_TEUS_PER_YEAR', 'value': '30000',
        'source_review': 'PUBLIC_WEBPAGE', 'official_signed_document_verified': False,
    },
    'RPN_ENV_COMMISSION_AUG_2026': {
        'source_url': 'https://rpn.gov.ru/regions/cmu23/gov-services/gov-eco-exp/',
        'stage': 'ENVIRONMENTAL_EXPERTISE_COMMISSION_STARTED', 'date': '2026-08-31',
        'measure': 'REGULATORY_ORDER_NUMBER', 'value': '878-О',
        'source_review': 'INDEXED_OFFICIAL_PAGE_TEXT_ONLY',
        'official_signed_document_verified': False,
    },
    'GGE_ENGINEERING_PUBLIC_OCT_2026': {
        'source_url': 'https://egrz.ru/organisation/news/be268787-74bd-f111-80ff-00505634024e',
        'stage': 'POSITIVE_ENGINEERING_EXPERTISE_REPORTED', 'date': '2026-10-01',
        'measure': 'PROJECT_DESIGN_TEUS_PER_YEAR', 'value': '150000',
        'source_review': 'OFFICIAL_PRESS_RELEASE',
        'official_signed_document_verified': False,
    },
}
CONTROLS = {
    'environmental_expertise_positive_signed_verified': False,
    'engineering_expertise_original_signed_verified': False,
    'environmental_expertise_negative_signed_verified': False,
    'design_30k_150k_revision_crosswalk_verified': False,
    'construction_permit_verified': False,
    'commissioning_permit_verified': False,
    'physical_containers_at_mlc_verified': False,
    'new_paid_bering_cargo_verified': False,
    'independent_assessment_complete': False,
    'bankable_revenue_approved': False,
    'investment_approved': False,
}
CI_RUNS = {
    '42641304489': {'name': 'Bering V30 primary-source and investment HOLD QA',
                    'conclusion': 'failure', 'check_annotations_count': 1,
                    'annotation_text_verified': False, 'runner_execution_verified': False},
    '42641304182': {'name': 'Bering Research QA',
                    'conclusion': 'failure', 'check_annotations_count': 2,
                    'annotation_text_verified': False, 'runner_execution_verified': False},
}


def evaluate(registry, diagnostic):
    problems = []
    def check(test, label):
        if not test:
            problems.append(label)

    if not isinstance(registry, dict):
        registry = {}
        problems.append('REGISTRY_NOT_OBJECT')
    if not isinstance(diagnostic, dict):
        diagnostic = {}
        problems.append('CI_NOT_OBJECT')
    check(set(registry) == {'schema', 'as_of', 'claims', 'controls'}, 'REGISTRY_SCHEMA_FIELDS')
    check(registry.get('schema') == 'V31_REGULATORY_STAGE_V1', 'REGISTRY_SCHEMA_VERSION')
    check(registry.get('as_of') == '2026-11-10', 'REGISTRY_AS_OF')
    check(registry.get('controls') == CONTROLS, 'REGISTRY_CONTROLS_UNSUPPORTED_PROMOTION')
    rows = registry.get('claims')
    if not isinstance(rows, list):
        rows = []
        problems.append('CLAIMS_NOT_LIST')
    found = set()
    for row in rows:
        if not isinstance(row, dict):
            problems.append('CLAIM_NOT_OBJECT')
            continue
        key = row.get('id')
        if not isinstance(key, str) or key not in CLAIMS:
            problems.append('CLAIM_UNKNOWN_ID')
            continue
        if key in found:
            problems.append('CLAIM_DUPLICATE')
        found.add(key)
        if row != {'id': key, **CLAIMS[key]}:
            problems.append('CLAIM_PINNED_FIELDS_CHANGED_' + key)
    check(len(rows) == len(CLAIMS) and found == set(CLAIMS), 'CLAIM_SET_MISMATCH')

    check(set(diagnostic) == {
        'schema', 'as_of', 'head_sha', 'source', 'runs', 'mac_source_device_online',
        'github_hosted_ci_green', 'billing_or_policy_cause_verified',
        'pre_runner_root_cause', 'external_independent_acceptance_complete',
        'investment_approved'
    }, 'CI_SCHEMA_FIELDS')
    check(diagnostic.get('schema') == 'V31_GITHUB_PRE_RUNNER_ANNOTATIONS_V1', 'CI_SCHEMA_VERSION')
    check(diagnostic.get('as_of') == '2026-11-10', 'CI_AS_OF')
    check(diagnostic.get('head_sha') == 'a15ce22516abcea09905bdf98237b12090116b61', 'CI_PARENT_SHA')
    check(diagnostic.get('source') == 'GITHUB_CONNECTED_CHECK_RUN_METADATA', 'CI_SOURCE')
    check(diagnostic.get('mac_source_device_online') is False, 'CI_MAC_STATE_UNVERIFIED')
    for field in ('github_hosted_ci_green', 'billing_or_policy_cause_verified',
                  'external_independent_acceptance_complete', 'investment_approved'):
        check(diagnostic.get(field) is False, 'CI_UNSUPPORTED_PROMOTION_' + field)
    check(diagnostic.get('pre_runner_root_cause') == 'UNKNOWN', 'CI_CAUSE_UNPROVEN')
    runs = diagnostic.get('runs')
    if not isinstance(runs, list):
        runs = []
        problems.append('CI_RUNS_NOT_LIST')
    found_runs = set()
    for row in runs:
        if not isinstance(row, dict):
            problems.append('CI_RUN_NOT_OBJECT')
            continue
        key = str(row.get('id', ''))
        if key not in CI_RUNS:
            problems.append('CI_RUN_UNKNOWN_ID')
            continue
        if key in found_runs:
            problems.append('CI_RUN_DUPLICATE')
        found_runs.add(key)
        if row != {'id': int(key), **CI_RUNS[key]}:
            problems.append('CI_RUN_PINNED_FIELDS_CHANGED_' + key)
    check(len(runs) == len(CI_RUNS) and found_runs == set(CI_RUNS), 'CI_RUN_SET_MISMATCH')
    safe = not problems
    return {
        'status': 'RESEARCH_CONTEXT_ONLY' if safe else 'INVALID',
        'source_as_of': '2026-11-10',
        'claims_in_snapshot': len(rows) if safe else None,
        'investor_card_30k_teu_per_year': '30000' if safe else None,
        'engineering_press_150k_teu_per_year': '150000' if safe else None,
        'capacity_sum_teu_per_year': None,
        'source_revisions_matched': False,
        'environmental_panel_started_order': '878-О' if safe else None,
        'environmental_expertise_final_result': None,
        'signed_engineering_certificate_verified': False,
        'commissioning_verified': False,
        'new_paid_bering_40ft': None,
        'new_group_margin_rub': None,
        'bering_npv_rub': None,
        'github_ci_annotations_observed_total': 3 if safe else None,
        'github_ci_annotation_contents_verified': False,
        'github_ci_root_cause': None,
        'hosted_runner_green': False,
        'P1': 'HOLD', 'P2': 'HOLD', 'P3': 'HOLD',
        'bankable_revenue_approved': False, 'investment_approved': False,
        'errors': problems,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--regulatory', type=Path,
                        default=Path('data/public/V31_REGULATORY_STAGE_CHAIN.json'))
    parser.add_argument('--ci', type=Path,
                        default=Path('quality/V31_GITHUB_PRE_RUNNER_ANNOTATIONS.json'))
    parser.add_argument('--out', type=Path)
    opts = parser.parse_args()
    try:
        reg = json.loads(opts.regulatory.read_text(encoding='utf-8'))
        ci = json.loads(opts.ci.read_text(encoding='utf-8'))
        result = evaluate(reg, ci)
    except (OSError, UnicodeError, ValueError, TypeError):
        result = evaluate({}, {})
        result['errors'].append('SOURCE_LOAD_FAILED')
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if opts.out:
        opts.out.write_text(output, encoding='utf-8')
    print(output, end='')
    return 0 if result['status'] == 'RESEARCH_CONTEXT_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())

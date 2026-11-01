#!/usr/bin/env python3
"""V28 one-SHA four-gate decision: market/OD/source/cash are different proofs.

This is an integration harness, not commercial admission. It runs all previous
fail-closed guards and prevents any market statistic or planned port capacity
from being promoted into a paid Bering volume or bankable project margin.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

INPUTS = {
    'v28_market': 'data/public/V28_MAGADAN_MARKET_PERIMETER.json',
    'v27_port': 'data/public/V27_PORT_MONTHLY_UNVERIFIED.json',
    'v27_od': 'data/od/V27_GROUP_24M_UNVERIFIED.json',
    'v26_intake': 'data/pilots/V26_EMPTY_PROOF_INTAKE.json',
}


def snapshot(root):
    result = {}
    for name, rel in INPUTS.items():
        path = root / rel
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise FileNotFoundError('Required source missing or unsafe: ' + rel)
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def dict_or_empty(value):
    return value if isinstance(value, dict) else {}


def run_gate(root, runner=None):
    root = Path(root).resolve()
    errors, output = [], {}
    try:
        before = snapshot(root)
    except OSError as ex:
        return {'status':'INVALID', 'errors':[str(ex)], 'investment_approved':False,
                'bankable_revenue_approved':False, 'P1':'HOLD','P2':'HOLD','P3':'HOLD'}
    commands = {
        'market': [sys.executable,'scripts/v28_market_perimeter.py', '--register', INPUTS['v28_market']],
        'monthly_and_OD': [sys.executable,'scripts/v27_monthly_od_gate.py', '--operator-monthly',INPUTS['v27_port'], '--od-24m',INPUTS['v27_od']],
        'document_intake': [sys.executable,'scripts/evidence_readiness_v26.py', '--intake',INPUTS['v26_intake']],
        'commercial_physical_payment': [sys.executable,'scripts/release_commercial_v25.py','--repo','.'],
    }
    run = runner or subprocess.run
    for key, command in commands.items():
        try:
            process = run(command, cwd=root, capture_output=True, text=True, timeout=110, check=False)
            if process.returncode:
                raise ValueError(f'exit={process.returncode}: {str(process.stderr)[-200:]}')
            result = json.loads(process.stdout)
            if not isinstance(result, dict):
                raise ValueError('Child response is not object')
            output[key] = result
        except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as ex:
            errors.append(key + ': ' + type(ex).__name__ + ' ' + str(ex))
    try:
        if snapshot(root) != before:
            errors.append('Input source bytes changed during integrated evaluation')
    except OSError:
        errors.append('Source files became unavailable during evaluation')
    if len(output) == 4:
        if output['market'].get('status') != 'CONTEXT_VALID_REVIEW_REQUIRED':
            errors.append('Market source perimeter not accepted for research context')
        if dict_or_empty(output['market'].get('historical_port_teu')).get('physical_40ft_containers') is not None:
            errors.append('Illicit conversion of port TEU to 40ft')
        if dict_or_empty(output['market'].get('project_capacity_version_conflict')).get('future_in_service_capacity') is not None:
            errors.append('Illicit promotion of future port capacity into operational value')
        if dict_or_empty(output['monthly_and_OD'].get('operator_monthly')).get('status') != 'HOLD':
            errors.append('Missing operator monthly research may not pass')
        if dict_or_empty(output['monthly_and_OD'].get('group_24m_od')).get('status') != 'HOLD':
            errors.append('Missing historical group OD may not pass')
        if dict_or_empty(output['monthly_and_OD'].get('group_24m_od')).get('projection') is not None:
            errors.append('Forecast invented without reviewed source data')
        if output['document_intake'].get('status') != 'HOLD':
            errors.append('Unverified real source intake may not pass')
        if output['document_intake'].get('source_categories_with_locally_verified_bytes') != 0:
            errors.append('Unexpected documentation claims in empty baseline')
        if output['commercial_physical_payment'].get('status') != 'HOLD':
            errors.append('Unverified paid commercial proof may not pass')
        for key, item in output.items():
            if item.get('investment_approved') is not False or item.get('bankable_revenue_approved') is not False:
                errors.append(key + ': forbidden investment or bankable flag')
    return {
        'status': 'INVALID' if errors else 'HOLD',
        'source_sha256': before,
        'component_status': {
            'market': output.get('market',{}).get('status'),
            'port_monthly': dict_or_empty(output.get('monthly_and_OD',{}).get('operator_monthly')).get('status'),
            'group_od': dict_or_empty(output.get('monthly_and_OD',{}).get('group_24m_od')).get('status'),
            'document_intake': output.get('document_intake',{}).get('status'),
            'commercial': output.get('commercial_physical_payment',{}).get('status'),
        },
        'secondary_market_teu': output.get('market',{}).get('historical_port_teu'),
        'signed_new_40ft': None,
        'new_commercial_gross_rub': None,
        'incremental_group_cm_rub': None,
        'bering_npv_rub': None,
        'P1':'HOLD','P2':'HOLD','P3':'HOLD',
        'bankable_revenue_approved':False,'investment_approved':False,
        'errors':errors,
        'note':'This combined gate tests read-only research baselines, NOT paid commercial operations or customer verification.'
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path('.'))
    p.add_argument('--out',type=Path)
    a = p.parse_args()
    report = run_gate(a.repo)
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if a.out:
        a.out.write_text(text,encoding='utf-8')
    print(text,end='')
    return 2 if report['status']=='INVALID' else 0


if __name__=='__main__':
    raise SystemExit(main())

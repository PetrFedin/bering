#!/usr/bin/env python3
"""Free local V24-V26 research QA fallback, NEVER a GitHub Actions success.

Runs against an authorized local checkout when available. Records exact local
source hashes, test count, data completeness and observed remote-Git unknowns.
It never changes main, pushes files, calls a bank or authenticates cargo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

FILES = (
    'scripts/shipment_identity_v24.py',
    'scripts/release_commercial_v24.py',
    'scripts/independent_custody_payment_v25.py',
    'scripts/release_commercial_v25.py',
    'scripts/public_market_forecast_v26.py',
    'scripts/evidence_readiness_v26.py',
    'data/public/V26_PUBLIC_SOURCE_REGISTER.json',
    'data/pilots/V26_EMPTY_PROOF_INTAKE.json',
    'data/pilots/V23_cross_pilot_unverified.json',
    'data/pilots/V24_identity_unverified.json',
    'data/pilots/V25_documentary_unverified.json',
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


def _run(cmd: list[str], repo: Path, max_seconds: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                          timeout=max_seconds, check=False)


def run_qa(repo: Path) -> dict:
    root = repo.resolve(strict=True)
    results = {'schema_version': 'V26_LOCAL_QA_1', 'python': platform.python_version(),
               'repo_directory': str(root), 'git_head': None, 'git_worktree_clean': None,
               'github_remote_test_executed': False, 'github_actions_green': False,
               'external_document_authentication': False,
               'source_files_sha256': {}, 'error_items': [], 'unit_tests': None,
               'documentary_baseline': None, 'market_report': None,
               'evidence_intake_baseline': None,
               'full_integrated_commercial_baseline': 'NOT_RUN',
               'project_investment_approved': False, 'status': 'BLOCKED'}
    if not (root/'scripts/public_market_forecast_v26.py').exists():
        results['error_items'].append('Required V26 forecasting script missing')
        return results
    for relative in FILES:
        path = root / relative
        if not path.is_file():
            results['error_items'].append('Missing local input ' + relative)
        else:
            results['source_files_sha256'][relative] = sha256_file(path)
    if results['error_items']:
        return results
    try:
        if (root/'.git').exists():
            head = _run(['git', 'rev-parse', '--verify', 'HEAD'], root)
            status = _run(['git', 'status', '--porcelain'], root)
            if head.returncode == 0:
                results['git_head'] = head.stdout.strip()
            if status.returncode == 0:
                results['git_worktree_clean'] = not status.stdout.strip()
        compile_cmd = [sys.executable, '-m', 'compileall', '-q'] + [p for p in FILES if p.endswith('.py')]
        compiled = _run(compile_cmd, root)
        if compiled.returncode != 0:
            results['error_items'].append('Python compilation: ' + compiled.stderr[-1500:])
            return results
        tests = _run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*v2*.py', '-q'], root)
        match = re.search(r'Ran\s+(\d+)\s+tests?', tests.stderr)
        count = int(match.group(1)) if match else None
        results['unit_tests'] = {'count': count, 'returncode': tests.returncode,
                                 'summary': tests.stderr[-2500:]}
        if tests.returncode != 0 or count is None or count < 200:
            results['error_items'].append('Local V24+V25+V26 unit test suite not verified')
        documentary = _run([sys.executable, 'scripts/independent_custody_payment_v25.py',
                           '--v23', 'data/pilots/V23_cross_pilot_unverified.json',
                           '--v24', 'data/pilots/V24_identity_unverified.json',
                           '--v25', 'data/pilots/V25_documentary_unverified.json'], root)
        if documentary.returncode != 0:
            results['error_items'].append('V25 documentary baseline CLI failed: ' + documentary.stderr[-1000:])
        else:
            parsed = json.loads(documentary.stdout)
            results['documentary_baseline'] = {
                'status': parsed.get('status'),
                'bank_gross_paid_rub': parsed.get('bank_gross_paid_rub'),
                'source_records': parsed.get('v25_documentary_records'),
                'bankable_revenue_approved': parsed.get('bankable_revenue_approved'),
            }
            if (parsed.get('status') != 'HOLD' or parsed.get('bank_gross_paid_rub') is not None
                    or parsed.get('bankable_revenue_approved') is not False):
                results['error_items'].append('Unverified documentary baseline was not fail-closed')
        market = _run([sys.executable, 'scripts/public_market_forecast_v26.py', '--sources',
                       'data/public/V26_PUBLIC_SOURCE_REGISTER.json'], root)
        if market.returncode != 0:
            results['error_items'].append('V26 public data validation failed: ' + market.stderr[-1000:])
        else:
            parsed = json.loads(market.stdout)
            results['market_report'] = {
                'status': parsed.get('status'), 'commercial_gate': parsed.get('commercial_gate'),
                'project_incremental_group_cm_rub': parsed.get('project_incremental_group_cm_rub'),
                'target_cagr_percent': parsed.get('operator_target_implied_annual_growth_percent'),
            }
            if (parsed.get('status') != 'PUBLIC_CONTEXT_ONLY'
                    or parsed.get('commercial_gate') != 'HOLD'
                    or parsed.get('project_incremental_group_cm_rub') is not None):
                results['error_items'].append('Public forecast contaminated pilot commercial approval')
        intake = _run([sys.executable, 'scripts/evidence_readiness_v26.py',
                       '--intake', 'data/pilots/V26_EMPTY_PROOF_INTAKE.json'], root)
        if intake.returncode != 0:
            results['error_items'].append('V26 source intake baseline CLI failed: ' + intake.stderr[-1000:])
        else:
            parsed = json.loads(intake.stdout)
            results['evidence_intake_baseline'] = {
                'status': parsed.get('status'),
                'required_slots': parsed.get('total_proof_categories'),
                'locally_verified_file_slots': parsed.get('source_categories_with_locally_verified_bytes'),
            }
            if (parsed.get('status') != 'HOLD' or parsed.get('total_proof_categories') != 29
                    or parsed.get('source_categories_with_locally_verified_bytes') != 0):
                results['error_items'].append('V26 proof readiness baseline was not fail-closed')
        if all((root/p).exists() for p in (
            'scripts/release_commercial_v23.py', 'scripts/commercial_gate.py',
            'data/pilots/P1.json', 'data/pilots/P2.json', 'data/pilots/P3.json')):
            integrated = _run([sys.executable, 'scripts/release_commercial_v25.py', '--repo', str(root)], root)
            if integrated.returncode != 0:
                results['error_items'].append('Full integrated gate process error: ' + integrated.stderr[-1200:])
            else:
                parsed = json.loads(integrated.stdout)
                results['full_integrated_commercial_baseline'] = parsed.get('status')
                if parsed.get('status') != 'HOLD' or parsed.get('investment_approved') is not False:
                    results['error_items'].append('Integrated Bering commercial baseline did not stay HOLD')
        else:
            results['full_integrated_commercial_baseline'] = 'NOT_RUN_PARTIAL_LOCAL_SNAPSHOT'
        results['status'] = 'LOCAL_QA_PASS_REMOTE_CI_UNVERIFIED' if not results['error_items'] else 'BLOCKED'
    except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        results['error_items'].append(type(exc).__name__ + ': ' + str(exc))
        results['status'] = 'BLOCKED'
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    receipt = run_qa(args.repo)
    output = json.dumps(receipt, ensure_ascii=False, indent=2) + '\n'
    if args.receipt:
        args.receipt.write_text(output, encoding='utf-8')
    print(output, end='')
    return 0 if receipt['status'] == 'LOCAL_QA_PASS_REMOTE_CI_UNVERIFIED' else 2


if __name__ == '__main__':
    raise SystemExit(main())

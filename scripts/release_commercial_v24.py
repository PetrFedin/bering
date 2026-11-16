#!/usr/bin/env python3
"""Read-only commercial gate: V23 arithmetic + V24 physical-shipment identity.

Both controls must review exactly the same V23 source bytes. Even two REVIEWs
never mean authenticated contracts, investment PASS or actual cash receipts.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def audit(repo: Path, *, cross_input: Path | None = None,
          identity_input: Path | None = None,
          evidence_index: Path | None = None,
          evidence_dir: Path | None = None) -> dict:
    errors = []
    if bool(evidence_index) != bool(evidence_dir):
        return {'status': 'INVALID', 'errors': ['Evidence index and directory must both be present'],
                'bankable_revenue_approved': False, 'investment_approved': False}
    root = repo.resolve(strict=True)
    cross = (cross_input or root / 'data/pilots/V23_cross_pilot_unverified.json').resolve()
    identity = (identity_input or root / 'data/pilots/V24_identity_unverified.json').resolve()
    cmds = {
        'financial_and_commercial': [sys.executable, str(root / 'scripts/release_commercial_v23.py'),
                                     '--repo', str(root), '--cross-input', str(cross)],
        'physical_source_identity': [sys.executable, str(root / 'scripts/shipment_identity_v24.py'),
                                     '--v23', str(cross), '--identities', str(identity)],
    }
    if evidence_index is not None:
        for cmd in cmds.values():
            cmd.extend(['--evidence-index', str(evidence_index.resolve()),
                        '--evidence-dir', str(evidence_dir.resolve())])
    parts = {}
    for name, args in cmds.items():
        try:
            result = subprocess.run(args, cwd=root, capture_output=True, text=True,
                                    timeout=90, check=False)
            if result.returncode not in (0, 2, 3):
                raise ValueError('Subprocess failed with exit ' + str(result.returncode))
            payload = json.loads(result.stdout)
            if not isinstance(payload, dict):
                raise ValueError('Subprocess result must be JSON object')
            parts[name] = payload
            if result.returncode != 0:
                errors.append(name + ': subprocess rejected input, exit ' + str(result.returncode))
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            errors.append(name + ': ' + str(exc))
    financial = parts.get('financial_and_commercial', {})
    physical = parts.get('physical_source_identity', {})
    allowed = ('HOLD', 'INVALID', 'REVIEW')
    for key, report in parts.items():
        if report.get('status') not in allowed:
            errors.append(key + ': missing or unexpected gate status')
        if report.get('bankable_revenue_approved') is not False:
            errors.append(key + ': unexpected bankable revenue flag')
    if financial.get('investment_approved') is not False:
        errors.append('Financial gate unexpectedly reports investment approval')
    if physical.get('contracts_authenticated') is not False:
        errors.append('Identity gate unexpectedly reports contract authentication')
    if financial.get('status') == 'INVALID' or physical.get('status') == 'INVALID':
        errors.append('At least one source gate reports INVALID')
    if not errors and financial.get('status') == physical.get('status') == 'REVIEW':
        status = 'REVIEW'
    elif errors:
        status = 'INVALID'
    else:
        status = 'HOLD'
    return {
        'status': status,
        'financial_and_commercial_gate': financial.get('status'),
        'physical_source_identity_gate': physical.get('status'),
        'cross_input_sha256': physical.get('v23_source_sha256'),
        'linked_40ft_containers': physical.get('linked_40ft_containers'),
        'incremental_group_cm_rub_screening_only':
            financial.get('cross_pilot_incremental_group_cm_rub') if status == 'REVIEW' else None,
        'errors': errors,
        'bankable_revenue_approved': False,
        'investment_approved': False,
        'contracts_authenticated': False,
        'independent_review_required': True,
        'note': 'Both REVIEW only means inputs are eligible for manual review; no validated freight or investment PASS.',
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path('.'))
    p.add_argument('--cross-input', type=Path)
    p.add_argument('--identity-input', type=Path)
    p.add_argument('--evidence-index', type=Path)
    p.add_argument('--evidence-dir', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--require-review', action='store_true')
    args = p.parse_args()
    result = audit(args.repo, cross_input=args.cross_input,
                   identity_input=args.identity_input,
                   evidence_index=args.evidence_index, evidence_dir=args.evidence_dir)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 2 if result['status'] == 'INVALID' else 3 if args.require_review and result['status'] != 'REVIEW' else 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""V25 fail-closed reviewer gate: V23/V24 commercial + V25 source assertions.

Executes read-only tools. Even if everything is REVIEW, the result is not
funding authorization or verification against banks, carriers or customers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def audit(repo: Path, *, cross_input: Path | None = None,
          identity_input: Path | None = None, documentary_input: Path | None = None,
          evidence_index: Path | None = None, evidence_dir: Path | None = None) -> dict:
    errors = []
    if bool(evidence_index) != bool(evidence_dir):
        return {'status': 'INVALID', 'errors': ['Both source evidence index and directory are required'],
                'bankable_revenue_approved': False, 'investment_approved': False}
    root = repo.resolve(strict=True)
    src23 = (cross_input or root/'data/pilots/V23_cross_pilot_unverified.json').resolve()
    src24 = (identity_input or root/'data/pilots/V24_identity_unverified.json').resolve()
    src25 = (documentary_input or root/'data/pilots/V25_documentary_unverified.json').resolve()
    try:
        prior = {str(p):file_hash(p) for p in (src23,src24,src25)}
    except (OSError, ValueError) as exc:
        return {'status': 'INVALID', 'errors': ['Input source files unavailable: '+str(exc)],
                'bankable_revenue_approved': False, 'investment_approved': False}
    commands = {
        'commercial_physical_v24': [
            sys.executable, str(root/'scripts/release_commercial_v24.py'), '--repo', str(root),
            '--cross-input', str(src23), '--identity-input', str(src24)],
        'documentary_v25': [
            sys.executable, str(root/'scripts/independent_custody_payment_v25.py'),
            '--v23', str(src23), '--v24', str(src24), '--v25', str(src25)],
    }
    if evidence_index is not None:
        for cmd in commands.values():
            cmd += ['--evidence-index', str(evidence_index.resolve()),
                    '--evidence-dir', str(evidence_dir.resolve())]
    reports = {}
    for name, command in commands.items():
        try:
            result = subprocess.run(command, cwd=root, capture_output=True,
                                    text=True, timeout=120, check=False)
            if result.returncode != 0:
                raise ValueError(f'exit {result.returncode}, stderr: {result.stderr[:200]}')
            payload = json.loads(result.stdout)
            if not isinstance(payload, dict):
                raise ValueError('Child report was not a JSON object')
            reports[name] = payload
        except (OSError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as exc:
            errors.append(name + ': ' + str(exc))
    try:
        after = {str(p):file_hash(p) for p in (src23,src24,src25)}
        if after != prior:
            errors.append('Source bytes changed while V25 gate executed')
    except OSError:
        errors.append('Input source files no longer available after evaluation')
    old = reports.get('commercial_physical_v24', {})
    new = reports.get('documentary_v25', {})
    for name, report in reports.items():
        if report.get('status') not in ('INVALID','HOLD','REVIEW'):
            errors.append(name + ': unknown status')
        if report.get('bankable_revenue_approved') is not False:
            errors.append(name + ': forbidden bankable_revenue flag')
        if report.get('investment_approved') is not False:
            errors.append(name + ': forbidden investment_approved flag')
    if new.get('source_content_authenticated') is not False or new.get('cash_reconciled_with_bank') is not False:
        errors.append('Source matcher cannot self-authenticate contents or cash')
    if new.get('v23_source_sha256') != prior.get(str(src23)) or new.get('v24_source_sha256') != prior.get(str(src24)):
        errors.append('V25 source receipt did not match exact current V23/V24 bytes')
    if old.get('cross_input_sha256') != prior.get(str(src23)):
        errors.append('V24 financial source receipt did not match exact V23 input bytes')
    if old.get('status') == 'INVALID' or new.get('status') == 'INVALID':
        errors.append('At least one source gate rejected input')
    status = 'INVALID' if errors else 'REVIEW' if old.get('status') == new.get('status') == 'REVIEW' else 'HOLD'
    return {
        'status': status,
        'commercial_physical_v24': old.get('status'),
        'documentary_v25': new.get('status'),
        'source_fingerprints': {'v23':prior.get(str(src23)), 'v24':prior.get(str(src24)),
                                'v25':prior.get(str(src25))},
        'linked_physical_containers': new.get('physical_container_units'),
        'verified_source_file_count_syntactic_only': new.get('source_evidence_files_verified'),
        'screening_incremental_group_cm_rub': old.get('incremental_group_cm_rub_screening_only') if status=='REVIEW' else None,
        'errors': errors,
        'bankable_revenue_approved': False,
        'investment_approved': False,
        'contracts_authenticated': False,
        'cash_independently_confirmed': False,
        'manual_independent_review_required': True,
        'note': 'REVIEW is not certification: actual carrier, terminal, receiving-party and banking sources still need independent validation.'
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, default=Path('.'))
    ap.add_argument('--cross-input', type=Path)
    ap.add_argument('--identity-input', type=Path)
    ap.add_argument('--documentary-input', type=Path)
    ap.add_argument('--evidence-index', type=Path)
    ap.add_argument('--evidence-dir', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--require-review', action='store_true')
    args = ap.parse_args()
    value = audit(args.repo, cross_input=args.cross_input,
                  identity_input=args.identity_input, documentary_input=args.documentary_input,
                  evidence_index=args.evidence_index, evidence_dir=args.evidence_dir)
    output = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.write_text(output, encoding='utf-8')
    print(output, end='')
    return 2 if value['status']=='INVALID' else 3 if args.require_review and value['status']!='REVIEW' else 0


if __name__ == '__main__':
    raise SystemExit(main())

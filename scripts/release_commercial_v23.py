#!/usr/bin/env python3
"""Join original per-pilot and V23 cross-pilot evidence gates, fail closed.

A REVIEW only requests human assessment; this command can never release capital,
assert true contractual demand or change original economic assumptions.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from decimal import Decimal, InvalidOperation
import sys
from pathlib import Path

PILOTS = ('P1', 'P2', 'P3')


def audit(repo: Path, *, index: Path | None = None, documents: Path | None = None,
          cross_input: Path | None = None) -> dict:
    root = repo.resolve(strict=True)
    if bool(index) != bool(documents):
        return {'status': 'INVALID', 'errors': ['Evidence index and documents directory must be supplied together'],
                'bankable_revenue_approved': False}
    cmd_pilot = [sys.executable, str(root / 'scripts/commercial_gate.py'),
                 *(str(root / 'data/pilots' / (p + '.json')) for p in PILOTS)]
    cross_source = (cross_input.resolve() if cross_input else
                    root / 'data/pilots/V23_cross_pilot_unverified.json')
    cmd_cross = [sys.executable, str(root / 'scripts/cross_pilot_additionality_v23.py'),
                 '--input', str(cross_source)]
    if index is not None:
        cmd_pilot.extend(['--evidence-index', str(index.resolve()) , '--evidence-dir', str(documents.resolve())])
        cmd_cross.extend(['--evidence-index', str(index.resolve()), '--evidence-dir', str(documents.resolve())])
    checks = {}
    errors = []
    for label, cmd in (('individual_pilots', cmd_pilot), ('cross_pilot', cmd_cross)):
        try:
            process = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                                     check=False, timeout=90)
            if process.returncode not in (0, 1, 2, 3):
                raise ValueError(f'unexpected return code {process.returncode}')
            parsed = json.loads(process.stdout)
            if not isinstance(parsed, dict):
                raise ValueError('JSON must be an object')
            checks[label] = parsed
            if process.returncode != 0:
                errors.append(f'{label}: subprocess returned nonzero code {process.returncode}')
        except (OSError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as exc:
            errors.append(f'{label}: {exc}')
    individual = checks.get('individual_pilots', {})
    cross = checks.get('cross_pilot', {})
    rows = individual.get('results') if isinstance(individual.get('results'), list) else []
    if len(rows) != 3 or individual.get('evaluated') != 3:
        errors.append('The individual gate did not assess exactly three pilots')
    ids = [r.get('pilot_id') for r in rows if isinstance(r, dict)]
    if set(ids) != set(PILOTS) or len(ids) != 3:
        errors.append('Individual pilot identities missing or duplicated')
    states = {r.get('pilot_id'): r.get('gate') for r in rows if isinstance(r, dict)}
    if cross.get('status') not in ('INVALID', 'HOLD', 'REVIEW'):
        errors.append('Unknown or missing V23 cross-pilot status')
    cross_rows = cross.get('pilots')
    if (not isinstance(cross_rows, dict) or set(cross_rows) != set(PILOTS)
            or not all(isinstance(cross_rows[p], dict) for p in PILOTS)):
        errors.append('V23 must evaluate all three pilot records as objects')
        cross_rows = {}
    if not all(isinstance(r, dict) and r.get('bankable_revenue_approved') is False for r in rows):
        errors.append('Unexpected individual bankability flag')
    if cross.get('bankable_revenue_approved') is not False:
        errors.append('Unexpected cross-pilot bankability flag')
    if any(r.get('errors') for r in rows if isinstance(r, dict)):
        errors.append('Individual pilot reported structural errors')
    if cross.get('status') == 'INVALID' or cross.get('errors'):
        errors.append('Cross-pilot data integrity failed')
    ready_for_tieout = (not errors and cross.get('status') == 'REVIEW'
                        and all(states.get(p) == 'REVIEW' and cross_rows[p].get('status') == 'REVIEW'
                                for p in PILOTS))
    if ready_for_tieout:
        try:
            total = Decimal('0')
            for p in PILOTS:
                own = next(row for row in rows if row['pilot_id'] == p)
                cross_row = cross_rows[p]
                counted = cross_row['classification_counts_40ft']['new']
                from_pilot = Decimal(str(own['net_new_40ft_containers']))
                if not isinstance(counted, int) or isinstance(counted, bool) or from_pilot != Decimal(counted):
                    raise ValueError(f'{p}: net-new 40ft volume differs across source gates')
                individual = Decimal(str(own['incremental_group_cm_rub']))
                group = Decimal(str(cross_row['screening_incremental_group_cm_rub']))
                if not individual.is_finite() or not group.is_finite() or individual != group:
                    raise ValueError(f'{p}: incremental margin differs across source gates')
                total += group
            group_total = Decimal(str(cross['screening_total_incremental_group_cm_rub']))
            if not group_total.is_finite() or group_total != total:
                raise ValueError('Group total differs from sum of pilot results')
        except (KeyError, IndexError, TypeError, StopIteration, ValueError, InvalidOperation) as exc:
            errors.append('Cross-source numeric reconciliation FAIL: ' + str(exc))
    gate = ('INVALID' if errors else 'REVIEW' if ready_for_tieout else 'HOLD')
    return {'status': gate, 'individual_gates': states,
            'cross_pilot_status': cross.get('status'),
            'cross_pilot_incremental_group_cm_rub': cross.get('screening_total_incremental_group_cm_rub')
                if gate == 'REVIEW' else None,
            'errors': errors,
            'bankable_revenue_approved': False, 'investment_approved': False,
            'independent_commercial_review_required': True,
            'note': 'HOLD / INVALID mean not admitted. REVIEW never implies contract authentication, NPV validity or investment PASS.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--evidence-index', type=Path)
    parser.add_argument('--evidence-dir', type=Path)
    parser.add_argument('--cross-input', type=Path, help='Externally reconciled V23 record file; default is zero-claim baseline')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--require-review', action='store_true')
    args = parser.parse_args()
    receipt = audit(args.repo, index=args.evidence_index, documents=args.evidence_dir,
                    cross_input=args.cross_input)
    text = json.dumps(receipt, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    print(text)
    return 2 if receipt['status'] == 'INVALID' else 3 if args.require_review and receipt['status'] != 'REVIEW' else 0


if __name__ == '__main__':
    raise SystemExit(main())

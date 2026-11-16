#!/usr/bin/env python3
"""V26 data-quality gate for real freight pilot evidence intake.

A byte-matching file and an asserted reviewer do not authenticate a payment,
shipment, historic customer or ownership. No amount of synthetic data emits
an investment approval or P1/P2/P3 commercial PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

COMMON = (
    'customer_order', 'priced_d2d_quote', 'carrier_waybill',
    'terminal_events', 'consignee_pod', 'invoice_net_vat_gross',
    'independent_bank_settlement', 'group_od_history_24m',
    'incumbent_group_margin_costs',
)
SPECIAL = {'P1': (), 'P2': ('reefer_temperature_energy',),
           'P3': ('feeder_and_customs_clearance',)}
SHA = re.compile(r'^[0-9a-f]{64}$')
DOCID = re.compile(r'^EV-[A-Za-z0-9_-]{6,100}$')
REVIEWER = re.compile(r'^[A-Za-z0-9_.-]{4,100}$')


def day(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value) if date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def evidence_file_valid(root: Path | None, slot: dict, cutoff: date) -> bool:
    if root is None:
        return False
    raw = slot.get('relative_path')
    digest = slot.get('sha256')
    submitter, reviewer = slot.get('submitted_by'), slot.get('reviewed_by')
    reviewed = day(slot.get('reviewed_on'))
    if (not isinstance(raw, str) or not raw or '\\' in raw or '\x00' in raw
            or Path(raw).is_absolute() or '..' in Path(raw).parts
            or not isinstance(digest, str) or not SHA.fullmatch(digest)
            or not isinstance(submitter, str) or not REVIEWER.fullmatch(submitter)
            or not isinstance(reviewer, str) or not REVIEWER.fullmatch(reviewer)
            or submitter.casefold() == reviewer.casefold()
            or reviewed is None or reviewed > cutoff
            or not isinstance(slot.get('source_org_id'), str)
            or not REVIEWER.fullmatch(slot['source_org_id'])):
        return False
    try:
        base = root.resolve(strict=True)
        path = base / raw
        if path.is_symlink():
            return False
        actual = path.resolve(strict=True)
        return actual.is_relative_to(base) and actual.is_file() and actual.stat().st_size > 0 and sha256_file(actual) == digest
    except (ValueError, OSError, RuntimeError):
        return False


def evaluate(payload: Any, evidence_root: Path | None = None) -> dict[str, Any]:
    errs: list[str] = []
    missed: list[str] = []
    if not isinstance(payload, dict):
        return {'status': 'INVALID', 'errors': ['Input must be object'],
                'investment_approved': False, 'bankable_revenue_approved': False}
    if payload.get('schema_version') != 'V26_INTAKE_1':
        errs.append('Unknown intake schema')
    cutoff = day(payload.get('as_of'))
    if cutoff is None or cutoff > date.today():
        errs.append('Invalid or future as_of date')
        cutoff = date.min
    pilots = payload.get('pilots')
    if not isinstance(pilots, dict) or set(pilots) != set(SPECIAL):
        errs.append('Must provide exactly P1, P2 and P3')
        pilots = {}
    totals = {}
    all_refids: dict[str, list[str]] = {}
    total_ready, total_required = 0, 0
    for pilot in SPECIAL:
        required = (*COMMON, *SPECIAL[pilot])
        total_required += len(required)
        value = pilots.get(pilot)
        if not isinstance(value, dict) or set(value) != set(required):
            errs.append(f'{pilot}: missing or extra proof categories')
            value = {}
        covered = 0
        for key in required:
            slot = value.get(key)
            path = pilot + '.' + key
            if not isinstance(slot, dict):
                errs.append(path + ': expected source descriptor')
                continue
            status = slot.get('status')
            if status not in ('MISSING', 'PRESENT_FOR_REVIEW'):
                errs.append(path + ': status invalid')
                continue
            if status == 'MISSING':
                if any(slot.get(field) is not None for field in (
                        'evidence_id', 'relative_path', 'sha256', 'source_org_id',
                        'submitted_by', 'reviewed_by', 'reviewed_on')):
                    errs.append(path + ': missing descriptor cannot have verified document fields')
                missed.append(path + ':not_received')
                continue
            evid = slot.get('evidence_id')
            if not isinstance(evid, str) or not DOCID.fullmatch(evid):
                errs.append(path + ': invalid evidence ID')
                continue
            all_refids.setdefault(evid.casefold(), []).append(path)
            if evidence_file_valid(evidence_root, slot, cutoff):
                covered += 1
            else:
                missed.append(path + ':source_byte_or_reviewer_verification_missing')
        total_ready += covered
        totals[pilot] = {'source_categories_with_valid_bytes': covered,
                         'source_categories_required': len(required),
                         'source_categories_missing_or_unverified': len(required) - covered,
                         'pilot_gate': 'HOLD',
                         'real_paid_40ft_volume': None}
    # Reusing one original may be legitimate for group OD baseline, but reusing an
    # invoice or bank receipt as proof of other distinct sources demands review.
    reused = {e: paths for e, paths in all_refids.items() if len(paths) > 1}
    if reused:
        missed.append('reused_source_ids_require_independent_multi_pilot_adjudication')
    if errs:
        for p in totals:
            totals[p]['source_categories_with_valid_bytes'] = None
    return {
        'status': 'INVALID' if errs else 'HOLD' if missed or total_ready != total_required else 'READY_FOR_MANUAL_EXTERNAL_AUTHENTICITY_REVIEW',
        'as_of': payload.get('as_of'),
        'total_proof_categories': total_required,
        'source_categories_with_locally_verified_bytes': total_ready if not errs else None,
        'per_pilot': totals,
        'duplicates_for_review': reused,
        'missing': sorted(set(missed)),
        'errors': sorted(set(errs)),
        'all_external_entities_authenticated': False,
        'original_source_content_truth_verified': False,
        'bank_receipts_independently_authenticated': False,
        'new_40ft_volume': None,
        'incremental_group_cm_rub': None,
        'bankable_revenue_approved': False,
        'investment_approved': False,
        'note': 'This is a document intake completeness gate, not proof of actual business or cash.',
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--intake', type=Path, required=True)
    p.add_argument('--evidence-dir', type=Path)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    result = evaluate(json.loads(args.intake.read_text(encoding='utf-8')), args.evidence_dir)
    msg = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.write_text(msg, encoding='utf-8')
    print(msg, end='')
    return 2 if result['status'] == 'INVALID' else 0


if __name__ == '__main__':
    raise SystemExit(main())

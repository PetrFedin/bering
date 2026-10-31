#!/usr/bin/env python3
"""Conservative V24 source-to-claim reconciliation for 40ft cargo.

One V23 economic shipment may contain several 40ft containers. Require
one identity record per shipment and one source-linked item per physical unit. Data consistency and
checksum integrity never authenticate shipping, payment or legal documents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

PILOTS = frozenset(('P1', 'P2', 'P3'))
# Intentionally narrow documented 40ft codes; unsupported equipment needs a reviewed schema extension.
DRY_ISO_TYPES = frozenset(('42G0', '42G1', '45G0', '45G1'))
REEFER_ISO_TYPES = frozenset(('42R1', '42R3', '45R1'))
CONTAINER = re.compile(r'^[A-Z]{3}U[0-9]{7}$')
IDENTIFIER = re.compile(r'^[A-Za-z0-9_-]{6,100}$')
EVIDENCE = re.compile(r'^EV-[A-Z0-9][A-Z0-9_-]{5,}$')
HEX = re.compile(r'^[0-9a-f]{64}$')
# ISO 6346 letter values deliberately skip multiples of 11.
LETTER_VALUES = dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    (10,12,13,14,15,16,17,18,19,20,21,23,24,25,26,27,28,29,
     30,31,32,34,35,36,37,38)))


def iso6346_valid(number: Any) -> bool:
    """Syntactic ISO 6346 checksum only, NOT evidence of a real container."""
    if not isinstance(number, str) or not CONTAINER.fullmatch(number):
        return False
    weighted = sum((LETTER_VALUES[ch] if ch.isalpha() else int(ch)) * (2 ** i)
                   for i, ch in enumerate(number[:10]))
    return weighted % 11 % 10 == int(number[10])


def iso6346_check_digit(first_ten: str) -> str:
    if not isinstance(first_ten, str) or not re.fullmatch(r'[A-Z]{3}U[0-9]{6}', first_ten):
        raise ValueError('Expected first ten ISO 6346 characters')
    weighted = sum((LETTER_VALUES[ch] if ch.isalpha() else int(ch)) * (2 ** i)
                   for i, ch in enumerate(first_ten))
    return str(weighted % 11 % 10)


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def has_reviewed_bytes(evidence_id: Any, index: Any, root: Path | None, as_of: date) -> bool:
    """Require separate reviewer + stored source-file SHA256; not signature proof."""
    if (not isinstance(evidence_id, str) or not EVIDENCE.fullmatch(evidence_id)
            or not isinstance(index, dict) or root is None):
        return False
    entry = index.get(evidence_id)
    if not isinstance(entry, dict) or entry.get('status') != 'VERIFIED':
        return False
    raw, digest = entry.get('relative_path'), entry.get('sha256')
    submitted, reviewed = entry.get('submitted_by'), entry.get('reviewed_by')
    reviewed_on = parse_date(entry.get('reviewed_on'))
    if (not isinstance(raw, str) or not raw or '\\' in raw or '\x00' in raw
            or Path(raw).is_absolute() or '..' in Path(raw).parts
            or not isinstance(digest, str) or not HEX.fullmatch(digest)
            or not isinstance(submitted, str) or not submitted.strip()
            or not isinstance(reviewed, str) or not reviewed.strip()
            or submitted.strip().casefold() == reviewed.strip().casefold()
            or reviewed_on is None or reviewed_on > as_of):
        return False
    try:
        base = root.resolve(strict=True)
        relative = Path(raw)
        target = base / relative
        if target.is_symlink():
            return False
        file = target.resolve(strict=True)
        if not file.is_relative_to(base) or not file.is_file() or file.stat().st_size == 0:
            return False
        h = hashlib.sha256()
        with file.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest() == digest
    except (OSError, ValueError, RuntimeError):
        return False


def _normalized_ref(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r'[\s\-_/]', '', value.upper())
    return cleaned if re.fullmatch(r'[A-Z0-9]{5,50}', cleaned) else None


def evaluate(v23: Any, v23_bytes: bytes, identity: Any, *,
             evidence_index: Any = None, evidence_root: Path | None = None) -> dict:
    errors: list[str] = []
    missing: list[str] = []
    ambiguous: list[str] = []
    if not isinstance(v23, dict) or not isinstance(identity, dict):
        return {'status': 'INVALID', 'errors': ['V23 and V24 inputs must be objects'],
                'bankable_revenue_approved': False, 'source_records_proved': False}
    if identity.get('schema_version') != 'V24':
        errors.append('identity.schema_version must be V24')
    if v23.get('schema_version') != 'V23':
        errors.append('v23.schema_version must be V23')
    pinned = identity.get('v23_input_sha256')
    if not isinstance(pinned, str) or not HEX.fullmatch(pinned) or pinned != hashlib.sha256(v23_bytes).hexdigest():
        errors.append('Exact V23 input SHA-256 not pinned or mismatched')
    as_of = parse_date(identity.get('as_of'))
    if as_of is None or identity.get('as_of') != v23.get('as_of'):
        errors.append('V24 as_of must be valid and equal to V23 as_of')
    if as_of is not None and as_of > date.today():
        errors.append('V24 as_of may not be a future observation date')
        as_of = date.min
    if identity.get('group_id') != v23.get('group_id'):
        errors.append('V24 group_id does not match V23 economic group')
    v23_rows = v23.get('shipments')
    identity_rows = identity.get('shipments')
    if not isinstance(v23_rows, list) or not isinstance(identity_rows, list):
        errors.append('Both input shipments fields must be arrays')
        v23_rows = v23_rows if isinstance(v23_rows, list) else []
        identity_rows = identity_rows if isinstance(identity_rows, list) else []
    reference: dict[tuple[str, str], dict] = {}
    for i, row in enumerate(v23_rows):
        if not isinstance(row, dict):
            errors.append(f'V23 shipment[{i}] must be an object')
            continue
        pilot, eid = row.get('pilot_id'), row.get('economic_shipment_id')
        if pilot not in PILOTS or not isinstance(eid, str) or not IDENTIFIER.fullmatch(eid):
            errors.append(f'V23 shipment[{i}] invalid pilot or economic_shipment_id')
            continue
        key = pilot, eid.casefold()
        if key in reference:
            errors.append(f'V23 duplicate shipment key: {key}')
        reference[key] = row
    seen_rows: set[tuple[str,str]] = set()
    # A waybill may legitimately contain multiple containers. The *pair* B/L+container is exclusive.
    bl_container: dict[tuple[str,str], str] = {}
    events: dict[str,str] = {}
    container_uses: dict[str,list[tuple[date,date,str,str]]] = {}
    linked_containers = 0
    verified_container_events = 0
    for i, row in enumerate(identity_rows):
        label = f'identity.shipments[{i}]'
        if not isinstance(row, dict):
            errors.append(label + ': record must be an object')
            continue
        pilot, eid = row.get('pilot_id'), row.get('economic_shipment_id')
        if pilot not in PILOTS or not isinstance(eid, str) or not IDENTIFIER.fullmatch(eid):
            errors.append(label + ': invalid pilot or economic_shipment_id')
            continue
        key = pilot, eid.casefold()
        if key in seen_rows:
            errors.append(label + ': duplicate identity row')
        seen_rows.add(key)
        matching = reference.get(key)
        if matching is None:
            errors.append(label + ': identity has no matching V23 economic shipment')
            continue
        if row.get('physical_consignment_key') != matching.get('physical_consignment_key'):
            errors.append(label + ': physical consignment key differs from V23')
        supplied_waybill = (matching.get('evidence') or {}).get('waybill') if isinstance(matching.get('evidence'), dict) else None
        if row.get('waybill_evidence_id') != supplied_waybill or not isinstance(supplied_waybill, str):
            errors.append(label + ': V24 waybill evidence ID differs from V23 source')
        if not has_reviewed_bytes(row.get('waybill_evidence_id'), evidence_index, evidence_root, as_of):
            missing.append(label + ':verified_waybill_source')
        containers = row.get('containers')
        quantity = matching.get('quantity_40ft')
        if (not isinstance(containers, list) or not isinstance(quantity, int)
                or isinstance(quantity, bool) or quantity <= 0 or len(containers) != quantity):
            errors.append(label + ': listed physical containers must equal V23 positive quantity_40ft')
            continue
        seen_in_shipment: set[str] = set()
        for j, c in enumerate(containers):
            c_label = label + f'.containers[{j}]'
            if not isinstance(c, dict):
                errors.append(c_label + ': record must be an object')
                continue
            number = c.get('container_number')
            if not iso6346_valid(number):
                errors.append(c_label + ': invalid ISO 6346 container number/check digit')
                continue
            if number in seen_in_shipment:
                errors.append(c_label + ': same physical container repeated within one economic shipment')
            seen_in_shipment.add(number)
            size_type = c.get('iso_size_type')
            permitted = REEFER_ISO_TYPES if pilot == 'P2' else DRY_ISO_TYPES
            if size_type not in permitted:
                errors.append(c_label + ': ISO 40ft size/type outside documented dry or reefer subset')
            loaded = parse_date(c.get('loaded_on'))
            delivered = parse_date(c.get('delivered_on'))
            if loaded is None or delivered is None or not (loaded <= delivered <= as_of):
                errors.append(c_label + ': invalid/future/reversed actual delivery dates')
                continue
            bl = _normalized_ref(c.get('bill_of_lading_ref'))
            if bl is None:
                errors.append(c_label + ': missing/invalid bill of lading reference')
                continue
            bl_key = (bl, number)
            if bl_key in bl_container:
                errors.append(c_label + ': same B/L and container counted twice at ' + bl_container[bl_key])
            bl_container[bl_key] = c_label
            event = c.get('container_event_evidence_id')
            if isinstance(event, str) and event in events:
                errors.append(c_label + ': one container event evidence ID reused at ' + events[event])
            if isinstance(event, str):
                events[event] = c_label
            if not has_reviewed_bytes(event, evidence_index, evidence_root, as_of):
                missing.append(c_label + ':verified_container_movement')
            else:
                verified_container_events += 1
            if not has_reviewed_bytes(c.get('delivery_evidence_id'), evidence_index, evidence_root, as_of):
                missing.append(c_label + ':verified_actual_delivery')
            for start, end, earlier_label, earlier_bl in container_uses.get(number, []):
                # The same container may be reused in successive shipments. Overlapping
                # intervals (including same-day handovers) are *ambiguous*, not proof of fraud.
                if loaded <= end and start <= delivered:
                    ambiguous.append(c_label + ': container time overlap with ' + earlier_label)
            container_uses.setdefault(number, []).append((loaded, delivered, c_label, bl))
            linked_containers += 1
    absent = set(reference) - seen_rows
    for pilot, eid in sorted(absent):
        missing.append('missing identity for V23 shipment: ' + pilot + '/' + eid)
    if len(v23_rows) == 0:
        missing.append('no external V23 shipments available')
    if len(identity_rows) == 0:
        missing.append('no externally documented V24 identities available')
    status = 'INVALID' if errors else 'HOLD' if missing or ambiguous else 'REVIEW'
    return {
        'status': status, 'v23_source_sha256': hashlib.sha256(v23_bytes).hexdigest(),
        'v23_shipment_records': len(v23_rows), 'identity_records': len(identity_rows),
        'linked_40ft_containers': linked_containers,
        'verified_container_event_files': verified_container_events,
        'errors': errors, 'missing': sorted(set(missing)),
        'ambiguous_overlaps': sorted(set(ambiguous)),
        'bankable_revenue_approved': False, 'source_records_proved': False,
        'contracts_authenticated': False,
        'linkage_review_required': True,
        'note': 'ISO checks are syntactic and do not verify true 40ft size; source-file SHA does not authenticate physical delivery or paid commitments.',
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--v23', type=Path, required=True)
    p.add_argument('--identities', type=Path, required=True)
    p.add_argument('--evidence-index', type=Path)
    p.add_argument('--evidence-dir', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--require-review', action='store_true')
    args = p.parse_args()
    if bool(args.evidence_index) != bool(args.evidence_dir):
        p.error('Evidence index and directory must be supplied together')
    raw = args.v23.read_bytes()
    evidence = json.loads(args.evidence_index.read_text(encoding='utf-8')) if args.evidence_index else None
    report = evaluate(json.loads(raw), raw, json.loads(args.identities.read_text(encoding='utf-8')),
                      evidence_index=evidence, evidence_root=args.evidence_dir)
    formatted = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.write_text(formatted, encoding='utf-8')
    print(formatted, end='')
    return 2 if report['status'] == 'INVALID' else 3 if args.require_review and report['status'] != 'REVIEW' else 0


if __name__ == '__main__':
    raise SystemExit(main())

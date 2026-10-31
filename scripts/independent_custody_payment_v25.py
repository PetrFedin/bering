#!/usr/bin/env python3
"""V25 documentary *claim* reconciliation for the Bering P1/P2/P3 research pilots.

Checks independent-source metadata, physical movement chronology and exact RUB
invoice/bank settlement arithmetic. It does NOT parse/authenticate shipping
contracts, establish beneficial ownership, verify payments at a bank or make
an investment decision. Source records and source-file hashes may be synthetic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from shipment_identity_v24 import has_reviewed_bytes, iso6346_valid, parse_date

PILOTS = frozenset(('P1', 'P2', 'P3'))
DOC_ID = re.compile(r'^[A-Za-z0-9_-]{6,100}$')
SHA = re.compile(r'^[a-f0-9]{64}$')
EVIDENCE_ID = re.compile(r'^EV-[A-Z0-9][A-Z0-9_-]{5,}$')
EVENT_ROLE = {
    'CARRIER_LOAD': 'CARRIER',
    'CARRIER_ARRIVE': 'CARRIER',
    'TERMINAL_RELEASE': 'TERMINAL',
    'CONSIGNEE_RECEIPT': 'CONSIGNEE',
}


def as_utc(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})', raw
    ):
        return None
    try:
        value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        return value.astimezone(timezone.utc)
    except ValueError:
        return None


def amount(raw: Any) -> Decimal | None:
    if isinstance(raw, bool) or isinstance(raw, float) or not isinstance(raw, (str, int)):
        return None
    try:
        val = Decimal(str(raw))
    except InvalidOperation:
        return None
    if not val.is_finite() or val < 0 or val.as_tuple().exponent < -2:
        return None
    return val


def ident(raw: Any) -> bool:
    return isinstance(raw, str) and bool(DOC_ID.fullmatch(raw))


def normalized_reference(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    value = re.sub(r'[\s/_-]', '', raw.upper())
    return value if re.fullmatch(r'[A-Z0-9]{5,60}', value) else None


def source_ok(eid: Any, index: Any, root: Path | None, cutoff: date) -> bool:
    return has_reviewed_bytes(eid, index, root, cutoff)


def provenance_matches(eid: Any, org: Any, event_day: date | None,
                       index: Any, cutoff: date) -> bool:
    """Check the separately curated source index names the claimed issuer/actor.

    An asserted org ID is NOT a proof of identity. Independent authentication
    of the original carrier/terminal/bank is still mandatory after REVIEW.
    """
    if (not isinstance(index, dict) or not isinstance(org, str)
            or not ident(org) or event_day is None):
        return False
    source = index.get(eid) if isinstance(eid, str) else None
    if not isinstance(source, dict):
        return False
    indexed_org = source.get('source_org_id')
    inspected = parse_date(source.get('reviewed_on'))
    return (isinstance(indexed_org, str) and ident(indexed_org)
            and indexed_org.casefold() == org.casefold()
            and inspected is not None and event_day <= inspected <= cutoff)


def _fail(status: str, errors: list[str], missing: list[str], warnings: list[str],
          stats: dict[str, Any], *, v23_sha: str = '', v24_sha: str = '') -> dict:
    return {
        'status': status,
        'v23_source_sha256': v23_sha,
        'v24_source_sha256': v24_sha,
        'errors': sorted(set(errors)),
        'missing': sorted(set(missing)),
        'manual_review': sorted(set(warnings)),
        **stats,
        'cash_reconciled_with_bank': False,
        'source_content_authenticated': False,
        'bankable_revenue_approved': False,
        'investment_approved': False,
        'manual_independent_verification_required': True,
        'interpretation': 'REVIEW is only a syntactic/byte-integrity screening outcome; no actual source authenticity, cash confirmation or finance approval.',
    }


def evaluate(v23: Any, raw23: bytes, v24: Any, raw24: bytes, v25: Any,
             *, evidence_index: Any = None, evidence_dir: Path | None = None) -> dict:
    """Evaluate zero-trust structured source assertions against V23/V24 pinned bytes."""
    errors: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []
    stats = dict(v23_shipments=0, v24_identity_records=0, v25_documentary_records=0,
                 physical_container_units=0, source_events_claimed=0,
                 source_evidence_files_verified=0, bank_settlements_claimed=0,
                 bank_gross_paid_rub=None)
    h23, h24 = hashlib.sha256(raw23).hexdigest(), hashlib.sha256(raw24).hexdigest()
    if not all(isinstance(a, dict) for a in (v23, v24, v25)):
        return _fail('INVALID', ['All inputs must be JSON objects'], missing, warnings, stats,
                     v23_sha=h23, v24_sha=h24)
    if (v23.get('schema_version'), v24.get('schema_version'), v25.get('schema_version')) != ('V23', 'V24', 'V25'):
        errors.append('Expected linked V23 / V24 / V25 schema versions')
    if v24.get('v23_input_sha256') != h23 or v25.get('v23_input_sha256') != h23:
        errors.append('V23 byte hash mismatch between documentary layers')
    if v25.get('v24_identity_sha256') != h24:
        errors.append('V24 byte hash mismatch; actual identity file must be pinned')
    if not all(v25.get('as_of') == src.get('as_of') and
               v25.get('group_id') == src.get('group_id')
               for src in (v23, v24)):
        errors.append('as_of and economic group must match all three inputs')
    cutoff = parse_date(v25.get('as_of'))
    if cutoff is None or cutoff > date.today():
        errors.append('V25 observation date invalid or future-dated')
        cutoff = date.min
    if v25.get('currency') != 'RUB':
        errors.append('V25 amounts require explicit RUB; other currencies need externally reviewed FX mapping')
    source23 = v23.get('shipments')
    source24 = v24.get('shipments')
    source25 = v25.get('shipments')
    if any(not isinstance(rows, list) for rows in (source23, source24, source25)):
        return _fail('INVALID', errors + ['Each shipments field must be a JSON array'], missing,
                     warnings, stats, v23_sha=h23, v24_sha=h24)
    stats['v23_shipments'] = len(source23)
    stats['v24_identity_records'] = len(source24)
    stats['v25_documentary_records'] = len(source25)
    claims23 = {}
    claims24 = {}
    for name, rows, lookup in (('V23', source23, claims23), ('V24', source24, claims24)):
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f'{name}[{i}]: record must be object')
                continue
            pilot, shipment = row.get('pilot_id'), row.get('economic_shipment_id')
            if pilot not in PILOTS or not ident(shipment):
                errors.append(f'{name}[{i}]: invalid pilot or shipment identity')
                continue
            key = pilot, shipment.casefold()
            if key in lookup:
                errors.append(f'{name}[{i}]: duplicate source shipment ID')
            lookup[key] = row
    if set(claims23) != set(claims24):
        errors.append('V23 and V24 source shipment sets differ')
    seen_shipments: set[tuple[str, str]] = set()
    used_event_ids: set[str] = set()
    used_invoice_refs: set[str] = set()
    used_bank_txns: set[str] = set()
    verified_source_ids: set[str] = set()
    used_evidence_rows: set[tuple[str, str]] = set()
    total_paid = Decimal('0')
    all_finance_complete = True
    for i, rec in enumerate(source25):
        ctx = f'V25.shipments[{i}]'
        if not isinstance(rec, dict):
            errors.append(ctx + ': expected object')
            continue
        pilot, shipment = rec.get('pilot_id'), rec.get('economic_shipment_id')
        if pilot not in PILOTS or not ident(shipment):
            errors.append(ctx + ': invalid pilot or shipment')
            continue
        key = pilot, shipment.casefold()
        if key in seen_shipments:
            errors.append(ctx + ': duplicate V25 shipment')
        seen_shipments.add(key)
        claim, identity = claims23.get(key), claims24.get(key)
        if claim is None or identity is None:
            errors.append(ctx + ': no matching linked V23/V24 economic shipment')
            continue
        if (rec.get('physical_consignment_key') != claim.get('physical_consignment_key')
                or rec.get('physical_consignment_key') != identity.get('physical_consignment_key')):
            errors.append(ctx + ': physical consignment key changed')
        if claim.get('classification') == 'EXCLUDED':
            # Out-of-scope volumes still require a canonical record, but are never admitted.
            missing.append(ctx + ': excluded shipment requires manual exclusion adjudication')
        units = identity.get('containers')
        if not isinstance(units, list):
            errors.append(ctx + ': missing V24 physical units')
            continue
        expected = {}
        for k, unit in enumerate(units):
            if not isinstance(unit, dict) or not iso6346_valid(unit.get('container_number')):
                errors.append(ctx + f': invalid V24 container at index {k}')
                continue
            num = unit['container_number']
            if num in expected:
                errors.append(ctx + ': V24 unit duplicated inside one shipment')
            expected[num] = unit
        stats['physical_container_units'] += len(expected)
        events = rec.get('events')
        if not isinstance(events, list):
            errors.append(ctx + ': events must be an array')
            events = []
        groups: dict[tuple[str, str, str], tuple[datetime, str, str]] = {}
        for k, ev in enumerate(events):
            path = ctx + f'.events[{k}]'
            if not isinstance(ev, dict):
                errors.append(path + ': event must be object')
                continue
            stats['source_events_claimed'] += 1
            event_id = ev.get('event_id')
            if not ident(event_id):
                errors.append(path + ': invalid event ID')
            elif event_id.casefold() in used_event_ids:
                errors.append(path + ': event ID reused across shipments')
            else:
                used_event_ids.add(event_id.casefold())
            num, kind, leg = ev.get('container_number'), ev.get('event_type'), ev.get('leg')
            if num not in expected:
                errors.append(path + ': container absent in V24 source identity')
                continue
            if kind not in EVENT_ROLE:
                errors.append(path + ': unsupported custody event type')
                continue
            required_legs = ('SHA-VVO','VVO-MGD') if pilot == 'P3' else ('VVO-MGD',)
            if leg not in required_legs:
                errors.append(path + ': custody event has wrong route leg')
                continue
            if leg == 'SHA-VVO' and kind in ('TERMINAL_RELEASE','CONSIGNEE_RECEIPT'):
                errors.append(path + ': final delivery cannot occur on P3 feeder leg')
                continue
            slot = num, leg, kind
            if slot in groups:
                errors.append(path + ': duplicate container/leg/custody event')
            occurred = as_utc(ev.get('occurred_at'))
            if occurred is None or occurred.date() > cutoff:
                errors.append(path + ': invalid/future event UTC datetime')
                continue
            org, role = ev.get('actor_org_id'), ev.get('actor_role')
            if not ident(org) or role != EVENT_ROLE[kind]:
                errors.append(path + ': actor role or independent organization ID invalid')
                continue
            doc_ref = normalized_reference(ev.get('leg_document_ref'))
            if doc_ref is None:
                errors.append(path + ': missing normalized leg document reference')
                continue
            if leg == 'VVO-MGD' and doc_ref != normalized_reference(expected[num].get('bill_of_lading_ref')):
                errors.append(path + ': domestic leg document ref differs from V24 B/L')
            event_evidence = ev.get('source_evidence_id')
            if not isinstance(event_evidence, str) or not EVIDENCE_ID.fullmatch(event_evidence):
                missing.append(path + ':source_evidence_id')
            elif source_ok(event_evidence, evidence_index, evidence_dir, cutoff):
                verified_source_ids.add(event_evidence)
                if not provenance_matches(event_evidence, org, occurred.date(), evidence_index, cutoff):
                    missing.append(path + ':source_actor_or_review_time_unverified')
            else:
                missing.append(path + ':verified_source_bytes')
            locator = ev.get('source_record_locator')
            if not ident(locator):
                missing.append(path + ':independent_source_record_locator')
            elif isinstance(event_evidence, str):
                source_row = (event_evidence, locator.casefold())
                if source_row in used_evidence_rows:
                    errors.append(path + ': same source document row and event counted twice')
                used_evidence_rows.add(source_row)
            groups[slot] = occurred, org.casefold(), doc_ref

        for num, unit in expected.items():
            legs = ('SHA-VVO', 'VVO-MGD') if pilot == 'P3' else ('VVO-MGD',)
            needed = [(leg, kind) for leg in legs for kind in ('CARRIER_LOAD','CARRIER_ARRIVE')]
            needed += [('VVO-MGD','TERMINAL_RELEASE'), ('VVO-MGD','CONSIGNEE_RECEIPT')]
            if not all((num, leg, event) in groups for leg, event in needed):
                missing.append(ctx + f':incomplete_custody_{num}')
                continue
            timeline = [groups[(num, leg, kind)][0] for leg, kind in needed]
            if any(a > b for a, b in zip(timeline, timeline[1:])):
                errors.append(ctx + f':unordered_custody_chain_{num}')
            for leg in legs:
                load, arrive = groups[(num,leg,'CARRIER_LOAD')], groups[(num,leg,'CARRIER_ARRIVE')]
                if load[1] != arrive[1] or load[2] != arrive[2]:
                    errors.append(ctx + f':carrier_identity_mismatch_{num}_{leg}')
            domestic_carrier = groups[(num,'VVO-MGD','CARRIER_LOAD')][1]
            terminal_org = groups[(num,'VVO-MGD','TERMINAL_RELEASE')][1]
            receiver_org = groups[(num,'VVO-MGD','CONSIGNEE_RECEIPT')][1]
            if len({domestic_carrier,terminal_org,receiver_org}) != 3:
                errors.append(ctx + f':non_independent_carrier_terminal_consignee_{num}')
            if timeline[0].date() != parse_date(unit.get('loaded_on')) or timeline[-1].date() != parse_date(unit.get('delivered_on')):
                errors.append(ctx + f':actual_event_dates_disagree_with_V24_{num}')

        fin = rec.get('financial')
        if not isinstance(fin, dict):
            errors.append(ctx + ': financial receipt is required per economic shipment')
            continue
        inv = fin.get('invoice')
        if not isinstance(inv, dict):
            errors.append(ctx + ': invoice must be object')
            continue
        invoice_ref = normalized_reference(inv.get('invoice_ref'))
        if invoice_ref is None:
            errors.append(ctx + ': invoice reference missing')
        elif invoice_ref in used_invoice_refs:
            errors.append(ctx + ': invoice double counted across shipments')
        else:
            used_invoice_refs.add(invoice_ref)
        invoice_date = parse_date(inv.get('issued_on'))
        if invoice_date is None or invoice_date > cutoff:
            errors.append(ctx + ': invalid/future invoice date')
        if inv.get('currency') != 'RUB' or inv.get('tax_basis') != 'EXPLICIT_NET_VAT_GROSS':
            errors.append(ctx + ': explicit invoice net/VAT/gross in RUB required')
        net, vat, gross = (amount(inv.get(k)) for k in ('net_rub','vat_rub','gross_rub'))
        if None in (net,vat,gross):
            missing.append(ctx + ':complete_invoice_decimal_amounts')
            all_finance_complete = False
        elif net <= 0 or gross <= 0 or net + vat != gross:
            errors.append(ctx + ': invoice net + stated VAT must exactly equal gross')
        issuer, payer = inv.get('issuer_org_id'), inv.get('payer_org_id')
        if not ident(issuer) or not ident(payer) or issuer.casefold() == payer.casefold():
            errors.append(ctx + ': invoice issuer and payer must be distinct identified organizations')
        if inv.get('adjustment_status') != 'NONE':
            missing.append(ctx + ':credit_note_or_invoice_adjustment_clearance')
        invoice_eid = inv.get('source_evidence_id')
        if not source_ok(invoice_eid, evidence_index, evidence_dir, cutoff):
            missing.append(ctx + ':verified_invoice_source')
        else:
            verified_source_ids.add(invoice_eid)
            if not provenance_matches(invoice_eid, issuer, invoice_date, evidence_index, cutoff):
                missing.append(ctx + ':invoice_source_issuer_or_review_time_unverified')
        settlements = fin.get('bank_settlements')
        if not isinstance(settlements, list) or not settlements:
            missing.append(ctx + ':bank_settlements_not_received')
            all_finance_complete = False
            continue
        paid = Decimal('0')
        v23_payment_eid = claim.get('evidence', {}).get('payment') if isinstance(claim.get('evidence'), dict) else None
        link_to_v23_payment = False
        for j, bank in enumerate(settlements):
            label = ctx + f'.bank_settlements[{j}]'
            if not isinstance(bank, dict):
                errors.append(label + ': settlement must be an object')
                continue
            stats['bank_settlements_claimed'] += 1
            txid = normalized_reference(bank.get('transaction_ref'))
            if txid is None:
                errors.append(label + ': invalid bank transaction reference')
            elif txid in used_bank_txns:
                errors.append(label + ': bank transaction double counted across shipments')
            else:
                used_bank_txns.add(txid)
            value = amount(bank.get('amount_gross_rub'))
            if value is None or value <= 0:
                errors.append(label + ': payment must be positive exact RUB decimal')
                all_finance_complete = False
            else:
                paid += value
            if bank.get('currency') != 'RUB' or bank.get('status') != 'SETTLED':
                missing.append(label + ':actual_settled_rub_bank_record')
                all_finance_complete = False
            if bank.get('reversal_status') != 'NONE':
                missing.append(label + ':bank_reversal_or_chargeback_clearance')
                all_finance_complete = False
            when = parse_date(bank.get('settled_on'))
            if when is None or when > cutoff or (invoice_date and when < invoice_date):
                errors.append(label + ': settlement date invalid, before invoice or in future')
            bank_org = bank.get('bank_org_id')
            if not ident(bank_org) or (ident(issuer) and bank_org.casefold() == issuer.casefold()):
                errors.append(label + ': bank must be a distinct identified organization')
            payment_eid = bank.get('source_evidence_id')
            if payment_eid == v23_payment_eid:
                link_to_v23_payment = True
            if not source_ok(payment_eid, evidence_index, evidence_dir, cutoff):
                missing.append(label + ':verified_bank_source')
            else:
                verified_source_ids.add(payment_eid)
                if not provenance_matches(payment_eid, bank_org, when, evidence_index, cutoff):
                    missing.append(label + ':bank_source_actor_or_review_time_unverified')
        if not link_to_v23_payment:
            missing.append(ctx + ':bank_evidence_not_linked_to_V23_payment_evidence')
        if gross is not None:
            if paid > gross:
                errors.append(ctx + ': bank payments exceed invoice gross')
            elif paid < gross:
                missing.append(ctx + ':invoice_not_fully_settled')
                all_finance_complete = False
            else:
                total_paid += paid

    if set(claims24) != seen_shipments:
        missing.extend(f'no V25 documentary records for {p}/{s}'
                       for p, s in sorted(set(claims24) - seen_shipments))
        if seen_shipments - set(claims24):
            errors.append('V25 has documentary records with no matching V24 source')
    if not source25:
        missing.append('no source-linked real-world documentary events or payments available')
    if not source23 or not source24:
        missing.append('no linked source V23/V24 shipments available')
    stats['source_evidence_files_verified'] = len(verified_source_ids)
    status = 'INVALID' if errors else 'HOLD' if missing or warnings or not all_finance_complete else 'REVIEW'
    stats['bank_gross_paid_rub'] = str(total_paid) if status == 'REVIEW' else None
    return _fail(status, errors, missing, warnings, stats, v23_sha=h23, v24_sha=h24)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--v23', type=Path, required=True)
    p.add_argument('--v24', type=Path, required=True)
    p.add_argument('--v25', type=Path, required=True)
    p.add_argument('--evidence-index', type=Path)
    p.add_argument('--evidence-dir', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--require-review', action='store_true')
    args = p.parse_args()
    if bool(args.evidence_index) != bool(args.evidence_dir):
        p.error('Supply --evidence-index and --evidence-dir together')
    raw23, raw24 = args.v23.read_bytes(), args.v24.read_bytes()
    index = json.loads(args.evidence_index.read_text(encoding='utf-8')) if args.evidence_index else None
    report = evaluate(json.loads(raw23), raw23, json.loads(raw24), raw24,
                      json.loads(args.v25.read_bytes()), evidence_index=index, evidence_dir=args.evidence_dir)
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.write_text(text, encoding='utf-8')
    print(text, end='')
    return 2 if report['status'] == 'INVALID' else 3 if args.require_review and report['status'] != 'REVIEW' else 0


if __name__ == '__main__':
    raise SystemExit(main())

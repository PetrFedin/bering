#!/usr/bin/env python3
"""V36: verify a *self-reported* local evidence event chain, not issuer truth.

Local-chain integrity cannot certify an external bank, signed permit, or the
provenance of its initial hash. The release decision remains permanently HOLD.
"""
import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 'BERING_V36_PRIVATE_EVENT_CHAIN_V1'
NOTICE = 'SELF_REPORTED_EVENTS_NOT_EXTERNAL_ATTESTATIONS'
PARENT_SHA = '01e5061cd24259128fc9685c2d3d89cbe3120ed1'
ZERO = '0' * 64
MAX_EVENTS = 10000
MAX_INPUT_BYTES = 8 * 1024 * 1024
TOKEN = re.compile(r'^(doc|event|actor|basis)-[a-z0-9][a-z0-9_-]{2,71}$')
SHA = re.compile(r'^[0-9a-f]{64}$')
ISO_UTC = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
ACTIONS = {
    'RECEIVED', 'BYTES_MATCH_CLAIMED', 'ISSUER_CONTACT_RECORDED',
    'CONTENT_REVIEW_RECORDED', 'BANK_TIEOUT_RECORDED', 'REJECTED',
}
ROLES = {'CUSTODIAN', 'TECH_REVIEWER', 'ISSUER_LIAISON', 'FINANCE_REVIEWER', 'INDEPENDENT_REVIEWER'}
KIND = {
    'ENGINEERING_DOCUMENT', 'ECOLOGICAL_CONCLUSION', 'CONSTRUCTION_PERMIT',
    'COMMISSIONING_PERMIT', 'OD_EXTRACT', 'WAYBILL', 'RECEIPT',
    'INVOICE', 'CREDIT_NOTE', 'BANK_STATEMENT', 'INDEPENDENT_QA',
}
FIELDS = {
    'sequence', 'event_token', 'document_token', 'source_kind', 'source_sha256',
    'recorded_at_utc', 'action', 'actor_token', 'actor_role', 'basis_token',
    'previous_event_sha256', 'event_sha256',
}
ROOT_FIELDS = {'schema', 'notice', 'parent_commit_sha', 'events'}
ROLE_FOR_ACTION = {
    'RECEIVED': {'CUSTODIAN'},
    'BYTES_MATCH_CLAIMED': {'CUSTODIAN', 'TECH_REVIEWER'},
    'ISSUER_CONTACT_RECORDED': {'ISSUER_LIAISON', 'INDEPENDENT_REVIEWER'},
    'CONTENT_REVIEW_RECORDED': {'TECH_REVIEWER', 'INDEPENDENT_REVIEWER'},
    'BANK_TIEOUT_RECORDED': {'FINANCE_REVIEWER', 'INDEPENDENT_REVIEWER'},
    'REJECTED': ROLES,
}
BASIS_REQUIRED = ACTIONS - {'RECEIVED'}
BANK_KINDS = {'OD_EXTRACT', 'WAYBILL', 'RECEIPT', 'INVOICE', 'CREDIT_NOTE', 'BANK_STATEMENT'}


def is_sha(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def is_token(value, prefix):
    return isinstance(value, str) and value.startswith(prefix + '-') and TOKEN.fullmatch(value) is not None


def contains_nonfinite(value):
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, list):
        return any(contains_nonfinite(part) for part in value)
    if isinstance(value, dict):
        return any(contains_nonfinite(part) for part in value.values())
    return False


def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def hash_event(event):
    return hashlib.sha256(canonical({k: v for k, v in event.items() if k != 'event_sha256'})).hexdigest()


def issue(status, errors, chain_head=None, claims=0, docs=0, checks=0, reviews=0, anchor=False):
    return {
        'schema': 'BERING_V36_RESEARCH_REPORT_V1',
        'status': status,
        'events_with_valid_hashes': claims if not errors else None,
        'self_reported_document_tokens': docs if not errors else None,
        'self_reported_byte_check_events': checks if not errors else None,
        'self_reported_review_events': reviews if not errors else None,
        'terminal_event_hash': chain_head if not errors else None,
        'matches_user_supplied_anchor': anchor if not errors else False,
        'external_anchor_independently_authenticated': False,
        'issuer_identity_authenticated': False,
        'signature_independently_verified': False,
        'bank_transaction_independently_verified': False,
        'real_paid_incremental_40ft': None,
        'group_incremental_contribution_rub': None,
        'bering_npv_rub': None,
        'github_hosted_ci_green': False,
        'independent_investment_acceptance_complete': False,
        'P1': 'HOLD', 'P2': 'HOLD', 'P3': 'HOLD',
        'bankable_revenue_approved': False, 'investment_approved': False,
        'errors': sorted(set(errors)),
        'limitation': 'Self-reported event chains do not prove independent issuer, signature, payment, cargo additionality, or investment value.',
    }


def validate(data, expected_head=None, now=None):
    """Fail closed on malformed chronology, roles, duplicates and hash links.

    even if all valid, NEVER auto-promote beyond claimed/reported evidence.
    """
    errors = []
    if not isinstance(data, dict) or set(data) != ROOT_FIELDS:
        return issue('INVALID', ['ROOT_SCHEMA_INVALID'])
    if contains_nonfinite(data):
        return issue('INVALID', ['NONFINITE_NUMERIC_INPUT'])
    if data.get('schema') != SCHEMA or data.get('notice') != NOTICE or data.get('parent_commit_sha') != PARENT_SHA:
        errors.append('ROOT_IDENTITY_CHANGED')
    events = data.get('events')
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        return issue('INVALID', errors + ['EVENTS_NOT_LIST_OR_TOO_MANY'])
    if expected_head is not None and not is_sha(expected_head):
        errors.append('ANCHOR_FORMAT_INVALID')
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        return issue('INVALID', errors + ['INVALID_NOW_VALUE'])
    now = now.astimezone(timezone.utc)
    prev = ZERO
    previous_time = None
    ids = set()
    received = {}
    custodians = {}
    rejected = set()
    bytes_count = reviews_count = 0
    for offset, event in enumerate(events, start=1):
        if not isinstance(event, dict) or set(event) != FIELDS:
            errors.append('EVENT_FIELD_SET_INVALID')
            continue
        seq = event['sequence']
        eid = event['event_token']
        doc = event['document_token']
        actor = event['actor_token']
        action = event['action']
        role = event['actor_role']
        basis = event['basis_token']
        kind = event['source_kind']
        digest = event['source_sha256']
        stamp = event['recorded_at_utc']
        if type(seq) is not int or seq != offset:
            errors.append('NONCONSECUTIVE_SEQUENCE')
        if not is_token(eid, 'event') or eid in ids:
            errors.append('INVALID_OR_DUPLICATE_EVENT_ID')
        else:
            ids.add(eid)
        if not is_token(doc, 'doc') or not is_token(actor, 'actor'):
            errors.append('INVALID_PSEUDONYMOUS_TOKEN')
            continue
        if not isinstance(kind, str) or kind not in KIND or not is_sha(digest):
            errors.append('INVALID_DOCUMENT_TYPE_OR_DIGEST')
            continue
        if not isinstance(action, str) or action not in ACTIONS or not isinstance(role, str) or role not in ROLES:
            errors.append('INVALID_ACTION_OR_ROLE')
            continue
        if role not in ROLE_FOR_ACTION[action]:
            errors.append('ROLE_NOT_PERMITTED_FOR_ACTION')
        if action in BASIS_REQUIRED and not is_token(basis, 'basis'):
            errors.append('REVIEW_OR_CHECK_WITHOUT_BASIS')
        if action == 'RECEIVED' and basis is not None:
            errors.append('RECEIPT_MUST_NOT_IMPLY_ATTESTATION')
        if not isinstance(stamp, str) or not ISO_UTC.fullmatch(stamp):
            errors.append('INVALID_EVENT_TIME')
        else:
            try:
                at = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
                if at > now or (previous_time is not None and at < previous_time):
                    errors.append('EVENT_TIME_REVERSED_OR_IN_FUTURE')
                previous_time = at
            except ValueError:
                errors.append('INVALID_EVENT_TIME')
        if event['previous_event_sha256'] != prev:
            errors.append('BROKEN_HASH_CHAIN')
        calc = hash_event(event)
        if not is_sha(event['event_sha256']) or event['event_sha256'] != calc:
            errors.append('EVENT_HASH_MISMATCH')
        prev = calc
        if doc in rejected:
            errors.append('EVENT_AFTER_REJECTION')
        if action == 'RECEIVED':
            if doc in received:
                errors.append('DUPLICATE_DOCUMENT_RECEIPT')
            else:
                received[doc] = (kind, digest)
                custodians[doc] = actor
        else:
            if doc not in received:
                errors.append('EVENT_BEFORE_RECEIPT')
            elif received[doc] != (kind, digest):
                errors.append('DOCUMENT_IDENTITY_DRIFT')
        if action == 'BYTES_MATCH_CLAIMED':
            bytes_count += 1
        if action in {'CONTENT_REVIEW_RECORDED', 'BANK_TIEOUT_RECORDED'}:
            reviews_count += 1
            if doc in custodians and custodians[doc] == actor:
                errors.append('REVIEWER_SAME_AS_CUSTODIAN')
        if action == 'BANK_TIEOUT_RECORDED' and kind not in BANK_KINDS:
            errors.append('FINANCIAL_REVIEW_OF_NONCOMMERCIAL_SOURCE')
        if action == 'REJECTED':
            rejected.add(doc)
    if expected_head is not None and expected_head != prev:
        errors.append('SUPPLIED_ANCHOR_MISMATCH')
    return issue('INVALID' if errors else ('NO_SOURCE_EVENTS' if not events else
                 'SELF_REPORTED_CHAIN_MATCHES_SUPPLIED_ANCHOR' if expected_head is not None else
                 'SELF_REPORTED_CHAIN_UNANCHORED'), errors, chain_head=prev,
                 claims=len(events), docs=len(received), checks=bytes_count,
                 reviews=reviews_count, anchor=bool(expected_head is not None and not errors))


def private_file(repo, file_name):
    """Use only regular local_private files, no path traversal or symlinks."""
    repo = Path(repo).resolve()
    raw_root = repo / 'local_private'
    if raw_root.is_symlink() or not raw_root.is_dir():
        raise ValueError('NO_LOCAL_PRIVATE')
    path = Path(file_name)
    if not path.is_absolute():
        path = repo / path
    try:
        parts = path.relative_to(raw_root).parts
    except ValueError as ex:
        raise ValueError('OUTSIDE_LOCAL_PRIVATE') from ex
    if not parts or '..' in parts or '.' in parts:
        raise ValueError('PATH_TRAVERSAL')
    for i in range(1, len(parts)+1):
        if raw_root.joinpath(*parts[:i]).is_symlink():
            raise ValueError('SYMLINK_PATH')
    if not path.is_file() or not path.resolve().is_relative_to(raw_root.resolve()):
        raise ValueError('MISSING_PRIVATE_FILE')
    if not (0 < path.stat().st_size <= MAX_INPUT_BYTES):
        raise ValueError('PRIVATE_FILE_SIZE_INVALID')
    return path


def run(repo, ledger_path=None, expected_head=None):
    if ledger_path is None:
        return issue('NO_PRIVATE_LEDGER', [])
    try:
        path = private_file(repo, ledger_path)
        payload = json.loads(path.read_text(encoding='utf-8'))
        return validate(payload, expected_head=expected_head)
    except (OSError, ValueError, UnicodeError, TypeError, json.JSONDecodeError):
        return issue('INVALID', ['PRIVATE_LEDGER_UNREADABLE_OR_UNSAFE'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--ledger', type=Path)
    parser.add_argument('--expected-head-sha256', type=str)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = run(args.repo, args.ledger, args.expected_head_sha256)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out is not None:
        args.out.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 2 if result['status'] == 'INVALID' else 0


if __name__ == '__main__':
    raise SystemExit(main())

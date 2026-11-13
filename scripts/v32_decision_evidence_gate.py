#!/usr/bin/env python3
"""Bering V32: fail-closed evidence docket with OPTIONAL private byte-only checks.

It does not validate signatures, invoice payment, OD additionality, legal permits,
expert conclusions, or investment returns. All proof categories stay HOLD. The
optional submission is read only from git-ignored local_private, NEVER from Git.
"""
import argparse
import hashlib
import json
from pathlib import Path

DOCKET_FILE = 'data/evidence/V32_DECISION_DOCUMENT_DOCKET.json'
IDS = (
    'MLC_ENGINEERING_ORIGINAL', 'MLC_PROJECT_REVISIONS',
    'MLC_ENVIRONMENTAL_FINAL', 'MLC_GEOLOGY_TBE_REVIEW',
    'MLC_CONSTRUCTION_PERMIT', 'MLC_OPERATION_PERMIT',
    'PORT_ACTUAL_TEU_24M', 'PILOT_P1_PAID_TRAIL',
    'PILOT_P2_PAID_TRAIL', 'PILOT_P3_PAID_TRAIL',
    'GROUP_EXISTING_BASELINE', 'INDEPENDENT_INVESTMENT_QA',
)
CATEGORIES = {'ENGINEERING', 'REGULATORY', 'PERMIT', 'PORT_OPERATIONS',
              'COMMERCIAL', 'INDEPENDENT_QA'}
RECORD_KEYS = {'id', 'category', 'required_evidence', 'intended_source',
               'source_identity_verified', 'status', 'source_sha256',
               'signed_original_authenticated', 'independent_content_reviewed',
               'permission_to_use_verified', 'decision_value'}
ROOT_KEYS = {'schema', 'as_of', 'meaning', 'source_reference_sha', 'requests_sent',
             'primary_documents_received', 'private_originals_committed_to_git',
             'records', 'prior_24m_od_slots_required', 'prior_24m_od_slots_verified',
             'signed_commercial_paid_40ft', 'incremental_group_cm_rub',
             'bering_npv_rub', 'ci_green_on_single_sha',
             'independent_acceptance_complete', 'investment_approved'}
SUBMISSION_KEYS = {'docket_id', 'relative_path', 'sha256'}
MAX_BYTES = 512 * 1024 * 1024


def sha256_file(path):
    dig = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            dig.update(block)
    return dig.hexdigest()


def check_docket(docket):
    errors = []
    if not isinstance(docket, dict):
        return ['DOCKET_NOT_OBJECT']
    if set(docket) != ROOT_KEYS:
        errors.append('DOCKET_SCHEMA_DRIFT')
    expected = {
        'schema': 'V32_DECISION_DOCUMENT_DOCKET_V1',
        'as_of': '2026-11-10',
        'source_reference_sha': '3c26772a22945252df5f09328d96ca39160861bc',
        'requests_sent': 0, 'primary_documents_received': 0,
        'private_originals_committed_to_git': False,
        'prior_24m_od_slots_required': 96, 'prior_24m_od_slots_verified': 0,
        'signed_commercial_paid_40ft': None, 'incremental_group_cm_rub': None,
        'bering_npv_rub': None, 'ci_green_on_single_sha': False,
        'independent_acceptance_complete': False, 'investment_approved': False,
    }
    for key, want in expected.items():
        if docket.get(key) != want or type(docket.get(key)) is not type(want):
            errors.append('UNSUPPORTED_BASELINE_PROMOTION_' + key)
    if not isinstance(docket.get('meaning'), str) or not docket['meaning'].strip():
        errors.append('MEANING_MISSING')
    records = docket.get('records')
    if not isinstance(records, list):
        return errors + ['RECORDS_NOT_ARRAY']
    found = set()
    for row in records:
        if not isinstance(row, dict):
            errors.append('RECORD_NOT_OBJECT')
            continue
        doc_id = row.get('id')
        if not isinstance(doc_id, str):
            errors.append('INVALID_DOCUMENT_IDENTIFIER')
            continue
        if doc_id in found:
            errors.append('DUPLICATED_DOCKET_ID')
        found.add(doc_id)
        if doc_id not in IDS or set(row) != RECORD_KEYS:
            errors.append('UNKNOWN_OR_MALFORMED_RECORD')
            continue
        if row.get('category') not in CATEGORIES:
            errors.append('UNKNOWN_CATEGORY')
        for field in ('required_evidence', 'intended_source'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append('MISSING_DESCRIPTION_' + doc_id)
        if row.get('status') != 'NOT_RECEIVED_NOT_ZERO':
            errors.append('STATUS_CANNOT_BE_RETROACTIVELY_PROMOTED')
        for key in ('source_identity_verified', 'signed_original_authenticated',
                    'independent_content_reviewed', 'permission_to_use_verified'):
            if row.get(key) is not False:
                errors.append('UNSUPPORTED_PROOF_' + doc_id + '_' + key)
        for key in ('source_sha256', 'decision_value'):
            if row.get(key) is not None:
                errors.append('UNSUPPORTED_VALUE_' + doc_id + '_' + key)
    if len(records) != len(IDS) or found != set(IDS):
        errors.append('MISSING_OR_EXTRA_REQUIRED_DOCUMENTS')
    return errors


def check_local_submission(repo, manifest_path, vault_root):
    """A SHA match means only identical local bytes, *not* certified evidence."""
    errors, confirmed = [], 0
    private_root = repo / 'local_private'
    if not private_root.is_dir() or private_root.is_symlink():
        return ['PRIVATE_VAULT_NOT_AVAILABLE'], 0
    private = private_root.resolve()
    for location, purpose in ((manifest_path, 'MANIFEST'), (vault_root, 'VAULT')):
        if location.is_symlink() or not location.resolve().is_relative_to(private):
            errors.append('UNSAFE_' + purpose + '_LOCATION')
    if errors:
        return errors, 0
    if not manifest_path.is_file() or not vault_root.is_dir():
        return ['SUBMISSION_MANIFEST_OR_VAULT_MISSING'], 0
    try:
        submission = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError):
        return ['SUBMISSION_JSON_INVALID'], 0
    if not isinstance(submission, dict) or set(submission) != {'schema', 'documents'} or submission.get('schema') != 'V32_PRIVATE_BYTES_SUBMISSION_V1' or not isinstance(submission.get('documents'), list):
        return ['SUBMISSION_SHAPE_INVALID'], 0
    if len(submission['documents']) > len(IDS):
        return ['TOO_MANY_SUBMISSIONS'], 0
    seen = set()
    for row in submission['documents']:
        if not isinstance(row, dict) or set(row) != SUBMISSION_KEYS:
            errors.append('INVALID_SUBMISSION_ROW')
            continue
        doc_id, rel, claimed_hash = (row.get(k) for k in ('docket_id', 'relative_path', 'sha256'))
        if doc_id not in IDS or doc_id in seen:
            errors.append('UNEXPECTED_OR_DUPLICATE_DOCUMENT_ID')
            continue
        seen.add(doc_id)
        if not isinstance(rel, str) or not rel or not isinstance(claimed_hash, str) or len(claimed_hash) != 64 or any(c not in '0123456789abcdef' for c in claimed_hash):
            errors.append('INVALID_FILE_REFERENCE_OR_DIGEST')
            continue
        relative = Path(rel)
        if relative.is_absolute() or '..' in relative.parts or '.' in relative.parts:
            errors.append('UNSAFE_FILE_REFERENCE')
            continue
        target = vault_root / relative
        if target.is_symlink() or not target.resolve().is_relative_to(vault_root.resolve()):
            errors.append('UNSAFE_DOCUMENT_LOCATION')
            continue
        if not target.is_file():
            errors.append('DOCUMENT_BYTES_MISSING')
            continue
        if target.stat().st_size <= 0 or target.stat().st_size > MAX_BYTES:
            errors.append('DOCUMENT_BYTES_INVALID_LENGTH')
            continue
        if sha256_file(target) != claimed_hash:
            errors.append('DOCUMENT_SHA256_MISMATCH')
            continue
        confirmed += 1
    return errors, confirmed


def evaluate(repo, manifest=None, vault=None):
    repo = Path(repo).resolve()
    errors, local_count = [], None
    try:
        p = repo / DOCKET_FILE
        if p.is_symlink() or not p.is_file():
            raise ValueError('Missing or symlinked docket')
        docket = json.loads(p.read_text(encoding='utf-8'))
        errors.extend(check_docket(docket))
    except (OSError, ValueError, UnicodeError):
        errors.append('DOCKET_LOAD_FAILED')
    if (manifest is None) != (vault is None):
        errors.append('SUBMISSION_MANIFEST_AND_VAULT_MUST_BE_PAIRED')
    elif manifest is not None:
        submission_errors, local_count = check_local_submission(repo, Path(manifest), Path(vault))
        errors.extend(submission_errors)
    invalid = bool(errors)
    return {
        'status': 'INVALID' if invalid else 'HOLD',
        'source_snapshot': '2026-11-10',
        'required_document_categories': len(IDS),
        'received_approved_originals_in_repo': 0,
        'source_verified_group_months': 0,
        'required_group_months': 96,
        'private_documents_with_recomputed_matching_sha256': local_count,
        'local_sha_check_is_signature_verification': False,
        'local_sha_check_is_payment_verification': False,
        'ecological_final_signed_confirmed': False,
        'engineering_design_versions_reconciled': False,
        'paid_incremental_40ft': None,
        'group_incremental_cm_rub': None,
        'bering_npv_rub': None,
        'github_hosted_ci_green': False,
        'independent_engineering_financial_acceptance': False,
        'P1': 'HOLD', 'P2': 'HOLD', 'P3': 'HOLD',
        'bankable_revenue_approved': False,
        'investment_approved': False,
        'errors': errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--private-manifest', type=Path)
    parser.add_argument('--private-vault', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    report = evaluate(args.repo, args.private_manifest, args.private_vault)
    text = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
    if args.out:
        args.out.write_text(text, encoding='utf-8')
    print(text, end='')
    return 2 if report['status'] == 'INVALID' else 0


if __name__ == '__main__':
    raise SystemExit(main())

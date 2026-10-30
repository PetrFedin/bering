#!/usr/bin/env python3
"""V22 original-source import: verify ZIP + 42 originals before optional local copy.

This is not contract authentication, a legal rights check, or proof of remote GitHub
preservation. No existing file is overwritten. Requires Python 3.11+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path

PACK_SHA256 = '284f14b29b3849c03450ae0d5b77eba5632696fc066750e4ed5f8792543a7f98'
MANIFEST_SHA256 = 'cc97918f23c8590189e078f9e09a54682404943bfc675a4b47e1c334702b945a'
MANIFEST_PATH = 'provenance/V20_IMPORT_SHA256.json'
LEDGER_PATH = 'provenance/V20_IMPORT_SHA256SUMS.txt'
MAX_MEMBER_BYTES = 30 * 1024 * 1024
MAX_TOTAL_BYTES = 160 * 1024 * 1024
SHA_RE = re.compile(r'[0-9a-f]{64}\Z')
ALLOWED_ROOTS = ('archive/originals/', 'data/registries/', 'audit/',
                 'scripts/audits/', 'tools/', 'provenance/')


class ImportBlocked(Exception):
    """Fail closed on damaged or unapproved source material."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_path(path: object) -> bool:
    if not isinstance(path, str) or not path or '\\' in path or '\x00' in path:
        return False
    if path.startswith('/') or '//' in path or ':' in path:
        return False
    return all(part not in ('', '.', '..') for part in path.split('/'))


def load_ledger(path: Path, count: int) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  (\S.*)', line)
        if not match or not safe_path(match[2]) or match[2] in entries:
            raise ImportBlocked('Invalid or duplicate entry in SHA256SUMS')
        entries[match[2]] = match[1]
    if len(entries) != count:
        raise ImportBlocked(f'Expected {count} ledger entries, got {len(entries)}')
    return entries


def read_zip_members(zf: zipfile.ZipFile, prefix: str) -> tuple[dict[str, zipfile.ZipInfo], list[str]]:
    if prefix and (not prefix.endswith('/') or not safe_path(prefix[:-1])):
        raise ImportBlocked('Unsafe ZIP prefix; use an ordinary folder name ending in /')
    members: dict[str, zipfile.ZipInfo] = {}
    ignored = []
    total = 0
    seen_raw: set[str] = set()
    for info in zf.infolist():
        raw_name = info.filename
        if raw_name in seen_raw:
            raise ImportBlocked(f'Duplicate ZIP entry: {raw_name}')
        seen_raw.add(raw_name)
        raw_path = raw_name[:-1] if info.is_dir() else raw_name
        if not safe_path(raw_path):
            raise ImportBlocked(f'Unsafe ZIP member path: {raw_name!r}')
        mode = stat.S_IFMT(info.external_attr >> 16)
        if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ImportBlocked(f'ZIP symlink or special entry: {raw_name!r}')
        if info.is_dir():
            continue
        if info.file_size > MAX_MEMBER_BYTES:
            raise ImportBlocked(f'ZIP member above size limit: {raw_name}')
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise ImportBlocked('ZIP uncompressed size exceeds limit')
        if prefix and not raw_name.startswith(prefix):
            ignored.append(raw_name)
            continue
        mapped = raw_name[len(prefix):]
        if not safe_path(mapped) or mapped in members:
            raise ImportBlocked(f'Duplicate or unsafe mapped file: {raw_name}')
        members[mapped] = info
    return members, ignored


def inspect_pack(repo: Path, pack: Path, *, pack_sha: str = PACK_SHA256,
                 manifest_sha: str = MANIFEST_SHA256, expected_count: int = 42,
                 prefix: str = '') -> tuple[dict, dict[str, bytes]]:
    root = repo.resolve(strict=True)
    if not (root / '.git').exists():
        raise ImportBlocked('Target directory is not a Git checkout')
    if not all(isinstance(s, str) and SHA_RE.fullmatch(s) for s in (pack_sha, manifest_sha)):
        raise ImportBlocked('Invalid expected SHA-256')
    observed_pack_sha = sha256_file(pack)
    if observed_pack_sha != pack_sha:
        raise ImportBlocked('Wrong original import pack SHA-256')
    ledger = load_ledger(root / LEDGER_PATH, expected_count)
    with zipfile.ZipFile(pack) as zf:
        members, ignored = read_zip_members(zf, prefix)
        if MANIFEST_PATH not in members:
            raise ImportBlocked('Missing pinned JSON manifest from ZIP')
        raw_manifest = zf.read(members[MANIFEST_PATH])
        if sha256_bytes(raw_manifest) != manifest_sha:
            raise ImportBlocked('Import manifest SHA-256 mismatch')
        manifest = json.loads(raw_manifest)
        entries = manifest.get('files') if isinstance(manifest, dict) else None
        if not isinstance(entries, list) or len(entries) != expected_count:
            raise ImportBlocked('Unexpected number of entries in import manifest')
        expected: dict[str, tuple[str, int]] = {}
        for row in entries:
            if not isinstance(row, dict):
                raise ImportBlocked('Invalid manifest entry type')
            path, digest, size = row.get('path'), row.get('sha256'), row.get('bytes')
            if (not safe_path(path) or not path.startswith(ALLOWED_ROOTS)
                    or path in expected):
                raise ImportBlocked(f'Unsafe/duplicate original path: {path!r}')
            if (not isinstance(digest, str) or not SHA_RE.fullmatch(digest)
                    or not isinstance(size, int) or isinstance(size, bool) or size < 0):
                raise ImportBlocked(f'Invalid digest or size: {path!r}')
            expected[path] = digest, size
        if set(expected) != set(ledger):
            raise ImportBlocked('JSON manifest paths differ from pinned SHA256SUMS ledger')
        if set(expected) - set(members):
            raise ImportBlocked(f'Missing archive files: {sorted(set(expected) - set(members))[:3]}')
        verified: dict[str, bytes] = {}
        for path, (digest, size) in expected.items():
            if ledger[path] != digest or members[path].file_size != size:
                raise ImportBlocked(f'Ledger/hash/size mismatch: {path}')
            content = zf.read(members[path])
            if len(content) != size or sha256_bytes(content) != digest:
                raise ImportBlocked(f'Changed original: {path}')
            verified[path] = content
        verified[MANIFEST_PATH] = raw_manifest
        ignored.extend(n for n in members if n not in expected and n != MANIFEST_PATH)

    for path, content in verified.items():
        dest = root / path
        parent = dest.parent
        while parent != root:
            if parent.is_symlink():
                raise ImportBlocked(f'Symlink in destination path: {path}')
            parent = parent.parent
        if dest.is_symlink() or (dest.exists() and
            (not dest.is_file() or sha256_file(dest) != sha256_bytes(content))):
            raise ImportBlocked(f'Refusing to overwrite changed or unsafe file: {path}')
    report = {
        'status': 'VERIFIED_PACK_NOT_IMPORTED', 'zip_sha256': observed_pack_sha,
        'manifest_sha256': sha256_bytes(raw_manifest), 'verified_origins': len(expected),
        'identical_present': sum((root / p).is_file() for p in verified),
        'new_files_pending': sum(not (root / p).exists() for p in verified),
        'ignored_unlisted_files': sorted(ignored), 'github_remote_verified': False,
        'contracts_verified': False, 'redistribution_rights_verified_by_software': False,
        'financial_recalculation_done': False, 'investment_approved': False,
    }
    return report, verified


def import_pack(repo: Path, pack: Path, *, apply: bool = False,
                approval: Path | None = None, pack_sha: str = PACK_SHA256,
                manifest_sha: str = MANIFEST_SHA256, expected_count: int = 42,
                prefix: str = '') -> dict:
    root = repo.resolve(strict=True)
    report, contents = inspect_pack(root, pack, pack_sha=pack_sha,
        manifest_sha=manifest_sha, expected_count=expected_count, prefix=prefix)
    if not apply:
        return report
    branch = subprocess.run(['git', '-C', str(root), 'symbolic-ref', '--quiet', '--short', 'HEAD'],
                            capture_output=True, text=True, check=False)
    if branch.returncode or branch.stdout.strip() in ('main', 'master', ''):
        raise ImportBlocked('Import requires a named topic branch, not main/master or detached HEAD')
    if approval is None or not approval.is_file():
        raise ImportBlocked('Import requires an explicit out-of-repository approval JSON')
    if approval.resolve().is_relative_to(root):
        raise ImportBlocked('Approval JSON must be kept outside the Git checkout')
    attestation = json.loads(approval.read_text(encoding='utf-8'))
    if (not isinstance(attestation, dict) or
        any(attestation.get(k) is not True for k in
            ('approved', 'redistribution_rights_reviewed', 'personal_data_screened')) or
        attestation.get('zip_sha256') != pack_sha or
        not isinstance(attestation.get('reviewer'), str) or not attestation['reviewer'].strip()):
        raise ImportBlocked('Rights/privacy attestation missing or inconsistent')
    pending = {p: data for p, data in contents.items() if not (root / p).exists()}
    created: list[Path] = []
    with tempfile.TemporaryDirectory(prefix='.v22-stage-', dir=root) as folder:
        temp = Path(folder)
        for index, (path, data) in enumerate(pending.items()):
            staged = temp / str(index)
            staged.write_bytes(data)
            if sha256_file(staged) != sha256_bytes(data):
                raise ImportBlocked(f'Staging verification failed: {path}')
        try:
            for index, (path, data) in enumerate(pending.items()):
                dest = root / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.parent.resolve().is_relative_to(root) or dest.is_symlink():
                    raise ImportBlocked(f'Unsafe apply destination: {path}')
                with dest.open('xb') as output, (temp / str(index)).open('rb') as src:
                    created.append(dest)
                    shutil.copyfileobj(src, output)
                if sha256_file(dest) != sha256_bytes(data):
                    raise ImportBlocked(f'Post-write verification failed: {path}')
        except (OSError, ImportBlocked):
            for path in reversed(created):
                path.unlink(missing_ok=True)
            raise
    report.update(status='IMPORTED_LOCALLY_UNCOMMITTED', new_files_written=len(created),
                  git_commit_verified=False, github_remote_verified=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--zip', type=Path, required=True)
    parser.add_argument('--prefix', default='')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--approval-json', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        report = import_pack(args.repo, args.zip, apply=args.apply,
                             approval=args.approval_json, prefix=args.prefix)
        status = 0
    except (ImportBlocked, OSError, ValueError, TypeError, KeyError,
            zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        report = {'status': 'BLOCKED', 'reason': str(exc), 'github_remote_verified': False,
                  'contracts_verified': False, 'investment_approved': False}
        status = 1
    formatted = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.write_text(formatted, encoding='utf-8')
    print(formatted)
    return status


if __name__ == '__main__':
    raise SystemExit(main())

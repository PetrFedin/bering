"""V22 synthetic-source regression tests. No confidential originals needed."""
from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.audits.import_originals_v22 import (
    ImportBlocked, import_pack, inspect_pack, MANIFEST_PATH, LEDGER_PATH,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'audit/test', str(self.repo)], check=True)
        self.sources = {
            'archive/originals/V08/example.xlsx': b'XLSX-FAKE-FIXTURE-A',
            'audit/example.json': b'{"tested":true}\n',
        }

    def bundle(self, *, manifest_sources=None, zip_sources=None, extra=None,
               prefix='', ledger_sources=None, duplicate=None):
        manifest_sources = self.sources if manifest_sources is None else manifest_sources
        zip_sources = manifest_sources if zip_sources is None else zip_sources
        ledger_sources = manifest_sources if ledger_sources is None else ledger_sources
        entries = [{'path': p, 'sha256': sha(v), 'bytes': len(v)}
                   for p, v in manifest_sources.items()]
        manifest = json.dumps({'files': entries}, separators=(',', ':')).encode()
        ledger_file = self.repo / LEDGER_PATH
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        ledger_file.write_text(
            ''.join(f'{sha(v)}  {p}\n' for p, v in ledger_sources.items()), encoding='utf-8')
        pack = self.root / 'pack.zip'
        with zipfile.ZipFile(pack, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(prefix + MANIFEST_PATH, manifest)
            for p, data in zip_sources.items():
                zf.writestr(prefix + p, data)
            if extra:
                for name, contents in extra.items():
                    zf.writestr(name, contents)
            if duplicate:
                zf.writestr(prefix + duplicate, zip_sources[duplicate])
        return pack, sha(pack.read_bytes()), sha(manifest)

    def inspect(self, pack, pack_sha, manifest_sha, *, prefix=''):
        return inspect_pack(
            self.repo, pack, pack_sha=pack_sha, manifest_sha=manifest_sha,
            expected_count=2, prefix=prefix)

    def apply(self, pack, pack_sha, manifest_sha, *, approval=None, apply=False):
        return import_pack(
            self.repo, pack, pack_sha=pack_sha, manifest_sha=manifest_sha,
            expected_count=2, approval=approval, apply=apply)

    def approval(self, *, approved=True, inside=False, zip_sha=None):
        path = (self.repo if inside else self.root) / 'approval.json'
        path.write_text(json.dumps({
            'approved': approved,
            'redistribution_rights_reviewed': True,
            'personal_data_screened': True,
            'zip_sha256': zip_sha,
            'reviewer': 'Unit Test Reviewer',
        }), encoding='utf-8')
        return path

    def test_dry_run_reports_no_github_or_contract_proof(self):
        args = self.bundle()
        report, contents = self.inspect(*args)
        self.assertEqual(report['status'], 'VERIFIED_PACK_NOT_IMPORTED')
        self.assertEqual(report['verified_origins'], 2)
        self.assertEqual(report['new_files_pending'], 3)
        self.assertFalse(report['github_remote_verified'])
        self.assertFalse(report['contracts_verified'])
        self.assertEqual(set(contents), {*self.sources, MANIFEST_PATH})
        self.assertFalse((self.repo / next(iter(self.sources))).exists())

    def test_valid_import_is_local_and_no_overwrites(self):
        args = self.bundle()
        approval = self.approval(zip_sha=args[1])
        report = self.apply(*args, approval=approval, apply=True)
        self.assertEqual(report['status'], 'IMPORTED_LOCALLY_UNCOMMITTED')
        self.assertEqual(report['new_files_written'], 3)
        self.assertFalse(report['github_remote_verified'])
        self.assertEqual(
            (self.repo / next(iter(self.sources))).read_bytes(),
            next(iter(self.sources.values())))
        self.assertEqual(
            self.apply(*args, approval=approval, apply=True)['new_files_written'], 0)

    def test_wrong_zip_hash_fails(self):
        pack, _, md = self.bundle()
        with self.assertRaisesRegex(ImportBlocked, 'Wrong original import pack'):
            self.inspect(pack, '0' * 64, md)

    def test_wrong_manifest_hash_fails(self):
        pack, digest, _ = self.bundle()
        with self.assertRaisesRegex(ImportBlocked, 'manifest SHA-256 mismatch'):
            self.inspect(pack, digest, '0' * 64)

    def test_archive_content_mismatch_ledger_fails(self):
        altered = dict(self.sources)
        altered['audit/example.json'] = b'X' * len(self.sources['audit/example.json'])
        pack, digest, md = self.bundle(zip_sources=altered)
        with self.assertRaisesRegex(ImportBlocked, 'Changed original'):
            self.inspect(pack, digest, md)

    def test_missing_zip_member_fails(self):
        missing = dict(self.sources)
        missing.pop('audit/example.json')
        pack, digest, md = self.bundle(zip_sources=missing)
        with self.assertRaisesRegex(ImportBlocked, 'Missing archive files'):
            self.inspect(pack, digest, md)

    def test_extra_archive_file_only_reported_ignored(self):
        pack, digest, md = self.bundle(extra={'extra/readme.txt': b'ignored'})
        report, _ = self.inspect(pack, digest, md)
        self.assertIn('extra/readme.txt', report['ignored_unlisted_files'])

    def test_zip_path_traversal_fails(self):
        pack, digest, md = self.bundle(extra={'../escape.txt': b'attack'})
        with self.assertRaisesRegex(ImportBlocked, 'Unsafe ZIP member path'):
            self.inspect(pack, digest, md)

    def test_zip_duplicate_member_fails(self):
        pack, digest, md = self.bundle(duplicate='audit/example.json')
        with self.assertRaisesRegex(ImportBlocked, 'Duplicate ZIP entry'):
            self.inspect(pack, digest, md)

    def test_zip_symlink_fails(self):
        pack, _, md = self.bundle()
        with zipfile.ZipFile(pack, 'a') as zf:
            info = zipfile.ZipInfo('archive/originals/link')
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, '/etc/passwd')
        with self.assertRaisesRegex(ImportBlocked, 'symlink or special'):
            self.inspect(pack, sha(pack.read_bytes()), md)

    def test_manifest_paths_cannot_escape_repo(self):
        unsafe = dict(self.sources)
        unsafe['archive/originals/../escape'] = b'danger'
        unsafe.pop('audit/example.json')
        pack, digest, md = self.bundle(manifest_sources=unsafe, zip_sources=unsafe)
        with self.assertRaises(ImportBlocked):
            self.inspect(pack, digest, md)

    def test_ledger_mismatch_fails(self):
        altered_ledger = dict(self.sources)
        altered_ledger['audit/example.json'] = b'altered ledger data'
        pack, digest, md = self.bundle(ledger_sources=altered_ledger)
        with self.assertRaisesRegex(ImportBlocked, 'Ledger/hash/size mismatch'):
            self.inspect(pack, digest, md)

    def test_preexisting_changed_file_cannot_be_overwritten(self):
        args = self.bundle()
        dest = self.repo / 'audit/example.json'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'other')
        with self.assertRaisesRegex(ImportBlocked, 'Refusing to overwrite'):
            self.inspect(*args)

    def test_symlink_parent_rejected(self):
        args = self.bundle()
        (self.repo / 'archive').mkdir()
        (self.repo / 'archive/originals').symlink_to(
            self.root, target_is_directory=True)
        with self.assertRaisesRegex(ImportBlocked, 'Symlink in destination path'):
            self.inspect(*args)

    def test_apply_requires_attestation(self):
        args = self.bundle()
        with self.assertRaisesRegex(ImportBlocked, 'requires an explicit'):
            self.apply(*args, apply=True)
        self.assertFalse((self.repo / 'audit/example.json').exists())

    def test_attestation_cannot_be_inside_repository(self):
        args = self.bundle()
        approval = self.approval(inside=True, zip_sha=args[1])
        with self.assertRaisesRegex(ImportBlocked, 'outside the Git checkout'):
            self.apply(*args, apply=True, approval=approval)

    def test_false_attestation_rejected(self):
        args = self.bundle()
        approval = self.approval(approved=False, zip_sha=args[1])
        with self.assertRaisesRegex(ImportBlocked, 'attestation missing'):
            self.apply(*args, apply=True, approval=approval)

    def test_wrong_attested_zip_rejected(self):
        args = self.bundle()
        approval = self.approval(zip_sha='0' * 64)
        with self.assertRaisesRegex(ImportBlocked, 'attestation missing'):
            self.apply(*args, apply=True, approval=approval)

    def test_main_branch_apply_rejected(self):
        args = self.bundle()
        subprocess.run(
            ['git', '-C', str(self.repo), 'symbolic-ref', 'HEAD', 'refs/heads/main'],
            check=True)
        with self.assertRaisesRegex(ImportBlocked, 'topic branch'):
            self.apply(*args, apply=True, approval=self.approval(zip_sha=args[1]))

    def test_nested_prefix_supported(self):
        pack, digest, md = self.bundle(prefix='package_root/')
        report, _ = self.inspect(pack, digest, md, prefix='package_root/')
        self.assertEqual(report['verified_origins'], 2)

    def test_invalid_expected_hash_rejected(self):
        pack, _, md = self.bundle()
        with self.assertRaisesRegex(ImportBlocked, 'Invalid expected SHA-256'):
            self.inspect(pack, 'not a digest', md)


if __name__ == '__main__':
    unittest.main()

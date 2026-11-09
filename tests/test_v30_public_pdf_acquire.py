"""V30 source acquisition remains rate-limit-safe and non-network in unit tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from v30_public_pdf_acquire import run, select, MANIFEST  # noqa: E402

class PublicPdfAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))["documents"]
        self.pdf = self.rows[0]
        self.name = self.pdf["path"].rsplit("/", 1)[-1]

    def test_frozen_manifest_contains_fifty_two_source_paths(self):
        self.assertEqual(len(self.rows), 52)

    def test_exact_document_select(self):
        self.assertEqual(select(self.rows, self.pdf["path"]), self.pdf)

    def test_basename_select(self):
        self.assertEqual(select(self.rows, self.name), self.pdf)

    def test_unknown_source_fails(self):
        with self.assertRaises(ValueError):
            select(self.rows, "imaginary_2026_approved.pdf")

    def test_duplicate_name_without_full_path_fails(self):
        with self.assertRaises(ValueError):
            select([self.pdf, {**self.pdf, "path": "/different/" + self.name}], self.name)

    def test_dry_run_does_not_download_or_certify(self):
        outdir = "local_private/v30_unit_test_no_network"
        r = run(ROOT, self.name, outdir, dry_run=True)
        self.assertEqual(r["status"], "DRY_RUN_NO_NETWORK")
        self.assertFalse(r["downloaded"])
        self.assertIsNone(r["actual_sha256"])
        self.assertFalse(r["approved_2026_design_revision_authenticated"])
        self.assertFalse(r["source_proves_bering_paid_cargo"])
        self.assertFalse((ROOT / outdir).exists())

    def test_outside_project_private_tree_fails(self):
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(ValueError):
                run(ROOT, self.name, Path(other), dry_run=True)

    def test_cli_list_without_network(self):
        run_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/v30_public_pdf_acquire.py"), "--repo", str(ROOT), "--list"],
            capture_output=True, text=True, cwd=ROOT, check=False
        )
        self.assertEqual(run_result.returncode, 0, run_result.stderr)
        self.assertEqual(len(run_result.stdout.splitlines()), 52)

    def test_cli_invalid_filename_fails_closed(self):
        run_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/v30_public_pdf_acquire.py"), "--repo", str(ROOT),
             "--name", "2026_expertise_final_signed.pdf", "--dry-run"],
            capture_output=True, text=True, cwd=ROOT, check=False
        )
        self.assertEqual(run_result.returncode, 2)
        self.assertFalse(json.loads(run_result.stdout)["source_proves_bering_paid_cargo"])

if __name__ == "__main__":
    unittest.main()

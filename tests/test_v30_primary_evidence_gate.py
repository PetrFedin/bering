"""V30 test: documentary receipt is not a bankable shipment or approved design."""
import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v30_primary_evidence_gate as gate  # noqa: E402


class PrimaryEvidenceGateTests(unittest.TestCase):
    def original(self):
        report = gate.evaluate(ROOT)
        self.assertEqual(report["status"], "HOLD", report["errors"])
        self.assertFalse(report["bankable_revenue_approved"])
        self.assertFalse(report["investment_approved"])
        return report

    def modified(self, input_name, change):
        rel = gate.INPUTS[input_name]
        before = gate.read_in_repo
        text = before(ROOT, rel)
        if input_name == "od_matrix":
            text = change(text)
        else:
            data = json.loads(text)
            change(data)
            text = json.dumps(data, ensure_ascii=False)
        def fake(repo, candidate):
            return text if candidate == rel else before(repo, candidate)
        with mock.patch.object(gate, "read_in_repo", side_effect=fake):
            return gate.evaluate(ROOT)

    def assert_invalid(self, input_name, change):
        report = self.modified(input_name, change)
        self.assertEqual(report["status"], "INVALID", report["errors"])
        self.assertFalse(report["bankable_revenue_approved"])
        self.assertFalse(report["investment_approved"])

    def test_baseline_holds_even_when_public_sha_receipt_matches(self):
        report = self.original()
        self.assertEqual(report["public_source_documents_in_owner_manifest"], 52)
        self.assertEqual(report["selected_public_pdf_downloads"], 10)
        self.assertEqual(report["claimed_digest_matches_in_versioned_receipt"], 4)
        self.assertIsNone(report["source_bytes_recomputed_at_runtime"])
        self.assertEqual(report["source_scope_status"], "RECEIPT_ONLY_BYTES_NOT_RECOMPUTED")

    def test_96_source_missing_months_are_not_zeros(self):
        r = self.original()
        self.assertEqual(r["od_required_group_months"], 96)
        self.assertEqual(r["od_authenticated_group_months"], 0)
        self.assertIsNone(r["real_new_paid_40ft"])
        self.assertIsNone(r["bering_npv_rub"])

    def test_document_incorrectly_marked_approved(self):
        self.assert_invalid("page_review", lambda x: x.__setitem__(
            "official_2026_positive_expertise_revisions_match_verified", True))

    def test_geographical_error_not_proven_in_approved_revision(self):
        self.original()
        self.assert_invalid("page_review", lambda x: x["findings"][0].__setitem__(
            "verified_in_approved_oct2026_revision", True))

    def test_misreported_public_bytes_digest(self):
        self.assert_invalid("byte_receipt", lambda x: x["files"][1].__setitem__(
            "byte_sha256", "f" * 64))

    def test_fake_download_success(self):
        self.assert_invalid("byte_receipt", lambda x: x["files"][0].update({
            "downloaded": True, "sha256_matches_owner": True,
            "byte_length_matches_owner": True,
        }))

    def test_duplicate_public_pdf_receipt(self):
        self.assert_invalid("byte_receipt", lambda x: x["files"].append(
            copy.deepcopy(x["files"][0])))

    def test_source_manifest_tampering_is_invalid(self):
        self.assert_invalid("owner_index", lambda x: x["documents"][0].__setitem__(
            "sha256_from_public_api", "0" * 64))

    def test_pilot_fictional_bank_settlement(self):
        self.assert_invalid("commercial_intake", lambda x: x.__setitem__(
            "verified_bank_settlements", 1))

    def test_pilot_fictional_revenue(self):
        self.assert_invalid("commercial_intake", lambda x: x.__setitem__(
            "bering_npv_rub", 100000))

    def test_pilot_fictional_sent_request(self):
        self.assert_invalid("commercial_intake", lambda x: x.__setitem__(
            "requests_sent", True))

    def test_zero_od_is_not_a_verified_value(self):
        def mutate(text):
            rows = list(csv.DictReader(io.StringIO(text)))
            rows[0]["physical_containers_40ft"] = "0"
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            return stream.getvalue()
        self.assert_invalid("od_matrix", mutate)

    def test_od_duplicate_rejected(self):
        def mutate(text):
            return text + text.splitlines()[1] + "\n"
        self.assert_invalid("od_matrix", mutate)

    def test_ci_promotion_to_green_rejected(self):
        self.assert_invalid("ci_diagnostic", lambda x: x.__setitem__(
            "github_hosted_ci_green", True))

    def test_billing_unknown_must_remain_unknown(self):
        self.assert_invalid("ci_diagnostic", lambda x: x.__setitem__(
            "github_hosted_runner_allocation_cause", "BILLING_CONFIRMED"))

    def test_no_local_directory_does_not_create_a_source_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            r = gate.evaluate(ROOT, Path(temp))
            self.assertEqual(r["status"], "HOLD", r["errors"])
            self.assertEqual(r["source_bytes_recomputed_at_runtime"], 0)
            self.assertEqual(r["source_files_not_locally_present"], 10)

    def test_local_bytes_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "Том 1.2_П-25-2025-00-ПЗ-1.2.pdf").write_bytes(b"FAKE-PDF")
            r = gate.evaluate(ROOT, folder)
            self.assertEqual(r["status"], "INVALID")
            self.assertTrue(any("Local source bytes" in x for x in r["errors"]))
            self.assertFalse(r["investment_approved"])

    def test_cli_cannot_invent_investment_approval(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/v30_primary_evidence_gate.py"),
             "--repo", str(ROOT)],
            capture_output=True, text=True, cwd=ROOT, check=False
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "HOLD", result["errors"])
        self.assertIsNone(result["new_paid_40ft"] if "new_paid_40ft" in result
                          else result["real_new_paid_40ft"])
        self.assertFalse(result["investment_approved"])


if __name__ == "__main__":
    unittest.main()

"""Source-claim stage and fail-closed immutability checks for Bering V29."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from v29_timeline_claim_guard import CLAIMS, evaluate  # noqa: E402

REGISTER = ROOT / "data/public/V29_COMPETITOR_TIMELINE_CLAIMS.json"

class StageClaimsTests(unittest.TestCase):
    def setUp(self):
        self.original = json.loads(REGISTER.read_text(encoding="utf-8"))

    def test_original_remains_research_context_only(self):
        report = evaluate(self.original)
        self.assertEqual(report["status"], "RESEARCH_CONTEXT_ONLY", report["errors"])
        self.assertEqual(report["reviewed_claim_rows"], len(CLAIMS))
        self.assertEqual(report["P1"], "HOLD")
        self.assertIsNone(report["new_paid_bering_40ft"])
        self.assertIsNone(report["operator_nov_2026_actual_containers"])
        self.assertIsNone(report["verified_commission_year"])
        self.assertIsNone(report["group_incremental_cm_rub"])
        self.assertIsNone(report["bering_npv_rub"])
        self.assertFalse(report["bankable_revenue_approved"])
        self.assertFalse(report["investment_approved"])

    def assert_invalid(self, altered):
        report = evaluate(altered)
        self.assertEqual(report["status"], "INVALID")
        self.assertFalse(report["investment_approved"])
        self.assertFalse(report["bankable_revenue_approved"])
        self.assertIsNone(report["design_oct_2026_teu_per_year"])

    def test_independent_claims_not_added(self):
        self.assertIsNone(evaluate(self.original)["design_versions_sum_teu_per_year"])

    def test_reordering_claims_is_semantically_safe(self):
        self.original["claims"].reverse()
        self.assertEqual(evaluate(self.original)["status"], "RESEARCH_CONTEXT_ONLY")

    def test_duplicate_claim_is_invalid(self):
        self.original["claims"].append(copy.deepcopy(self.original["claims"][0]))
        self.assert_invalid(self.original)

    def test_deleted_claim_is_invalid(self):
        self.original["claims"].pop()
        self.assert_invalid(self.original)

    def test_extra_claim_is_invalid(self):
        extra = copy.deepcopy(self.original["claims"][0])
        extra["id"] = "FORGED_COMPLETED_TERMINAL"
        self.original["claims"].append(extra)
        self.assert_invalid(self.original)

    def test_each_pinned_source_claim_is_immutable(self):
        for i, row in enumerate(self.original["claims"]):
            for field, replacement in (
                ("value", "777777"), ("stage", "COMMISSIONED"),
                ("source_url", "https://example.com/forged"),
                ("entity_scope", "BERING_PROJECT"),
                ("measure", "ACTUAL_SHIPMENTS")
            ):
                with self.subTest(id=row["id"], field=field):
                    candidate = copy.deepcopy(self.original)
                    candidate["claims"][i][field] = replacement
                    self.assert_invalid(candidate)

    def test_all_claims_reject_promotion_flags(self):
        for i, row in enumerate(self.original["claims"]):
            for key in (
                "source_document_bytes_authenticated",
                "physical_commissioning_verified",
                "actual_paid_bering_cargo_verified"
            ):
                with self.subTest(id=row["id"], key=key):
                    candidate = copy.deepcopy(self.original)
                    candidate["claims"][i][key] = True
                    self.assert_invalid(candidate)

    def test_controls_are_not_overridable(self):
        for key in self.original["controls"]:
            with self.subTest(key=key):
                candidate = copy.deepcopy(self.original)
                candidate["controls"][key] = not candidate["controls"][key]
                self.assert_invalid(candidate)

    def test_unknown_actual_proof_cannot_be_smuggled(self):
        self.original["actual_bering_40ft"] = 120000
        self.assert_invalid(self.original)

    def test_claim_field_injection_fails(self):
        self.original["claims"][1]["commissioned_in_service"] = True
        self.assert_invalid(self.original)

    def test_corrupted_input_fails_without_approval(self):
        for data in (None, [], 1, "foo", {}, {"claims": []}):
            with self.subTest(value=data):
                self.assert_invalid(data)

    def test_cli_fail_closed_on_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "bad.json"
            bad.write_text("{not-json", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/v29_timeline_claim_guard.py"),
                 "--register", str(bad)],
                capture_output=True, text=True, cwd=ROOT, check=False
            )
            self.assertEqual(result.returncode, 2)
            output = json.loads(result.stdout)
            self.assertEqual(output["status"], "INVALID")
            self.assertFalse(output["investment_approved"])

if __name__ == "__main__":
    unittest.main()

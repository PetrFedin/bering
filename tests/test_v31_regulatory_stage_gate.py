"""Regression against promotion of public news or unallocated runners into bankability."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from v31_regulatory_stage_gate import evaluate  # noqa: E402

REG = json.loads((ROOT / 'data/public/V31_REGULATORY_STAGE_CHAIN.json').read_text())
CI = json.loads((ROOT / 'quality/V31_GITHUB_PRE_RUNNER_ANNOTATIONS.json').read_text())


class RegulatoryAndCiTests(unittest.TestCase):
    def test_baseline_is_only_research_context(self):
        result = evaluate(REG, CI)
        self.assertEqual(result['status'], 'RESEARCH_CONTEXT_ONLY', result['errors'])
        self.assertFalse(result['investment_approved'])
        self.assertIsNone(result['environmental_expertise_final_result'])
        self.assertIsNone(result['new_paid_bering_40ft'])
        self.assertIsNone(result['bering_npv_rub'])
        self.assertIsNone(result['capacity_sum_teu_per_year'])

    def reject(self, change, target='reg'):
        reg, ci = copy.deepcopy(REG), copy.deepcopy(CI)
        change(reg if target == 'reg' else ci)
        result = evaluate(reg, ci)
        self.assertEqual(result['status'], 'INVALID', result['errors'])
        self.assertFalse(result['bankable_revenue_approved'])
        self.assertFalse(result['investment_approved'])

    def test_claim_order_is_nonsemantic(self):
        reg = copy.deepcopy(REG)
        reg['claims'].reverse()
        self.assertEqual(evaluate(reg, CI)['status'], 'RESEARCH_CONTEXT_ONLY')

    def test_unknown_claim_rejected(self):
        self.reject(lambda x: x['claims'].append({'id': 'COMMISSIONED'}))

    def test_duplicate_claim_rejected(self):
        self.reject(lambda x: x['claims'].append(copy.deepcopy(x['claims'][0])))

    def test_missing_claim_rejected(self):
        self.reject(lambda x: x['claims'].pop())

    def test_30k_to_150k_revision_cannot_be_backfilled(self):
        self.reject(lambda x: x['claims'][0].__setitem__('value', '150000'))

    def test_env_open_is_not_env_positive(self):
        self.reject(lambda x: x['claims'][1].__setitem__('stage', 'POSITIVE_ENV_EXPERTISE'))
        self.reject(lambda x: x['controls'].__setitem__('environmental_expertise_positive_signed_verified', True))

    def test_negative_env_outcome_not_invented(self):
        self.reject(lambda x: x['controls'].__setitem__('environmental_expertise_negative_signed_verified', True))

    def test_gge_news_is_not_a_signed_certificate(self):
        self.reject(lambda x: x['claims'][2].__setitem__('official_signed_document_verified', True))
        self.reject(lambda x: x['controls'].__setitem__('engineering_expertise_original_signed_verified', True))

    def test_commissioning_proof_not_inferred(self):
        self.reject(lambda x: x['controls'].__setitem__('commissioning_permit_verified', True))
        self.reject(lambda x: x['controls'].__setitem__('physical_containers_at_mlc_verified', True))

    def test_github_annotations_are_not_executed_steps(self):
        self.reject(lambda x: x['runs'][0].__setitem__('runner_execution_verified', True), 'ci')
        self.reject(lambda x: x['runs'][0].__setitem__('annotation_text_verified', True), 'ci')

    def test_annotation_counts_are_immutable(self):
        self.reject(lambda x: x['runs'][1].__setitem__('check_annotations_count', 0), 'ci')

    def test_github_root_cause_cannot_be_guessed(self):
        self.reject(lambda x: x.__setitem__('pre_runner_root_cause', 'BILLING'), 'ci')

    def test_ci_success_cannot_be_faked(self):
        self.reject(lambda x: x.__setitem__('github_hosted_ci_green', True), 'ci')

    def test_prior_commit_sha_is_pinned(self):
        self.reject(lambda x: x.__setitem__('head_sha', '0' * 40), 'ci')

    def test_unknown_fields_and_shape_rejected(self):
        self.reject(lambda x: x.__setitem__('unverified_cashflow', 100))
        self.reject(lambda x: x.__setitem__('runs', 'wrong'), 'ci')
        for payload in ([], None, {}, 'wrong'):
            with self.subTest(payload=payload):
                self.assertEqual(evaluate(payload, CI)['status'], 'INVALID')

    def test_cli_handles_corrupt_input_with_exit_two(self):
        with tempfile.TemporaryDirectory() as p:
            bad = Path(p) / 'bad.json'
            bad.write_text('{bad json', encoding='utf-8')
            proc = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/v31_regulatory_stage_gate.py'),
                 '--regulatory', str(bad),
                 '--ci', str(ROOT / 'quality/V31_GITHUB_PRE_RUNNER_ANNOTATIONS.json')],
                capture_output=True, text=True, cwd=ROOT, check=False
            )
            self.assertEqual(proc.returncode, 2)
            self.assertFalse(json.loads(proc.stdout)['investment_approved'])


if __name__ == '__main__':
    unittest.main()

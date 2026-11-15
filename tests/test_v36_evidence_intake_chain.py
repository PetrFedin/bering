"""V36 self-reported event provenance tests: no real customer or bank files."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import v36_evidence_intake_chain as gate


class EventChainTests(unittest.TestCase):
    def setUp(self):
        self.ledger = json.loads((ROOT / 'data/evidence/V36_EMPTY_PRIVATE_EVENT_LEDGER_TEMPLATE.json').read_text())
        self.now = datetime.fromisoformat('2026-11-16T12:00:00+00:00')

    def add(self, action='RECEIVED', document='doc-001', kind='BANK_STATEMENT',
            actor='actor-keeper', role='CUSTODIAN', basis=None,
            sha=None, at=None):
        n = len(self.ledger['events']) + 1
        previous = self.ledger['events'][-1]['event_sha256'] if self.ledger['events'] else gate.ZERO
        event = {
            'sequence': n, 'event_token': f'event-{n:04d}',
            'document_token': document, 'source_kind': kind,
            'source_sha256': sha or '1' * 64,
            'recorded_at_utc': at or f'2026-11-15T10:00:{n:02d}Z',
            'action': action, 'actor_token': actor, 'actor_role': role,
            'basis_token': basis, 'previous_event_sha256': previous,
            'event_sha256': '',
        }
        event['event_sha256'] = gate.hash_event(event)
        self.ledger['events'].append(event)
        return event

    def verify(self, expected=None):
        return gate.validate(self.ledger, expected_head=expected, now=self.now)

    def assert_invalid(self, code=None):
        r = self.verify()
        self.assertEqual(r['status'], 'INVALID', r['errors'])
        if code:
            self.assertIn(code, r['errors'])
        self.assertFalse(r['bankable_revenue_approved'])
        self.assertFalse(r['investment_approved'])
        self.assertIsNone(r['real_paid_incremental_40ft'])
        self.assertIsNone(r['bering_npv_rub'])

    def test_empty_template_is_not_received_documents(self):
        r = self.verify()
        self.assertEqual(r['status'], 'NO_SOURCE_EVENTS', r['errors'])
        self.assertEqual(r['self_reported_document_tokens'], 0)
        self.assertIsNone(r['real_paid_incremental_40ft'])

    def test_single_receipt_is_not_bank_proof(self):
        self.add()
        r = self.verify()
        self.assertEqual(r['status'], 'SELF_REPORTED_CHAIN_UNANCHORED', r['errors'])
        self.assertEqual(r['self_reported_document_tokens'], 1)
        self.assertFalse(r['bank_transaction_independently_verified'])
        self.assertFalse(r['external_anchor_independently_authenticated'])

    def test_complete_claimed_review_chain_stays_hold(self):
        self.add()
        self.add('BYTES_MATCH_CLAIMED', basis='basis-sha-1')
        self.add('ISSUER_CONTACT_RECORDED', actor='actor-liaison', role='ISSUER_LIAISON', basis='basis-mail-1')
        self.add('CONTENT_REVIEW_RECORDED', actor='actor-reviewer', role='TECH_REVIEWER', basis='basis-review-1')
        self.add('BANK_TIEOUT_RECORDED', actor='actor-finance', role='FINANCE_REVIEWER', basis='basis-finance-1')
        result = self.verify()
        self.assertEqual(result['status'], 'SELF_REPORTED_CHAIN_UNANCHORED', result['errors'])
        self.assertEqual(result['events_with_valid_hashes'], 5)
        self.assertEqual(result['self_reported_byte_check_events'], 1)
        self.assertEqual(result['self_reported_review_events'], 2)
        self.assertIsNone(result['bering_npv_rub'])
        self.assertFalse(result['signature_independently_verified'])
        self.assertFalse(result['bank_transaction_independently_verified'])
        self.assertFalse(result['investment_approved'])

    def test_user_anchor_can_match_but_is_not_independently_authenticated(self):
        event = self.add()
        r = self.verify(event['event_sha256'])
        self.assertEqual(r['status'], 'SELF_REPORTED_CHAIN_MATCHES_SUPPLIED_ANCHOR')
        self.assertTrue(r['matches_user_supplied_anchor'])
        self.assertFalse(r['external_anchor_independently_authenticated'])
        self.assertFalse(r['bankable_revenue_approved'])

    def test_anchor_mismatch_fails(self):
        self.add()
        self.ledger['events'][0]['event_sha256'] = gate.hash_event(self.ledger['events'][0])
        self.assertEqual(self.verify('f' * 64)['status'], 'INVALID')

    def test_malformed_anchor_fails(self):
        self.add()
        self.assertEqual(self.verify('BANK_OK')['status'], 'INVALID')

    def test_hash_body_tampering_detected(self):
        self.add()
        self.ledger['events'][0]['source_sha256'] = '2' * 64
        self.assert_invalid('EVENT_HASH_MISMATCH')

    def test_out_of_order_chain_detected(self):
        self.add()
        e = self.add('BYTES_MATCH_CLAIMED', basis='basis-check-1')
        e['previous_event_sha256'] = 'f' * 64
        e['event_sha256'] = gate.hash_event(e)
        self.assert_invalid('BROKEN_HASH_CHAIN')

    def test_source_switched_after_receipt_is_rejected(self):
        self.add()
        self.add('BYTES_MATCH_CLAIMED', sha='9'*64, basis='basis-check-1')
        self.assert_invalid('DOCUMENT_IDENTITY_DRIFT')

    def test_event_before_receipt_rejected(self):
        self.add('CONTENT_REVIEW_RECORDED', actor='actor-reviewer', role='TECH_REVIEWER', basis='basis-review-1')
        self.assert_invalid('EVENT_BEFORE_RECEIPT')

    def test_duplicate_receipt_rejected(self):
        self.add()
        self.add()
        self.assert_invalid('DUPLICATE_DOCUMENT_RECEIPT')

    def test_duplicate_event_token_rejected(self):
        self.add()
        second = self.add('BYTES_MATCH_CLAIMED', basis='basis-check-1')
        second['event_token'] = 'event-0001'
        second['event_sha256'] = gate.hash_event(second)
        self.assert_invalid('INVALID_OR_DUPLICATE_EVENT_ID')

    def test_nonconsecutive_sequence_rejected(self):
        e = self.add()
        e['sequence'] = 5
        e['event_sha256'] = gate.hash_event(e)
        self.assert_invalid('NONCONSECUTIVE_SEQUENCE')

    def test_actor_cannot_independently_review_own_received_document(self):
        self.add()
        self.add('CONTENT_REVIEW_RECORDED', actor='actor-keeper', role='TECH_REVIEWER', basis='basis-review-1')
        self.assert_invalid('REVIEWER_SAME_AS_CUSTODIAN')

    def test_external_actor_can_claim_review_but_does_not_prove_identity(self):
        self.add()
        self.add('CONTENT_REVIEW_RECORDED', actor='actor-other', role='INDEPENDENT_REVIEWER', basis='basis-review-1')
        r = self.verify()
        self.assertEqual(r['status'], 'SELF_REPORTED_CHAIN_UNANCHORED')
        self.assertFalse(r['issuer_identity_authenticated'])

    def test_wrong_role_for_receipt_rejected(self):
        self.add(actor='actor-finance', role='FINANCE_REVIEWER')
        self.assert_invalid('ROLE_NOT_PERMITTED_FOR_ACTION')

    def test_bank_tieout_on_noncommercial_regulation_rejected(self):
        self.add(kind='ECOLOGICAL_CONCLUSION')
        self.add('BANK_TIEOUT_RECORDED', kind='ECOLOGICAL_CONCLUSION', actor='actor-finance',
                 role='FINANCE_REVIEWER', basis='basis-review-1')
        self.assert_invalid('FINANCIAL_REVIEW_OF_NONCOMMERCIAL_SOURCE')

    def test_missing_review_basis_rejected(self):
        self.add()
        self.add('CONTENT_REVIEW_RECORDED', actor='actor-other', role='TECH_REVIEWER')
        self.assert_invalid('REVIEW_OR_CHECK_WITHOUT_BASIS')

    def test_received_must_not_have_basis(self):
        self.add(basis='basis-fake')
        self.assert_invalid('RECEIPT_MUST_NOT_IMPLY_ATTESTATION')

    def test_event_after_rejection_rejected(self):
        self.add()
        self.add('REJECTED', actor='actor-other', role='INDEPENDENT_REVIEWER', basis='basis-reject-1')
        self.add('CONTENT_REVIEW_RECORDED', actor='actor-another', role='TECH_REVIEWER', basis='basis-review-1')
        self.assert_invalid('EVENT_AFTER_REJECTION')

    def test_rejection_itself_is_allowed_but_does_not_certify(self):
        self.add()
        self.add('REJECTED', actor='actor-other', role='INDEPENDENT_REVIEWER', basis='basis-reject-1')
        r = self.verify()
        self.assertEqual(r['status'], 'SELF_REPORTED_CHAIN_UNANCHORED', r['errors'])
        self.assertFalse(r['investment_approved'])

    def test_future_event_rejected(self):
        self.add(at='2030-01-01T00:00:00Z')
        self.assert_invalid('EVENT_TIME_REVERSED_OR_IN_FUTURE')

    def test_reversed_chronology_rejected(self):
        self.add(at='2026-11-15T11:00:00Z')
        self.add('BYTES_MATCH_CLAIMED', at='2026-11-15T10:00:00Z', basis='basis-review-1')
        self.assert_invalid('EVENT_TIME_REVERSED_OR_IN_FUTURE')

    def test_non_utc_time_rejected(self):
        self.add(at='2026-11-15T10:00:00+02:00')
        self.assert_invalid('INVALID_EVENT_TIME')

    def test_impossible_date_rejected(self):
        self.add(at='2026-13-45T10:00:00Z')
        self.assert_invalid('INVALID_EVENT_TIME')

    def test_claimed_payload_extra_field_rejected(self):
        e = self.add()
        e['bank_approved'] = True
        self.assert_invalid('EVENT_FIELD_SET_INVALID')

    def test_unknown_action_rejected(self):
        e = self.add(action='BANK_CERTIFIED')
        self.assert_invalid('INVALID_ACTION_OR_ROLE')

    def test_unknown_source_type_rejected(self):
        self.add(kind='MONEY_PRINTED')
        self.assert_invalid('INVALID_DOCUMENT_TYPE_OR_DIGEST')

    def test_non_hex_source_digest_rejected(self):
        self.add(sha='notashavalidsha')
        self.assert_invalid('INVALID_DOCUMENT_TYPE_OR_DIGEST')

    def test_bad_object_shapes_rejected(self):
        for payload in (None, [], 123, 'no', {}, {'events':[]}, {'schema':gate.SCHEMA, 'events':[]}):
            with self.subTest(payload=payload):
                self.assertEqual(gate.validate(payload)['status'], 'INVALID')

    def test_changed_parent_commit_rejected(self):
        self.ledger['parent_commit_sha'] = 'f'*40
        self.assert_invalid('ROOT_IDENTITY_CHANGED')

    def test_pseudonym_tokens_required(self):
        self.add(actor='Alice Johnson')
        self.assert_invalid('INVALID_PSEUDONYMOUS_TOKEN')

    def test_hidden_risk_recomputed_chain_does_not_authenticate_issuer(self):
        e = self.add()
        first = self.verify()
        e['source_sha256'] = 'f'*64
        e['event_sha256'] = gate.hash_event(e)
        second = self.verify()
        self.assertEqual(first['status'], second['status'])
        self.assertFalse(second['issuer_identity_authenticated'])
        self.assertNotEqual(first['terminal_event_hash'], second['terminal_event_hash'])

    def test_nonfinite_number_rejected_without_crash(self):
        e = self.add()
        e['event_token'] = float('nan')
        result = self.verify()
        self.assertEqual(result['status'], 'INVALID')
        self.assertIn('NONFINITE_NUMERIC_INPUT', result['errors'])

    def test_unknown_role_type_list_cannot_crash(self):
        e = self.add()
        e['actor_role'] = ['CUSTODIAN']
        e['event_sha256'] = gate.hash_event(e)
        r = self.verify()
        self.assertEqual(r['status'], 'INVALID')

    def test_unknown_action_type_list_cannot_crash(self):
        e = self.add()
        e['action'] = ['RECEIVED']
        e['event_sha256'] = gate.hash_event(e)
        r = self.verify()
        self.assertEqual(r['status'], 'INVALID')

    def test_unknown_kind_type_list_cannot_crash(self):
        e = self.add()
        e['source_kind'] = ['BANK_STATEMENT']
        e['event_sha256'] = gate.hash_event(e)
        r = self.verify()
        self.assertEqual(r['status'], 'INVALID')


class PrivateLocationTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.repo = Path(t.name) / 'repo'
        self.private = self.repo / 'local_private'
        self.private.mkdir(parents=True)
        self.p = self.private / 'ledger.json'
        self.payload = json.loads((ROOT / 'data/evidence/V36_EMPTY_PRIVATE_EVENT_LEDGER_TEMPLATE.json').read_text())
        self.p.write_text(json.dumps(self.payload), encoding='utf-8')

    def test_default_without_ledger_is_not_zero_business(self):
        r = gate.run(self.repo)
        self.assertEqual(r['status'], 'NO_PRIVATE_LEDGER')
        self.assertIsNone(r['real_paid_incremental_40ft'])

    def test_empty_private_ledger_reads_without_certification(self):
        r = gate.run(self.repo, 'local_private/ledger.json')
        self.assertEqual(r['status'], 'NO_SOURCE_EVENTS', r['errors'])
        self.assertFalse(r['investment_approved'])

    def test_outside_private_rejected(self):
        outside = self.repo/'outside.json'
        outside.write_text(self.p.read_text())
        self.assertEqual(gate.run(self.repo, outside)['status'], 'INVALID')

    def test_path_traversal_rejected(self):
        self.assertEqual(gate.run(self.repo, '../etc/passwd')['status'], 'INVALID')

    def test_symlink_source_rejected(self):
        link = self.private/'link.json'
        link.symlink_to(self.p)
        self.assertEqual(gate.run(self.repo, link)['status'], 'INVALID')

    def test_symlink_directory_rejected(self):
        real = self.private/'real'
        real.mkdir()
        (real/'a.json').write_text(self.p.read_text())
        link = self.private/'link'
        link.symlink_to(real, target_is_directory=True)
        self.assertEqual(gate.run(self.repo, link/'a.json')['status'], 'INVALID')

    def test_bad_json_rejected(self):
        self.p.write_text('not json')
        self.assertEqual(gate.run(self.repo, self.p)['status'], 'INVALID')

    def test_zero_byte_file_rejected(self):
        self.p.write_bytes(b'')
        self.assertEqual(gate.run(self.repo, self.p)['status'], 'INVALID')

    def test_cli_no_records_hold(self):
        p = subprocess.run([sys.executable, str(ROOT/'scripts/v36_evidence_intake_chain.py'),
                            '--repo', str(self.repo)],capture_output=True,text=True,check=False)
        self.assertEqual(p.returncode, 0)
        r=json.loads(p.stdout)
        self.assertEqual(r['status'],'NO_PRIVATE_LEDGER')
        self.assertFalse(r['investment_approved'])

    def test_cli_bad_input_exit_two(self):
        self.p.write_text('{invalid')
        p = subprocess.run([sys.executable, str(ROOT/'scripts/v36_evidence_intake_chain.py'),
                            '--repo', str(self.repo),'--ledger','local_private/ledger.json'],
                           capture_output=True,text=True,check=False)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)['status'],'INVALID')


if __name__ == '__main__':
    unittest.main()

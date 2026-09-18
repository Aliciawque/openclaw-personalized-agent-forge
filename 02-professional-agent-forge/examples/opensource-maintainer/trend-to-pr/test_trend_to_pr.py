# SPDX-License-Identifier: MIT
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from trend_to_pr import Ledger, ValidationError, compare, gate, repo_id, snapshot


def snap(day='2026-09-18', names=('org/a', 'org/b')):
    return {'schema_version': 1, 'date': day, 'timezone': 'America/Los_Angeles',
            'scope': 'github-trending:daily:all', 'complete': True,
            'source_url': 'https://github.com/trending', 'source_verified_for': day,
            'repositories': [{'repo': name, 'rank': i} for i, name in enumerate(names, 1)]}


def evidence():
    return {'repo': 'org/a', 'intent': 'add-reproducible-ledger',
            'license_reviewed': True, 'contributing_reviewed': True, 'duplicate_checked': True,
            'ai_policy_compatible': True, 'change_reviewed': True, 'privacy_checked': True,
            'human_action_required': False, 'value_statement': 'Prevents duplicate submissions',
            'scope': 'Original isolated example', 'source_revision': 'fixture-revision',
            'tested_revision': 'fixture-revision', 'tests_status': 'passed', 'tests_exit_code': 0,
            'tests_command': 'python -m unittest', 'tests_log': 'fixture only: OK',
            'policy_evidence': 'fixture: owner-authorized example',
            'duplicate_search_evidence': 'fixture: no duplicate found'}


class SnapshotTests(unittest.TestCase):
    def test_normalizes_case(self):
        self.assertEqual(repo_id('Cloudflare/Security-Audit-Skill'), 'cloudflare/security-audit-skill')

    def test_rejects_urls_and_paths(self):
        for name in ['https://github.com/a/b', '../x', 'a/..', 'a/b/c', 'a/b\n', 42]:
            with self.subTest(name=name), self.assertRaises(ValidationError):
                repo_id(name)

    def test_baseline_not_new(self):
        result = compare(snap())
        self.assertEqual(result['mode'], 'baseline')
        self.assertEqual(result['entered_since_previous'], [])
        self.assertEqual(len(result['baseline_repositories']), 2)

    def test_empty_snapshot_fails(self):
        with self.assertRaises(ValidationError):
            snapshot(snap(names=()))

    def test_incomplete_snapshot_fails(self):
        value = snap(); value['complete'] = False
        with self.assertRaises(ValidationError): snapshot(value)

    def test_duplicate_normalized_repo_fails(self):
        with self.assertRaises(ValidationError): snapshot(snap(names=('Org/A', 'org/a')))

    def test_invalid_date_and_timezone_fail(self):
        for key, value in [('date', '2026-02-30'), ('timezone', 'Invalid/Zone')]:
            raw = snap(); raw[key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError): snapshot(raw)

    def test_stale_source_fails(self):
        raw = snap(); raw['source_verified_for'] = '2026-09-17'
        with self.assertRaises(ValidationError): snapshot(raw)

    def test_gaps_are_not_called_daily_additions(self):
        result = compare(snap(), snap('2026-09-14', ('org/b',)))
        self.assertEqual(result['gap_days'], 4)
        self.assertFalse(result['consecutive_days'])

    def test_first_seen_and_returning_differ(self):
        result = compare(snap(names=('org/a', 'org/c', 'org/d')),
                         snap('2026-09-17', ('org/a', 'org/b')),
                         [snap('2026-09-16', ('org/c',))])
        self.assertEqual(result['returning'], ['org/c'])
        self.assertEqual(result['first_seen_in_recorded_history'], ['org/d'])
        self.assertEqual(result['departed'], ['org/b'])

    def test_rank_change(self):
        result = compare(snap(names=('org/b', 'org/a')), snap('2026-09-17'))
        self.assertEqual(result['rank_change'], {'org/a': -1, 'org/b': 1})

    def test_future_history_and_timezone_mismatch_fail(self):
        for old in [snap('2026-09-19'), snap('2026-09-17') | {'timezone': 'UTC'}]:
            with self.assertRaises(ValidationError): compare(snap(), old)

    def test_invalid_metrics_rank_and_boolean_version_fail(self):
        for field, value in [('stars_today', -1), ('stars_total', True), ('rank', 3)]:
            raw = snap(); raw['repositories'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError): snapshot(raw)
        raw = snap(); raw['schema_version'] = True
        with self.assertRaises(ValidationError): snapshot(raw)


class GateTests(unittest.TestCase):
    def test_complete_evidence_passes(self):
        self.assertTrue(gate(evidence())['eligible_for_reviewed_submission'])

    def test_missing_policies_fail_closed(self):
        for key in ('license_reviewed', 'contributing_reviewed', 'duplicate_checked',
                    'ai_policy_compatible', 'change_reviewed', 'privacy_checked'):
            raw = evidence(); del raw[key]
            with self.subTest(key=key): self.assertFalse(gate(raw)['eligible_for_reviewed_submission'])

    def test_string_true_does_not_pass(self):
        raw = evidence(); raw['change_reviewed'] = 'true'
        self.assertFalse(gate(raw)['eligible_for_reviewed_submission'])

    def test_human_requirement_blocks(self):
        raw = evidence(); raw['human_action_required'] = True
        self.assertFalse(gate(raw)['eligible_for_reviewed_submission'])

    def test_failing_unrun_or_boolean_exit_code_blocks(self):
        for code in (1, None, False):
            raw = evidence(); raw['tests_exit_code'] = code
            self.assertFalse(gate(raw)['eligible_for_reviewed_submission'])
        raw = evidence(); raw['tests_status'] = 'not_run'
        self.assertFalse(gate(raw)['eligible_for_reviewed_submission'])

    def test_stale_revision_blocks(self):
        raw = evidence(); raw['tested_revision'] = 'older'
        self.assertFalse(gate(raw)['eligible_for_reviewed_submission'])

    def test_empty_logs_blocks(self):
        raw = evidence(); raw['tests_log'] = ' '
        self.assertFalse(gate(raw)['eligible_for_reviewed_submission'])

    def test_intent_key_stable_across_dates_and_case(self):
        a = evidence(); b = evidence() | {'date': '2026-09-19', 'repo': 'ORG/A'}
        self.assertEqual(gate(a)['action_key'], gate(b)['action_key'])


class LedgerTests(unittest.TestCase):
    def setUp(self): self.ledger = Ledger(':memory:')
    def tearDown(self): self.ledger.close()

    def test_same_day_retry_is_idempotent(self):
        self.ledger.ingest(snap())
        self.assertEqual(self.ledger.ingest(snap())['mode'], 'already_recorded')

    def test_same_day_changes_do_not_overwrite(self):
        self.ledger.ingest(snap())
        with self.assertRaises(ValidationError): self.ledger.ingest(snap(names=('org/c',)))
        self.assertEqual(self.ledger.ingest(snap())['mode'], 'already_recorded')

    def test_older_snapshot_rejected(self):
        self.ledger.ingest(snap())
        with self.assertRaises(ValidationError): self.ledger.ingest(snap('2026-09-17'))

    def test_incomplete_ingest_does_not_poison_state(self):
        with self.assertRaises(ValidationError): self.ledger.ingest(snap() | {'complete': False})
        self.assertEqual(self.ledger.ingest(snap())['mode'], 'baseline')

    def test_reservation_prevents_double_submission(self):
        self.ledger.reserve(evidence())
        with self.assertRaises(ValidationError): self.ledger.reserve(evidence())

    def test_blocked_evidence_cannot_reserve(self):
        with self.assertRaises(ValidationError): self.ledger.reserve(evidence() | {'tests_status': 'failed'})
        self.assertEqual(self.ledger.reserve(evidence())['state'], 'reserved')

    def test_record_and_retry(self):
        key = self.ledger.reserve(evidence())['action_key']
        url = 'https://github.com/org/a/pull/1'
        self.assertEqual(self.ledger.record(key, url)['state'], 'submitted')
        self.assertEqual(self.ledger.record(key, url)['url'], url)
        with self.assertRaises(ValidationError): self.ledger.record(key, 'https://github.com/org/a/pull/2')

    def test_record_requires_reservation_and_matching_repo(self):
        with self.assertRaises(ValidationError): self.ledger.record('missing', 'https://github.com/org/a/pull/1')
        key = self.ledger.reserve(evidence())['action_key']
        for url in ('https://github.com/other/a/pull/1', 'https://evil.example/org/a/pull/1',
                    'https://github.com/org/a/issues/1', 'https://github.com/org/a/pull/1?x=1'):
            with self.subTest(url=url), self.assertRaises(ValidationError): self.ledger.record(key, url)

    def test_sqlite_persists_across_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.db'
            first = Ledger(path); first.ingest(snap('2026-09-17')); first.close()
            second = Ledger(path)
            try: self.assertEqual(second.ingest(snap())['mode'], 'comparison')
            finally: second.close()

    def test_two_connections_do_not_reserve_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.db'
            first, second = Ledger(path), Ledger(path)
            try:
                first.reserve(evidence())
                with self.assertRaises(ValidationError): second.reserve(evidence())
            finally: first.close(); second.close()

    def test_cli_malformed_json_is_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'broken.json'; path.write_text('{', encoding='utf-8')
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('trend_to_pr.py')),
                                     'gate', str(path)], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertIn('error', json.loads(result.stderr))


if __name__ == '__main__': unittest.main()

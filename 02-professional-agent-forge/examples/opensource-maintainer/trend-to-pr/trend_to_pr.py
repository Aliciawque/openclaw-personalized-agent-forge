#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline, evidence-first ledger for a human/agent open-source workflow.

No network, shell execution, model selection, publishing or merging is performed.
Inputs are attestations from a trusted collector/reviewer, not proof of truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ValidationError(ValueError):
    """An input cannot safely participate in this workflow."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def repo_id(value: Any) -> str:
    require(isinstance(value, str), 'repository must be a string')
    require(bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}', value)),
            'repository must be owner/name, not a URL or filesystem path')
    require(value.split('/')[1] not in {'.', '..'}, 'invalid repository name')
    return value.lower()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def snapshot(value: Any) -> dict[str, Any]:
    require(isinstance(value, dict), 'snapshot must be an object')
    require(type(value.get('schema_version')) is int and value['schema_version'] == 1,
            'schema_version must be 1')
    require(value.get('scope') == 'github-trending:daily:all', 'unsupported snapshot scope')
    require(value.get('complete') is True, 'partial/unverified snapshot: cannot update baseline')
    require(value.get('source_url') == 'https://github.com/trending', 'unexpected source URL')
    require(isinstance(value.get('date'), str), 'date must be YYYY-MM-DD')
    try:
        day = date.fromisoformat(value['date'])
        require(day.isoformat() == value['date'], 'date must be canonical YYYY-MM-DD')
        ZoneInfo(value['timezone'])
    except (ValueError, KeyError, TypeError, ZoneInfoNotFoundError) as exc:
        raise ValidationError('invalid date or IANA timezone') from exc
    require(value.get('source_verified_for') == value['date'],
            'collector must attest the source is for the requested date')
    items = value.get('repositories')
    require(isinstance(items, list) and 0 < len(items) <= 100, 'snapshot needs 1..100 repositories')
    seen: set[str] = set()
    rows = []
    for rank, item in enumerate(items, 1):
        require(isinstance(item, dict), 'repository row must be an object')
        name = repo_id(item.get('repo'))
        require(name not in seen, 'duplicate repository after case normalization')
        require(type(item.get('rank')) is int and item['rank'] == rank,
                'ranks must be contiguous in input order, starting at 1')
        seen.add(name)
        row = {'repo': name, 'rank': rank}
        for field in ('stars_today', 'stars_total'):
            count = item.get(field)
            require(count is None or (type(count) is int and count >= 0),
                    f'{field} must be a nonnegative integer or null')
            row[field] = count
        rows.append(row)
    return {key: value[key] for key in ('schema_version', 'date', 'timezone', 'scope',
                                      'complete', 'source_url', 'source_verified_for')} | {'repositories': rows}


def compare(current: Any, previous: Any = None, history: list[Any] | None = None) -> dict[str, Any]:
    cur = snapshot(current)
    previous = snapshot(previous) if previous is not None else None
    old: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for raw in (history or []) + ([previous] if previous is not None else []):
        prior = snapshot(raw)
        require((prior['scope'], prior['timezone']) == (cur['scope'], cur['timezone']),
                'cannot compare different scopes or timezones')
        require(prior['date'] < cur['date'], 'history must precede current date')
        seen.update(row['repo'] for row in prior['repositories'])
    if previous:
        old = {row['repo']: row for row in previous['repositories']}
    now = {row['repo']: row for row in cur['repositories']}
    entered = sorted(now.keys() - old.keys()) if previous else []
    gap = (date.fromisoformat(cur['date']) - date.fromisoformat(previous['date'])).days if previous else None
    return {'mode': 'comparison' if previous else 'baseline', 'date': cur['date'],
            'previous_date': previous['date'] if previous else None, 'gap_days': gap,
            'consecutive_days': gap == 1, 'baseline_repositories': sorted(now) if not previous else [],
            'entered_since_previous': entered, 'first_seen_in_recorded_history': [r for r in entered if r not in seen],
            'returning': [r for r in entered if r in seen], 'departed': sorted(old.keys() - now.keys()),
            'continuing': sorted(now.keys() & old.keys()),
            'rank_change': {r: old[r]['rank'] - now[r]['rank'] for r in sorted(now.keys() & old.keys())}}


def gate(value: Any) -> dict[str, Any]:
    """Check explicit evidence metadata; does not authenticate claims or run tests."""
    require(isinstance(value, dict), 'evidence must be an object')
    target = repo_id(value.get('repo'))
    intent = value.get('intent')
    require(isinstance(intent, str) and bool(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', intent)),
            'intent must be a stable lowercase slug, reused across retries and dates')
    reasons = []
    for key in ('license_reviewed', 'contributing_reviewed', 'duplicate_checked',
                'ai_policy_compatible', 'change_reviewed', 'privacy_checked'):
        if value.get(key) is not True:
            reasons.append(f'{key}: explicit true required')
    if value.get('human_action_required') is not False:
        reasons.append('human_action_required: must be explicitly false')
    for key in ('value_statement', 'scope', 'source_revision', 'policy_evidence', 'duplicate_search_evidence'):
        if not isinstance(value.get(key), str) or not value[key].strip():
            reasons.append(f'{key}: evidence required')
    if value.get('tests_status') != 'passed':
        reasons.append('tests_status: actual passing tests required')
    code = value.get('tests_exit_code')
    if type(code) is not int or code != 0:
        reasons.append('tests_exit_code: integer 0 required')
    for key in ('tests_command', 'tests_log'):
        if not isinstance(value.get(key), str) or not value[key].strip():
            reasons.append(f'{key}: evidence required')
    if not value.get('source_revision') or value.get('tested_revision') != value.get('source_revision'):
        reasons.append('tested_revision: must match the proposed source revision')
    return {'eligible_for_reviewed_submission': not reasons, 'reasons': reasons,
            'action_key': digest({'repo': target, 'intent': intent}), 'repo': target, 'intent': intent,
            'warning': 'Eligibility is not a security attestation, human approval, or permission grant.'}


class Ledger:
    """SQLite local state. Successful writes are transactional, retries fail closed."""
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(path, timeout=5)
        self.db.execute('CREATE TABLE IF NOT EXISTS snapshots (scope TEXT, timezone TEXT, day TEXT, digest TEXT, payload TEXT, PRIMARY KEY(scope, timezone, day))')
        self.db.execute('CREATE TABLE IF NOT EXISTS actions (key TEXT PRIMARY KEY, repo TEXT, intent TEXT, state TEXT, evidence_digest TEXT, url TEXT)')

    def close(self) -> None:
        self.db.close()

    def ingest(self, raw: Any) -> dict[str, Any]:
        cur = snapshot(raw)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            existing = self.db.execute('SELECT digest FROM snapshots WHERE scope=? AND timezone=? AND day=?',
                                       (cur['scope'], cur['timezone'], cur['date'])).fetchone()
            if existing:
                require(existing[0] == digest(cur), 'same-day snapshot differs: preserve original; record intraday changes separately')
                return {'mode': 'already_recorded', 'date': cur['date']}
            rows = self.db.execute('SELECT day,payload FROM snapshots WHERE scope=? AND timezone=? ORDER BY day',
                                   (cur['scope'], cur['timezone'])).fetchall()
            require(not rows or rows[-1][0] < cur['date'], 'cannot ingest an older snapshot into the active timeline')
            history = [json.loads(row[1]) for row in rows]
            result = compare(cur, history[-1] if history else None, history)
            self.db.execute('INSERT INTO snapshots VALUES (?,?,?,?,?)',
                            (cur['scope'], cur['timezone'], cur['date'], digest(cur), canonical(cur)))
            return result

    def reserve(self, evidence: Any) -> dict[str, Any]:
        decision = gate(evidence)
        require(decision['eligible_for_reviewed_submission'], '; '.join(decision['reasons']))
        with self.db:
            try:
                self.db.execute('INSERT INTO actions VALUES (?,?,?,?,?,NULL)',
                                (decision['action_key'], decision['repo'], decision['intent'], 'reserved', digest(evidence)))
            except sqlite3.IntegrityError as exc:
                raise ValidationError('action already reserved/submitted; reconcile GitHub before any retry') from exc
        return {'action_key': decision['action_key'], 'state': 'reserved',
                'next': 'Use authorized GitHub tools; then record the actual returned PR URL. No submission was performed.'}

    def record(self, key: str, url: str) -> dict[str, str]:
        parsed = urlsplit(url)
        require(parsed.scheme == 'https' and parsed.netloc == 'github.com' and not parsed.query and not parsed.fragment,
                'expected an exact HTTPS GitHub PR URL')
        match = re.fullmatch(r'/([^/]+/[^/]+)/pull/([1-9][0-9]*)', parsed.path)
        require(match is not None, 'expected /owner/repo/pull/number')
        target = repo_id(match.group(1))
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT repo,state,url FROM actions WHERE key=?', (key,)).fetchone()
            require(row is not None, 'cannot record an unreserved action')
            require(row[0] == target, 'PR URL repository differs from reserved target')
            if row[1] == 'submitted':
                require(row[2] == url, 'action already recorded with a different URL')
            else:
                self.db.execute("UPDATE actions SET state='submitted',url=? WHERE key=?", (url, key))
        return {'action_key': key, 'state': 'submitted', 'url': url}


def load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', default='trend-to-pr.sqlite3')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('ingest', 'gate', 'reserve'):
        sub.add_parser(name).add_argument('input')
    record = sub.add_parser('record')
    record.add_argument('key')
    record.add_argument('url')
    args = parser.parse_args(argv)
    ledger = None
    try:
        if args.command == 'gate':
            result = gate(load(args.input))
        else:
            ledger = Ledger(args.state)
            if args.command == 'ingest':
                result = ledger.ingest(load(args.input))
            elif args.command == 'reserve':
                result = ledger.reserve(load(args.input))
            else:
                result = ledger.record(args.key, args.url)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if result.get('eligible_for_reviewed_submission') is False else 0
    except (ValidationError, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        if ledger is not None:
            ledger.close()


if __name__ == '__main__':
    sys.exit(main())

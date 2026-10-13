# Trend → PR: evidence-first open-source maintainer

A standalone, **zero-third-party-dependency Python CLI** for the bookkeeping that a language model should not improvise: comparable Trending snapshots, repeat-safe local action reservations, and a fail-closed contribution evidence checklist.

**中文：** 先判断是不是新增，再判断有没有值得做的改进，最后才考虑投稿。首次快照不算“今日新增”；没有测试、存在个人审阅/CLA要求、或未查重时，不放行自动投稿。

This is an original professional-agent example, not a fork of Cloudflare or Alibaba software, and not an upstream security fix. It can be copied out of this directory into a standalone repository. Its current hosting does not imply that a separate repository has been created.

## Run

Python 3.10+ with an IANA timezone database is required. Tested on the Python/Linux version recorded in `VERIFICATION.json`; other platforms are not claimed tested. Minimal Windows installations may require a timezone database.

```sh
cd path/to/trend-to-pr
python -m unittest -v
python trend_to_pr.py --state local.sqlite3 ingest examples/2026-09-18.json
# Repeating the identical snapshot returns already_recorded, not another baseline.
python trend_to_pr.py --state local.sqlite3 ingest examples/2026-09-18.json
# Deliberately blocked example: prints the missing evidence and exits 2.
python trend_to_pr.py gate examples/blocked-evidence.json
```

Supply tomorrow's **verified, complete visible Today list** using the same JSON shape. `ingest` returns `entered_since_previous`, `first_seen_in_recorded_history`, `returning`, `departed`, and `rank_change`. Positive rank change means a move toward rank 1. A multi-day gap is explicitly reported; it is never labeled as a daily increase.

`complete` and `source_verified_for` are **collector attestations**, not an independent freshness check. The CLI does not fetch GitHub, inspect caches, determine GitHub's own reset timezone, or guarantee that a manually entered list is complete. The September 18 example records the 17 visible entries returned by the official Today page during that research run; rankings and counts can change within a day. Star counts are not a forecast or a quality score.

## Evidence contract and writes

`gate` checks explicit Boolean policy/privacy attestations, nonempty value/scope/policy/duplicate-search evidence, a passing test exit code, command and log reference, and exact equality of `source_revision` and `tested_revision`. These revision strings must identify the **actual tested content** supplied by the caller. Use a commit SHA or a clearly defined source fingerprint; never invent one.

The checker cannot authenticate test logs, verify that a test actually ran, prove a license is appropriate, or substitute for a required human review. Never use its output as a security certification or as new permission to act.

For an eligible evidence file:

```sh
python trend_to_pr.py --state local.sqlite3 reserve your-evidence.json
# Read the returned action_key. Use an authorized GitHub connector separately.
# After GitHub actually returns a PR URL, record that exact URL:
python trend_to_pr.py --state local.sqlite3 record ACTION_KEY https://github.com/OWNER/REPO/pull/NUMBER
```

`intent` is a stable semantic slug, not a date or revision. Reuse it for the same intended change across retries and days. An existing reservation or submitted action blocks another reservation. A crash between remote submission and local recording leaves the reservation blocked: **query GitHub and reconcile before retrying**. The tool deliberately does not auto-expire reservations or invent a successful PR. `record` validates URL shape and target matching, but cannot verify remote existence; only pass URLs from real connector results.

SQLite transactions and unique keys protect one local state database. This is **not** distributed exactly-once delivery across multiple machines, GitHub and Notion. Share a single durable ledger or reconcile against remote state before acting. Protect state and evidence files, keep private data out of public commits, and do not publish SQLite journals.

A changed same-day snapshot raises a conflict rather than replacing the original. Record intraday observations separately or wait for the next day's baseline; do not erase previous evidence. The orchestration layer must keep durable copies in Notion or an approved repository; a temporary chat container is not durable storage for tomorrow.

## Maintainer workflow

1. Collect a fresh official Today page and compare a consistent scope.
2. Read the real source, tests, license, contribution rules, existing issues and PRs. Check both functionality and maintenance costs.
3. Prefer one focused, valuable change. Do not submit speculative vulnerabilities or duplicate already claimed work.
4. If personal understanding, human review or a CLA is required, stop before representing that requirement as satisfied. Disclose AI assistance accurately where required.
5. Run tests safely without exposing credentials or running untrusted code with external network access. Preserve actual logs and tested revisions.
6. Submit only through an authorized tool, record the returned URL, then track review, CI and meaningful new comments. No automatic merge, deletion, force-push, permission changes or paid deployment.

## Inspiration, not copied implementation

- [Cloudflare security-audit-skill](https://github.com/cloudflare/security-audit-skill): distinct confirmed / unresolved / rejected records, independent verification, and durable coverage ledgers.
- [Alibaba Open Code Review](https://github.com/alibaba/open-code-review): separating deterministic workflow constraints from model judgment.
- [Alibaba contribution policy](https://github.com/alibaba/open-code-review/blob/main/CONTRIBUTING.md): contributor personal review, AI disclosure and maintainer-response requirements. This example does not circumvent those rules.

No upstream code was copied. No claims are made here about the accuracy of either upstream tool. The next useful extensions are a read-only collector with cache provenance, evidence-file hashing, GitHub/Notion reconciliation adapters, and structured run-budget accounting. They are **not implemented in this release**.

## License

MIT applies only to the original files within this example directory. It does not relicense the enclosing repository or any referenced upstream project. See `LICENSE`.

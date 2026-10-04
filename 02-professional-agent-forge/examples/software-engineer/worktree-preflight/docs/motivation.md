# Motivation and source review

Public sources checked on **2026-10-02 (UTC)**. No upstream code is incorporated
in this project. This note records what motivated an independent diagnostic;
it is not an upstream bug report or a request for maintainers to review it.

## Historical failure, already fixed upstream

[Impeccable #887](https://github.com/pbakaus/impeccable/issues/887) was opened by
yesolz on September 30, 2026. It documented local ignore rules being written to
a linked worktree's administrative directory instead of the shared exclude
file. The report included a real-worktree reproduction and offered to prepare
a fix after approval.

A fresh read of the public API, including the issue timeline and associated PR,
showed the issue was already completed. [PR #908](https://github.com/pbakaus/impeccable/pull/908)
merged on **2026-10-02 at 01:14:20Z** in commit
[`cf4bfc213a33c1debe91fed93a76fd8e3f3ddd62`](https://github.com/pbakaus/impeccable/commit/cf4bfc213a33c1debe91fed93a76fd8e3f3ddd62).
It corrected the hook, live, and detect-config writers. The issue closed one
second later. Cached search pages still showed it open, so those snapshots were
not used to describe its current status.

The live `main` commit reviewed was
[`508d7e8955de3b3caf2d8676e85206723d41a887`](https://github.com/pbakaus/impeccable/commit/508d7e8955de3b3caf2d8676e85206723d41a887).
The following source and tests were inspected:

- [Shared Git-layout helper and unit tests](https://github.com/pbakaus/impeccable/blob/508d7e8955de3b3caf2d8676e85206723d41a887/crates/common/src/git.rs):
  resolves `commondir` for a linked layout. Its comment explains the deliberate
  choice not to start Git on every edit and to work when Git is absent
- [Hook resolver](https://github.com/pbakaus/impeccable/blob/508d7e8955de3b3caf2d8676e85206723d41a887/crates/hook/src/hook_lib.rs):
  finds the enclosing repository and prefixes patterns for nested directories;
  the effective exclude target now uses the shared helper
- [Live resolver and regression](https://github.com/pbakaus/impeccable/blob/508d7e8955de3b3caf2d8676e85206723d41a887/crates/live/src/gitignore.rs):
  follows a gitfile and now resolves the common exclude; the test constructs a
  linked layout with a relative `commondir`
- [Hook integration tests](https://github.com/pbakaus/impeccable/blob/508d7e8955de3b3caf2d8676e85206723d41a887/crates/hook/tests/hook_tests.rs):
  the existing basic test checks generated content/idempotence and nested
  prefixes; the new linked-worktree regression creates a real repository and
  worktree and asserts behavior using Git's `check-ignore`

No upstream tests were executed here; these were read as public evidence. The
new project's independent tests were executed locally.

## Why a standalone tool still helps

An occasional diagnostic has different constraints from a hook running after
every edit. It can require Git, use Git's authoritative path resolution, inspect
an existing installation without modifying it, and return a machine-readable
answer useful across installers and agent tools.

The added value is the combination of:

1. Distinguishing shared metadata from worktree-local metadata, without telling
   users to move caches that should remain local
2. Detecting an already-created but ineffective exclude file
3. Querying rule matches with negation/source/line evidence while explicitly
   stating that tracking is not inspected
4. Enforcing explicit rule-match expectations with stable exit codes and a reusable
   regression suite

No new upstream defect is claimed. Fixing #887 again would duplicate completed
work. This project's scope remains diagnostics rather than automatic repair or
replacement of Impeccable's runtime design.

## Contribution boundaries

Impeccable's [contribution guidelines](https://github.com/pbakaus/impeccable/blob/508d7e8955de3b3caf2d8676e85206723d41a887/AGENTS.md#contributing-issue-and-pr-guidelines)
and [PR template](https://github.com/pbakaus/impeccable/blob/508d7e8955de3b3caf2d8676e85206723d41a887/.github/PULL_REQUEST_TEMPLATE.md)
require maintainer direction for outside PRs and describe additional restrictions
on AI-submitted issues/PRs. No issue, comment, PR, fork, or other mutation was
made to that project while preparing this work.

## Git references behind the implementation

- [Repository layout](https://git-scm.com/docs/gitrepository-layout): shared
  versus per-worktree metadata and `commondir`
- [rev-parse](https://git-scm.com/docs/git-rev-parse): canonical absolute path
  output and `--git-path` relocation handling
- [check-ignore](https://git-scm.com/docs/git-check-ignore): NUL-delimited verbose
  records, negation, and the distinction between tracked paths and `--no-index`
- [ls-files](https://git-scm.com/docs/git-ls-files): index inventory and sparse
  directory reporting
- [Git 2.45 release notes](https://github.com/git/git/blob/v2.45.0/Documentation/RelNotes/2.45.0.txt):
  introduction of the no-lazy-fetch safeguard; the minimum supported Git version
- [Git configuration](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corefsmonitor):
  fsmonitor boolean semantics on modern Git

Independent review found that disabling optional locks alone does not make
index inspection read-only: sparse-index expansion can fetch objects, error
paths can create tree objects, and split-index reads can refresh timestamps.
The final design therefore avoids index inspection altogether. It uses only
`check-ignore --no-index` for rule evidence and makes no claim about actual
tracking or privacy. A positive rule can still match an already-tracked file.
Regression fixtures verify unchanged file contents and mtimes for sparse,
partial, and split-index layouts, including missing objects and stale sparse
configuration. This narrower scope is intentional.

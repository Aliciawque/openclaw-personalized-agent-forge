# worktree-preflight

A small, read-only Git diagnostic for maintainers of coding-agent tools,
installers, and developer scripts. Resolve the right `info/exclude` file,
catch unused worktree-specific exclude files, and explain ignore-rule matches.

**Rule checks do not inspect tracking.** A positive match does not establish
that a file is untracked, private, or safe to publish. Ignore rules do not
untrack files that were already added to the index.

Python **3.10+**, Git **2.45+**, and no third-party Python dependencies. Run the
single file directly; no installation or network access is needed.

## Quick start

From this directory:

```sh
python3 worktree_preflight.py /path/to/repo
python3 worktree_preflight.py /path/to/linked-worktree \
  --check .agent/config.local.json --check .agent/cache.json
python3 worktree_preflight.py /path/to/linked-worktree \
  --check .agent/cache.json --require-rule-ignore --strict --json
```

`--check` paths are relative to the directory argument, including when that
argument is a subdirectory. Absolute paths inside the working tree also work.
Paths need not exist: the tool asks Git about their rules without creating
them. Use `--check=--leading-dash` for a filename beginning with a dash.

The report includes:

- The working-tree root, per-worktree Git directory, shared/common Git
  directory, and effective `info/exclude` path
- A warning if a distinct per-worktree `info/exclude` exists but Git resolves
  that special file elsewhere; a symlink/hardlink to the effective file is not
  flagged
- Each requested path's matching ignore source, line number, pattern, and
  whether the pattern is negated
- Versioned JSON and explicit exit codes for rule-matching requirements

This combines layout diagnosis, misplaced-file detection, rule provenance,
negation handling, and a reusable regression assertion. It is useful before or
after an installer writes local excludes. It does not automatically repair them.

## Why use Git as the authority?

A linked worktree's `.git` is usually a file pointing to its own administrative
directory. Appending `info/exclude` to that directory can produce a real file
that Git does not use. This tool resolves paths with:

```sh
git rev-parse --path-format=absolute --git-dir
git rev-parse --path-format=absolute --git-common-dir
git rev-parse --path-format=absolute --git-path info/exclude
```

It does not duplicate `.git`/`commondir` parsing or implement an ignore-pattern
engine. Rule evidence comes from `git check-ignore --no-index --verbose
--non-matching --stdin -z`. NUL-delimited output preserves spaces, tabs, and
newlines. The tool deliberately never runs `ls-files`, reads the index, or
reports whether a path is tracked.

Historical motivation is [Impeccable issue #887](https://github.com/pbakaus/impeccable/issues/887).
**That upstream bug was already fixed in merged [PR #908](https://github.com/pbakaus/impeccable/pull/908)**
on October 2, 2026. This is an independent cross-tool diagnostic, not an
Impeccable patch or a claim that its current version is broken. See
[the source review](docs/motivation.md) for pinned sources and the existing fix.

## Outcomes and automation

- Exit **0**: inspection completed and requested requirements passed. Ordinary
  layout warnings still appear unless `--strict` is used
- Exit **1**: `--require-rule-ignore` found a checked path without a positive
  ignore-rule match, or `--strict` found a layout warning
- Exit **2**: invalid arguments, missing/old Git, non-repository input, invalid
  path, Git refusal/warning, timeout, or another operational error

`--require-rule-ignore` asserts only a hypothetical positive rule match for
each specified path, independent of tracking. It needs at least one `--check`.
A bare repository or administrative Git directory can be inspected for layout;
rule probes require a working directory. A directory probe is not a recursive
check of its children.

`--json` writes a single JSON object to stdout, including on errors. Normal
human errors go to stderr. `--help` and `--version` retain standard text output.
`--timeout SECONDS` bounds each Git subprocess (default: 10; maximum: 300).

### JSON contract (schema version 1)

All reports contain `schema_version`, `tool_version`, `status`, `exit_code`,
and `errors`. `status` is `ok`, `findings`, or `error`. `findings` can have exit
code 0 when warnings are informational; use `exit_code` for pass/fail.

Completed reports also include `repository`, `checks`, `diagnostics`,
`requirements`, `environment`, `directory`, `git_version`,
`scope: "ignore_rules_only"`, and `tracking_checked: false`.

Each check has:

- `input` and normalized worktree-relative `path`
- `exists` (including dangling symlinks) and `tracking_checked: false`
- `state`: `rule_excludes`, `rule_includes` (a negated rule), or `no_rule`
- `rules_would_ignore`: true only for a positive rule match
- `match`: null or `{source, line, pattern, negated}` from Git

There is deliberately no `ignored`, `tracked`, or `untracked` field.
`match.source` is returned as Git reports it: absolute or relative to the
working-tree root. Error reports have no partial check results. Key order is
stable, check order matches input, and no timestamps/random IDs are emitted.
Unchanged inputs, environment, and repository metadata produce identical JSON.

## Safety and scope

- No repairs, staging, commits, config changes, installs, or network calls.
  No inspected files are opened for writing
- Every inherited `GIT_*` environment variable is removed for subprocesses,
  so a parent hook's `GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR`, `GIT_INDEX_FILE`,
  or config injection cannot silently redirect the selected target. Removed
  **names only** are reported. This intentionally does not emulate a custom
  environment-driven Git invocation
- Repository, worktree, user/global, and system configuration still apply,
  including `core.excludesFile`; `HOME` and `XDG_CONFIG_HOME` are preserved.
  `core.fsmonitor=false` disables the configured fsmonitor helper; optional Git
  locks are disabled. `GIT_NO_LAZY_FETCH=1` prevents fetching promised objects;
  Git 2.45+ is required for that defense. Git's safe-directory checks remain
- Avoiding index reads is deliberate: seemingly read-only index commands can
  expand sparse indexes, create/fetch objects, or refresh split-index timestamps.
  Tests verify no content or mtime changes for these layouts using rule-only
  checks, including a partial clone fixture with a missing sparse tree
- Paths outside the working tree and its `.git` metadata are rejected as probe
  targets. Git rejects traversal beyond symlinks. The selected working tree's
  rules apply; run separately against a submodule's own directory for its rules
- An unused exclude warning reports the presence of a different file, not proof
  it contains active rules. Comment-only files may also warn. Review before
  changing anything: the effective exclude may be shared by worktrees
- This is not a secret scanner, a privacy check, or a security guarantee. Paths,
  files, and configuration can change while separate Git commands run
- Reports can contain local paths and private ignore patterns. Review before
  sharing. No file bodies or environment values are included
- Verified locally on Linux with Python 3.12 and Git 2.52. Windows/macOS and older
  supported versions are not yet verified. POSIX-only tests skip on Windows

## Development

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile worktree_preflight.py tests/test_preflight.py
```

Tests use isolated temporary homes and real temporary Git repositories, including
linked worktrees. Coverage includes misplaced excludes, bare/separate/unborn
repositories, subdirectories, negation, global/nested rules, tracked-file
rule-only semantics, spaces, symlinks/loops, unusual filenames, inherited Git
overrides, filesystem boundaries, CLI exits, errors, fsmonitor suppression,
partial/sparse/split indexes, and unchanged file contents/mtimes.

Prepared with AI assistance. Original implementation and tests; no Impeccable
code is copied. The [MIT license](LICENSE) applies to this project directory
only, not to other projects in a containing repository.

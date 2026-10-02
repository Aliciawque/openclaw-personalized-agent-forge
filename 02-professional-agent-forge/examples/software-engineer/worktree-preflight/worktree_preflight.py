#!/usr/bin/env python3
"""Read-only Git layout and ignore diagnostics; Python standard library only."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Sequence

VERSION = "0.1.0"
SCHEMA_VERSION = 1


class PreflightError(Exception):
    """A diagnostic could not be completed, rather than a failed expectation."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

    def as_dict(self) -> dict:
        return {"code": self.code, "message": str(self)}


class Git:
    def __init__(self, directory: Path, timeout: float):
        self.directory = directory
        self.timeout = timeout
        # A hook or agent may inherit GIT_DIR / GIT_INDEX_FILE from another repo.
        # Target the directory the caller chose, not that hidden environment.
        self.removed_environment = sorted(k for k in os.environ if k.startswith("GIT_"))
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0",
                        GIT_NO_LAZY_FETCH="1", LC_ALL="C")

    def run(self, *args: str, input_data: bytes | None = None,
            allowed: tuple[int, ...] = (0,), directory: Path | None = None):
        command = ["git", "--no-pager", "--no-optional-locks", "-c", "core.fsmonitor=false",
                   "-C", str(directory or self.directory), *args]
        try:
            result = subprocess.run(command, input=input_data, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=self.env,
                                    timeout=self.timeout, check=False)
        except FileNotFoundError as exc:
            raise PreflightError("git_not_found", "Git is not installed or not on PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise PreflightError("git_timeout", f"Git exceeded {self.timeout:g} seconds") from exc
        except OSError as exc:
            raise PreflightError("git_execution_failed", str(exc)) from exc
        if result.returncode not in allowed or result.stderr:
            detail = os.fsdecode(result.stderr).rstrip("\n")
            raise PreflightError("git_failed", detail or f"Git exited {result.returncode}")
        return result

    def text(self, *args: str) -> str:
        # Remove just Git's record terminator, never whitespace in a path.
        return os.fsdecode(self.run(*args).stdout).removesuffix("\n")

    def path(self, *args: str) -> Path:
        value = self.text("rev-parse", "--path-format=absolute", *args)
        if not os.path.isabs(value):
            raise PreflightError("invalid_git_output", "Git did not return an absolute path")
        return Path(value)


def file_state(path: Path) -> dict:
    """Inspect metadata only; never open a file, symlink, device, or FIFO."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {"path": str(path), "kind": "missing", "size_bytes": None}
    except OSError as exc:
        raise PreflightError("path_unreadable", f"Cannot inspect {path}: {exc}") from exc
    kind = ("symlink" if stat.S_ISLNK(metadata.st_mode) else
            "file" if stat.S_ISREG(metadata.st_mode) else
            "directory" if stat.S_ISDIR(metadata.st_mode) else "special")
    return {"path": str(path), "kind": kind,
            "size_bytes": metadata.st_size if kind == "file" else None}


def same_path(left: Path, right: Path) -> bool:
    if left == right:
        return True
    try:
        return os.path.samefile(left, right)
    except OSError:
        try:
            return left.resolve() == right.resolve()
        except (OSError, RuntimeError) as exc:
            raise PreflightError("path_unreadable", f"Cannot resolve exclude paths: {exc}") from exc


def probe(git: Git, root: Path, start: Path, requested: str) -> dict:
    if not requested or "\0" in requested:
        raise PreflightError("invalid_check_path", "Check paths must be nonempty and contain no NUL")
    # Normalize '..' without dereferencing the final symlink: Git ignores links,
    # not their targets. Git itself rejects paths beyond a symlink.
    absolute = Path(os.path.abspath(start / requested))
    try:
        relative = absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise PreflightError("outside_worktree", f"Check path is outside the worktree: {requested}") from exc
    if relative == "." or relative.split("/", 1)[0].lower() == ".git":
        raise PreflightError("invalid_check_path", "Check a worktree path, not its root or .git metadata")
    query = relative + ("/" if requested.endswith(("/", os.sep)) else "")
    result = git.run("check-ignore", "--stdin", "-z", "--verbose", "--non-matching",
                     "--no-index", input_data=os.fsencode(query) + b"\0",
                     allowed=(0, 1), directory=root)
    fields = result.stdout.split(b"\0")
    if len(fields) != 5 or fields[-1] != b"" or os.fsdecode(fields[3]) != query:
        raise PreflightError("invalid_git_output", "Unexpected check-ignore record")
    source, line, pattern = (os.fsdecode(v) for v in fields[:3])
    match = None
    if source:
        try:
            line_number = int(line)
        except ValueError as exc:
            raise PreflightError("invalid_git_output", "Invalid check-ignore line number") from exc
        match = {"source": source, "line": line_number, "pattern": pattern,
                 "negated": pattern.startswith("!")}
    rules_would_ignore = bool(match and not match["negated"])
    state = "rule_excludes" if rules_would_ignore else "rule_includes" if match else "no_rule"
    return {"input": requested, "path": relative, "exists": os.path.lexists(absolute),
            "state": state, "tracking_checked": False,
            "rules_would_ignore": rules_would_ignore, "match": match}



def inspect_repository(repository: str | os.PathLike = ".", checks: Sequence[str] = (),
                       *, timeout: float = 10.0, require_rule_ignore: bool = False,
                       strict: bool = False) -> dict:
    """Return a schema-v1 report. Operational failures raise PreflightError."""
    if not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise PreflightError("invalid_timeout", "Timeout must be a finite number greater than 0 and at most 300 seconds")
    if require_rule_ignore and not checks:
        raise PreflightError("missing_checks", "--require-rule-ignore needs at least one --check path")
    try:
        start = Path(repository).expanduser().resolve(strict=True)
        if not start.is_dir():
            raise PreflightError("not_directory", "Repository argument must be an existing directory")
    except (OSError, ValueError, RuntimeError) as exc:
        raise PreflightError("invalid_directory", str(exc)) from exc
    git = Git(start, timeout)
    version = git.text("--version")
    parsed = re.search(r"git version (\d+)\.(\d+)", version)
    if not parsed or tuple(map(int, parsed.groups())) < (2, 45):
        raise PreflightError("unsupported_git", "Git 2.45 or newer is required (no-lazy-fetch support)")
    git_dir = git.path("--git-dir")
    common_dir = git.path("--git-common-dir")
    exclude = git.path("--git-path", "info/exclude")
    bare = git.text("rev-parse", "--is-bare-repository") == "true"
    inside = git.text("rev-parse", "--is-inside-work-tree") == "true"
    root = git.path("--show-toplevel") if inside else None
    if checks and root is None:
        raise PreflightError("no_worktree", "Ignore checks require a working directory, not a bare repo or gitdir")
    local_exclude = git_dir / "info" / "exclude"
    shared = not same_path(git_dir, common_dir)
    misplaced = not same_path(local_exclude, exclude)
    local_state = file_state(local_exclude)
    effective_state = file_state(exclude)
    diagnostics = []
    if misplaced and local_state["kind"] != "missing":
        diagnostics.append({
            "code": "unused_worktree_exclude", "severity": "warning",
            "message": "A per-worktree info/exclude exists, but Git resolves info/exclude elsewhere.",
            "path": str(local_exclude), "effective_path": str(exclude),
            "action": "Review this file manually. Put intended repository-local rules in the effective "
                      "exclude file; it is shared by worktrees. Rerun with --check to inspect rule matches. "
                      "Do not blindly move rules or worktree-local caches."})
    if effective_state["kind"] not in ("file", "missing", "symlink"):
        diagnostics.append({"code": "unusable_exclude", "severity": "warning",
                            "message": "The effective exclude path is not a regular file or symlink.",
                            "path": str(exclude),
                            "action": "Inspect its type and permissions before relying on local excludes."})
    # Prevent check-ignore from opening an effective FIFO/device and hanging.
    if checks:
        try:
            mode = exclude.stat().st_mode
        except FileNotFoundError:
            mode = None
        except OSError as exc:
            raise PreflightError("path_unreadable", str(exc)) from exc
        if mode is not None and not stat.S_ISREG(mode):
            raise PreflightError("unsafe_exclude_type", "Ignore probes require a regular effective exclude file")
    results = [probe(git, root, start, p) for p in checks]
    failures = [r["path"] for r in results if require_rule_ignore and not r["rules_would_ignore"]]
    exit_code = 1 if failures or (strict and diagnostics) else 0
    return {"schema_version": SCHEMA_VERSION, "tool_version": VERSION,
            "status": "findings" if failures or diagnostics else "ok", "exit_code": exit_code,
            "git_version": version, "directory": str(start),
            "scope": "ignore_rules_only", "tracking_checked": False,
            "repository": {"worktree_root": str(root) if root else None,
                           "git_dir": str(git_dir), "common_dir": str(common_dir),
                           "bare": bare, "inside_worktree": inside,
                           "linked_worktree": shared and not bare,
                           "effective_exclude": effective_state,
                           "git_dir_exclude": local_state,
                           "git_dir_exclude_is_effective": not misplaced},
            "environment": {"removed_git_variables": git.removed_environment},
            "checks": results, "diagnostics": diagnostics,
            "requirements": {"positive_ignore_rule_for_all_checks": require_rule_ignore, "strict": strict,
                             "failed_paths": failures}, "errors": []}


def quoted(value) -> str:
    return json.dumps(value, ensure_ascii=True)


def human_report(report: dict) -> str:
    if report["status"] == "error":
        return "\n".join(f"ERROR [{e['code']}]: {quoted(e['message'])}" for e in report["errors"])
    repo = report["repository"]
    kind = "bare repository" if repo["bare"] else "linked worktree" if repo["linked_worktree"] else "repository"
    lines = [f"worktree-preflight: {kind}",
             f"  Worktree:        {quoted(repo['worktree_root'])}",
             f"  Git directory:   {quoted(repo['git_dir'])}",
             f"  Common directory:{' '}{quoted(repo['common_dir'])}",
             f"  Effective exclude: {quoted(repo['effective_exclude']['path'])} "
             f"({repo['effective_exclude']['kind']})"]
    removed = report["environment"]["removed_git_variables"]
    if removed:
        lines.append("  Ignored inherited Git variables: " + quoted(removed))
    for item in report["diagnostics"]:
        lines.extend([f"WARNING [{item['code']}]: {item['message']}",
                      f"  Path: {quoted(item['path'])}", f"  Next: {item['action']}"])
    if report["checks"]:
        lines.append("Rule checks only: tracking is NOT checked. Ignore rules do not untrack files.")
    for check in report["checks"]:
        lines.append(f"{check['state'].upper()}: {quoted(check['path'])}")
        if check["match"]:
            match = check["match"]
            lines.append(f"  Rule: {quoted(match['source'])}:{match['line']} {quoted(match['pattern'])}")
    if not report["checks"]:
        lines.append("No paths checked. Use --check PATH to inspect ignore-rule matches.")
    if report["requirements"]["failed_paths"]:
        lines.append("FAIL: one or more requested paths have no positive ignore-rule match.")
    lines.append(f"Exit status: {report['exit_code']}")
    return "\n".join(lines)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PreflightError("usage", message)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    parser = Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("repository", nargs="?", default=".", help="existing repo or worktree directory")
    parser.add_argument("--check", action="append", default=[], metavar="PATH",
                        help="probe a path relative to repository argument; repeat as needed")
    parser.add_argument("--require-rule-ignore", action="store_true", help="exit 1 unless every checked path has a positive ignore rule")
    parser.add_argument("--strict", action="store_true", help="exit 1 on layout warnings")
    parser.add_argument("--json", action="store_true", help="emit schema-v1 JSON, including errors")
    parser.add_argument("--timeout", type=float, default=10, help="seconds per Git command, at most 300 (default: 10)")
    parser.add_argument("--version", action="version", version=VERSION)
    try:
        options = parser.parse_args(args)
        report = inspect_repository(options.repository, options.check, timeout=options.timeout,
                                    require_rule_ignore=options.require_rule_ignore, strict=options.strict)
    except PreflightError as exc:
        report = {"schema_version": SCHEMA_VERSION, "tool_version": VERSION,
                  "status": "error", "exit_code": 2, "errors": [exc.as_dict()]}
    if "--json" in args:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print(human_report(report), file=sys.stderr if report["status"] == "error" else sys.stdout)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())

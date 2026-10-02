"""Real-Git integration tests. No network, packages, or user config required."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import worktree_preflight as wp


@unittest.skipUnless(shutil.which("git"), "Git required")
class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="preflight tests ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        home = self.base / "home"
        home.mkdir()
        env = {k: v for k, v in os.environ.items()
               if k in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR")}
        env.update(HOME=str(home), USERPROFILE=str(home), XDG_CONFIG_HOME=str(home / "xdg"))
        self.env_patch = patch.dict(os.environ, env, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.repo = self.base / "repo with spaces"
        self.git(self.base, "-c", "init.templateDir=", "init", "-q", "-b", "main", str(self.repo))
        self.git(self.repo, "config", "user.name", "Test")
        self.git(self.repo, "config", "user.email", "test@example.invalid")

    def git(self, cwd, *args, check=True, input_data=None):
        result = subprocess.run(["git", "-C", str(cwd), *args], check=False,
                                input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        return result

    def write(self, relative, content):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def linked(self):
        self.git(self.repo, "commit", "--allow-empty", "-qm", "Initial")
        worktree = self.base / "linked tree"
        self.git(self.repo, "worktree", "add", "-qb", "linked", str(worktree))
        return worktree

    def cli(self, *args):
        return subprocess.run([sys.executable, str(Path(wp.__file__)), *map(str, args)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def test_unborn_repository_needs_no_commit_or_exclude_file(self):
        report = wp.inspect_repository(self.repo)
        self.assertEqual(report["repository"]["git_dir"], str(self.repo / ".git"))
        self.assertEqual(report["repository"]["common_dir"], str(self.repo / ".git"))
        self.assertEqual(report["repository"]["effective_exclude"]["kind"], "missing")
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["checks"], [])

    def test_linked_worktree_misdirected_rules_then_effective_rules(self):
        worktree = self.linked()
        report = wp.inspect_repository(worktree)
        repo = report["repository"]
        self.assertTrue(repo["linked_worktree"])
        self.assertNotEqual(repo["git_dir"], repo["common_dir"])
        effective = Path(repo["effective_exclude"]["path"])
        unused = Path(repo["git_dir_exclude"]["path"])
        self.assertEqual(effective, self.repo / ".git" / "info" / "exclude")
        unused.parent.mkdir()
        unused.write_text(".agent/cache.json\n")
        report = wp.inspect_repository(worktree, [".agent/cache.json"], require_rule_ignore=True)
        self.assertFalse(report["checks"][0]["rules_would_ignore"])
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["diagnostics"][0]["code"], "unused_worktree_exclude")
        effective.parent.mkdir(exist_ok=True)
        effective.write_text(".agent/cache.json\n")
        report = wp.inspect_repository(worktree, [".agent/cache.json"], require_rule_ignore=True)
        self.assertTrue(report["checks"][0]["rules_would_ignore"])
        self.assertEqual(report["checks"][0]["match"]["source"], str(effective))
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(wp.inspect_repository(worktree, strict=True)["exit_code"], 1)
        # Independent oracle: Git's ordinary indexed behavior, without --no-index.
        result = self.git(worktree, "check-ignore", "-q", ".agent/cache.json", check=False)
        self.assertEqual(result.returncode, 0)

    def test_subdirectory_paths_are_relative_to_requested_directory(self):
        nested = self.repo / "src" / "nested"
        nested.mkdir(parents=True)
        self.write(".gitignore", "src/nested/cache.json\n")
        report = wp.inspect_repository(nested, ["cache.json"], require_rule_ignore=True)
        self.assertEqual(report["repository"]["worktree_root"], str(self.repo))
        self.assertEqual(report["checks"][0]["path"], "src/nested/cache.json")
        self.assertEqual(report["exit_code"], 0)

    def test_bare_repository_layout_and_probe_error(self):
        bare = self.base / "bare repo.git"
        self.git(self.base, "init", "--bare", "-q", str(bare))
        report = wp.inspect_repository(bare)
        self.assertTrue(report["repository"]["bare"])
        self.assertIsNone(report["repository"]["worktree_root"])
        self.assertEqual(report["repository"]["effective_exclude"]["path"], str(bare / "info/exclude"))
        with self.assertRaisesRegex(wp.PreflightError, "working directory"):
            wp.inspect_repository(bare, ["cache.json"])

    def test_gitdir_input_is_not_mistaken_for_worktree(self):
        report = wp.inspect_repository(self.repo / ".git")
        self.assertFalse(report["repository"]["inside_worktree"])
        self.assertIsNone(report["repository"]["worktree_root"])
        with self.assertRaises(wp.PreflightError):
            wp.inspect_repository(self.repo / ".git", ["config"])

    def test_separate_git_dir_is_not_linked_worktree(self):
        work = self.base / "separate tree"
        admin = self.base / "separate admin"
        self.git(self.base, "init", "-q", "--separate-git-dir", str(admin), str(work))
        report = wp.inspect_repository(work)
        self.assertEqual(report["repository"]["git_dir"], str(admin))
        self.assertFalse(report["repository"]["linked_worktree"])
        self.assertTrue(report["repository"]["git_dir_exclude_is_effective"])

    def test_negated_pattern_is_not_ignored(self):
        self.write(".gitignore", "*.tmp\n!keep.tmp\n")
        results = wp.inspect_repository(self.repo, ["a.tmp", "keep.tmp", "a.txt"])["checks"]
        self.assertTrue(results[0]["rules_would_ignore"])
        self.assertFalse(results[1]["rules_would_ignore"])
        self.assertTrue(results[1]["match"]["negated"])
        self.assertIsNone(results[2]["match"])

    def test_escaped_exclamation_is_positive_pattern(self):
        self.write(".gitignore", "\\!secret\n")
        check = wp.inspect_repository(self.repo, ["!secret"])["checks"][0]
        self.assertTrue(check["rules_would_ignore"])
        self.assertFalse(check["match"]["negated"])

    def test_tracked_file_is_reported_as_hypothetical_rule_match_only(self):
        self.write("cache.json", "{}")
        self.git(self.repo, "add", "cache.json")
        self.write(".gitignore", "cache.json\n")
        report = wp.inspect_repository(self.repo, ["cache.json"], require_rule_ignore=True)
        check = report["checks"][0]
        self.assertEqual(check["state"], "rule_excludes")
        self.assertTrue(check["rules_would_ignore"])
        self.assertFalse(check["tracking_checked"])
        self.assertFalse(report["tracking_checked"])
        self.assertNotIn("ignored", check)
        self.assertNotIn("tracked", check)
        self.assertIn("tracking is NOT checked", wp.human_report(report))
        self.assertEqual(report["exit_code"], 0)  # Rule requirement only.
        # Independently prove why a rule match must not claim actual ignoredness.
        self.assertEqual(self.git(self.repo, "check-ignore", "-q", "cache.json", check=False).returncode, 1)

    def test_filename_globs_are_literal_query_paths(self):
        self.write("a.txt", "tracked")
        self.git(self.repo, "add", "a.txt")
        check = wp.inspect_repository(self.repo, ["*.txt"])["checks"][0]
        self.assertEqual(check["path"], "*.txt")
        self.assertEqual(check["state"], "no_rule")
        self.assertFalse(check["tracking_checked"])

    def test_nonexistent_path_does_not_get_created(self):
        self.write(".gitignore", "future/\n")
        check = wp.inspect_repository(self.repo, ["future/cache"])["checks"][0]
        self.assertTrue(check["rules_would_ignore"])
        self.assertFalse(check["exists"])
        self.assertFalse((self.repo / "future").exists())

    def test_ignore_precedence_nested_file_and_global_config(self):
        global_ignore = self.base / "global excludes"
        global_ignore.write_text("*.tmp\n")
        self.git(self.repo, "config", "core.excludesFile", str(global_ignore))
        self.write("sub/.gitignore", "!keep.tmp\n")
        checks = wp.inspect_repository(self.repo, ["other.tmp", "sub/keep.tmp"])["checks"]
        self.assertEqual(checks[0]["match"]["source"], str(global_ignore))
        self.assertTrue(checks[0]["rules_would_ignore"])
        self.assertFalse(checks[1]["rules_would_ignore"])
        self.assertEqual(checks[1]["match"]["source"], "sub/.gitignore")

    @unittest.skipIf(os.name == "nt", "POSIX filename test")
    def test_nul_protocol_handles_newlines_tabs_unicode_and_leading_dash(self):
        self.write(".gitignore", "*.tmp\n")
        names = ["line\nbreak.tmp", "tab\tname.tmp", "snowman-☃.tmp", "--dash.tmp"]
        checks = wp.inspect_repository(self.repo, names)["checks"]
        self.assertEqual([p["path"] for p in checks], names)
        self.assertTrue(all(p["rules_would_ignore"] for p in checks))
        self.assertNotIn("line\nbreak.tmp", wp.human_report(wp.inspect_repository(self.repo, names)))

    @unittest.skipIf(os.name == "nt", "POSIX filename test")
    def test_newline_at_end_of_repository_name_is_preserved(self):
        renamed = self.base / "repo\n"
        self.repo.rename(renamed)
        report = wp.inspect_repository(renamed)
        self.assertEqual(report["repository"]["worktree_root"], str(renamed))

    @unittest.skipIf(os.name == "nt", "Symlink privileges vary on Windows")
    def test_symlink_repository_input(self):
        alias = self.base / "alias"
        alias.symlink_to(self.repo, target_is_directory=True)
        self.assertEqual(wp.inspect_repository(alias)["directory"], str(self.repo))

    @unittest.skipIf(os.name == "nt", "Symlink privileges vary on Windows")
    def test_symlink_path_itself_is_checked_without_following_target(self):
        (self.repo / "link").symlink_to(self.base / "outside")
        self.write(".gitignore", "link\n")
        self.assertTrue(wp.inspect_repository(self.repo, ["link"])["checks"][0]["rules_would_ignore"])
        with self.assertRaises(wp.PreflightError):
            wp.inspect_repository(self.repo, ["link/file"])

    @unittest.skipIf(os.name == "nt", "Symlink privileges vary on Windows")
    def test_local_exclude_symlink_to_effective_file_is_not_misdirected(self):
        worktree = self.linked()
        repo = wp.inspect_repository(worktree)["repository"]
        effective = Path(repo["effective_exclude"]["path"])
        effective.parent.mkdir(exist_ok=True)
        effective.write_text("cache\n")
        local = Path(repo["git_dir_exclude"]["path"])
        local.parent.mkdir()
        local.symlink_to(effective)
        report = wp.inspect_repository(worktree, ["cache"])
        self.assertEqual(report["diagnostics"], [])
        self.assertTrue(report["checks"][0]["rules_would_ignore"])

    @unittest.skipIf(os.name == "nt", "Symlink privileges vary on Windows")
    def test_looping_local_exclude_is_a_structured_error(self):
        worktree = self.linked()
        local = Path(wp.inspect_repository(worktree)["repository"]["git_dir_exclude"]["path"])
        local.parent.mkdir()
        local.symlink_to("exclude")
        result = self.cli(worktree, "--json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout)["errors"][0]["code"], "path_unreadable")

    @unittest.skipIf(os.name == "nt", "Symlink privileges vary on Windows")
    def test_looping_effective_exclude_probe_is_a_structured_error(self):
        exclude = self.repo / ".git/info/exclude"
        exclude.parent.mkdir(exist_ok=True)
        exclude.symlink_to("exclude")
        result = self.cli(self.repo, "--json", "--check", "file")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        self.assertIn(json.loads(result.stdout)["errors"][0]["code"], {"git_failed", "path_unreadable"})

    def test_ambient_git_overrides_cannot_redirect_repository_or_index(self):
        other = self.base / "other"
        self.git(self.base, "init", "-q", str(other))
        self.write("cache", "x")
        self.git(self.repo, "add", "cache")
        malicious = {"GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other),
                     "GIT_COMMON_DIR": str(other / ".git"), "GIT_INDEX_FILE": str(other / "index"),
                     "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.bare", "GIT_CONFIG_VALUE_0": "true",
                     "GIT_CONFIG_PARAMETERS": "'core.bare=true'"}
        with patch.dict(os.environ, malicious):
            report = wp.inspect_repository(self.repo, ["cache"])
        self.assertEqual(report["repository"]["worktree_root"], str(self.repo))
        self.assertFalse(report["checks"][0]["tracking_checked"])
        self.assertEqual(report["environment"]["removed_git_variables"], sorted(malicious))

    def test_safe_directory_is_not_bypassed(self):
        # Git's ownership test hook is for tests, so assert command construction
        # instead of granting or changing ownership on the developer's machine.
        git = wp.Git(self.repo, 10)
        with patch("worktree_preflight.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            git.run("ls-files")
        command = run.call_args.args[0]
        self.assertIn("core.fsmonitor=false", command)
        self.assertNotIn("safe.directory=*", command)
        self.assertEqual(run.call_args.kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")
        self.assertEqual(run.call_args.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")

    @unittest.skipIf(os.name == "nt", "Executable shell hook test")
    def test_fsmonitor_hook_is_not_executed(self):
        marker = self.base / "hook-ran"
        hook = self.base / "fsmonitor"
        hook.write_text(f"#!/bin/sh\nprintf ran > '{marker}'\n")
        hook.chmod(0o700)
        self.write("tracked", "x")
        self.git(self.repo, "add", "tracked")
        self.git(self.repo, "config", "core.fsmonitor", str(hook))
        wp.inspect_repository(self.repo, ["tracked"])
        self.assertFalse(marker.exists())

    def test_rule_probe_does_not_read_a_corrupted_index(self):
        self.write(".gitignore", "cache\n")
        index = self.repo / ".git/index"
        index.write_bytes(b"deliberately not a Git index")
        before = (index.read_bytes(), index.stat().st_mtime_ns)
        report = wp.inspect_repository(self.repo, ["cache"], require_rule_ignore=True)
        self.assertEqual(report["exit_code"], 0)
        self.assertFalse(report["tracking_checked"])
        self.assertEqual((index.read_bytes(), index.stat().st_mtime_ns), before)

    def test_sparse_index_missing_promised_object_does_not_fetch(self):
        self.write("visible/file", "visible data")
        self.write("hidden/file", "different hidden data")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "Sparse fixture")
        hidden_tree = self.git(self.repo, "rev-parse", "HEAD:hidden").stdout.decode().strip()
        origin = self.base / "fixture origin.git"
        self.git(self.base, "clone", "--bare", "--no-hardlinks", str(self.repo), str(origin))
        self.git(self.repo, "remote", "add", "origin", str(origin))
        self.git(self.repo, "config", "remote.origin.promisor", "true")
        self.git(self.repo, "config", "remote.origin.partialclonefilter", "blob:none")
        self.git(self.repo, "sparse-checkout", "init", "--cone", "--sparse-index")
        self.git(self.repo, "sparse-checkout", "set", "visible")
        self.assertIn(b"hidden/", self.git(self.repo, "ls-files", "--sparse").stdout)
        # Layout and rule-only inspection do not need to read the index.
        self.assertEqual(wp.inspect_repository(self.repo)["status"], "ok")
        missing = self.repo / ".git/objects" / hidden_tree[:2] / hidden_tree[2:]
        missing.unlink()  # Remove only an object in this test-created fixture.
        def snapshot():
            return {str(p.relative_to(self.repo)): (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in (self.repo / ".git").rglob("*") if p.is_file()}
        before = snapshot()
        result = self.cli(self.repo, "--check", "hidden/file", "--json")
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)["tracking_checked"])
        self.assertEqual(result.stderr, "")
        self.assertEqual(snapshot(), before)
        self.assertFalse(missing.exists())
        # Rule-only checks must not expand or repair stale sparse indexes even
        # after every relevant configuration key and rules file is removed.
        for scope in ("--local", "--worktree"):
            for key in ("index.sparse", "core.sparseCheckout", "core.sparseCheckoutCone",
                        "remote.origin.promisor"):
                self.git(self.repo, "config", scope, "--unset-all", key, check=False)
        (self.repo / ".git/info/sparse-checkout").unlink()
        before = snapshot()
        result = self.cli(self.repo, "--check", "hidden/file", "--json")
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)["tracking_checked"])
        self.assertEqual(snapshot(), before)

    def test_stale_sparse_rules_and_split_index_stay_unchanged(self):
        self.write("visible/file", "visible")
        self.write("hidden/file", "hidden")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "Full index")
        rules = self.repo / ".git/info/sparse-checkout"
        rules.parent.mkdir(exist_ok=True)
        rules.write_text("/*\n!/*/\n/visible/\n")
        def snapshot():
            return {str(p.relative_to(self.repo)): (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in (self.repo / ".git").rglob("*") if p.is_file()}
        before = snapshot()
        report = wp.inspect_repository(self.repo, ["hidden/file", "visible/file", "cache"])
        self.assertFalse(report["tracking_checked"])
        self.assertEqual(snapshot(), before)
        rules.unlink()
        self.git(self.repo, "update-index", "--split-index")
        before = snapshot()
        report = wp.inspect_repository(self.repo, ["hidden/file"])
        self.assertFalse(report["tracking_checked"])
        self.assertEqual(snapshot(), before)

    def test_inspection_does_not_change_file_content_or_mtime(self):
        worktree = self.linked()
        (worktree / "cache.tmp").write_text("cache")
        (worktree / ".gitignore").write_text("*.tmp\n")
        def snapshot():
            return {str(p.relative_to(self.base)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                    for p in self.base.rglob("*") if p.is_file()}
        before = snapshot()
        wp.inspect_repository(worktree, ["cache.tmp", "missing"])
        self.assertEqual(snapshot(), before)

    def test_boundaries_and_bad_inputs(self):
        for path in ("../outside", str(self.base / "outside"), ".", ".git/config", "", "x\0y"):
            with self.subTest(path=path), self.assertRaises(wp.PreflightError):
                wp.inspect_repository(self.repo, [path])
        nested = self.repo / "nested"
        nested.mkdir()
        self.assertEqual(wp.inspect_repository(nested, ["../file"])["checks"][0]["path"], "file")

    def test_nonrepository_missing_directory_and_file(self):
        self.write("ordinary", "x")
        for directory in (self.base, self.base / "missing", self.repo / "ordinary"):
            with self.subTest(directory=directory), self.assertRaises(wp.PreflightError):
                wp.inspect_repository(directory)

    def test_corrupted_gitfile(self):
        invalid = self.base / "broken"
        invalid.mkdir()
        (invalid / ".git").write_text("gitdir: /this/does/not/exist\n")
        with self.assertRaises(wp.PreflightError):
            wp.inspect_repository(invalid)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "Requires FIFO")
    def test_fifo_effective_exclude_is_not_opened(self):
        info = self.repo / ".git/info"
        info.mkdir(exist_ok=True)
        os.mkfifo(info / "exclude")
        report = wp.inspect_repository(self.repo)
        self.assertEqual(report["diagnostics"][0]["code"], "unusable_exclude")
        with self.assertRaisesRegex(wp.PreflightError, "regular effective"):
            wp.inspect_repository(self.repo, ["cache"])

    def test_json_cli_success_failure_error_and_determinism(self):
        self.write(".gitignore", "*.tmp\n")
        success = self.cli(self.repo, "--json", "--check", "cache.tmp", "--require-rule-ignore")
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(success.stdout, self.cli(self.repo, "--json", "--check", "cache.tmp", "--require-rule-ignore").stdout)
        self.assertEqual(json.loads(success.stdout)["schema_version"], 1)
        failure = self.cli(self.repo, "--json", "--check", "cache.txt", "--require-rule-ignore")
        self.assertEqual(failure.returncode, 1)
        self.assertEqual(json.loads(failure.stdout)["requirements"]["failed_paths"], ["cache.txt"])
        error = self.cli(self.base, "--json")
        self.assertEqual(error.returncode, 2)
        self.assertEqual(json.loads(error.stdout)["status"], "error")
        self.assertEqual(error.stderr, "")
        usage = self.cli("--json", "--nonexistent-flag")
        self.assertEqual(json.loads(usage.stdout)["errors"][0]["code"], "usage")

    def test_human_help_and_version(self):
        self.assertIn("No paths checked", self.cli(self.repo).stdout)
        self.assertIn("--require-rule-ignore", self.cli("--help").stdout)
        self.assertEqual(self.cli("--version").stdout.strip(), wp.VERSION)


class FailureTests(unittest.TestCase):
    def test_timeout_missing_git_and_nonzero_errors(self):
        git = wp.Git(Path.cwd(), 0.5)
        for failure, code in ((FileNotFoundError(), "git_not_found"),
                              (subprocess.TimeoutExpired("git", 0.5), "git_timeout"),
                              (PermissionError("denied"), "git_execution_failed")):
            with self.subTest(code=code), patch("worktree_preflight.subprocess.run", side_effect=failure):
                with self.assertRaises(wp.PreflightError) as caught:
                    git.run("rev-parse")
                self.assertEqual(caught.exception.code, code)
        with patch("worktree_preflight.subprocess.run", return_value=subprocess.CompletedProcess([], 128, b"", b"fatal: broken\n")):
            with self.assertRaisesRegex(wp.PreflightError, "fatal: broken"):
                git.run("rev-parse")

    def test_nonfinite_timeout_and_empty_requirements(self):
        for timeout in (0, -1, float("nan"), float("inf"), 1e300, 301):
            with self.subTest(timeout=timeout), self.assertRaises(wp.PreflightError):
                wp.inspect_repository(timeout=timeout)
        with self.assertRaises(wp.PreflightError):
            wp.inspect_repository(require_rule_ignore=True)

    def test_old_git_and_invalid_output_errors(self):
        with patch.object(wp.Git, "text", return_value="git version 2.30.9"):
            with self.assertRaisesRegex(wp.PreflightError, "2.45"):
                wp.inspect_repository()
        git = wp.Git(Path.cwd(), 10)
        with patch.object(git, "text", return_value="--path-format=absolute\n.git"):
            with self.assertRaises(wp.PreflightError):
                git.path("--git-dir")


if __name__ == "__main__":
    unittest.main()

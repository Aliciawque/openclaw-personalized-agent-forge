"""Independent review probes. Does not modify the implementation under review."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'package_preflight.py'
spec = importlib.util.spec_from_file_location('preflight_under_review', MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class AdversarialReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'package'
        self.root.mkdir()
        (self.root/'soul.md').write_text('## Core drive\nReal body.\n')
        self.profile = {'name': 'review', 'files': {'soul.md': [['Core drive']]}}

    def findings(self, text):
        (self.root/'soul.md').write_text(text)
        return p.audit(self.root, self.profile, files_only=True)['findings']

    def test_literal_comment_opener_in_fenced_code_does_not_hide_headings(self):
        text = '```html\n<!--\n```\n## Core drive\nReal body.\n'
        self.assertEqual([s['heading'] for s in p.sections(text)], ['Core drive'])

    def test_literal_comment_opener_in_inline_code_does_not_hide_link(self):
        self.assertIn('missing_link', [x['code'] for x in self.findings('`<!--`\n[bad](missing.md)')])

    def test_unmatched_unequal_backticks_do_not_hide_link(self):
        self.assertIn('missing_link', [x['code'] for x in self.findings('`[bad](missing.md)``')])

    def test_multiline_code_span_link_is_ignored(self):
        self.assertEqual(self.findings('`example\n[bad](missing.md)\nend`'), [])

    def test_escaped_link_opening_is_literal(self):
        self.assertEqual(self.findings(r'\[bad](missing.md)'), [])

    def test_backtick_in_fence_info_string_is_not_a_fence(self):
        text = '```md`not-a-fence\n## Core drive\nReal body.\n'
        self.assertEqual([s['heading'] for s in p.sections(text)], ['Core drive'])

    def test_regular_file_cannot_be_intermediate_path_component(self):
        self.assertIsNotNone(p.link_target_issue(self.root, 'soul.md/../soul.md'))

    def test_windows_drive_double_slash_not_accepted(self):
        self.assertIsNotNone(p.link_target_issue(self.root, 'C://private/file'))

    def test_deep_invalid_profile_returns_configuration_json_not_traceback(self):
        profile = Path(self.tmp.name)/'deep.json'
        profile.write_text('{"name":"test","files":{"soul.md":' + '['*10000 + '"x"' + ']'*10000 + '}}')
        result = subprocess.run([sys.executable, '-B', str(MODULE), str(self.root), '--profile', str(profile), '--json'], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2, result.stderr[-200:])
        self.assertFalse(json.loads(result.stdout)['passed'])
        self.assertEqual(result.stderr, '')

    def test_symlink_loop_refused(self):
        (self.root/'loop').symlink_to(self.root/'loop')
        self.assertEqual(p.link_target_issue(self.root, 'loop')[0], 'unsafe_link')

    def test_intermediate_symlink_refused_even_when_normalized_away(self):
        (self.root/'alias').symlink_to(self.root)
        self.assertEqual(p.link_target_issue(self.root, 'alias/../soul.md')[0], 'unsafe_link')

    def test_directory_parent_path_allowed(self):
        (self.root/'sub').mkdir()
        self.assertIsNone(p.link_target_issue(self.root, 'sub/../soul.md'))

    def test_encoded_absolute_path_refused(self):
        self.assertEqual(p.link_target_issue(self.root, '%2Ftmp%2Fsecret')[0], 'unsafe_link')

    def test_linked_content_not_opened_and_package_unchanged(self):
        linked = self.root/'reference.md'
        linked.write_bytes(b'\xff' * 100)
        (self.root/'soul.md').write_text('## Core drive\n[reference](reference.md)')
        before = {q.name: (q.read_bytes(), q.stat().st_mtime_ns) for q in self.root.iterdir()}
        actual_open = os.open
        opened = []
        def readonly_open(path, flags, *args, **kwargs):
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
            opened.append(Path(path).name)
            return actual_open(path, flags, *args, **kwargs)
        with patch.object(p.os, 'open', readonly_open):
            result = p.audit(self.root, self.profile)
        self.assertTrue(result['passed'])
        self.assertEqual(opened, ['soul.md'])
        after = {q.name: (q.read_bytes(), q.stat().st_mtime_ns) for q in self.root.iterdir()}
        self.assertEqual(before, after)

    def test_inline_code_cannot_swallow_a_new_paragraph_heading(self):
        text = 'A literal unmatched `\n\n## Core drive\nAn obligation uses `x`.\n'
        self.assertEqual([s['heading'] for s in p.sections(text)], ['Core drive'])

    def test_escaped_backtick_does_not_hide_a_real_link(self):
        self.assertIn('missing_link', [x['code'] for x in self.findings(r'\`[bad](missing.md)`')])

    def test_surrogate_profile_strings_do_not_break_json_output(self):
        for key in ['name', 'source']:
            with self.subTest(key=key):
                value = dict(self.profile)
                value[key] = chr(0xD800)
                profile = Path(self.tmp.name)/'surrogate.json'
                profile.write_text(json.dumps(value))
                result = subprocess.run([sys.executable, '-B', str(MODULE), str(self.root), '--profile', str(profile), '--json'], capture_output=True, text=True, timeout=5)
                self.assertIn(result.returncode, [0, 2], result.stderr[-200:])
                json.loads(result.stdout)
                self.assertEqual(result.stderr, '')

    def test_profile_leaf_symlink_refused(self):
        target = Path(self.tmp.name)/'profile.json'
        target.write_text(json.dumps(self.profile))
        alias = Path(self.tmp.name)/'alias.json'
        alias.symlink_to(target)
        with self.assertRaises(ValueError):
            p.load_profile(alias)

if __name__ == '__main__':
    unittest.main(verbosity=2)

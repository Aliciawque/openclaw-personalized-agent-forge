import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import package_preflight as p

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'package'
        self.root.mkdir()
        for name, labels in p.REQUIRED.items():
            (self.root/name).write_text('\n\n'.join('## '+label+'\nA concrete professional obligation.' for label in labels), encoding='utf8')
    def write(self, value, name='soul.md'):
        (self.root/name).write_text(value, encoding='utf8')
    def append(self, value):
        with (self.root/'soul.md').open('a', encoding='utf8') as f:f.write('\n'+value+'\n')
    def codes(self):return [i['code'] for i in p.audit(self.root)['findings']]
    def test_complete_contract(self):
        self.assertTrue(p.audit(self.root)['passed'])
        self.assertEqual(sum(map(len,p.REQUIRED.values())),26)
    def test_missing_file(self):
        (self.root/'tools.md').unlink();self.assertIn('unreadable_file',self.codes())
    def test_empty_file(self):self.write('');self.assertIn('empty_file',self.codes())
    def test_invalid_utf8(self):
        (self.root/'soul.md').write_bytes(b'\xff');self.assertIn('unreadable_file',self.codes())
    def test_utf8_bom(self):
        f=self.root/'soul.md';f.write_bytes(b'\xef\xbb\xbf'+f.read_bytes());self.assertTrue(p.audit(self.root)['passed'])
    def test_oversized(self):self.write('x'*(p.MAX_BYTES+1));self.assertIn('unreadable_file',self.codes())
    def test_directory_in_place_of_file(self):
        f=self.root/'tools.md';f.unlink();f.mkdir();self.assertIn('unreadable_file',self.codes())
    def test_file_symlink(self):
        f=self.root/'tools.md';f.unlink();f.symlink_to(self.root/'soul.md');self.assertIn('unreadable_file',self.codes())
    def test_root_symlink(self):
        link=Path(self.tmp.name)/'alias';link.symlink_to(self.root)
        with self.assertRaises(ValueError):p.audit(link)
    def test_missing_root(self):
        with self.assertRaises(ValueError):p.audit(self.root/'no')
    def test_empty_heading(self):
        self.append('## Core drive');self.assertIn('duplicate_section',self.codes())
    def test_empty_section(self):
        self.write('## Core drive\n<!-- hidden -->\n## Professional beliefs\ntext');self.assertIn('empty_section',self.codes())
    def test_nonlatin_body(self):
        self.write('## Core drive\n调查实际问题');self.assertNotIn('empty_section',self.codes())
    def test_punctuation_heading_normalization(self):
        f=self.root/'soul.md';self.write(f.read_text().replace('Non-negotiables','NON NEGOTIABLES'));self.assertTrue(p.audit(self.root)['passed'])
    def test_fenced_fake_heading(self):
        self.write('```md\n## Core drive\ntext\n```');self.assertIn('missing_section',self.codes())
    def test_long_fence_short_inner(self):
        self.assertEqual(p.sections('````md\n```\n## hidden\ntext\n````\n## visible\ntext')[0]['heading'],'visible')
    def test_tilde_fence(self):self.assertEqual(p.sections('~~~md\n## hidden\ntext\n~~~'),[])
    def test_fence_different_character(self):self.assertEqual(p.sections('```\n~~~\n## hidden\ntext'),[])
    def test_html_comment_heading(self):self.assertEqual(p.sections('<!--\n## hidden\ntext\n-->'),[])
    def test_unclosed_comment(self):self.assertEqual(p.sections('<!--\n## hidden\ntext'),[])
    def test_nested_section_body(self):self.assertTrue(p.sections('## Core drive\n### Detail\nAn obligation')[0]['nonempty'])
    def test_heading_not_body(self):self.assertFalse(p.sections('## Core drive\n### Detail')[0]['nonempty'])
    def test_sibling_not_body(self):self.assertFalse(p.sections('## Core drive\n## Next\ntext')[0]['nonempty'])
    def test_fenced_content_alone_is_not_prose(self):self.assertFalse(p.sections('## Core drive\n```\ncode\n```')[0]['nonempty'])
    def test_simple_link_exists(self):self.append('[Tools](tools.md)');self.assertTrue(p.audit(self.root)['passed'])
    def test_link_missing(self):self.append('[Missing](missing.md)');self.assertIn('missing_link',self.codes())
    def test_fragment_not_followed(self):self.append('[Tools](tools.md#missing-fragment)');self.assertTrue(p.audit(self.root)['passed'])
    def test_local_fragment_not_checked(self):self.append('[Here](#fake)');self.assertTrue(p.audit(self.root)['passed'])
    def test_remote_not_fetched(self):self.append('[Remote](https://invalid.example/x)');self.assertTrue(p.audit(self.root)['passed'])
    def test_external_image_not_fetched(self):self.append('![Remote](https://invalid.example/image.png)');self.assertTrue(p.audit(self.root)['passed'])
    def test_code_link_ignored(self):self.append('`[fake](missing.md)`');self.assertNotIn('missing_link',self.codes())
    def test_fenced_link_ignored(self):self.append('```\n[bad](missing.md)\n```');self.assertNotIn('missing_link',self.codes())
    def test_parent_escape(self):self.append('[outside](../secret.md)');self.assertIn('unsafe_link',self.codes())
    def test_encoded_escape(self):self.append('[outside](%2e%2e/secret.md)');self.assertIn('unsafe_link',self.codes())
    def test_absolute_path(self):self.append('[outside](/tmp/x)');self.assertIn('unsafe_link',self.codes())
    def test_windows_path(self):self.append('[outside](C:/private/x)');self.assertIn('unsafe_link',self.codes())
    def test_nul_path(self):self.append('[outside](bad%00path)');self.assertIn('unsafe_link',self.codes())
    def test_backslash_path(self):self.append('[outside](..\\x)');self.assertIn('unsafe_link',self.codes())
    def test_internal_symlink(self):
        (self.root/'shortcut').symlink_to(self.root/'tools.md');self.append('[alias](shortcut)');self.assertIn('unsafe_link',self.codes())
    def test_symlink_directory(self):
        (self.root/'alias').symlink_to(self.root);self.append('[alias](alias/tools.md)');self.assertIn('unsafe_link',self.codes())
    def test_encoded_unicode_space_link(self):
        (self.root/'测试 文档.md').write_text('text');self.append('[docs](%E6%B5%8B%E8%AF%95%20%E6%96%87%E6%A1%A3.md)');self.assertTrue(p.audit(self.root)['passed'])
    def test_angle_link(self):
        (self.root/'my doc.md').write_text('text');self.append('[docs](<my doc.md>)');self.assertTrue(p.audit(self.root)['passed'])
    def test_link_title(self):self.append('[docs](tools.md "Tools")');self.assertTrue(p.audit(self.root)['passed'])
    def test_files_only(self):
        self.write('Alternative organization');self.assertTrue(p.audit(self.root,files_only=True)['passed'])
    def test_files_only_still_links(self):self.write('[bad](../x)');self.assertFalse(p.audit(self.root,files_only=True)['passed'])
    def test_read_only(self):
        before={f.name:(f.read_bytes(),f.stat().st_mtime_ns) for f in self.root.iterdir()};p.audit(self.root)
        after={f.name:(f.read_bytes(),f.stat().st_mtime_ns) for f in self.root.iterdir()};self.assertEqual(before,after)
    def profile(self, value):
        f=Path(self.tmp.name)/'profile.json';f.write_text(json.dumps(value));return f
    def test_alias_profile(self):
        f=self.profile({'name':'中文','files':{'soul.md':[['核心目标','Core drive']]}})
        self.write('## 核心目标\n按实际证据协作');self.assertTrue(p.audit(self.root,p.load_profile(f))['passed'])
    def test_alias_duplicate_sections(self):
        f=self.profile({'name':'alias','files':{'soul.md':[['核心目标','Core drive']]}})
        self.write('## 核心目标\ntext\n## Core drive\ntext');self.assertEqual(p.audit(self.root,p.load_profile(f))['findings'][0]['code'],'duplicate_section')
    def test_invalid_profiles(self):
        for data in [{}, {'name':'x','files':{}},{'name':'x','files':{'../x.md':[['A']]}},{'name':'x','files':{'x.md':[['A'],['a']]}},{'name':'x','files':{'x.md':[['']]}},{'name':'x','files':{'x.md':['A']}}]:
            with self.subTest(data=data),self.assertRaises(ValueError):p.load_profile(self.profile(data))
    def test_bad_json_profile(self):
        f=self.profile({});f.write_text('{')
        with self.assertRaises(ValueError):p.load_profile(f)
    def test_cli_pass(self):
        r=subprocess.run([sys.executable,p.__file__,str(self.root),'--json'],capture_output=True,text=True);self.assertEqual(r.returncode,0);self.assertTrue(json.loads(r.stdout)['passed'])
    def test_cli_failure(self):
        self.write('');r=subprocess.run([sys.executable,p.__file__,str(self.root),'--json'],capture_output=True,text=True);self.assertEqual(r.returncode,1);self.assertFalse(json.loads(r.stdout)['passed'])
    def test_cli_configuration_error(self):
        r=subprocess.run([sys.executable,p.__file__,str(self.root/'absent'),'--json'],capture_output=True,text=True);self.assertEqual(r.returncode,2);self.assertIn('error',json.loads(r.stdout))
    def test_fifo_refused_without_blocking(self):
        if not hasattr(os,'mkfifo'):self.skipTest('no FIFO support')
        f=self.root/'tools.md';f.unlink();os.mkfifo(f);self.assertIn('unreadable_file',self.codes())

if __name__=='__main__':unittest.main()

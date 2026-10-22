import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from analyzer.integration import join_results, write_integrated_report
from integrated_cli import run


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'target'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Alice')
        self.git('config', 'user.email', 'alice@example.com')
        (self.repo / 'src/pkg').mkdir(parents=True)
        (self.repo / 'src/pkg/__init__.py').write_text('')
        (self.repo / 'src/pkg/service.py').write_text('def helper():\n    return 1\n\ndef caller():\n    return helper()\n\ndef removed():\n    return 0\n')
        (self.repo / 'src/pkg/danger.py').write_text('raise RuntimeError("TARGET MUST NOT EXECUTE")\n')
        self.git('add', '.')
        self.git('commit', '-m', 'feat: initial')
        self.initial = self.git('rev-parse', 'HEAD')
        self.git('config', 'user.name', 'Bob')
        self.git('config', 'user.email', 'bob@example.com')
        (self.repo / 'src/pkg/service.py').write_text('def helper():\n    return 2\n\ndef caller():\n    return helper()\n')
        self.git('add', '.')
        self.git('commit', '-m', 'fix: update helper')
        self.head = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def test_committed_snapshot_join_and_reports(self):
        (self.repo / 'src/pkg/service.py').write_text('def dirty_only():\n    return 99\n')
        out = self.root / 'report'
        result = run(str(self.repo), str(out))
        self.assertEqual(result['commit'], self.head)
        helper = next(r for r in result['functions'] if r['name'] == 'helper')
        self.assertEqual(helper['match'], 'unique_key')
        self.assertEqual(helper['change_count'], 1)
        self.assertEqual(helper['authors'], ['alice@example.com', 'bob@example.com'])
        self.assertTrue(any(e['source'].endswith('.caller') for e in helper['callers']))
        removed = next(r for r in result['functions'] if r['name'] == 'removed')
        self.assertEqual(removed['match'], 'unmatched')
        self.assertFalse(any('dirty_only' in n for n in result['nodes']))
        for path in ['index.html', 'integrated_result.json', 'git/report.html',
                     'git/git_insights.json', 'static/report.html', 'static/graph_result.json']:
            self.assertTrue((out / path).is_file(), path)
        graph = json.loads((out / 'static/graph_result.json').read_text())
        self.assertEqual(graph['commit'], self.head)
        self.assertIn('dirty_only', (self.repo / 'src/pkg/service.py').read_text())
        with self.assertRaisesRegex(ValueError, '새 출력 폴더'):
            run(str(self.repo), str(out))

    def test_non_head_revision_and_skipped_link(self):
        linked = False
        try:
            (self.repo / 'outside.py').symlink_to(self.root / 'missing')
            linked = True
        except (OSError, NotImplementedError):
            pass  # Some Windows accounts cannot create symlinks.
        if linked:
            self.git('add', '.')
            self.git('commit', '-m', 'chore: symlink')
        result = run(str(self.repo), str(self.root / 'old'), revision=self.initial)
        self.assertEqual(result['commit'], self.initial)
        self.assertTrue(any(n['name'] == 'removed' for n in result['nodes'].values()))
        if linked:
            latest = run(str(self.repo), str(self.root / 'latest'))
            self.assertTrue(any('outside.py' in w for w in latest['warnings']))

    def test_url_branch_uses_single_clone(self):
        self.git('branch', 'old-version', self.initial)
        real_run = subprocess.run
        clones = []
        def transport(args, **kwargs):
            if args[:2] == ['git', 'clone']:
                clones.append(args[-2])
                args = [*args[:-2], str(self.repo), args[-1]]
            return real_run(args, **kwargs)
        with patch('integrated_cli.subprocess.run', side_effect=transport):
            result = run('https://github.com/example/target', str(self.root / 'url'), revision='old-version')
        self.assertEqual(clones, ['https://github.com/example/target.git'])
        self.assertEqual(result['repository'], 'example/target')
        self.assertEqual(result['commit'], self.initial)

    def test_mismatch_ambiguity_and_html_escape(self):
        history = {'head': 'abc', 'repository': 'test', 'source': {}, 'scope': {}, 'pairs': [],
                   'warnings': ['</script><script>alert(1)</script>'],
                   'commits': [{'sha': 'abc', 'author': 'a', 'date': '2026-01-01',
                                'message': 'fix', 'classification': {}, 'excluded_reason': None,
                                'files': [{'path': 'f.py', 'old_path': 'f.py',
                                           'functions': [{'name': 'f', 'kind': 'modified', 'facts': []}]}]}]}
        symbols = {'commit': 'abc', 'symbols': [
            {'id': 'one', 'kind': 'FUNCTION', 'file': 'f.py', 'qualified_name': 'f'},
            {'id': 'two', 'kind': 'FUNCTION', 'file': 'f.py', 'qualified_name': 'f'}]}
        graph = {'commit': 'abc', 'nodes': [], 'edges': []}
        result = join_results(history, symbols, graph)
        self.assertEqual(result['functions'][0]['match'], 'ambiguous_key')
        self.assertEqual(result['functions'][0]['callers'], [])
        write_integrated_report(result, self.root / 'html')
        self.assertNotIn('</script><script>alert(1)', (self.root / 'html/index.html').read_text())
        wrong = copy.deepcopy(graph)
        wrong['commit'] = 'wrong'
        with self.assertRaises(ValueError):
            join_results(history, symbols, wrong)


if __name__ == '__main__':
    unittest.main()

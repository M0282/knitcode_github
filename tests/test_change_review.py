import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from analyzer.change_review import graph_delta, impact_candidates, missing_cochanges
from change_review_cli import run


class ChangeReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'project'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Tester')
        self.git('config', 'user.email', 'tester@example.com')
        self.put('pkg/__init__.py', '')
        self.put('pkg/service.py', 'def leaf(n):\n    return n\n')
        self.put('pkg/api.py', 'from .service import leaf\ndef middle(x):\n    return leaf(x)\ndef top(x):\n    return middle(x)\n')
        self.put('tests/test_api.py', 'from pkg.api import top\ndef test_top():\n    assert top(1)\n')
        self.put('tests/test_service.py', 'from pkg.service import leaf\ndef test_leaf():\n    assert leaf(1)\n')
        self.put('legacy.py', 'def removed():\n    return 1\ndef old_caller():\n    return removed()\n')
        self.put('danger.py', 'raise RuntimeError("ANALYSIS MUST NOT EXECUTE TARGET CODE")\n')
        self.commit('feat: initial')
        for n in range(1, 4):
            self.put('pkg/service.py', f'def leaf(n):\n    return n + {n}\n')
            self.put('tests/test_service.py', f'from pkg.service import leaf\ndef test_leaf():\n    assert leaf(1) == {n+1}\n')
            self.commit(f'fix: service revision {n}')
        self.base = self.git('rev-parse', 'HEAD')
        self.put('pkg/service.py', 'def leaf(n, currency):\n    return extra(n)\ndef extra(n):\n    return n + 4\n')
        self.put('legacy.py', 'def old_caller():\n    return removed()\n')
        self.commit('feat: new API </script><script>alert(1)</script>')
        self.head = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], capture_output=True,
                              text=True, check=True).stdout.strip()

    def put(self, path, text):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)

    def analyze(self, label='report', **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return run(str(self.repo), base=self.base, head=self.head,
                       output=str(self.root / label), **kwargs)

    def test_end_to_end_signature_impact_tests_cochanges(self):
        self.put('pkg/service.py', 'def dirty_only():\n    pass\n')
        data = self.analyze()
        self.assertEqual(data['base'], self.base)
        self.assertEqual(data['head'], self.head)
        self.assertEqual(data['signature_changes'][0]['name'], 'leaf')
        self.assertEqual(data['signature_changes'][0]['after'], 'leaf(n, currency)')
        head_impact = next(r for r in data['impacts'] if r['side'] == 'head' and r['function'] == 'leaf')
        candidates = {c['node']['canonical_name']: c for c in head_impact['candidates']}
        self.assertEqual(candidates['pkg.api.middle']['distance'], 1)
        self.assertEqual(candidates['pkg.api.top']['distance'], 2)
        self.assertFalse(candidates['pkg.api.top']['file_changed'])
        self.assertEqual(candidates['tests.test_api.test_top']['distance'], 3)
        self.assertEqual(candidates['tests.test_api.test_top']['path'][0]['source'], 'FUNCTION:tests.test_api.test_top')
        self.assertEqual(candidates['tests.test_api.test_top']['path'][-1]['target'], 'FUNCTION:pkg.service.leaf')
        removed = next(r for r in data['impacts'] if r['side'] == 'base' and r['function'] == 'removed')
        self.assertTrue(any(c['node']['name'] == 'old_caller' for c in removed['candidates']))
        test = next(r for r in data['test_candidates'] if r['side'] == 'head' and r['file'] == 'tests/test_api.py')
        self.assertTrue(any(r['type'] == 'call_path' for r in test['reasons']))
        co = next(r for r in data['cochanges']['recommendations'] if r['candidate_file'] == 'tests/test_service.py')
        self.assertEqual(co['support'], 3)
        self.assertEqual(co['conditional_ratio'], 1)
        self.assertNotIn(self.head, co['evidence_commits'])
        self.assertEqual(data['cochanges']['history_commit'], self.base)
        self.assertTrue(any(r['target']['name'] == 'pkg.service.extra' for r in data['structure']['added_relations']))
        self.assertTrue(any(r['target']['name'] == 'legacy.removed' for r in data['structure']['removed_relations']))
        self.assertNotIn('dirty_only', json.dumps(data))
        self.assertIn('dirty_only', (self.repo / 'pkg/service.py').read_text())
        out = self.root / 'report'
        for file in ('index.html', 'change_review.json', 'base/report.html',
                     'head/report.html', 'git/report.html', 'git/git_insights.json'):
            self.assertTrue((out / file).is_file())
        html = (out / 'index.html').read_text()
        self.assertNotIn('</script><script>alert(1)', html)
        self.assertNotIn('__REPORT_DATA__', html)
        self.assertEqual(json.loads((out / 'change_review.json').read_text())['head'], self.head)
        git_data = json.loads((out / 'git/git_insights.json').read_text())
        self.assertEqual(git_data['head'], self.head)
        self.assertEqual(data['git_summary']['head'], self.head)
        self.assertFalse(data['git_summary']['github_api_enabled'])

    def test_depth_limit_is_explicit(self):
        data = self.analyze(max_depth=1)
        root = next(r for r in data['impacts'] if r['side'] == 'head' and r['function'] == 'leaf')
        self.assertTrue(root['depth_limited'])
        self.assertFalse(any(c['node']['name'] == 'top' for c in root['candidates']))

    def test_parse_failure_and_threshold(self):
        self.put('bad.py', 'def broken(:\n')
        self.commit('feat: syntax error fixture')
        self.head = self.git('rev-parse', 'HEAD')
        data = self.analyze(min_support=4)
        self.assertTrue(any('bad.py' in w for w in data['warnings']))
        self.assertEqual(data['cochanges']['recommendations'], [])
        file = next(r for r in data['files'] if r['path'] == 'bad.py')
        self.assertTrue(file['diagnostics'])

    def test_merge_base_and_remote_branch_single_clone(self):
        self.git('branch', 'feature', self.head)
        self.git('checkout', '-b', 'target', self.base)
        self.put('README.md', 'target-only change')
        self.commit('docs: target side')
        target_sha = self.git('rev-parse', 'HEAD')
        real_run = subprocess.run
        clones = []
        def transport(args, **kwargs):
            if args[:2] == ['git', 'clone']:
                clones.append(args[-2])
                args = [*args[:-2], str(self.repo), args[-1]]
            return real_run(args, **kwargs)
        def fake_github(data, max_commits):
            data['github'] = {'enabled': True, 'records': [{'sha': data['head']}],
                              'warnings': [], 'commit_limit': max_commits}
        with patch('change_review_cli.subprocess.run', side_effect=transport), \
             patch('change_review_cli.enrich_github', side_effect=fake_github), \
             contextlib.redirect_stdout(io.StringIO()):
            result = run('https://github.com/example/project', base='target', head='feature',
                         merge_base=True, output=str(self.root / 'remote'),
                         github_api=True, api_commits=7)
        self.assertEqual(len(clones), 1)
        self.assertEqual(result['base'], self.base)
        self.assertEqual(result['source']['requested_base_sha'], target_sha)
        self.assertEqual(result['head'], self.head)
        self.assertFalse(any(f['path'] == 'README.md' for f in result['files']))
        self.assertTrue(result['git_summary']['github_api_enabled'])
        self.assertEqual(result['git_summary']['github_records'], 1)

    def test_same_revision_and_output_protection(self):
        self.head = self.base
        data = self.analyze()
        self.assertEqual(data['summary']['changed_files'], 0)
        self.assertEqual(data['impacts'], [])
        with self.assertRaisesRegex(ValueError, '출력 폴더'):
            self.analyze()
        for options in ({'max_nodes': 0}, {'min_support': 0}, {'min_confidence': 2}, {'source_roots': ['../escape']}):
            with self.assertRaises(ValueError):
                self.analyze(label='invalid', **options)

    def test_file_rename_preserves_path_evidence(self):
        self.git('reset', '--hard', self.base)
        self.git('mv', 'pkg/service.py', 'pkg/renamed_service.py')
        self.commit('refactor: rename file')
        self.head = self.git('rev-parse', 'HEAD')
        data = self.analyze()
        file = next(f for f in data['files'] if f['path'] == 'pkg/renamed_service.py')
        self.assertTrue(file['status'].startswith('R'))
        self.assertEqual(file['functions'][0]['kind'], 'file_renamed')
        self.assertTrue(any(r['file'] == 'pkg/service.py' and r['side'] == 'base' for r in data['impacts']))
        self.assertTrue(any(r['file'] == 'pkg/renamed_service.py' and r['side'] == 'head' for r in data['impacts']))


class GraphUnitTests(unittest.TestCase):
    def test_cycle_duplicate_roots_and_budget(self):
        nodes = [{'id': x, 'file': 'project/f.py', 'kind': 'FUNCTION', 'name': x,
                  'canonical_name': 'f.' + x} for x in ('f', 'g', 'h', 'other_f')]
        edges = [{'source': s, 'target': t, 'type': 'CALLS', 'evidence': {'certainty': 'may_call'}}
                 for s, t in [('g','f'), ('h','g'), ('f','h'), ('g','other_f')]]
        symbols = {'repository': 'project', 'symbols': [dict(n, qualified_name='f' if n['id'] == 'other_f' else n['id']) for n in nodes]}
        snapshots = {'head': {'symbols': symbols, 'graph': {'repository': 'project', 'commit': 'abc', 'nodes': nodes, 'edges': edges}}}
        files = [{'path': 'f.py', 'old_path': 'f.py', 'functions': [{'name': 'f', 'kind': 'modified', 'before': {}, 'after': {}}]}]
        results = impact_candidates(files, snapshots, max_depth=5, max_nodes=1)
        row = results[0]
        self.assertTrue(row['ambiguous_root'])
        self.assertTrue(row['node_limited'])
        self.assertEqual(len(row['candidates']), 2)
        self.assertTrue(all(c['path'][0]['evidence']['certainty'] == 'may_call' for c in row['candidates']))

    def test_line_shift_does_not_invent_relation(self):
        nodes = [{'id': x, 'file': 'project/f.py', 'kind': 'FUNCTION', 'canonical_name': 'f.' + x} for x in ('a','b')]
        before = {'repository':'project','nodes': nodes, 'edges':[{'source':'a','target':'b','type':'CALLS','evidence':{'line':3}}]}
        after = copy.deepcopy(before)
        after['edges'][0]['evidence']['line'] = 30
        diff = graph_delta(before, after)
        self.assertEqual(diff['added_relations'], [])
        self.assertEqual(diff['removed_relations'], [])

    def test_cochange_filters_changed_missing_and_direction(self):
        pair = {'a':'a.py','b':'b.py','count':3,'a_changes':3,'b_changes':10,
                'p_b_given_a':1,'p_a_given_b':0.3,'jaccard':0.3,'commits':['1','2','3']}
        history = {'head':'base','scope':{},'pairs':[pair]}
        files = [{'path':'a.py','old_path':'a.py','status':'M'}]
        self.assertEqual(len(missing_cochanges(history, files, {'a.py','b.py'})['recommendations']), 1)
        self.assertEqual(missing_cochanges(history, files, {'a.py'})['recommendations'], [])
        self.assertEqual(missing_cochanges(history, files+[{'path':'b.py','old_path':'b.py','status':'M'}], {'a.py','b.py'})['recommendations'], [])
        self.assertEqual(missing_cochanges(history, [{'path':'b.py','old_path':'b.py','status':'M'}], {'a.py','b.py'})['recommendations'], [])


if __name__ == '__main__':
    unittest.main()

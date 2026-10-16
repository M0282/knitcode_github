import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from git_insights_cli import analyze_target, write_report


class ExternalTargetTests(unittest.TestCase):
    def test_url_targets_external_history(self):
        with tempfile.TemporaryDirectory() as temp:
            upstream = Path(temp) / 'external'
            upstream.mkdir()
            def git(*args):
                return subprocess.run(['git', '-C', str(upstream), *args], check=True, capture_output=True)
            git('init', '-b', 'main')
            git('config', 'user.name', 'Alice')
            git('config', 'user.email', 'alice@example.com')
            (upstream / 'service.py').write_text('def lookup(x):\n    return x.name\n')
            (upstream / 'test_service.py').write_text('# initial\n')
            git('add', '.')
            git('commit', '-m', 'feat: initial service')
            git('config', 'user.name', 'Bob')
            git('config', 'user.email', 'bob@example.com')
            (upstream / 'service.py').write_text('def lookup(x):\n    if x is None:\n        return None\n    return x.name\n')
            (upstream / 'test_service.py').write_text('# regression case\n')
            git('add', '.')
            git('commit', '-m', 'fix: missing user')
            git('checkout', '-b', 'feature')
            (upstream / 'extra.py').write_text('def extra():\n    return 1\n')
            git('add', '.')
            git('commit', '-m', 'feat: extra')
            git('checkout', 'main')
            real_run = subprocess.run
            targets = []
            def transport(args, **kwargs):
                if args[:2] == ['git', 'clone']:
                    targets.append(args[-2])
                    args = [*args[:-2], str(upstream), args[-1]]
                return real_run(args, **kwargs)
            # Only substitute the network transport; real clone, history and AST run end to end.
            with patch('git_insights_cli.subprocess.run', side_effect=transport):
                data = analyze_target('https://github.com/example/external')
                branch = analyze_target('https://github.com/example/external', revision='feature')
            self.assertEqual(targets, ['https://github.com/example/external.git'] * 2)
            self.assertEqual(data['repository'], 'example/external')
            hot = next(r for r in data['hotspots'] if r['name']=='service.py::lookup')
            self.assertEqual(hot['count'],1)
            self.assertEqual(hot['bugfixes'],1)
            event = next(r for r in data['test_changes'] if r['path']=='service.py')
            self.assertTrue(event['related_test_changed'])
            self.assertEqual(event['candidates'][0]['path'],'test_service.py')
            self.assertEqual(len(data['commits']), 2)
            self.assertEqual(len(branch['commits']), 3)
            self.assertEqual({a['id'] for a in data['authors']}, {'alice@example.com', 'bob@example.com'})
            self.assertEqual(data['pairs'][0]['count'], 1)
            fix = next(c for c in data['commits'] if c['classification']['type'] == 'bugfix')
            change = next(f for f in fix['files'] if f['path'] == 'service.py')['functions'][0]
            self.assertIn('조건 분기: 0 → 1', change['facts'])
            self.assertIn('+    if x is None:', fix['files'][0]['diff'])
            data['warnings'].append('</script><script>alert(1)</script>')
            output = Path(temp) / 'report'
            write_report(data, output)
            self.assertEqual(json.loads((output / 'git_insights.json').read_text())['repository'], 'example/external')
            self.assertNotIn('</script><script>alert(1)', (output / 'report.html').read_text())

    def test_reject_other_url(self):
        with self.assertRaises(ValueError):
            analyze_target('https://example.com/project')


if __name__ == '__main__':
    unittest.main()

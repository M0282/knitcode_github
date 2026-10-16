import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from analyzer.github_api import Client, enrich_github, issue_refs

class ExtensionsTests(unittest.TestCase):
    def test_issue_refs(self):
        self.assertEqual(issue_refs('fix #12 and other/repo#42 https://github.com/other/repo/issues/43', 'owner/repo'), [('other/repo',42),('other/repo',43),('owner/repo',12)])

    def test_api_links_and_unknown_checks(self):
        class Fake(Client):
            def get(self, path):
                self.requests+=1
                if '/pulls?' in path: return [{'number':1,'title':'fix #12','body':'case','html_url':'https://github.com/o/r/pull/1'}]
                if '/issues/12' in path: return {'number':12,'title':'bug','state':'closed','body':'reproduce'}
                if '/check-runs?' in path: return None
                return {'statuses':[{'context':'ci','state':'failure'}]}
        d={'repository':'o/r','commits':[{'sha':'a'*40,'message':'fix'}]}
        enrich_github(d,client=Fake())
        r=d['github']['records'][0]
        self.assertEqual(r['issues'][0]['number'],12)
        self.assertFalse(r['checks_complete'])
        self.assertEqual(r['statuses'][0]['state'],'failure')

    def test_pagination(self):
        class Fake(Client):
            def get(self,path): return [0]*100 if 'page=1' in path.split('per_page=100&')[-1] else [1]
        r=Fake().pages('/repos/a/b/commits/x/pulls')
        self.assertEqual(len(r['items']),101)
        self.assertTrue(r['complete'])

    def test_rate_limit_and_no_token_leak(self):
        c=Client(token='never-store-this')
        with patch('analyzer.github_api.build_opener') as opener:
            opener.return_value.open.side_effect=HTTPError('https://api.github.com',403,'denied',{'X-RateLimit-Remaining':'0'},None)
            self.assertIsNone(c.get('/repos/a/b'))
            self.assertIsNone(c.get('/repos/a/c'))
        self.assertTrue(c.stopped)
        self.assertEqual(c.requests,1)
        self.assertNotIn('never-store-this',str(c.warnings))

if __name__=='__main__': unittest.main()

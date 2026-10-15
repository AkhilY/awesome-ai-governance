import tempfile
import unittest
from pathlib import Path
from app import create_app, assess, QUESTIONS

class DeskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = dict(TESTING=True, SECRET_KEY='test-key', DATABASE=str(Path(self.tmp.name) / 'test.db'))
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as s:
            self.token = s['csrf']

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, path, **data):
        return self.client.post(path, data=dict(csrf=self.token, **data))

    def test_full_workflow_and_persistence(self):
        self.assertEqual(self.post('/demo').status_code, 302)
        self.post('/demo')
        self.assertIn(b'Total proposals', self.client.get('/').data)
        record = self.client.get('/proposals/3/export').json
        self.assertEqual(record['assessment']['level'], 'High')
        self.assertEqual(record['status'], 'Pending review')
        for status in ['Changes requested', 'Approved']:
            self.assertEqual(self.post('/proposals/3/decision', status=status, reviewer='Akhil', rationale='Documented review conditions.').status_code, 302)
        record = self.client.get('/proposals/3/export').json
        self.assertEqual(record['status'], 'Approved')
        self.assertEqual(len(record['decisions']), 2)
        self.assertEqual(record['decisions'][1]['status'], 'Changes requested')
        other = create_app(self.config).test_client()
        self.assertEqual(other.get('/proposals/3/export').json['status'], 'Approved')
        self.assertEqual(other.get('/proposals/4').status_code, 404)
        filtered = self.client.get('/?status=Approved').data
        self.assertIn(b'Participant records assistant', filtered)
        self.assertNotIn(b'Class description writer', filtered)

    def test_validation_csrf_and_escaping(self):
        self.assertEqual(self.client.post('/demo').status_code, 400)
        self.post('/new', title='incomplete')
        self.assertEqual(self.client.get('/proposals/1').status_code, 404)
        answers = dict.fromkeys(QUESTIONS, 'no') | dict(human='yes', accessible='yes', vendor='yes')
        r = self.post('/new', title='<script>alert(1)</script>', owner='Owner', purpose='Example', **answers)
        self.assertEqual(r.status_code, 302)
        page = self.client.get(r.location)
        self.assertIn(b'&lt;script&gt;', page.data)
        self.assertNotIn(b'<script>alert', page.data)
        self.assertEqual(self.post('/proposals/1/decision', status='Approved', reviewer='', rationale='').status_code, 400)
        self.assertEqual(self.client.get('/proposals/999/export').status_code, 404)
        self.assertIn("frame-ancestors 'none'", page.headers['Content-Security-Policy'])

    def test_rule_coverage(self):
        base = dict(sensitive='no', consequential='no', public='no', vulnerable='no', human='yes', accessible='yes', vendor='yes')
        self.assertEqual(assess(base)['level'], 'Low')
        for key in ('sensitive', 'consequential'):
            self.assertEqual(assess(base | {key:'yes'})['level'], 'High')
        self.assertEqual(assess(base | {'human':'no'})['level'], 'High')
        for key, value in [('public','yes'), ('vulnerable','yes'), ('accessible','no'), ('vendor','no')]:
            self.assertEqual(assess(base | {key:value})['level'], 'Moderate')
        for key in QUESTIONS:
            self.assertEqual(assess(base | {key:'unknown'})['level'], 'Moderate')

if __name__ == '__main__':
    unittest.main()

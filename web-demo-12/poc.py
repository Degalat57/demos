"""Entry point: runs the app in-process, writes outputs to out/, runs checks. `python3 poc.py --serve` starts localhost:8000."""
import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import app, process  # noqa: E402

OUT = Path(__file__).parent / 'out'


def call(method, path, body=b''):
    env = {'REQUEST_METHOD': method, 'PATH_INFO': path, 'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body)}
    got = {}
    chunks = app(env, lambda s, h: got.update(status=int(s.split()[0]), headers=dict(h)))
    return got['status'], got['headers'], b''.join(chunks)


CASES = [
    ('valid', b'{"label": "sample batch", "values": [3, 4.5, 10]}'),
    ('empty_body', b''),
    ('malformed_json', b'{"label": "x", "values": [1,'),
    ('missing_fields', b'{}'),
    ('bad_types', b'{"label": "  ", "values": [1, "two", true], "extra": 1}'),
]


class Checks(unittest.TestCase):
    def test_valid_known_answer(self):
        s, h, b = call('POST', '/api/process', CASES[0][1])
        r = json.loads(b)['result']
        self.assertEqual(s, 200)
        self.assertEqual(h['Content-Type'], 'application/json')
        vals = [3, 4.5, 10]
        total = 0
        for v in vals:
            total += v
        self.assertEqual(r['sum'], total)
        self.assertAlmostEqual(r['mean'] * r['count'], r['sum'], places=4)
        self.assertEqual((r['min'], r['max'], r['count']), (3, 10, 3))

    def test_empty(self):
        s, _, b = call('POST', '/api/process', b'')
        self.assertEqual(s, 400)
        self.assertEqual(json.loads(b)['errors'][0]['error'], 'empty body')

    def test_malformed(self):
        s, _, b = call('POST', '/api/process', CASES[2][1])
        self.assertEqual(s, 400)
        self.assertFalse(json.loads(b)['ok'])

    def test_field_errors(self):
        s, _, b = call('POST', '/api/process', CASES[4][1])
        fields = sorted(e['field'] for e in json.loads(b)['errors'])
        self.assertEqual(s, 422)
        self.assertEqual(fields, ['extra', 'label', 'values[1]', 'values[2]'])

    def test_limits(self):
        self.assertEqual(process(json.dumps({'label': 'a' * 51, 'values': [1]}).encode())[0], 422)
        self.assertEqual(process(json.dumps({'label': 'a', 'values': list(range(101))}).encode())[0], 422)
        self.assertEqual(process(json.dumps({'label': 'a', 'values': list(range(100))}).encode())[0], 200)

    def test_routes_and_page(self):
        self.assertEqual(call('GET', '/api/process')[0], 405)
        self.assertEqual(call('GET', '/nope')[0], 404)
        s, h, b = call('GET', '/')
        self.assertEqual(s, 200)
        self.assertIn(b'/api/process', b)


def main():
    if '--serve' in sys.argv:
        from wsgiref.simple_server import make_server
        print('Serving on localhost:8000 (Ctrl+C to stop)')
        make_server('127.0.0.1', 8000, app).serve_forever()
        return
    OUT.mkdir(exist_ok=True)
    summary = []
    for name, body in CASES:
        s, _, b = call('POST', '/api/process', body)
        (OUT / ('%s.json' % name)).write_bytes(b)
        summary.append('%-15s HTTP %d' % (name, s))
    (OUT / 'index.html').write_bytes(call('GET', '/')[2])
    (OUT / 'summary.txt').write_text('\n'.join(summary) + '\n', 'utf-8')
    print('\n'.join(summary))
    res = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert res.wasSuccessful(), res.failures + res.errors
    print('POC_CHECKS_PASSED %d' % res.testsRun)


if __name__ == '__main__':
    main()

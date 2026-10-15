"""Entry point: synthetic brand spec -> page list + component map -> REST API (stdlib model of the Flask
routes) -> single responsive page (React-style components in plain JS, no CDN). Runs its own checks."""
import json
import random
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
random.seed(7)

BRAND = {
    'name': 'Northwind Studio (synthetic)',
    'colors': {'primary': '#1f4e79', 'accent': '#f2a541', 'text': '#1b1b1b', 'bg': '#fafafa'},
    'font': 'system-ui, sans-serif',
    'tagline': 'Calm, useful products for small teams.',
    'pages': {
        'home': ['NavBar', 'Hero', 'FeatureGrid', 'CallToAction', 'Footer'],
        'about': ['NavBar', 'TextBlock', 'Footer'],
        'services': ['NavBar', 'FeatureGrid', 'Footer'],
        'contact': ['NavBar', 'ContactForm', 'Footer'],
    },
}
FEATURES = [{'id': i + 1, 'title': t, 'body': 'Sample text %d for the %s block.' % (random.randint(10, 99), t.lower())}
            for i, t in enumerate(['Fast', 'Accessible', 'Responsive', 'Tested'])]


def page_list(brand):
    return [{'slug': s, 'path': '/' if s == 'home' else '/' + s, 'components': c} for s, c in brand['pages'].items()]


def component_map(brand):
    m = {}
    for slug, comps in brand['pages'].items():
        for c in comps:
            m.setdefault(c, []).append(slug)
    return dict(sorted(m.items()))


class Api:
    """Same routes and JSON the Flask app would serve (GET /api/brand, /api/pages, /api/features, POST /api/contact)."""

    def __init__(self):
        self.messages = []

    def handle(self, method, path, body=None):
        if method == 'GET' and path == '/api/brand':
            return 200, {k: BRAND[k] for k in ('name', 'colors', 'font', 'tagline')}
        if method == 'GET' and path == '/api/pages':
            return 200, page_list(BRAND)
        if method == 'GET' and path == '/api/features':
            return 200, FEATURES
        if method == 'POST' and path == '/api/contact':
            body = body or {}
            errs = [f for f in ('name', 'email', 'message') if not str(body.get(f, '')).strip()]
            if '@' not in str(body.get('email', '')):
                errs.append('email') if 'email' not in errs else None
            if errs:
                return 400, {'errors': sorted(set(errs))}
            self.messages.append(body)
            return 201, {'id': len(self.messages)}
        return 404, {'error': 'not found'}


FLASK_APP = '''from flask import Flask, jsonify, request
import poc

app = Flask(__name__, static_folder="out", static_url_path="")
api = poc.Api()


@app.route("/api/<path:p>", methods=["GET", "POST"])
def route(p):
    status, data = api.handle(request.method, "/api/" + p, request.get_json(silent=True))
    return jsonify(data), status
'''

HTML = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Home</title>
<style>
:root{--p:%(primary)s;--a:%(accent)s;--t:%(text)s;--bg:%(bg)s}
*{box-sizing:border-box}body{margin:0;font-family:%(font)s;color:var(--t);background:var(--bg)}
nav{display:flex;justify-content:space-between;align-items:center;padding:1rem;background:var(--p);color:#fff;flex-wrap:wrap}
nav a{color:#fff;margin-left:1rem;text-decoration:none}
.hero{padding:3rem 1rem;text-align:center}.hero h1{font-size:clamp(1.6rem,5vw,3rem);margin:0 0 .5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;padding:1rem;max-width:1100px;margin:auto}
.card{background:#fff;border-radius:8px;padding:1rem;box-shadow:0 1px 4px #0002}
.cta{text-align:center;padding:2rem}button{background:var(--a);border:0;padding:.8rem 1.4rem;border-radius:6px;font-size:1rem;cursor:pointer}
#msg{margin-top:1rem;font-weight:bold}footer{text-align:center;padding:1rem;font-size:.9rem;color:#555}
</style></head><body><div id="root"></div>
<script>
const DATA = %(data)s;
const h = (tag, props, ...kids) => { const e = document.createElement(tag); Object.assign(e, props || {});
  kids.flat().forEach(k => e.append(k)); return e; };
const NavBar = () => h('nav', null, h('strong', null, DATA.brand.name),
  h('div', null, DATA.pages.map(p => h('a', {href: '#' + p.slug}, p.slug))));
const Hero = () => h('section', {className: 'hero'}, h('h1', null, DATA.brand.name), h('p', null, DATA.brand.tagline));
const FeatureGrid = () => h('section', {className: 'grid'},
  DATA.features.map(f => h('div', {className: 'card'}, h('h3', null, f.title), h('p', null, f.body))));
const CallToAction = () => { const m = h('div', {id: 'msg'});
  return h('section', {className: 'cta'}, h('button', {id: 'cta', onclick: () => { m.textContent = 'Thanks - we will be in touch.'; }}, 'Get started'), m); };
const Footer = () => h('footer', null, 'Synthetic sample page');
const C = {NavBar, Hero, FeatureGrid, CallToAction, Footer};
const home = DATA.pages.find(p => p.slug === 'home');
document.getElementById('root').append(...home.components.map(n => C[n]()));
</script></body></html>
'''


def build(api):
    OUT.mkdir(exist_ok=True)
    pages = api.handle('GET', '/api/pages')[1]
    cmap = component_map(BRAND)
    lines = ['# Page list and component map (synthetic brand spec)', '']
    for p in pages:
        lines.append('- %s (%s): %s' % (p['slug'], p['path'], ', '.join(p['components'])))
    lines += ['', '## Components', ''] + ['- %s: used on %s' % (c, ', '.join(s)) for c, s in cmap.items()]
    (OUT / 'scope.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (OUT / 'component_map.json').write_text(json.dumps(cmap, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    data = {'brand': api.handle('GET', '/api/brand')[1], 'pages': pages, 'features': api.handle('GET', '/api/features')[1]}
    html = HTML % dict(BRAND['colors'], font=BRAND['font'], data=json.dumps(data, sort_keys=True))
    (OUT / 'index.html').write_text(html, encoding='utf-8')
    (OUT / 'app_flask.py.txt').write_text(FLASK_APP, encoding='utf-8')
    return data, cmap


class T(unittest.TestCase):
    def setUp(self):
        self.api = Api()
        self.data, self.cmap = build(self.api)

    def test_component_map_two_ways(self):
        n1 = sum(len(c) for c in BRAND['pages'].values())
        n2 = sum(len(v) for v in self.cmap.values())
        self.assertEqual(n1, n2)

    def test_every_component_rendered(self):
        html = (OUT / 'index.html').read_text(encoding='utf-8')
        for c in BRAND['pages']['home']:
            self.assertIn('const %s' % c, html)
        self.assertIn('name="viewport"', html)

    def test_contact_validation(self):
        self.assertEqual(self.api.handle('POST', '/api/contact', {})[0], 400)
        self.assertEqual(self.api.handle('POST', '/api/contact', {'name': 'A', 'email': 'bad', 'message': 'x'})[1],
                         {'errors': ['email']})
        self.assertEqual(self.api.handle('POST', '/api/contact', {'name': 'A', 'email': 'a@b', 'message': 'x'})[0], 201)

    def test_unknown_route(self):
        self.assertEqual(self.api.handle('GET', '/api/nope')[0], 404)

    def test_pages_paths_unique(self):
        paths = [p['path'] for p in self.data['pages']]
        self.assertEqual(len(paths), len(set(paths)))


if __name__ == '__main__':
    r = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    assert r.wasSuccessful()
    print('POC_CHECKS_PASSED %d' % r.testsRun)

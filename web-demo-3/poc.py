"""Static PCB company site generator: sitemap, pages, China-access dependency checklist. Stdlib only."""
import json
import random
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

OUT = Path('out')
SECTIONS = ['product', 'information', 'news', 'industry', 'culture']
TITLES = {'product': 'Products', 'information': 'Company Information', 'news': 'News',
          'industry': 'Industry', 'culture': 'Culture'}
# Third-party resources commonly blocked or unreliable from mainland China (public knowledge).
BLOCKED = [
    ('Google Fonts', 'fonts.googleapis.com', 'self-host font files'),
    ('Google Analytics / Tag Manager', 'googletagmanager.com', 'self-hosted analytics or regional analytics'),
    ('Google Maps embed', 'maps.googleapis.com', 'static map image'),
    ('reCAPTCHA', 'google.com/recaptcha', 'self-hosted captcha or server-side checks'),
    ('YouTube embeds', 'youtube.com', 'self-hosted video file'),
    ('Facebook pixel / SDK', 'connect.facebook.net', 'remove or load only outside China'),
    ('X (Twitter) widgets', 'platform.twitter.com', 'plain text link-free share buttons'),
    ('Instagram embeds', 'instagram.com', 'static images'),
    ('Google-hosted libraries (jQuery etc.)', 'ajax.googleapis.com', 'self-host the library'),
    ('Disqus comments', 'disqus.com', 'no third-party comments'),
]
BLOCKED_HOSTS = [b[1].split('/')[0] for b in BLOCKED]


def synth_content(seed=42):
    rng = random.Random(seed)
    layers = [2, 4, 6, 8, 10, 12]
    products = []
    for i in range(6):
        products.append({'sku': 'PCB-%03d' % (i + 1), 'name': 'Demo Board %d' % (i + 1),
                         'layers': layers[i], 'thickness_mm': rng.choice([0.8, 1.0, 1.6, 2.0]),
                         'finish': rng.choice(['HASL', 'ENIG', 'OSP', 'Immersion Silver']),
                         'min_trace_mil': rng.choice([3, 4, 5, 6])})
    news = [{'date': '2025-0%d-1%d' % (m, m), 'title': 'Sample news item %d' % m,
             'body': 'Synthetic announcement number %d.' % m} for m in range(1, 5)]
    return {
        'product': products,
        'information': ['Example PCB Co. is a synthetic demo manufacturer.',
                        'Capabilities: prototype to volume, 2 to 12 layers.'],
        'news': sorted(news, key=lambda n: n['date'], reverse=True),
        'industry': ['Trend: HDI boards in compact devices.', 'Standard: IPC class 2 vs class 3 overview.',
                     'Material note: FR-4 vs high-Tg laminates.'],
        'culture': ['Quality first.', 'Safe and clean workplace.', 'Continuous learning.'],
    }


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def nav():
    items = ['<a href="index.html">Home</a>'] + ['<a href="%s.html">%s</a>' % (s, TITLES[s]) for s in SECTIONS]
    return '<nav>' + ' | '.join(items) + '</nav>'


CSS = ('body{font-family:Arial,"Microsoft YaHei",sans-serif;margin:0;color:#222}header{background:#0b5d3b;'
       'color:#fff;padding:16px}nav a{color:#fff;margin:0 4px}main{padding:16px}table{border-collapse:collapse}'
       'td,th{border:1px solid #999;padding:4px 8px}section{margin-bottom:18px}')


def page(title, body):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>%s</title>'
            '<style>%s</style></head><body><header><h1>Example PCB Co.</h1>%s</header><main><h2>%s</h2>%s'
            '</main><footer><p>Synthetic demo site.</p></footer></body></html>\n') % (esc(title), CSS, nav(),
                                                                                      esc(title), body)


def section_body(sec, data):
    if sec == 'product':
        rows = ''.join('<tr><td>%s</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td><td>%d</td></tr>' % (
            p['sku'], esc(p['name']), p['layers'], p['thickness_mm'], p['finish'], p['min_trace_mil'])
            for p in data)
        return ('<table id="products"><tr><th>SKU</th><th>Name</th><th>Layers</th><th>Thickness mm</th>'
                '<th>Finish</th><th>Min trace mil</th></tr>%s</table>' % rows)
    if sec == 'news':
        return ''.join('<article><h3>%s %s</h3><p>%s</p></article>' % (n['date'], esc(n['title']), esc(n['body']))
                       for n in data)
    return '<ul>' + ''.join('<li>%s</li>' % esc(x) for x in data) + '</ul>'


def build():
    OUT.mkdir(exist_ok=True)
    c = synth_content()
    pages = {}
    home = ''.join('<section id="%s"><h3><a href="%s.html">%s</a></h3>%s</section>' % (
        s, s, TITLES[s], section_body(s, c[s][:3])) for s in SECTIONS)
    pages['index.html'] = page('Home', home)
    for s in SECTIONS:
        pages[s + '.html'] = page(TITLES[s], section_body(s, c[s]))
    for name, html in pages.items():
        (OUT / name).write_text(html, encoding='utf-8')
    sitemap = {'home': 'index.html', 'sections': [{'id': s, 'title': TITLES[s], 'page': s + '.html',
                                                   'items': len(c[s])} for s in SECTIONS]}
    (OUT / 'sitemap.json').write_text(json.dumps(sitemap, indent=2) + '\n', encoding='utf-8')
    lines = ['# China access dependency checklist', '',
             '| Third-party resource | Host | Replacement |', '|---|---|---|']
    lines += ['| %s | %s | %s |' % b for b in BLOCKED]
    lines += ['', 'Generated pages scanned: %d; external references found: %d' % (
        len(pages), sum(len(external_refs(h)) for h in pages.values())),
        '', 'Hosting: choose a host reachable from both regions (e.g. Hong Kong / Singapore region or ICP-filed '
        'mainland host plus overseas mirror); verify by real page loads from both sides.']
    (OUT / 'china_checklist.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return c, pages, sitemap


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ('href', 'src') and v:
                self.refs.append(v)


def refs(html):
    p = Refs()
    p.feed(html)
    return p.refs


def external_refs(html):
    return [r for r in refs(html) if re.match(r'^([a-z]+:)?//', r)]


C, PAGES, SITEMAP = build()


class T(unittest.TestCase):
    def test_five_sections(self):
        self.assertEqual([s['id'] for s in SITEMAP['sections']], SECTIONS)
        for s in SECTIONS:
            assert (OUT / (s + '.html')).is_file()

    def test_internal_links_resolve(self):
        for html in PAGES.values():
            for r in refs(html):
                assert r in PAGES, r

    def test_no_blocked_or_external(self):
        for html in PAGES.values():
            assert external_refs(html) == []
            for h in BLOCKED_HOSTS:
                assert h not in html

    def test_product_rows_preserved(self):
        html = PAGES['product.html']
        assert html.count('<tr>') - 1 == len(C['product']) == SITEMAP['sections'][0]['items']
        assert sum(p['layers'] for p in C['product']) == sum(int(x) for x in re.findall(
            r'</td><td>(\d+)</td><td>[\d.]+</td>', html))

    def test_deterministic(self):
        assert synth_content() == synth_content()

    def test_news_sorted(self):
        d = [n['date'] for n in C['news']]
        assert d == sorted(d, reverse=True)


if __name__ == '__main__':
    r = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    assert r.wasSuccessful()
    print('Outputs:', ', '.join(sorted(p.name for p in OUT.iterdir())))
    print('POC_CHECKS_PASSED %d' % r.testsRun)

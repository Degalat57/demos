"""Synthetic business site: page map, static HTML templates, WordPress WXR import, sitemap, SEO audit."""
import json
import random
import unittest
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

random.seed(7)
BASE = Path(__file__).resolve().parent
OUT = BASE / 'out'
SITE = 'example.test'  # placeholder host, never a real domain
BRAND = {'name': 'Northwind Studio', 'primary': '#1f4e79', 'accent': '#f2a541'}

PAGES = [
    {'slug': '', 'title': 'Home', 'h1': 'Clear, reliable services for growing teams',
     'desc': 'Northwind Studio offers practical services for small teams. See what we do and get in touch.',
     'sections': [('What we do', 'Planning, delivery and support in one place.'),
                  ('Why choose us', 'Plain pricing, fast replies and tidy handover.')]},
    {'slug': 'about', 'title': 'About', 'h1': 'About Northwind Studio',
     'desc': 'Learn how Northwind Studio works, the values behind the team and how projects are run.',
     'sections': [('Our approach', 'Small steps, frequent reviews, written plans.'),
                  ('Our values', 'Honesty, clarity and care for detail.')]},
    {'slug': 'services', 'title': 'Services', 'h1': 'Services',
     'desc': 'Browse the Northwind Studio service list: planning, delivery and ongoing support packages.',
     'sections': [('Planning', 'Scope, timeline and budget agreed up front.'),
                  ('Delivery', 'Weekly progress with a visible checklist.'),
                  ('Support', 'Monthly care plan with fixed response times.')]},
    {'slug': 'contact', 'title': 'Contact', 'h1': 'Contact us',
     'desc': 'Send Northwind Studio a message with the contact form and expect a reply within one working day.',
     'sections': [('Send a message', 'Use the form below; all fields are required.')]},
]


def url(p):
    return '/' + (p['slug'] + '/' if p['slug'] else '')


def render(p):
    nav = ''.join('<li><a href="%s"%s>%s</a></li>' % (url(q), ' aria-current="page"' if q is p else '', q['title'])
                  for q in PAGES)
    body = ''.join('<section><h2>%s</h2><p>%s</p></section>' % s for s in p['sections'])
    if p['slug'] == 'contact':
        body += ('<form id="contact" onsubmit="event.preventDefault();this.hidden=true;'
                 'document.getElementById(\'thanks\').hidden=false;">'
                 '<label for="n">Name</label><input id="n" name="name" required>'
                 '<label for="m">Message</label><textarea id="m" name="message" required></textarea>'
                 '<button type="submit">Send</button></form><p id="thanks" hidden>Thanks, message received.</p>')
    css = ('body{margin:0;font-family:system-ui,sans-serif;line-height:1.5;color:#222}'
           'header{background:%s;color:#fff;padding:1rem}header a{color:#fff}'
           'nav ul{list-style:none;display:flex;flex-wrap:wrap;gap:1rem;padding:0;margin:.5rem 0}'
           'main{max-width:60rem;margin:auto;padding:1rem}h1{color:%s}'
           'button{background:%s;border:0;padding:.6rem 1.2rem;font-size:1rem;min-height:48px}'
           'label,input,textarea{display:block;width:100%%;max-width:30rem;margin:.3rem 0}'
           'input,textarea{min-height:44px}@media(max-width:600px){nav ul{flex-direction:column}}'
           ) % (BRAND['primary'], BRAND['primary'], BRAND['accent'])
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>%s | %s</title><meta name="description" content="%s">'
            '<meta name="robots" content="index, follow"><link rel="canonical" href="%s">'
            '<style>%s</style></head><body><header><strong>%s</strong>'
            '<nav aria-label="Main"><ul>%s</ul></nav></header><main><h1>%s</h1>%s'
            '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" alt="%s illustration" width="1" height="1">'
            '</main><footer><p>Sample site, synthetic content.</p></footer></body></html>\n'
            ) % (p['title'], BRAND['name'], p['desc'], url(p), css, BRAND['name'], nav, p['h1'], body, p['title'])


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.meta, self.title, self._t, self.lang, self.canon, self.imgs = [], {}, '', False, None, None, []
        self.links = []

    def handle_starttag(self, tag, a):
        a = dict(a)
        self.tags.append(tag)
        if tag == 'html':
            self.lang = a.get('lang')
        elif tag == 'meta' and 'name' in a:
            self.meta[a['name']] = a.get('content', '')
        elif tag == 'title':
            self._t = True
        elif tag == 'link' and a.get('rel') == 'canonical':
            self.canon = a.get('href')
        elif tag == 'img':
            self.imgs.append(a)
        elif tag == 'a':
            self.links.append(a.get('href'))

    def handle_endtag(self, tag):
        if tag == 'title':
            self._t = False

    def handle_data(self, d):
        if self._t:
            self.title += d


def audit(html, known_urls):
    s = Scan()
    s.feed(html)
    heads = [int(t[1]) for t in s.tags if t in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')]
    checks = {
        'title_10_60': 10 <= len(s.title) <= 60,
        'meta_description_50_160': 50 <= len(s.meta.get('description', '')) <= 160,
        'viewport': 'width=device-width' in s.meta.get('viewport', ''),
        'indexable': 'noindex' not in s.meta.get('robots', ''),
        'lang': bool(s.lang),
        'canonical': bool(s.canon),
        'single_h1': heads.count(1) == 1,
        'heading_order': bool(heads) and heads[0] == 1 and all(b - a <= 1 for a, b in zip(heads, heads[1:])),
        'img_alt': all(i.get('alt') for i in s.imgs),
        'nav_links_resolve': all(h in known_urls for h in s.links),
    }
    return {'score': round(100 * sum(checks.values()) / len(checks)), 'checks': checks}


def sitemap():
    root = ET.Element('urlset', xmlns='urn:sitemaps-0.9')
    for p in PAGES:
        ET.SubElement(ET.SubElement(root, 'url'), 'loc').text = url(p)
    return ET.tostring(root, encoding='unicode') + '\n'


def wxr():
    """Minimal WordPress eXtended RSS so pages can be imported into a staging install."""
    ns = 'urn:wordpress-export-1.2'
    ET.register_namespace('wp', ns)
    rss = ET.Element('rss', version='2.0')
    ch = ET.SubElement(rss, 'channel')
    ET.SubElement(ch, 'title').text = BRAND['name'] + ' (staging)'
    ET.SubElement(ch, '{%s}wxr_version' % ns).text = '1.2'
    for i, p in enumerate(PAGES, 1):
        it = ET.SubElement(ch, 'item')
        ET.SubElement(it, 'title').text = p['title']
        ET.SubElement(it, '{%s}post_id' % ns).text = str(i)
        ET.SubElement(it, '{%s}post_name' % ns).text = p['slug'] or 'home'
        ET.SubElement(it, '{%s}post_type' % ns).text = 'page'
        ET.SubElement(it, '{%s}status' % ns).text = 'publish'
        ET.SubElement(it, '{%s}menu_order' % ns).text = str(i)
        ET.SubElement(it, 'description').text = p['desc']
    return ET.tostring(rss, encoding='unicode') + '\n'


def build():
    OUT.mkdir(exist_ok=True)
    known = {url(p) for p in PAGES}
    report = {}
    for p in PAGES:
        d = OUT / 'site' / p['slug'] if p['slug'] else OUT / 'site'
        d.mkdir(parents=True, exist_ok=True)
        html = render(p)
        (d / 'index.html').write_text(html, 'utf-8')
        report[url(p)] = audit(html, known)
    (OUT / 'sitemap.xml').write_text(sitemap(), 'utf-8')
    (OUT / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n', 'utf-8')
    (OUT / 'wordpress-pages.xml').write_text(wxr(), 'utf-8')
    (OUT / 'seo-audit.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', 'utf-8')
    return report


class T(unittest.TestCase):
    def test_all_pages_full_score(self):
        r = build()
        self.assertEqual(len(r), 4)
        for u, v in r.items():
            self.assertEqual(v['score'], 100, (u, v))

    def test_audit_catches_bad_page(self):
        bad = '<html><head><title>x</title><meta name="robots" content="noindex"></head><body><h2>a</h2><h1>b</h1><h1>c</h1><img src="a"></body></html>'
        c = audit(bad, set())['checks']
        for k in ('title_10_60', 'indexable', 'single_h1', 'heading_order', 'img_alt', 'lang', 'viewport'):
            self.assertFalse(c[k], k)

    def test_sitemap_and_wxr_match_page_map(self):
        build()
        locs = [e.text for e in ET.parse(OUT / 'sitemap.xml').getroot().iter() if e.tag.endswith('loc')]
        self.assertEqual(locs, [url(p) for p in PAGES])
        items = ET.parse(OUT / 'wordpress-pages.xml').getroot().findall('./channel/item')
        self.assertEqual([i.findtext('title') for i in items], [p['title'] for p in PAGES])

    def test_unique_titles_and_descriptions(self):
        self.assertEqual(len({p['title'] for p in PAGES}), len(PAGES))
        self.assertEqual(len({p['desc'] for p in PAGES}), len(PAGES))

    def test_deterministic(self):
        a = render(PAGES[2])
        self.assertEqual(a, render(PAGES[2]))


if __name__ == '__main__':
    build()
    res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    assert res.wasSuccessful()
    print('POC_CHECKS_PASSED %d' % res.testsRun)

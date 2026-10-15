"""Homepage wireframe + linked location/homes/enquiry pages for a property development site (synthetic data).
Also emits a WordPress page-tree import plan (JSON) and a lead-routing CSV. Stdlib only, deterministic."""
import csv
import html
import io
import json
import random
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'out'
random.seed(42)

PAGES = [  # slug, title, parent, purpose (buyer question)
    ('index', 'Home', None, 'What is this development and why should I care?'),
    ('location', 'Location', 'index', 'Where is it and what is nearby?'),
    ('homes', 'Homes', 'index', 'Which home types exist and are they available?'),
    ('enquiry', 'Enquire', 'index', 'How do I request details or book a viewing?'),
]
NAV = [(s, t) for s, t, _, _ in PAGES]


def make_homes():
    types = [('Studio', 0), ('One bedroom', 1), ('Two bedroom', 2), ('Three bedroom', 3)]
    rows = []
    for i in range(12):
        name, beds = types[i % 4]
        rows.append({'plot': 'P%02d' % (i + 1), 'type': name, 'beds': beds,
                     'area_m2': 35 + beds * 22 + random.randint(0, 9),
                     'price': 150000 + beds * 60000 + random.randint(0, 20) * 1000,
                     'status': random.choice(['Available', 'Available', 'Reserved', 'Sold'])})
    return rows


def route_lead(lead):
    """Agreed lead routing (placeholder rules): viewing requests to sales diary, others to info inbox queue."""
    if lead['intent'] == 'viewing':
        return 'sales-viewings'
    if lead.get('beds') is not None and lead['beds'] >= 3:
        return 'sales-family'
    return 'sales-general'


def validate_lead(lead):
    errs = []
    if not lead.get('name', '').strip():
        errs.append('name')
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[a-z]{2,}', lead.get('contact', '')):
        errs.append('contact')
    if lead.get('intent') not in ('details', 'viewing'):
        errs.append('intent')
    return errs


CSS = """body{font-family:Georgia,serif;margin:0;color:#222;background:#fafafa}
header{display:flex;justify-content:space-between;align-items:center;padding:12px 24px;border-bottom:1px solid #ccc}
nav a{margin-left:16px;color:#222;text-decoration:none;letter-spacing:.05em}
.box{border:2px dashed #999;background:#eee;display:flex;align-items:center;justify-content:center;color:#666}
.hero{height:320px;margin:16px 24px;font-size:20px}
section{padding:12px 24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.card{border:1px solid #bbb;padding:10px;background:#fff}.cta{display:inline-block;padding:10px 18px;border:2px solid #222;margin:6px;cursor:pointer;background:#fff}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:4px 8px;text-align:left}
form label{display:block;margin:8px 0}#result{margin-top:10px;font-weight:bold}
@media(max-width:600px){header{flex-direction:column}nav a{margin:4px}}"""


def page(slug, title, body):
    nav = ''.join('<a href="%s.html" data-nav="%s">%s</a>' % (s, s, html.escape(t)) for s, t in NAV)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>%s | Sample Development</title><style>%s</style>'
            '</head><body data-page="%s"><header><strong>[LOGO] Sample Development</strong><nav>%s</nav></header>'
            '<main>%s</main><footer><section>Wireframe only - synthetic content.</section></footer></body></html>\n'
            % (html.escape(title), CSS, slug, nav, body))


def build_pages(homes):
    avail = [h for h in homes if h['status'] == 'Available']
    home = ('<div class="box hero">[HERO IMAGE] Headline + one-line promise</div>'
            '<section><a class="cta" href="enquiry.html?intent=viewing" id="cta-viewing">Book a viewing</a>'
            '<a class="cta" href="enquiry.html?intent=details" id="cta-details">Request details</a></section>'
            '<section class="grid"><div class="card"><h3>Location</h3><div class="box" style="height:90px">[MAP]</div>'
            '<a href="location.html">Explore the area</a></div><div class="card"><h3>Homes</h3><p>%d of %d homes '
            'available</p><a href="homes.html">See home types</a></div><div class="card"><h3>Enquire</h3><p>Short form, '
            'reply by the sales team</p><a href="enquiry.html">Enquire now</a></div></section>'
            '<section><h3>Buyer journey</h3><ol><li>Discover (hero)</li><li>Where (location)</li><li>Which home '
            '(homes)</li><li>Act (enquiry)</li></ol></section>') % (len(avail), len(homes))
    loc = ('<section><h2>Location</h2><div class="box" style="height:240px">[INTERACTIVE MAP]</div></section>'
           '<section class="grid">' + ''.join('<div class="card">%s: [placeholder minutes]</div>' % x for x in
                                              ('Transport', 'Schools', 'Shops', 'Parks')) +
           '</section><section><a class="cta" href="enquiry.html?intent=viewing">Book a viewing</a></section>')
    rows = ''.join('<tr data-status="%s"><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%s</td>'
                   '<td><a href="enquiry.html?intent=details&amp;plot=%s">Enquire</a></td></tr>'
                   % (h['status'], h['plot'], h['type'], h['beds'], h['area_m2'], h['price'], h['status'], h['plot'])
                   for h in homes)
    hm = ('<section><h2>Homes</h2><label><input type="checkbox" id="only-avail"> Show available only</label>'
          '<table id="homes"><tr><th>Plot</th><th>Type</th><th>Beds</th><th>m2</th><th>Price</th><th>Status</th>'
          '<th></th></tr>' + rows + '</table></section><script>document.getElementById("only-avail").onchange='
          'function(e){document.querySelectorAll("#homes tr[data-status]").forEach(function(r){r.style.display='
          '(e.target.checked&&r.dataset.status!=="Available")?"none":""})}</script>')
    enq = ('<section><h2>Enquire</h2><form id="enquiry"><label>Name <input name="name" id="f-name"></label>'
           '<label>Email <input name="contact" id="f-contact"></label><label>I want to <select name="intent" '
           'id="f-intent"><option value="details">Request details</option><option value="viewing">Book a viewing'
           '</option></select></label><label>Plot (optional) <input name="plot" id="f-plot"></label>'
           '<button type="submit" class="cta" id="f-submit">Send</button></form><div id="result"></div></section>'
           '<script>var q=new URLSearchParams(location.search);if(q.get("intent"))document.getElementById("f-intent")'
           '.value=q.get("intent");if(q.get("plot"))document.getElementById("f-plot").value=q.get("plot");'
           'document.getElementById("enquiry").onsubmit=function(e){e.preventDefault();var n=this.name.value.trim(),'
           'c=this.contact.value,i=this.intent.value,r=document.getElementById("result");if(!n||!/^[^@\\s]+@[^@\\s]+'
           '\\.[a-z]{2,}$/.test(c)){r.textContent="Please add a name and a valid email.";return}r.textContent='
           '"Thanks - routed to "+(i==="viewing"?"sales-viewings":"sales-general")+" (demo, nothing sent).";}'
           '</script>')
    return {'index': page('index', 'Home', home), 'location': page('location', 'Location', loc),
            'homes': page('homes', 'Homes', hm), 'enquiry': page('enquiry', 'Enquire', enq)}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.append(dict(attrs).get('href', ''))


def links_of(doc):
    p = Links()
    p.feed(doc)
    return p.hrefs


def wp_plan():
    return {'theme': 'block theme (to be chosen)', 'pages': [
        {'slug': 'home' if s == 'index' else s, 'title': t, 'parent': p and 'home', 'buyer_question': q,
         'template': 'front-page' if s == 'index' else 'page-' + s} for s, t, p, q in PAGES],
        'custom_post_types': [{'name': 'home_unit', 'fields': ['plot', 'type', 'beds', 'area_m2', 'price', 'status']}],
        'forms': [{'name': 'enquiry', 'fields': ['name', 'contact', 'intent', 'plot']}]}


AT = chr(64)
SAMPLE_LEADS = [
    {'name': 'Test A', 'contact': 'a' + AT + 'example.test', 'intent': 'viewing', 'beds': 2},
    {'name': 'Test B', 'contact': 'b' + AT + 'example.test', 'intent': 'details', 'beds': 3},
    {'name': 'Test C', 'contact': 'c' + AT + 'example.test', 'intent': 'details', 'beds': None},
    {'name': '', 'contact': 'bad', 'intent': 'x', 'beds': None},
]


def build():
    OUT.mkdir(exist_ok=True)
    homes = make_homes()
    pages = build_pages(homes)
    for s, doc in pages.items():
        (OUT / (s + '.html')).write_text(doc, 'utf-8')
    (OUT / 'wp-page-plan.json').write_text(json.dumps(wp_plan(), indent=2) + '\n', 'utf-8')
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['name', 'intent', 'valid', 'route'])
    for ld in SAMPLE_LEADS:
        e = validate_lead(ld)
        w.writerow([ld['name'] or '(blank)', ld['intent'], 'yes' if not e else 'no:' + '|'.join(e),
                    route_lead(ld) if not e else '-'])
    (OUT / 'lead-routing.csv').write_text(buf.getvalue(), 'utf-8')
    return homes, pages


HOMES, PAGES_HTML = build()


class T(unittest.TestCase):
    def test_all_internal_links_resolve(self):
        for s, doc in PAGES_HTML.items():
            for h in links_of(doc):
                self.assertTrue((OUT / h.split('?')[0]).is_file(), (s, h))

    def test_every_page_reaches_enquiry(self):
        for doc in PAGES_HTML.values():
            self.assertTrue(any(h.startswith('enquiry.html') for h in links_of(doc)))

    def test_available_count_two_ways(self):
        n = sum(1 for h in HOMES if h['status'] == 'Available')
        self.assertEqual(n, PAGES_HTML['homes'].count('data-status="Available"'))
        self.assertIn('%d of 12 homes' % n, PAGES_HTML['index'])

    def test_rows_preserved(self):
        self.assertEqual(PAGES_HTML['homes'].count('<tr data-status='), len(HOMES))

    def test_lead_validation_and_routing(self):
        self.assertEqual(validate_lead(SAMPLE_LEADS[3]), ['name', 'contact', 'intent'])
        self.assertEqual([route_lead(x) for x in SAMPLE_LEADS[:3]], ['sales-viewings', 'sales-family', 'sales-general'])

    def test_plan_matches_nav(self):
        self.assertEqual(len(wp_plan()['pages']), len(NAV))


if __name__ == '__main__':
    res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    assert res.wasSuccessful()
    print('POC_CHECKS_PASSED %d' % res.testsRun)

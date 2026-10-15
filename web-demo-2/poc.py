"""Mobile-first HTML5 + CSS grid screen built from synthetic content; validated with stdlib only."""
import random
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

random.seed(7)
OUT = Path(__file__).resolve().parent / 'out'
BREAKPOINTS = (360, 768, 1280)
CARDS = [('Card %d' % i, 'Synthetic item %d, score %d' % (i, random.randint(10, 99))) for i in range(1, 7)]

CSS = """*,*::before,*::after{box-sizing:border-box}
body{margin:0;font-family:system-ui,sans-serif;color:#1d2330;background:#f6f7fb}
.layout{display:grid;grid-template-columns:1fr;grid-template-areas:"head" "nav" "main" "foot";gap:12px;padding:12px}
header{grid-area:head}nav{grid-area:nav}main{grid-area:main}footer{grid-area:foot}
nav ul{display:flex;flex-wrap:wrap;gap:8px;list-style:none;margin:0;padding:0}
nav a{display:block;padding:10px 12px;min-height:44px;border-radius:6px;background:#e3e8f4;color:#1d2330;text-decoration:none}
.cards{display:grid;grid-template-columns:1fr;gap:12px}
.card{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
img{max-width:100%;height:auto}
@media (min-width:768px){.cards{grid-template-columns:repeat(2,1fr)}}
@media (min-width:1280px){.layout{grid-template-columns:220px 1fr;grid-template-areas:"head head" "nav main" "foot foot";max-width:1280px;margin:0 auto}
nav ul{flex-direction:column}.cards{grid-template-columns:repeat(3,1fr)}}
"""


def build_html():
    cards = '\n'.join('      <article class="card"><h2>%s</h2><p>%s</p></article>' % c for c in CARDS)
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sample screen</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="layout">
    <header><h1>Sample dashboard</h1></header>
    <nav aria-label="Main"><ul><li><a href="#overview">Overview</a></li><li><a href="#items">Items</a></li><li><a href="#settings">Settings</a></li></ul></nav>
    <main id="items"><section class="cards">
%s
    </section></main>
    <footer><p>Synthetic demo content</p></footer>
  </div>
</body>
</html>
""" % cards


def columns_at(css, width):
    """Resolve .cards column count at a viewport width by applying min-width media rules in order."""
    cols = 1
    for mw, body in re.findall(r'@media \(min-width:(\d+)px\)\{(.*?)\}\s*(?=@media|$)', css, re.S):
        if width >= int(mw):
            m = re.search(r'\.cards\{grid-template-columns:repeat\((\d+),1fr\)', body)
            if m:
                cols = int(m.group(1))
    return cols


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.stack, self.ok = [], [], True

    def handle_starttag(self, t, a):
        self.tags.append((t, dict(a)))
        if t not in ('meta', 'link'):
            self.stack.append(t)

    def handle_endtag(self, t):
        if not self.stack or self.stack.pop() != t:
            self.ok = False


class T(unittest.TestCase):
    def test_html_well_formed_and_semantic(self):
        p = Tags(); p.feed((OUT / 'index.html').read_text())
        self.assertTrue(p.ok and not p.stack)
        names = [t for t, _ in p.tags]
        for t in ('header', 'nav', 'main', 'footer'):
            self.assertIn(t, names)
        self.assertEqual(names.count('article'), len(CARDS))
        self.assertTrue(any(t == 'meta' and a.get('name') == 'viewport' for t, a in p.tags))

    def test_mobile_first_columns(self):
        css = (OUT / 'styles.css').read_text()
        self.assertNotIn('max-width:', css.split('@media')[0].replace('max-width:100%', ''))
        self.assertEqual([columns_at(css, w) for w in BREAKPOINTS], [1, 2, 3])

    def test_columns_match_report(self):
        rep = (OUT / 'breakpoints.csv').read_text().splitlines()
        self.assertEqual(len(rep), 1 + len(BREAKPOINTS))
        rows = [r.split(',') for r in rep[1:]]
        for w, c, rows_n in rows:
            self.assertEqual(int(rows_n), -(-len(CARDS) // int(c)))

    def test_braces_balanced(self):
        css = (OUT / 'styles.css').read_text()
        self.assertEqual(css.count('{'), css.count('}'))


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / 'index.html').write_text(build_html())
    (OUT / 'styles.css').write_text(CSS)
    lines = ['width_px,card_columns,card_rows']
    for w in BREAKPOINTS:
        c = columns_at(CSS, w)
        lines.append('%d,%d,%d' % (w, c, -(-len(CARDS) // c)))
    (OUT / 'breakpoints.csv').write_text('\n'.join(lines) + '\n')
    r = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    assert r.wasSuccessful()
    print('POC_CHECKS_PASSED %d' % r.testsRun)


if __name__ == '__main__':
    main()

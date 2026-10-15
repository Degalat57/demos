"""Entry point: audit a synthetic homepage at 375/768/1440, rebuild its nav accessibly, self-test."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit import audit, VIEWPORTS, parse

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'

OLD = """<!DOCTYPE html><html><head><title>Sample Co</title>
<style>.topbar{width:1200px}.menu{min-width:800px}</style></head><body>
<div class="topbar"><img src="logo.png"><div class="menu">
<span onclick="go('home')">Home</span><span onclick="go('services')">Services</span>
<span onclick="go('about')">About</span><span onclick="go('contact')">Contact</span></div></div>
<main><h1>Welcome</h1><img src="hero.jpg" alt="Hero"></main></body></html>"""

NAV_CSS = """*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif}
.site-nav{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:#123;color:#fff;max-width:100%}
.site-nav a{color:#fff;text-decoration:none;display:block;padding:12px 14px;min-height:44px}
.site-nav a:focus-visible,.nav-toggle:focus-visible{outline:3px solid #fc0;outline-offset:2px}
.nav-toggle{min-height:44px;min-width:44px;background:none;color:#fff;border:1px solid #fff;border-radius:4px}
.nav-list{list-style:none;margin:0;padding:0;display:none}
.nav-list.open{display:block;position:absolute;top:68px;left:0;right:0;background:#123}
@media (min-width:768px){.nav-toggle{display:none}.nav-list{display:flex}}
main{padding:16px}img{max-width:100%;height:auto}"""

NAV_JS = """const b=document.querySelector('.nav-toggle'),l=document.getElementById('nav-list');
b.addEventListener('click',()=>{const o=b.getAttribute('aria-expanded')!=='true';b.setAttribute('aria-expanded',String(o));l.classList.toggle('open',o);if(o)l.querySelector('a').focus();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&b.getAttribute('aria-expanded')==='true'){b.click();b.focus();}});"""

ITEMS = [('Home', '#home'), ('Services', '#services'), ('About', '#about'), ('Contact', '#contact')]


def new_page():
    lis = ''.join('<li><a href="%s">%s</a></li>' % (h, t) for t, h in ITEMS)
    return ("""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Sample Co</title>
<link rel="stylesheet" href="nav.css"></head><body>
<nav class="site-nav" aria-label="Main"><a href="#home"><img src="logo.svg" alt="Sample Co home" width="120" height="32"></a>
<button class="nav-toggle" aria-expanded="false" aria-controls="nav-list">Menu</button>
<ul class="nav-list" id="nav-list">%s</ul></nav>
<main id="home"><h1>Welcome</h1><p>Synthetic demo page.</p></main>
<script src="nav.js"></script></body></html>""" % lis)


def report_md(name, r):
    lines = ['# Audit: %s' % name, '', 'Global issues:'] + (['- ' + m for m in r['global']] or ['- none'])
    for vp in VIEWPORTS:
        lines += ['', '## %dpx (score %d/100)' % (vp, r['scores'][vp])]
        lines += ['- ' + m for m in r['viewports'][vp]] or ['- no overflow']
        lines += []
    return '\n'.join(lines) + '\n'


class T(unittest.TestCase):
    def setUp(self):
        self.old, self.new = audit(OLD), audit(new_page())

    def test_old_has_issues(self):
        g = ' '.join(self.old['global'])
        for k in ('viewport', 'alt', 'lang', '<nav>', 'non-focusable'):
            self.assertIn(k, g)
        self.assertEqual(len(self.old['viewports'][375]), 2)
        self.assertEqual(len(self.old['viewports'][1440]), 0)

    def test_new_clean_all_viewports(self):
        self.assertEqual(self.new['global'], [])
        for vp in VIEWPORTS:
            self.assertEqual(self.new['scores'][vp], 100)

    def test_scores_monotone(self):
        s = self.old['scores']
        self.assertLessEqual(s[375], s[768])
        self.assertLessEqual(s[768], s[1440])

    def test_nav_keyboard_semantics(self):
        tags = parse(new_page())
        links = [a for t, a in tags if t == 'a']
        self.assertEqual(len(links), len(ITEMS) + 1)
        btn = [a for t, a in tags if t == 'button'][0]
        self.assertEqual(btn['aria-expanded'], 'false')
        self.assertEqual(btn['aria-controls'], 'nav-list')
        self.assertIn('focus-visible', NAV_CSS)
        self.assertIn('min-height:44px', NAV_CSS)
        self.assertIn('Escape', NAV_JS)


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / 'index.html').write_text(new_page())
    (OUT / 'nav.css').write_text(NAV_CSS + '\n')
    (OUT / 'nav.js').write_text(NAV_JS + '\n')
    ro, rn = audit(OLD), audit(new_page())
    (OUT / 'audit_before.md').write_text(report_md('original homepage (synthetic)', ro))
    (OUT / 'audit_after.md').write_text(report_md('rebuilt navigation (synthetic)', rn))
    (OUT / 'audit.json').write_text(json.dumps({'before': ro, 'after': rn}, indent=1, sort_keys=True) + '\n')
    print('before scores', ro['scores'], 'after', rn['scores'])
    res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    assert res.wasSuccessful()
    print('POC_CHECKS_PASSED %d' % res.testsRun)


if __name__ == '__main__':
    main()

"""Builds a 3-page static site (Home, About, Contact) from a synthetic design-token file.
Tokens -> CSS custom properties; photo carousel uses CSS scroll-snap with a small JS controller."""
import json
import random
import re
import struct
import unittest
import zlib
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
random.seed(7)

TOKENS = {
    "color": {"bg": "#0e0f13", "surface": "#181a21", "text": "#f2f2f4", "muted": "#9aa0ad",
              "accent": "#c9a86a", "accent-ink": "#14120d"},
    "font": {"display": "'Playfair Display', Georgia, serif",
             "body": "Inter, system-ui, -apple-system, sans-serif"},
    "size": {"base": "16px", "h1": "clamp(2.2rem, 5vw, 4rem)", "h2": "clamp(1.5rem, 3vw, 2.2rem)"},
    "space": {"xs": "4px", "sm": "8px", "md": "16px", "lg": "32px", "xl": "64px"},
    "radius": {"card": "14px"},
}
PAGES = [("index.html", "Home"), ("about.html", "About Us"), ("contact.html", "Contact")]
N_SLIDES = 5


def css_vars(tokens):
    lines = []
    for group, vals in tokens.items():
        for k, v in vals.items():
            lines.append("  --%s-%s: %s;" % (group, k, v))
    return ":root {\n" + "\n".join(lines) + "\n}\n"


BASE_CSS = """*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--color-bg);color:var(--color-text);font:var(--size-base)/1.6 var(--font-body)}
h1,h2{font-family:var(--font-display);line-height:1.15}h1{font-size:var(--size-h1)}h2{font-size:var(--size-h2)}
header{display:flex;justify-content:space-between;align-items:center;padding:var(--space-md) var(--space-lg);
position:sticky;top:0;background:var(--color-bg)}
nav a{color:var(--color-muted);margin-left:var(--space-md);text-decoration:none}nav a[aria-current]{color:var(--color-accent)}
main{max-width:1100px;margin:0 auto;padding:var(--space-lg)}
.carousel{position:relative}
.track{display:flex;gap:var(--space-md);overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;
padding-bottom:var(--space-sm)}
.slide{flex:0 0 100%;scroll-snap-align:center;border-radius:var(--radius-card);overflow:hidden;margin:0}
.slide img{width:100%;height:auto;display:block}
.ctrl{position:absolute;top:45%;background:var(--color-accent);color:var(--color-accent-ink);border:0;
border-radius:50%;width:44px;height:44px;font-size:20px;cursor:pointer}.prev{left:var(--space-sm)}.next{right:var(--space-sm)}
.dots{display:flex;justify-content:center;gap:var(--space-sm);margin-top:var(--space-sm)}
.dots button{width:10px;height:10px;border-radius:50%;border:0;background:var(--color-muted);padding:0}
.dots button[aria-current=true]{background:var(--color-accent)}
form{display:grid;gap:var(--space-md);max-width:520px}
input,textarea{padding:var(--space-sm);border-radius:8px;border:1px solid var(--color-muted);background:var(--color-surface);color:var(--color-text)}
.btn{background:var(--color-accent);color:var(--color-accent-ink);border:0;padding:var(--space-sm) var(--space-md);border-radius:8px}
#status{color:var(--color-accent)}
@media (max-width:640px){header{flex-direction:column}main{padding:var(--space-md)}nav a{margin:0 var(--space-sm)}}
"""

JS = """document.querySelectorAll('.carousel').forEach(function(c){
 var t=c.querySelector('.track'),s=t.querySelectorAll('.slide'),d=c.querySelector('.dots'),i=0;
 s.forEach(function(_,k){var b=document.createElement('button');b.setAttribute('aria-label','Slide '+(k+1));
  b.onclick=function(){go(k)};d.appendChild(b)});
 function go(k){i=(k+s.length)%s.length;t.scrollTo({left:s[i].offsetLeft-t.offsetLeft,behavior:'smooth'});mark()}
 function mark(){d.querySelectorAll('button').forEach(function(b,k){b.setAttribute('aria-current',k===i)});c.dataset.index=i}
 c.querySelector('.prev').onclick=function(){go(i-1)};c.querySelector('.next').onclick=function(){go(i+1)};
 t.addEventListener('scroll',function(){var n=Math.round(t.scrollLeft/t.clientWidth);if(n!==i){i=n;mark()}});mark()});
var f=document.querySelector('form');if(f){f.onsubmit=function(e){e.preventDefault();
 document.getElementById('status').textContent=f.checkValidity()?'Thanks - message ready to send.':'Please fill all fields.'}}
"""


def slide_png(k, w=480, h=240):
    """Tiny synthetic gradient photo as an optimised PNG (no external tools)."""
    r0, g0, b0 = random.randint(20, 120), random.randint(20, 120), random.randint(60, 160)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw += bytes(((r0 + x // 4) % 256, (g0 + y // 2) % 256, (b0 + (x + y) // 8) % 256))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def page(fname, title, body):
    nav = "".join('<a href="%s"%s>%s</a>' % (f, ' aria-current="page"' if f == fname else "", t)
                  for f, t in PAGES)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s | Sample Brand</title><link rel="stylesheet" href="styles.css"></head><body>'
            '<header><strong>Sample Brand</strong><nav>%s</nav></header><main>%s</main>'
            '<script src="site.js" defer></script></body></html>\n' % (title, nav, body))


def carousel():
    slides = "".join('<figure class="slide"><img src="img/slide%d.png" alt="Sample photo %d" width="480" '
                     'height="240" loading="%s"></figure>' % (k + 1, k + 1, "eager" if k == 0 else "lazy")
                     for k in range(N_SLIDES))
    return ('<section class="carousel" aria-label="Photo carousel"><div class="track">%s</div>'
            '<button class="ctrl prev" aria-label="Previous">&#8249;</button>'
            '<button class="ctrl next" aria-label="Next">&#8250;</button><div class="dots"></div></section>' % slides)


BODIES = {
    "index.html": "<h1>Crafted for the modern eye</h1><p>Placeholder hero copy.</p>" + carousel(),
    "about.html": "<h1>About Us</h1><h2>Our story</h2><p>Placeholder story text for the brand.</p>",
    "contact.html": ('<h1>Contact</h1><form novalidate><input name="name" placeholder="Name" required>'
                     '<input name="mail" type="email" placeholder="Email" required>'
                     '<textarea name="msg" rows="5" placeholder="Message" required></textarea>'
                     '<button class="btn" type="submit">Send</button></form><p id="status"></p>'),
}


def build():
    (OUT / "site" / "img").mkdir(parents=True, exist_ok=True)
    (OUT / "design-tokens.json").write_text(json.dumps(TOKENS, indent=2) + "\n")
    (OUT / "site" / "styles.css").write_text(css_vars(TOKENS) + BASE_CSS)
    (OUT / "site" / "site.js").write_text(JS)
    for k in range(N_SLIDES):
        (OUT / "site" / "img" / ("slide%d.png" % (k + 1))).write_bytes(slide_png(k))
    for f, t in PAGES:
        (OUT / "site" / f).write_text(page(f, t, BODIES[f]))


class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def parse(f):
    p = Collect()
    p.feed((OUT / "site" / f).read_text())
    return p.tags


class T(unittest.TestCase):
    def test_every_token_is_a_css_var(self):
        css = (OUT / "site" / "styles.css").read_text()
        defined = dict(re.findall(r"--([\w-]+):\s*([^;]+);", css))
        n = sum(len(v) for v in TOKENS.values())
        self.assertEqual(len(defined), n)
        for g, vals in TOKENS.items():
            for k, v in vals.items():
                self.assertEqual(defined["%s-%s" % (g, k)], v)
        for used in set(re.findall(r"var\(--([\w-]+)\)", css)):
            self.assertIn(used, defined)

    def test_carousel_scroll_snap(self):
        css = (OUT / "site" / "styles.css").read_text()
        self.assertIn("scroll-snap-type:x mandatory", css)
        self.assertIn("scroll-snap-align:center", css)
        imgs = [a for t, a in parse("index.html") if t == "img"]
        self.assertEqual(len(imgs), N_SLIDES)
        for a in imgs:
            self.assertTrue((OUT / "site" / a["src"]).is_file())
            self.assertTrue(a["alt"] and a["width"] and a["height"])

    def test_nav_links_resolve_on_all_pages(self):
        for f, _ in PAGES:
            tags = parse(f)
            hrefs = [a["href"] for t, a in tags if t == "a"]
            self.assertEqual(hrefs, [p for p, _ in PAGES])
            cur = [a["href"] for t, a in tags if t == "a" and "aria-current" in a]
            self.assertEqual(cur, [f])
            self.assertTrue(any(t == "meta" and a.get("name") == "viewport" for t, a in tags))

    def test_contact_form_fields_required(self):
        req = [a["name"] for t, a in parse("contact.html") if t in ("input", "textarea") and "required" in a]
        self.assertEqual(req, ["name", "mail", "msg"])


if __name__ == "__main__":
    build()
    r = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    assert r.wasSuccessful()
    print("POC_CHECKS_PASSED %d" % r.testsRun)

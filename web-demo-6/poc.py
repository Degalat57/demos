"""Story timeline site generator: five chapters -> static HTML page + WordPress block markup. Stdlib only."""
import html
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

CHAPTERS = [
    ("early-life", "Early Life", "1960s", "Placeholder: childhood, family and the place where the story begins."),
    ("career", "Career Journey", "1980s", "Placeholder: first jobs, mentors and the skills learned on the way."),
    ("challenges", "Challenges", "1990s", "Placeholder: the setbacks faced and how they were overcome."),
    ("achievements", "Achievements", "2000s", "Placeholder: key milestones, recognition and turning points."),
    ("growth", "Company Growth", "2010s", "Placeholder: founding the company and how it grew over time."),
]

CSS = """body{margin:0;font-family:Georgia,serif;background:#faf8f4;color:#2b2b2b}
header{text-align:center;padding:4rem 1rem;background:#1f2a38;color:#fff}
nav{display:flex;flex-wrap:wrap;justify-content:center;gap:1rem;padding:1rem;background:#eee8dc;position:sticky;top:0}
nav a{color:#1f2a38;text-decoration:none;font-weight:bold}
.timeline{max-width:900px;margin:2rem auto;position:relative;padding:0 1rem}
.timeline:before{content:'';position:absolute;left:50%;top:0;bottom:0;width:3px;background:#c9a96e}
.chapter{display:flex;gap:2rem;margin:3rem 0;align-items:center}
.chapter:nth-child(even){flex-direction:row-reverse}
.photo{flex:1;aspect-ratio:4/3;background:#d9d2c3;display:flex;align-items:center;justify-content:center;color:#6b6252;border-radius:8px}
.text{flex:1;background:#fff;padding:1.5rem;border-radius:8px;box-shadow:0 2px 8px #0002}
.era{color:#c9a96e;font-weight:bold}
@media(max-width:700px){.chapter,.chapter:nth-child(even){flex-direction:column}.timeline:before{display:none}}"""


def chapter_html(i, c):
    slug, title, era, body = (html.escape(x) for x in c)
    return (f'<section class="chapter" id="{slug}"><div class="photo">Photo {i + 1} placeholder</div>'
            f'<div class="text"><span class="era">{era}</span><h2>Chapter {i + 1}: {title}</h2>'
            f'<p>{body}</p></div></section>')


def build_page(chapters):
    nav = "".join(f'<a href="#{html.escape(c[0])}">{html.escape(c[1])}</a>' for c in chapters)
    secs = "\n".join(chapter_html(i, c) for i, c in enumerate(chapters))
    return ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>A Success Story</title><style>{CSS}</style></head><body>"
            "<header><h1>From Humble Beginnings</h1><p>Placeholder subtitle for the story.</p></header>"
            f"<nav>{nav}</nav><main class=\"timeline\">\n{secs}\n</main>"
            "<footer style=\"text-align:center;padding:2rem\">Placeholder footer</footer></body></html>\n")


def build_wp_blocks(chapters):
    """WordPress Gutenberg block markup, pasteable into the code editor of a page."""
    parts = []
    for i, (slug, title, era, body) in enumerate(chapters):
        parts.append(
            f'<!-- wp:group {{"anchor":"{slug}","className":"chapter"}} -->\n'
            f'<div id="{slug}" class="wp-block-group chapter">'
            f'<!-- wp:media-text {{"mediaPosition":"{"right" if i % 2 else "left"}"}} -->\n'
            f'<div class="wp-block-media-text"><figure class="wp-block-media-text__media"></figure>'
            f'<div class="wp-block-media-text__content">'
            f'<!-- wp:heading -->\n<h2>{html.escape(era)} - {html.escape(title)}</h2>\n<!-- /wp:heading -->\n'
            f'<!-- wp:paragraph -->\n<p>{html.escape(body)}</p>\n<!-- /wp:paragraph -->'
            f'</div></div>\n<!-- /wp:media-text --></div>\n<!-- /wp:group -->')
    return "\n\n".join(parts) + "\n"


class Checks(unittest.TestCase):
    def setUp(self):
        self.page = build_page(CHAPTERS)
        self.wp = build_wp_blocks(CHAPTERS)

    def test_five_chapters_in_order(self):
        ids = re.findall(r'<section class="chapter" id="([^"]+)"', self.page)
        self.assertEqual(ids, [c[0] for c in CHAPTERS])
        assert len(ids) == 5

    def test_nav_matches_sections(self):
        nav = re.findall(r'<a href="#([^"]+)"', self.page)
        self.assertEqual(nav, re.findall(r'id="([^"]+)"', self.page))

    def test_wp_blocks_balanced(self):
        for b in ("group", "media-text", "heading", "paragraph"):
            assert len(re.findall(r"<!-- wp:" + b + r"[ ]", self.wp)) == \
                self.wp.count(f"<!-- /wp:{b} -->"), b
        assert self.wp.count("<!-- /wp:group -->") == 5

    def test_escaping(self):
        out = chapter_html(0, ("x", "<b>&", "e", "p"))
        assert "<b>&" not in out and "&lt;b&gt;&amp;" in out

    def test_deterministic(self):
        assert build_page(CHAPTERS) == self.page


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(build_page(CHAPTERS), "utf-8")
    (OUT / "wordpress-blocks.html").write_text(build_wp_blocks(CHAPTERS), "utf-8")
    (OUT / "chapters.json").write_text(json.dumps([dict(zip(("slug", "title", "era", "body"), c))
                                                   for c in CHAPTERS], indent=2) + "\n", "utf-8")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    assert res.wasSuccessful()
    print("POC_CHECKS_PASSED", res.testsRun)


if __name__ == "__main__":
    main()

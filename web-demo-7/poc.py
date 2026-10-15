"""Site map + homepage copy for a scan-to-BIM/CAD service site, positioned by LOD. Stdlib only."""
import html
import json
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
BASE = "/"  # relative paths only; domain set at deployment

# LOD tiers: placeholder descriptions, to be confirmed against the services actually offered
LODS = [
    ("LOD 100", "Massing", "Overall volumes, levels and footprints for feasibility and area studies."),
    ("LOD 200", "Generic elements", "Walls, floors, roofs and openings with approximate size and position."),
    ("LOD 300", "Precise geometry", "Elements modelled at measured size and location for design and coordination."),
    ("LOD 350", "Coordination", "Adds connections and interfaces between systems for clash detection."),
    ("LOD 400", "Fabrication ready", "Detail sufficient for shop drawings and prefabrication, where scope allows."),
]

PAGES = [
    ("home", "/", "Home", None),
    ("services", "/services/", "Services", None),
    ("scan-to-bim", "/services/scan-to-bim/", "Scan to BIM", "services"),
    ("scan-to-cad", "/services/scan-to-cad/", "Scan to CAD (2D drawings)", "services"),
    ("lod", "/levels-of-detail/", "Levels of detail", None),
    ("process", "/process/", "How it works", None),
    ("formats", "/file-formats/", "Inputs and file formats", None),
    ("sectors", "/sectors/", "Who it is for", None),
    ("quote", "/request-a-quote/", "Request a quote", None),
    ("faq", "/faq/", "FAQ", None),
    ("privacy", "/privacy/", "Privacy", None),
]

STEPS = ["Send point cloud and scope", "Receive fixed quote and LOD agreement",
         "Model production and quality check", "Delivery in agreed native and exchange formats"]


def sitemap_tree():
    by = {k: {"slug": k, "path": p, "title": t, "children": []} for k, p, t, _ in PAGES}
    roots = []
    for k, _, _, parent in PAGES:
        (by[parent]["children"] if parent else roots).append(by[k])
    return roots


def sitemap_xml():
    root = ET.Element("urlset")
    for _, path, _, _ in PAGES:
        u = ET.SubElement(root, "url")
        ET.SubElement(u, "loc").text = path
    return ET.tostring(root, encoding="unicode")


def homepage_html():
    e = html.escape
    lod_rows = "".join(f"<tr><th scope='row'>{e(a)}</th><td>{e(b)}</td><td>{e(c)}</td></tr>" for a, b, c in LODS)
    steps = "".join(f"<li>{e(s)}</li>" for s in STEPS)
    nav = "".join(f"<a href='{p}'>{e(t)}</a>" for k, p, t, par in PAGES if not par and k not in ("home", "privacy"))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scan to BIM and CAD modelling by level of detail</title>
<meta name="description" content="Point clouds converted into BIM models and CAD drawings at an agreed level of detail, with a fixed quote before work starts.">
<style>
body{{margin:0;font:16px/1.55 system-ui,sans-serif;color:#1d2329;background:#fff}}
header,main,footer{{max-width:68rem;margin:auto;padding:0 1rem}}
nav{{display:flex;flex-wrap:wrap;gap:.4rem 1rem;padding:1rem 0;border-bottom:1px solid #dde}}
nav a{{color:#1d2329;text-decoration:none}} h1{{font-size:clamp(1.7rem,4vw,2.6rem);line-height:1.2}}
.cta{{display:inline-block;background:#174a7c;color:#fff;padding:.75rem 1.2rem;border-radius:4px;text-decoration:none}}
table{{border-collapse:collapse;width:100%}} th,td{{text-align:left;padding:.5rem;border-bottom:1px solid #e3e6ea;vertical-align:top}}
.wrap{{overflow-x:auto}} ol{{padding-left:1.2rem}}
</style></head><body>
<header><nav aria-label="Main">{nav}</nav></header>
<main>
<section id="hero"><h1>Laser scans turned into BIM models and CAD drawings, at the level of detail you specify</h1>
<p>Send a point cloud, choose the LOD per discipline, and receive a fixed quote before any modelling starts.</p>
<a class="cta" id="quote-cta" href="/request-a-quote/">Request a quote</a></section>
<section id="deliverables"><h2>What you receive</h2><ul>
<li>BIM models of existing buildings for design, renovation and coordination</li>
<li>2D CAD plans, sections and elevations derived from the same scan</li>
<li>A short QA note stating LOD, tolerance and what was not modelled</li></ul></section>
<section id="lod"><h2>Levels of detail</h2><div class="wrap"><table>
<thead><tr><th scope="col">Level</th><th scope="col">Name</th><th scope="col">What is modelled</th></tr></thead>
<tbody>{lod_rows}</tbody></table></div></section>
<section id="process"><h2>How it works</h2><ol>{steps}</ol></section>
<section id="cta-end"><h2>Have a scan ready?</h2><p>Describe the building, the disciplines and the LOD you need.</p>
<a class="cta" href="/request-a-quote/">Request a quote</a></section>
</main><footer><p><a href="/privacy/">Privacy</a></p></footer></body></html>
"""


def perf_budget(page):
    """Offline proxy for mobile load checks (Lighthouse needs a browser and network)."""
    return {"html_bytes": len(page.encode()), "external_scripts": len(re.findall(r"<script[^>]*src=", page)),
            "external_stylesheets": len(re.findall(r"<link[^>]*stylesheet", page)),
            "images": len(re.findall(r"<img\b", page)), "has_viewport": 'name="viewport"' in page,
            "budget_html_bytes": 30000}


class Checks(unittest.TestCase):
    def setUp(self):
        self.page = homepage_html()

    def test_sitemap_xml_matches_tree(self):
        locs = [u.find("loc").text for u in ET.fromstring(sitemap_xml())]
        def walk(ns):
            for n in ns:
                yield n["path"]
                yield from walk(n["children"])
        self.assertEqual(sorted(locs), sorted(walk(sitemap_tree())))
        self.assertEqual(len(locs), len(set(locs)))

    def test_all_lods_on_homepage_in_order(self):
        pos = [self.page.index(f">{l}<") for l, _, _ in LODS]
        self.assertEqual(pos, sorted(pos))

    def test_links_resolve_to_sitemap(self):
        paths = {p for _, p, _, _ in PAGES}
        for href in re.findall(r"href='([^']+)'|href=\"([^\"]+)\"", self.page):
            self.assertIn(href[0] or href[1], paths)

    def test_seo_basics(self):
        self.assertEqual(self.page.count("<h1"), 1)
        t = re.search(r"<title>(.*?)</title>", self.page).group(1)
        d = re.search(r'name="description" content="([^"]+)"', self.page).group(1)
        self.assertLessEqual(len(t), 60)
        self.assertLessEqual(len(d), 160)

    def test_perf_budget(self):
        b = perf_budget(self.page)
        self.assertTrue(b["has_viewport"])
        self.assertEqual(b["external_scripts"] + b["external_stylesheets"] + b["images"], 0)
        self.assertLess(b["html_bytes"], b["budget_html_bytes"])


def main():
    OUT.mkdir(exist_ok=True)
    page = homepage_html()
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT / "sitemap.json").write_text(json.dumps(sitemap_tree(), indent=2) + "\n", encoding="utf-8")
    (OUT / "sitemap.xml").write_text(sitemap_xml() + "\n", encoding="utf-8")
    (OUT / "perf_budget.json").write_text(json.dumps(perf_budget(page), indent=2) + "\n", encoding="utf-8")
    res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert res.wasSuccessful()
    print("POC_CHECKS_PASSED", res.testsRun)


if __name__ == "__main__":
    main()

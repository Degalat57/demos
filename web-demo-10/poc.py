"""One-page site design kit: synthetic logo -> Figma style tokens -> two wireframe layouts (SVG + HTML preview)."""
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

# Synthetic stand-in for the logo folder (the real logo files arrive after hire).
SYNTH_LOGO = """<svg width="240" height="80" viewBox="0 0 240 80">
<rect x="0" y="0" width="80" height="80" rx="16" fill="#1F4E79"/>
<circle cx="40" cy="40" r="20" fill="#F2A541"/>
<text x="96" y="50" font-family="Montserrat" font-weight="700" font-size="28" fill="#1F4E79">Acme</text>
<text x="96" y="70" font-family="Source Sans 3" font-size="12" fill="#5B6770">sample brand</text>
</svg>"""


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(h):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def extract_cues(svg):
    """Colours (by frequency, then first appearance) and font families from an SVG logo."""
    cols = [c.upper() for c in re.findall(r'(?:fill|stroke)="(#[0-9A-Fa-f]{3,6})"', svg)]
    order = sorted(dict.fromkeys(cols), key=lambda c: (-cols.count(c), cols.index(c)))
    fonts = list(dict.fromkeys(re.findall(r'font-family="([^"]+)"', svg)))
    return order, fonts


def build_tokens(colors, fonts):
    primary = colors[0]
    accent = colors[1] if len(colors) > 1 else primary
    muted = colors[2] if len(colors) > 2 else "#666666"
    text = "#1A1A1A" if contrast("#1A1A1A", "#FFFFFF") >= contrast(primary, "#FFFFFF") else primary
    on_primary = "#FFFFFF" if contrast("#FFFFFF", primary) >= contrast("#1A1A1A", primary) else "#1A1A1A"
    head = fonts[0] if fonts else "Inter"
    body = fonts[1] if len(fonts) > 1 else head
    color = {k: {"$type": "color", "$value": v} for k, v in (
        ("primary", primary), ("accent", accent), ("muted", muted), ("text", text),
        ("on-primary", on_primary), ("surface", "#FFFFFF"), ("surface-alt", "#F4F6F8"))}
    scale = [("display", head, 700, 48, 56), ("h2", head, 700, 32, 40), ("h3", head, 600, 22, 30),
             ("body", body, 400, 16, 24), ("caption", body, 400, 13, 18), ("button", head, 600, 16, 20)]
    typo = {n: {"$type": "typography", "$value": {"fontFamily": f, "fontWeight": w, "fontSize": "%dpx" % s,
                                                  "lineHeight": "%dpx" % lh}} for n, f, w, s, lh in scale}
    space = {str(i): {"$type": "dimension", "$value": "%dpx" % (i * 8)} for i in (1, 2, 3, 4, 6, 8, 12)}
    return {"color": color, "typography": typo, "spacing": space,
            "$meta": {"source": "synthetic logo", "contrast_text_on_surface": round(contrast(text, "#FFFFFF"), 2),
                      "contrast_on_primary": round(contrast(on_primary, primary), 2)}}


# Two distinct content hierarchies for a one-page site (desktop frame 1440 wide, mobile 390).
LAYOUTS = {
    "A_hero_first": {"note": "Big promise + CTA above the fold; proof after. Best when the offer is simple.",
                     "sections": [("nav", 80), ("hero", 560), ("benefits-3col", 360), ("testimonials", 320),
                                  ("cta-band", 220), ("footer", 160)]},
    "B_story_scroll": {"note": "Problem -> steps -> proof -> CTA; split hero. Best when the offer needs explaining.",
                       "sections": [("nav", 80), ("split-hero", 480), ("problem", 280), ("how-it-works-steps", 420),
                                    ("gallery-grid", 440), ("faq", 360), ("contact-form", 400), ("footer", 160)]},
}


def frame_svg(layout, tokens, width):
    c = {k: v["$value"] for k, v in tokens["color"].items()}
    head = tokens["typography"]["h3"]["$value"]["fontFamily"]
    scale = 1 if width >= 1000 else 0.75
    y, parts = 0, []
    for i, (name, h) in enumerate(layout["sections"]):
        h = int(h * (scale if width < 1000 else 1))
        if width < 1000 and ("3col" in name or "split" in name or "grid" in name or "steps" in name):
            h = int(h * 1.6)  # stacked columns on mobile
        fill = c["primary"] if name in ("hero", "cta-band", "footer") else (c["surface-alt"] if i % 2 else c["surface"])
        ink = c["on-primary"] if fill == c["primary"] else c["text"]
        parts.append('<rect x="0" y="%d" width="%d" height="%d" fill="%s" stroke="%s"/>' % (y, width, h, fill, c["muted"]))
        parts.append('<text x="24" y="%d" font-family="%s" font-size="18" fill="%s">%s</text>' % (y + 32, head, ink, name))
        if "hero" in name or "cta" in name:
            parts.append('<rect x="24" y="%d" width="160" height="44" rx="8" fill="%s"/>' % (y + h - 72, c["accent"]))
        y += h
    return ('<svg width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>'
            % (width, y, width, y, "".join(parts))), y


def build():
    OUT.mkdir(exist_ok=True)
    (OUT / "synthetic_logo.svg").write_text(SYNTH_LOGO, encoding="utf-8")
    colors, fonts = extract_cues(SYNTH_LOGO)
    tokens = build_tokens(colors, fonts)
    (OUT / "figma_tokens.json").write_text(json.dumps(tokens, indent=2, sort_keys=True), encoding="utf-8")
    html = ['<!doctype html><html><head><meta charset="utf-8"><title>Wireframes</title></head>',
            '<body style="font-family:sans-serif;background:#ddd"><h1>Two layout options (synthetic brand)</h1>']
    heights = {}
    for key, lay in LAYOUTS.items():
        html.append('<section id="%s"><h2>%s</h2><p>%s</p>' % (key, key, lay["note"]))
        for label, w in (("desktop", 1440), ("mobile", 390)):
            svg, h = frame_svg(lay, tokens, w)
            heights[(key, label)] = h
            (OUT / ("wireframe_%s_%s.svg" % (key, label))).write_text(svg, encoding="utf-8")
            html.append('<div class="frame" title="%s %s" style="display:inline-block;vertical-align:top;margin:8px;zoom:0.25">%s</div>' % (key, label, svg))
        html.append("</section>")
    html.append("</body></html>")
    (OUT / "index.html").write_text("\n".join(html), encoding="utf-8")
    return colors, fonts, tokens, heights


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.colors, cls.fonts, cls.tokens, cls.heights = build()

    def test_colors_from_logo(self):
        self.assertEqual(self.colors[0], "#1F4E79")  # most frequent fill
        self.assertEqual(set(self.colors), {"#1F4E79", "#F2A541", "#5B6770"})
        self.assertEqual(self.fonts, ["Montserrat", "Source Sans 3"])

    def test_contrast_known_answer(self):
        self.assertAlmostEqual(contrast("#FFFFFF", "#000000"), 21.0, places=6)
        self.assertGreaterEqual(self.tokens["$meta"]["contrast_on_primary"], 4.5)
        self.assertGreaterEqual(self.tokens["$meta"]["contrast_text_on_surface"], 4.5)

    def test_layouts_distinct_and_heights(self):
        a = [s for s, _ in LAYOUTS["A_hero_first"]["sections"]]
        b = [s for s, _ in LAYOUTS["B_story_scroll"]["sections"]]
        self.assertNotEqual(a[1:-1], b[1:-1])
        self.assertEqual(self.heights[("A_hero_first", "desktop")], sum(h for _, h in LAYOUTS["A_hero_first"]["sections"]))

    def test_outputs_parse(self):
        import xml.etree.ElementTree as ET
        svgs = sorted(OUT.glob("wireframe_*.svg"))
        self.assertEqual(len(svgs), 4)
        for p in svgs:
            ET.fromstring(p.read_text(encoding="utf-8"))
        t = json.loads((OUT / "figma_tokens.json").read_text(encoding="utf-8"))
        self.assertEqual(len(t["typography"]), 6)

    def test_short_hex(self):
        self.assertEqual(hex_to_rgb("#fff"), (255, 255, 255))


if __name__ == "__main__":
    res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert res.wasSuccessful()
    print("POC_CHECKS_PASSED %d" % res.testsRun)

"""Static, Lighthouse-style homepage audit (stdlib only). Not real Lighthouse: heuristic checks on HTML/CSS."""
import re
from html.parser import HTMLParser

VIEWPORTS = (375, 768, 1440)


class _P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def parse(html):
    p = _P()
    p.feed(html)
    return p.tags


def fixed_widths(html):
    """All px widths declared in inline styles/CSS (width: Npx / min-width: Npx)."""
    return [int(n) for n in re.findall(r'(?<![-\w])(?:min-)?width\s*:\s*(\d+)px', html)]


def audit(html):
    tags = parse(html)
    issues = []
    metas = [a for t, a in tags if t == 'meta']
    if not any(a.get('name') == 'viewport' for a in metas):
        issues.append(('all', 'missing viewport meta'))
    for t, a in tags:
        if t == 'img' and not a.get('alt'):
            issues.append(('all', 'img without alt: %s' % a.get('src', '?')))
        if t == 'img' and not (a.get('width') and a.get('height')):
            issues.append(('all', 'img without width/height (layout shift): %s' % a.get('src', '?')))
    if not any(t == 'html' and a.get('lang') for t, a in tags):
        issues.append(('all', 'html lang missing'))
    if not any(t == 'nav' for t, _ in tags):
        issues.append(('all', 'no <nav> landmark'))
    for t, a in tags:
        if t in ('div', 'span') and 'onclick' in a and 'tabindex' not in a:
            issues.append(('all', 'click handler on non-focusable <%s>' % t))
    per_vp = {}
    for vp in VIEWPORTS:
        over = [w for w in fixed_widths(html) if w > vp]
        per_vp[vp] = ['fixed width %dpx overflows %dpx viewport' % (w, vp) for w in over]
    n_global = len(issues)
    scores = {vp: max(0, 100 - 3 * n_global - 15 * len(per_vp[vp])) for vp in VIEWPORTS}
    return {'global': [m for _, m in issues], 'viewports': per_vp, 'scores': scores}

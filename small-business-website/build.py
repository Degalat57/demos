#!/usr/bin/env python3
"""Static site builder for the small-business website template.

Reads site.json and templates/*.html, writes a complete static site to dist/.
Python 3 standard library only. Idempotent.

Usage:
    python3 build.py            # build the site
    python3 build.py --check    # build, then verify the output
"""
import json
import os
import re
import shutil
import sys
from datetime import date
from html import escape
from string import Template

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_JSON = os.path.join(ROOT, "site.json")
TEMPLATES = os.path.join(ROOT, "templates")
ASSETS = os.path.join(ROOT, "assets")
DIST = os.path.join(ROOT, "dist")

ICONS = {
    "wrench": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4l-6 6a1.5 1.5 0 0 0 2.1 2.1l6-6a4 4 0 0 0 5.4-5.4l-2.3 2.3-2.1-2.1 2.3-2.3z"/>',
    "paint": '<path d="M4 4h12a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H9l-3 3v-3H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M9 14v5a2 2 0 0 0 2 2h1"/>',
    "bolt": '<path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z"/>',
    "drop": '<path d="M12 2s7 7.6 7 12a7 7 0 0 1-14 0c0-4.4 7-12 7-12z"/>',
    "home": '<path d="M3 11 12 3l9 8"/><path d="M5 10v10h14V10"/>',
    "leaf": '<path d="M4 20c0-8 6-14 16-14 0 10-6 16-14 16"/><path d="M4 20c4-4 8-6 12-7"/>',
}


def load_site():
    with open(SITE_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_template(name):
    with open(os.path.join(TEMPLATES, name), "r", encoding="utf-8") as fh:
        return fh.read()


def render(template_str, mapping):
    """Render a template using string.Template ($key / ${key})."""
    return Template(template_str).safe_substitute(mapping)


def icon_svg(name, label):
    path = ICONS.get(name, ICONS["wrench"])
    return (
        '<svg class="icon" viewBox="0 0 24 24" role="img" aria-label="%s" '
        'fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">%s</svg>'
        % (escape(label), path)
    )


def format_date(iso):
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return date(y, m, d).strftime("%B %-d, %Y") if os.name != "nt" else date(y, m, d).strftime("%B %d, %Y")
    except Exception:
        return iso


def reading_time(html):
    text = re.sub(r"<[^>]+>", " ", html)
    words = len(text.split())
    return max(1, round(words / 200))


def build_theme_css(site):
    return (
        ":root{--primary:%s;--accent:%s;--primary-dark:%s;}\n"
        % (site["primaryColor"], site["accentColor"], site["primaryColor"])
    )


def build_favicon(site):
    color = site["primaryColor"]
    initial = escape(site["name"].strip()[:1].upper() or "B")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        'aria-label="%s logo">\n'
        '  <rect width="64" height="64" rx="14" fill="%s"/>\n'
        '  <text x="32" y="44" font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif" '
        'font-size="36" font-weight="700" fill="#ffffff" text-anchor="middle">%s</text>\n'
        "</svg>\n" % (escape(site["name"]), color, initial)
    )


def nav_html(site, current, root):
    items = [
        ("index.html", "Home"),
        ("services.html", "Services"),
        ("about.html", "About"),
        ("blog/index.html", "Blog"),
        ("contact.html", "Contact"),
    ]
    out = []
    for href, label in items:
        cls = ' class="active" aria-current="page"' if href == current else ""
        out.append('<li><a href="%s%s"%s>%s</a></li>' % (root, href, cls, label))
    return "\n          ".join(out)


def services_cards(site, root=""):
    cards = []
    for s in site["services"]:
        cards.append(
            '<article class="card service-card">\n'
            '  <div class="card-icon">%s</div>\n'
            "  <h3>%s</h3>\n"
            "  <p>%s</p>\n"
            "</article>"
            % (icon_svg(s["icon"], s["title"]), escape(s["title"]), escape(s["summary"]))
        )
    return "\n".join(cards)


def testimonials_html(site):
    out = []
    for t in site["testimonials"]:
        out.append(
            '<figure class="testimonial">\n'
            '  <blockquote><p>&ldquo;%s&rdquo;</p></blockquote>\n'
            '  <figcaption><strong>%s</strong><span>%s</span></figcaption>\n'
            "</figure>"
            % (escape(t["quote"]), escape(t["name"]), escape(t["role"]))
        )
    return "\n".join(out)


def team_html(site):
    out = []
    for m in site["team"]:
        initials = "".join(p[0] for p in m["name"].split()[:2]).upper()
        out.append(
            '<article class="card team-card">\n'
            '  <div class="avatar" aria-hidden="true">%s</div>\n'
            "  <h3>%s</h3>\n"
            '  <p class="role">%s</p>\n'
            "  <p>%s</p>\n"
            "</article>"
            % (escape(initials), escape(m["name"]), escape(m["role"]), escape(m["bio"]))
        )
    return "\n".join(out)


def faq_html(site):
    faqs = [
        ("Are you licensed and insured?",
         "Yes. We are fully licensed and carry liability insurance. We are happy to provide documentation before any work begins."),
        ("Do you offer free estimates?",
         "We provide free, no-obligation estimates for most projects. For larger renovations we may schedule a short on-site visit to scope the work accurately."),
        ("What areas do you serve?",
         "We serve %s and the surrounding neighborhoods. If you are just outside our area, call us — we often can still help." % escape(site["address"]["city"])),
        ("How soon can you start?",
         "Small repairs are often scheduled within a few days. Larger projects are typically booked one to three weeks out depending on the season."),
        ("What payment methods do you accept?",
         "We accept major credit cards, checks, and bank transfers. For larger projects we can arrange a simple deposit and milestone schedule."),
    ]
    out = []
    for q, a in faqs:
        out.append(
            "<details>\n  <summary>%s</summary>\n  <p>%s</p>\n</details>" % (escape(q), a)
        )
    return "\n".join(out)


def faq_jsonld(site):
    faqs = [
        ("Are you licensed and insured?",
         "Yes. We are fully licensed and carry liability insurance. We are happy to provide documentation before any work begins."),
        ("Do you offer free estimates?",
         "We provide free, no-obligation estimates for most projects. For larger renovations we may schedule a short on-site visit to scope the work accurately."),
        ("What areas do you serve?",
         "We serve %s and the surrounding neighborhoods." % site["address"]["city"]),
        ("How soon can you start?",
         "Small repairs are often scheduled within a few days. Larger projects are typically booked one to three weeks out."),
        ("What payment methods do you accept?",
         "We accept major credit cards, checks, and bank transfers."),
    ]
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs
        ],
    }
    return json.dumps(data, indent=2)


def local_business_jsonld(site):
    addr = site["address"]
    data = {
        "@context": "https://schema.org",
        "@type": "HomeAndConstructionBusiness",
        "name": site["name"],
        "description": site["description"],
        "url": site["url"],
        "telephone": site["phone"],
        "email": site["email"],
        "address": {
            "@type": "PostalAddress",
            "streetAddress": addr["street"],
            "addressLocality": addr["city"],
            "addressRegion": addr["region"],
            "postalCode": addr["postal"],
            "addressCountry": addr["country"],
        },
        "openingHours": site["hours"],
    }
    same = [v for v in site.get("social", {}).values() if v]
    if same:
        data["sameAs"] = same
    return json.dumps(data, indent=2)


def article_jsonld(site, post):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post["title"],
        "description": post["excerpt"],
        "datePublished": post["date"],
        "author": {"@type": "Organization", "name": site["name"]},
        "publisher": {"@type": "Organization", "name": site["name"]},
        "mainEntityOfPage": "%s/blog/%s.html" % (site["url"].rstrip("/"), post["slug"]),
    }, indent=2)


def breadcrumb_jsonld(site, post):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": site["url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": site["url"] + "/blog/"},
            {"@type": "ListItem", "position": 3, "name": post["title"],
             "item": "%s/blog/%s.html" % (site["url"].rstrip("/"), post["slug"])},
        ],
    }, indent=2)


def post_cards(site, root=""):
    out = []
    for p in site["posts"]:
        out.append(
            '<article class="card post-card">\n'
            '  <p class="meta"><time datetime="%s">%s</time> · %d min read</p>\n'
            '  <h3><a href="%sblog/%s.html">%s</a></h3>\n'
            "  <p>%s</p>\n"
            '  <p><a class="read-more" href="%sblog/%s.html">Read article &rarr;</a></p>\n'
            "</article>"
            % (escape(p["date"]), escape(format_date(p["date"])), reading_time(p["body_html"]),
               root, escape(p["slug"]), escape(p["title"]), escape(p["excerpt"]),
               root, escape(p["slug"]))
        )
    return "\n".join(out)


def related_posts(site, current_slug, root=""):
    others = [p for p in site["posts"] if p["slug"] != current_slug][:2]
    out = []
    for p in others:
        out.append(
            '<li><a href="%s%s.html">%s</a></li>' % (root, escape(p["slug"]), escape(p["title"]))
        )
    return "\n".join(out)


def build():
    site = load_site()
    base_tpl = read_template("base.html")
    theme_css = build_theme_css(site)
    build_date = date.today().isoformat()
    pages = []

    def page(filename, title, description, content, extra_head="", canonical_path=None, og_type="website"):
        canonical = site["url"].rstrip("/") + "/" + (canonical_path if canonical_path is not None else filename)
        if canonical.endswith("index.html"):
            canonical = canonical[: -len("index.html")]
        # Compute root prefix based on depth of the output file.
        depth = filename.count("/")
        root = "../" * depth
        mapping = {
            "lang": "en",
            "root": root,
            "site_name": escape(site["name"]),
            "title": escape(title),
            "description": escape(description),
            "canonical": escape(canonical),
            "og_type": og_type,
            "og_url": escape(canonical),
            "theme_css": theme_css,
            "nav": nav_html(site, filename, root),
            "content": content,
            "extra_head": extra_head,
            "year": str(date.today().year),
            "phone": escape(site["phone"]),
            "email": escape(site["email"]),
            "address_street": escape(site["address"]["street"]),
            "address_city": escape(site["address"]["city"]),
            "address_region": escape(site["address"]["region"]),
            "address_postal": escape(site["address"]["postal"]),
            "hours": escape(site["hours"]),
            "facebook": escape(site["social"].get("facebook", "")),
            "instagram": escape(site["social"].get("instagram", "")),
            "linkedin": escape(site["social"].get("linkedin", "")),
            "primaryColor": escape(site["primaryColor"]),
        }
        html = render(base_tpl, mapping)
        out_path = os.path.join(DIST, filename)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(html)
        pages.append(filename)

    # Home
    home_tpl = read_template("home.html")
    home_content = render(home_tpl, {
        "root": "",
        "site_name": escape(site["name"]),
        "tagline": escape(site["tagline"]),
        "description": escape(site["description"]),
        "phone": escape(site["phone"]),
        "city": escape(site["address"]["city"]),
        "services_cards": services_cards(site, root=""),
        "testimonials": testimonials_html(site),
        "jsonld": local_business_jsonld(site),
    })
    page("index.html", "%s — %s" % (site["name"], site["tagline"]),
         site["description"], home_content,
         extra_head='<script type="application/ld+json">\n%s\n</script>' % local_business_jsonld(site))

    # About
    about_tpl = read_template("about.html")
    about_content = render(about_tpl, {
        "root": "",
        "site_name": escape(site["name"]),
        "city": escape(site["address"]["city"]),
        "team": team_html(site),
    })
    page("about.html", "About %s — Local Home Repair in %s" % (site["name"], site["address"]["city"]),
         "Meet the team behind %s. Licensed, insured, and committed to honest work in %s." % (site["name"], site["address"]["city"]),
         about_content)

    # Services
    services_tpl = read_template("services.html")
    service_sections = []
    for s in site["services"]:
        anchor = re.sub(r"[^a-z0-9]+", "-", s["title"].lower()).strip("-")
        service_sections.append(
            '<section class="service-section" id="%s">\n'
            '  <div class="service-section-icon">%s</div>\n'
            "  <h2>%s</h2>\n"
            "  <p>%s</p>\n"
            '  <p><a class="btn btn-outline" href="contact.html">Request a quote</a></p>\n'
            "</section>"
            % (anchor, icon_svg(s["icon"], s["title"]), escape(s["title"]), escape(s["summary"]))
        )
    services_content = render(services_tpl, {
        "root": "",
        "site_name": escape(site["name"]),
        "city": escape(site["address"]["city"]),
        "service_sections": "\n".join(service_sections),
        "faq": faq_html(site),
    })
    page("services.html", "Services — %s" % site["name"],
         "Plumbing, electrical, painting, roofing, carpentry, and landscaping services in %s." % site["address"]["city"],
         services_content,
         extra_head='<script type="application/ld+json">\n%s\n</script>' % faq_jsonld(site))

    # Contact
    contact_tpl = read_template("contact.html")
    contact_content = render(contact_tpl, {
        "root": "",
        "site_name": escape(site["name"]),
        "phone": escape(site["phone"]),
        "email": escape(site["email"]),
        "address_street": escape(site["address"]["street"]),
        "address_city": escape(site["address"]["city"]),
        "address_region": escape(site["address"]["region"]),
        "address_postal": escape(site["address"]["postal"]),
        "hours": escape(site["hours"]),
        "form_action": escape(site.get("formAction", "")),
    })
    page("contact.html", "Contact %s — Get a Free Estimate" % site["name"],
         "Call, email, or send a message to %s for a free estimate on your home repair or renovation project." % site["name"],
         contact_content,
         extra_head='<script type="application/ld+json">\n%s\n</script>' % local_business_jsonld(site))

    # Blog index
    blog_tpl = read_template("blog_index.html")
    blog_content = render(blog_tpl, {
        "root": "../",
        "site_name": escape(site["name"]),
        "post_cards": post_cards(site, root="../"),
    })
    page("blog/index.html", "Blog — Home Care Tips from %s" % site["name"],
         "Practical home maintenance and repair advice from the %s team." % site["name"],
         blog_content, canonical_path="blog/")

    # Posts
    post_tpl = read_template("post.html")
    for p in site["posts"]:
        post_content = render(post_tpl, {
            "root": "../",
            "site_name": escape(site["name"]),
            "title": escape(p["title"]),
            "date": escape(format_date(p["date"])),
            "date_iso": escape(p["date"]),
            "reading_time": str(reading_time(p["body_html"])),
            "body": p["body_html"],
            "related": related_posts(site, p["slug"], root=""),
            "jsonld": article_jsonld(site, p),
            "breadcrumb_jsonld": breadcrumb_jsonld(site, p),
        })
        page("blog/%s.html" % p["slug"], "%s — %s Blog" % (p["title"], site["name"]),
             p["excerpt"], post_content, canonical_path="blog/%s.html" % p["slug"], og_type="article")

    # 404
    notfound_tpl = read_template("404.html")
    notfound_content = render(notfound_tpl, {
        "root": "",
        "site_name": escape(site["name"]),
    })
    page("404.html", "Page Not Found — %s" % site["name"],
         "The page you are looking for could not be found.", notfound_content)

    # sitemap.xml
    urls = []
    for f in pages:
        if f == "404.html":
            continue
        loc = site["url"].rstrip("/") + "/" + f
        if loc.endswith("index.html"):
            loc = loc[: -len("index.html")]
        urls.append(
            "  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n  </url>"
            % (escape(loc), build_date)
        )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n</urlset>\n"
    )
    with open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(sitemap)

    # robots.txt
    with open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % site["url"].rstrip("/"))

    # site.webmanifest
    manifest = {
        "name": site["name"],
        "short_name": site["name"][:12],
        "description": site["description"],
        "start_url": "./",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": site["primaryColor"],
        "icons": [{"src": "favicon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }
    with open(os.path.join(DIST, "site.webmanifest"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    # favicon.svg
    with open(os.path.join(DIST, "favicon.svg"), "w", encoding="utf-8") as fh:
        fh.write(build_favicon(site))

    # copy assets
    if os.path.isdir(ASSETS):
        shutil.copytree(ASSETS, os.path.join(DIST, "assets"), dirs_exist_ok=True)

    print("Built %d pages:" % len(pages))
    for f in pages:
        print("  dist/%s" % f)
    print("  dist/sitemap.xml")
    print("  dist/robots.txt")
    print("  dist/site.webmanifest")
    print("  dist/favicon.svg")
    return pages


def _resolve_link(page_path, href):
    """Resolve an internal href/src relative to the page's own directory.

    Returns the absolute filesystem path it should point to, or None if the
    link is external / non-file (http(s), mailto:, tel:, data:, #fragment).
    """
    if not href:
        return None
    if href.startswith(("http://", "https://", "mailto:", "tel:", "data:", "javascript:")):
        return None
    if href.startswith("#"):
        return None
    # Strip query and fragment.
    target = href.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    # Absolute-from-root paths are not allowed for internal links; treat as
    # relative to dist root so we can still report them as broken.
    if target.startswith("/"):
        resolved = os.path.normpath(os.path.join(DIST, target.lstrip("/")))
    else:
        resolved = os.path.normpath(os.path.join(os.path.dirname(page_path), target))
    # Trailing "/" means directory index.
    if target.endswith("/"):
        resolved = os.path.join(resolved, "index.html")
    return resolved


def check():
    failures = []
    html_files = []
    for dirpath, _dirs, files in os.walk(DIST):
        for f in files:
            if f.endswith(".html"):
                html_files.append(os.path.join(dirpath, f))

    titles = {}
    descriptions = {}

    for path in html_files:
        rel = os.path.relpath(path, DIST)
        with open(path, "r", encoding="utf-8") as fh:
            html = fh.read()

        # h1 count
        h1s = re.findall(r"<h1[\s>]", html)
        if len(h1s) != 1:
            failures.append("%s: expected exactly one <h1>, found %d" % (rel, len(h1s)))

        # title
        m = re.search(r"<title>(.*?)</title>", html, re.S)
        if not m:
            failures.append("%s: missing <title>" % rel)
        else:
            t = m.group(1).strip()
            if t in titles:
                failures.append("%s: duplicate <title> with %s" % (rel, titles[t]))
            titles[t] = rel

        # meta description
        m = re.search(r'<meta name="description" content="(.*?)"', html, re.S)
        if not m:
            failures.append("%s: missing meta description" % rel)
        else:
            d = m.group(1).strip()
            if d in descriptions:
                failures.append("%s: duplicate meta description with %s" % (rel, descriptions[d]))
            descriptions[d] = rel

        # canonical
        if not re.search(r'<link rel="canonical"', html):
            failures.append("%s: missing canonical link" % rel)

        # og tags
        for prop in ("og:title", "og:description", "og:type", "og:url"):
            if not re.search(r'property="%s"' % prop, html):
                failures.append("%s: missing %s" % (rel, prop))

        # lang
        if not re.search(r'<html[^>]*\blang="', html):
            failures.append("%s: missing lang attribute" % rel)

        # viewport
        if not re.search(r'name="viewport"', html):
            failures.append("%s: missing viewport meta" % rel)

        # img/svg role=img alt/aria-label
        for tag in re.findall(r"<img[^>]*>", html):
            if "alt=" not in tag:
                failures.append("%s: <img> without alt" % rel)
        for tag in re.findall(r"<svg[^>]*role=\"img\"[^>]*>", html):
            if "aria-label=" not in tag:
                failures.append("%s: svg role=img without aria-label" % rel)

        # internal links resolve (relative to the page's own directory)
        for href in re.findall(r'href="([^"]+)"', html):
            resolved = _resolve_link(path, href)
            if resolved is None:
                continue
            if not os.path.exists(resolved):
                failures.append("%s: broken link -> %s" % (rel, href))

        for src in re.findall(r'src="([^"]+)"', html):
            resolved = _resolve_link(path, src)
            if resolved is None:
                continue
            if not os.path.exists(resolved):
                failures.append("%s: broken src -> %s" % (rel, src))

    if failures:
        print("\nCHECK FAILED (%d issues):" % len(failures))
        for f in failures:
            print("  - %s" % f)
        sys.exit(1)
    print("\nCHECK PASSED: %d HTML files verified." % len(html_files))


if __name__ == "__main__":
    build()
    if "--check" in sys.argv:
        check()

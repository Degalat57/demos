"""Healthcare WordPress sitemap + appointment-flow prototype (synthetic data, stdlib only)."""
import json, random, re, unittest, html
import xml.etree.ElementTree as ET
from pathlib import Path

random.seed(7)
OUT = Path(__file__).resolve().parent / "out"
SERVICES = ["General Checkup", "Pediatrics", "Dermatology", "Cardiology", "Physiotherapy"]
FIRST = ["Alex", "Sam", "Jordan", "Riley", "Casey", "Morgan"]
LAST = ["Rowe", "Lind", "Hart", "Vale", "Moss", "Reed"]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def build_data():
    doctors = []
    for i in range(6):
        name = "Dr. %s %s" % (FIRST[i], LAST[i])
        doctors.append({"name": name, "slug": slug(name), "services": sorted(random.sample(SERVICES, 2))})
    return doctors


def build_sitemap(doctors):
    """WordPress page tree: (title, slug, parent, post_type)."""
    pages = [("Home", "", None, "page"), ("Services", "services", None, "page")]
    pages += [(s, "services/" + slug(s), "services", "service") for s in SERVICES]
    pages.append(("Our Doctors", "doctors", None, "page"))
    pages += [(d["name"], "doctors/" + d["slug"], "doctors", "doctor") for d in doctors]
    pages += [("Request an Appointment", "appointments", None, "page"),
              ("Contact", "contact", None, "page"), ("Privacy Policy", "privacy-policy", None, "page")]
    return [{"title": t, "path": "/" + p + ("/" if p else ""), "parent": par, "post_type": pt} for t, p, par, pt in pages]


def sitemap_xml(pages):
    root = ET.Element("urlset")
    for p in pages:
        ET.SubElement(ET.SubElement(root, "url"), "loc").text = "{site}" + p["path"]
    return ET.tostring(root, encoding="unicode")


class Booking:
    """Appointment requests with double-booking protection and server-side validation."""
    SLOTS = ["09:00", "10:00", "11:00", "14:00", "15:00"]

    def __init__(self, doctors):
        self.doctors = {d["slug"]: d for d in doctors}
        self.taken = set()

    def validate(self, r):
        errs = []
        if not re.fullmatch(r"[A-Za-z .'-]{2,60}", r.get("name", "")):
            errs.append("name")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", r.get("email", "")):
            errs.append("email")
        d = self.doctors.get(r.get("doctor"))
        if not d:
            errs.append("doctor")
        elif r.get("service") not in d["services"]:
            errs.append("service")
        if r.get("slot") not in self.SLOTS or not re.fullmatch(r"2030-\d\d-\d\d", r.get("date", "")):
            errs.append("slot")
        return errs

    def request(self, r):
        errs = self.validate(r)
        if errs:
            return {"ok": False, "errors": errs}
        key = (r["doctor"], r["date"], r["slot"])
        if key in self.taken:
            return {"ok": False, "errors": ["slot_taken"]}
        self.taken.add(key)
        return {"ok": True}


CSS = ("body{font-family:system-ui,sans-serif;margin:0;color:#123}header{background:#0b6e8a;color:#fff;padding:1rem}"
       "nav a{color:#fff;margin-right:1rem}main{max-width:900px;margin:auto;padding:1rem}"
       ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem}"
       ".card{border:1px solid #cde;border-radius:8px;padding:1rem}label{display:block;margin-top:.6rem}"
       "button{margin-top:1rem;padding:.6rem 1.2rem;background:#0b6e8a;color:#fff;border:0;border-radius:6px}"
       "#msg{margin-top:1rem;font-weight:bold}a:focus,button:focus,input:focus,select:focus{outline:3px solid #f90}")


def render_site(pages, doctors):
    top = [p for p in pages if p["parent"] is None]
    nav = "".join('<a href="#%s">%s</a>' % (slug(p["title"]) or "home", html.escape(p["title"])) for p in top)
    svc = "".join('<div class="card"><h3>%s</h3><p>Treatment information placeholder.</p></div>' % s for s in SERVICES)
    docs = "".join('<div class="card"><h3>%s</h3><p>%s</p></div>' % (html.escape(d["name"]), ", ".join(d["services"])) for d in doctors)
    dopts = "".join('<option value="%s">%s</option>' % (d["slug"], html.escape(d["name"])) for d in doctors)
    sopts = "".join("<option>%s</option>" % s for s in Booking.SLOTS)
    js = ("const D=%s;const taken=new Set();const ds=document.getElementById('doctor'),ss=document.getElementById('service');"
          "function fill(){ss.innerHTML=D[ds.value].map(s=>'<option>'+s+'</option>').join('')}ds.onchange=fill;fill();"
          "document.getElementById('f').onsubmit=e=>{e.preventDefault();const f=new FormData(e.target);"
          "const m=document.getElementById('msg');if(!/^[A-Za-z .'-]{2,60}$/.test(f.get('name'))||!/^[^@\\s]+@[^@\\s]+\\.[a-z]{2,}$/.test(f.get('email'))){m.textContent='Please check name and email.';return}"
          "const k=f.get('doctor')+f.get('date')+f.get('slot');if(taken.has(k)){m.textContent='That slot is already taken.';return}"
          "taken.add(k);m.textContent='Request received for '+f.get('date')+' '+f.get('slot')+'.'};"
          ) % json.dumps({d["slug"]: d["services"] for d in doctors})
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Sample Clinic</title><style>%s</style></head><body><header><strong>Sample Clinic</strong><nav aria-label='Main'>%s</nav></header><main>"
            "<section id='home'><h1>Care made simple</h1></section><section id='services'><h2>Services</h2><div class='cards'>%s</div></section>"
            "<section id='our-doctors'><h2>Our Doctors</h2><div class='cards'>%s</div></section>"
            "<section id='request-an-appointment'><h2>Request an Appointment</h2><form id='f'>"
            "<label for='name'>Name</label><input id='name' name='name' required><label for='email'>Email</label><input id='email' name='email' type='email' required>"
            "<label for='doctor'>Doctor</label><select id='doctor' name='doctor'>%s</select><label for='service'>Service</label><select id='service' name='service'></select>"
            "<label for='date'>Date</label><input id='date' name='date' value='2030-01-15'><label for='slot'>Time</label><select id='slot' name='slot'>%s</select>"
            "<button type='submit'>Send request</button><div id='msg' role='status' aria-live='polite'></div></form></section>"
            "<section id='contact'><h2>Contact</h2><p>Contact details placeholder.</p></section><section id='privacy-policy'><h2>Privacy Policy</h2><p>Minimal data: name, email, preferred slot.</p></section>"
            "</main><script>%s</script></body></html>") % (CSS, nav, svc, docs, dopts, sopts, js)


DOCS = build_data()
PAGES = build_sitemap(DOCS)


class T(unittest.TestCase):
    def test_page_count(self):
        self.assertEqual(len(PAGES), 6 + len(SERVICES) + len(DOCS))
        self.assertEqual(len({p["path"] for p in PAGES}), len(PAGES))

    def test_parents_exist(self):
        paths = {p["path"].strip("/") for p in PAGES}
        for p in PAGES:
            assert p["parent"] is None or p["parent"] in paths

    def test_xml_matches(self):
        root = ET.fromstring(sitemap_xml(PAGES))
        self.assertEqual(len(root), len(PAGES))

    def test_double_booking(self):
        b = Booking(DOCS); d = DOCS[0]
        r = {"name": "Test Patient", "email": "t" + "@" + "example.test", "doctor": d["slug"], "service": d["services"][0], "date": "2030-01-15", "slot": "09:00"}
        self.assertTrue(b.request(r)["ok"])
        self.assertEqual(b.request(dict(r))["errors"], ["slot_taken"])
        self.assertTrue(b.request(dict(r, doctor=DOCS[1]["slug"], service=DOCS[1]["services"][0]))["ok"])

    def test_validation(self):
        b = Booking(DOCS)
        res = b.request({"name": "<x>", "email": "bad", "doctor": "nope", "date": "2030-01-01", "slot": "03:00"})
        self.assertEqual(res["errors"], ["name", "email", "doctor", "slot"])

    def test_html_nav(self):
        h = render_site(PAGES, DOCS)
        for p in PAGES:
            if p["parent"] is None:
                self.assertIn(html.escape(p["title"]), h)


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "sitemap.json").write_text(json.dumps(PAGES, indent=2))
    (OUT / "sitemap.xml").write_text(sitemap_xml(PAGES))
    (OUT / "index.html").write_text(render_site(PAGES, DOCS))
    res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    assert res.wasSuccessful()
    print("POC_CHECKS_PASSED %d" % res.testsRun)


if __name__ == "__main__":
    main()

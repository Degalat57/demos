"""Rental marketplace core: SQLite schema, roles, permissions, listings, filters, inquiries, moderation."""
import html
import json
import random
import sqlite3

CATEGORIES = ("student", "residential", "commercial", "services")
ROLES = ("renter", "owner", "agent", "provider", "admin")
ACTIONS = ("browse", "inquire", "create_listing", "edit_own_listing", "report", "moderate", "manage_users")
PERMS = {
    "renter": {"browse", "inquire", "report"},
    "owner": {"browse", "create_listing", "edit_own_listing", "report"},
    "agent": {"browse", "create_listing", "edit_own_listing", "report"},
    "provider": {"browse", "create_listing", "edit_own_listing", "report"},
    "admin": set(ACTIONS),
}
# providers may only list in services; owners/agents only property categories
ALLOWED_CATS = {"owner": CATEGORIES[:3], "agent": CATEGORIES[:3], "provider": ("services",), "admin": CATEGORIES}
CITIES = ("Northtown", "Riverside", "Hillcrest", "Lakeview")

USER_STORIES = [
    ("renter", "student", "As a renter I filter student rooms by price and area so I find one near campus."),
    ("renter", "residential", "As a renter I send an inquiry on a flat so the owner can contact me."),
    ("owner", "residential", "As an owner I post a listing with photos, price and location."),
    ("owner", "commercial", "As an owner I edit or deactivate my commercial listing."),
    ("agent", "residential", "As an agent I manage listings for several owners from one dashboard (Phase 2)."),
    ("provider", "services", "As a service provider I list my repair service with a price from."),
    ("admin", "all", "As an admin I review reported listings and hide or restore them."),
    ("renter", "commercial", "As a renter I report a suspicious commercial listing."),
]


class Denied(Exception):
    pass


def connect():
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL);
    CREATE TABLE listings(id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id),
      category TEXT NOT NULL, title TEXT NOT NULL, price INTEGER NOT NULL CHECK(price>0),
      city TEXT NOT NULL, photos TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active');
    CREATE TABLE inquiries(id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL REFERENCES listings(id),
      sender_id INTEGER NOT NULL REFERENCES users(id), message TEXT NOT NULL);
    CREATE TABLE reports(id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL REFERENCES listings(id),
      reporter_id INTEGER NOT NULL REFERENCES users(id), reason TEXT NOT NULL, resolved INTEGER DEFAULT 0);
    """)
    return db


def role_of(db, uid):
    r = db.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        raise Denied("unknown user")
    return r[0]


def need(db, uid, action):
    role = role_of(db, uid)
    if action not in PERMS[role]:
        raise Denied("%s cannot %s" % (role, action))
    return role


def add_user(db, name, role):
    assert role in ROLES
    return db.execute("INSERT INTO users(name,role) VALUES(?,?)", (name, role)).lastrowid


def post_listing(db, uid, category, title, price, city, photos):
    role = need(db, uid, "create_listing")
    if category not in ALLOWED_CATS[role]:
        raise Denied("%s cannot list in %s" % (role, category))
    if not title.strip() or not photos:
        raise ValueError("title and at least one photo required")
    if int(price) <= 0:
        raise ValueError("price must be positive")
    return db.execute("INSERT INTO listings(owner_id,category,title,price,city,photos) VALUES(?,?,?,?,?,?)",
                      (uid, category, title.strip(), int(price), city, json.dumps(photos))).lastrowid


def edit_listing(db, uid, lid, **fields):
    role = need(db, uid, "edit_own_listing")
    row = db.execute("SELECT owner_id FROM listings WHERE id=?", (lid,)).fetchone()
    if not row or (row[0] != uid and role != "admin"):
        raise Denied("not your listing")
    for k, v in fields.items():
        if k not in ("title", "price", "city", "status"):
            raise ValueError(k)
        db.execute("UPDATE listings SET %s=? WHERE id=?" % k, (v, lid))


def search(db, category=None, min_price=None, max_price=None, city=None):
    q, a = "SELECT id,category,title,price,city FROM listings WHERE status='active'", []
    for cond, val in (("category=?", category), ("price>=?", min_price), ("price<=?", max_price),
                      ("city=?", city)):
        if val is not None:
            q += " AND " + cond
            a.append(val)
    return db.execute(q + " ORDER BY price, id", a).fetchall()


def send_inquiry(db, uid, lid, message):
    need(db, uid, "inquire")
    row = db.execute("SELECT status FROM listings WHERE id=?", (lid,)).fetchone()
    if not row or row[0] != "active":
        raise ValueError("listing not available")
    if not message.strip():
        raise ValueError("empty message")
    return db.execute("INSERT INTO inquiries(listing_id,sender_id,message) VALUES(?,?,?)",
                      (lid, uid, message.strip())).lastrowid


def owner_inbox(db, uid):
    return db.execute("SELECT i.id,l.title,i.message FROM inquiries i JOIN listings l ON l.id=i.listing_id "
                      "WHERE l.owner_id=? ORDER BY i.id", (uid,)).fetchall()


def report(db, uid, lid, reason):
    need(db, uid, "report")
    return db.execute("INSERT INTO reports(listing_id,reporter_id,reason) VALUES(?,?,?)",
                      (lid, uid, reason)).lastrowid


def moderation_queue(db, uid):
    need(db, uid, "moderate")
    return db.execute("SELECT r.id,r.listing_id,r.reason FROM reports r WHERE resolved=0 ORDER BY r.id").fetchall()


def moderate(db, uid, report_id, hide):
    need(db, uid, "moderate")
    lid = db.execute("SELECT listing_id FROM reports WHERE id=?", (report_id,)).fetchone()[0]
    db.execute("UPDATE listings SET status=? WHERE id=?", ("hidden" if hide else "active", lid))
    db.execute("UPDATE reports SET resolved=1 WHERE id=?", (report_id,))


def seed(db, seed_value=7):
    rng = random.Random(seed_value)
    ids = {r: [add_user(db, "%s_%d" % (r, i), r) for i in range(1, 4)] for r in ROLES if r != "admin"}
    ids["admin"] = [add_user(db, "admin_1", "admin")]
    names = {"student": "Room", "residential": "Flat", "commercial": "Office", "services": "Repair service"}
    base = {"student": 300, "residential": 700, "commercial": 1500, "services": 40}
    for n in range(40):
        cat = CATEGORIES[n % 4]
        role = "provider" if cat == "services" else rng.choice(["owner", "agent"])
        uid = rng.choice(ids[role])
        price = base[cat] + rng.randrange(0, base[cat], 10)
        post_listing(db, uid, cat, "%s #%d" % (names[cat], n + 1), price, rng.choice(CITIES),
                     ["photo_%d_%d.jpg" % (n + 1, k) for k in range(1, rng.randint(2, 4))])
    return ids


def render_html(db):
    rows = db.execute("SELECT id,category,title,price,city,photos FROM listings WHERE status='active' "
                      "ORDER BY id").fetchall()
    data = [dict(id=r[0], category=r[1], title=r[2], price=r[3], city=r[4], photos=len(json.loads(r[5])))
            for r in rows]
    opts = "".join('<option value="%s">%s</option>' % (c, c) for c in CITIES)
    cats = "".join('<option value="%s">%s</option>' % (c, c) for c in CATEGORIES)
    return """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Rentals (synthetic demo)</title>
<style>body{font-family:sans-serif;margin:0;background:#f4f5f7}header{background:#234;color:#fff;padding:12px}
form,.card{background:#fff;margin:8px;padding:10px;border-radius:8px}label{display:block;margin:4px 0}
input,select,textarea,button{width:100%%;padding:8px;box-sizing:border-box;font-size:16px}
.card b{float:right}#msg{color:green;margin:8px}</style></head><body>
<header><h1>Rentals</h1><small>Synthetic demo data</small></header>
<form id="post"><h2>Post a listing</h2>
<label>Category<select id="pcat">CATS</select></label><label>Title<input id="ptitle"></label>
<label>Price<input id="pprice" type="number"></label><label>Location<select id="pcity">OPTS</select></label>
<button type="button" id="pbtn">Post</button></form>
<form id="filter"><h2>Filter</h2><label>Category<select id="fcat"><option value="">any</option>CATS</select></label>
<label>Max price<input id="fmax" type="number"></label>
<label>Location<select id="fcity"><option value="">any</option>OPTS</select></label>
<button type="button" id="fbtn">Apply</button></form>
<div id="count" style="margin:8px"></div><div id="list"></div><div id="msg"></div>
<script>
var L=DATA;
function show(){var c=fcat.value,m=parseInt(fmax.value||"0"),t=fcity.value;
var r=L.filter(function(x){return(!c||x.category==c)&&(!m||x.price<=m)&&(!t||x.city==t)});
r.sort(function(a,b){return a.price-b.price||a.id-b.id});
count.textContent=r.length+" listings";list.innerHTML="";
r.forEach(function(x){var d=document.createElement("div");d.className="card";
d.innerHTML="<b>"+x.price+"</b>"+x.title+"<br><small>"+x.category+" &middot; "+x.city+"</small>"+
"<textarea placeholder='Message'></textarea><button type='button'>Send inquiry</button>";
d.querySelector("button").onclick=function(){var t=d.querySelector("textarea").value.trim();
msg.textContent=t?"Inquiry sent for "+x.title:"Message required";};list.appendChild(d);});}
pbtn.onclick=function(){var p=parseInt(pprice.value||"0");if(!ptitle.value.trim()||p<=0){msg.textContent="Title and positive price required";return;}
L.push({id:L.length+1000,category:pcat.value,title:ptitle.value.trim(),price:p,city:pcity.value,photos:1});
msg.textContent="Listing posted";show();};fbtn.onclick=show;show();
</script></body></html>""".replace("CATS", cats).replace("OPTS", opts).replace(
        "DATA", html.escape(json.dumps(data), quote=False).replace("&amp;", "&"))

"""Entry point: builds synthetic marketplace, runs the post/filter/inquire/moderate flow, writes out/, runs checks."""
import csv
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import market as m  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def build():
    OUT.mkdir(exist_ok=True)
    db = m.connect()
    ids = m.seed(db)
    with (OUT / "user_stories.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["role", "category", "story"])
        w.writerows(m.USER_STORIES)
    with (OUT / "permissions_matrix.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["role"] + list(m.ACTIONS) + ["categories"])
        for r in m.ROLES:
            w.writerow([r] + ["yes" if a in m.PERMS[r] else "no" for a in m.ACTIONS]
                       + ["|".join(m.ALLOWED_CATS.get(r, ()))])
    owner, renter, admin = ids["owner"][0], ids["renter"][0], ids["admin"][0]
    lid = m.post_listing(db, owner, "student", "Bright room near campus", 350, "Riverside", ["a.jpg", "b.jpg"])
    hits = m.search(db, category="student", max_price=400, city="Riverside")
    iq = m.send_inquiry(db, renter, lid, "Is it free next month?")
    rep = m.report(db, renter, 5, "duplicate listing")
    queue = m.moderation_queue(db, admin)
    m.moderate(db, admin, rep, hide=True)
    flow = {"posted_listing": lid, "filter_student_le400_riverside": [list(h) for h in hits],
            "inquiry_id": iq, "owner_inbox": [list(x) for x in m.owner_inbox(db, owner)],
            "queue_before": [list(q) for q in queue], "listing5_status":
                db.execute("SELECT status FROM listings WHERE id=5").fetchone()[0]}
    (OUT / "flow.json").write_text(json.dumps(flow, indent=2, sort_keys=True) + "\n")
    (OUT / "index.html").write_text(m.render_html(db))
    return db, ids


class Checks(unittest.TestCase):
    def setUp(self):
        self.db = m.connect()
        self.ids = m.seed(self.db)

    def test_filter_matches_python(self):
        rows = self.db.execute("SELECT id,category,price,city,status FROM listings").fetchall()
        exp = sorted((r[2], r[0]) for r in rows if r[1] == "residential" and r[2] <= 1000
                     and r[3] == "Lakeview" and r[4] == "active")
        got = [(r[3], r[0]) for r in m.search(self.db, "residential", None, 1000, "Lakeview")]
        self.assertEqual(got, exp)

    def test_row_counts(self):
        self.assertEqual(len(m.search(self.db)), 40)
        self.assertEqual(sum(len(m.search(self.db, c)) for c in m.CATEGORIES), 40)

    def test_permissions(self):
        with self.assertRaises(m.Denied):
            m.post_listing(self.db, self.ids["renter"][0], "student", "x", 1, "Riverside", ["p"])
        with self.assertRaises(m.Denied):
            m.post_listing(self.db, self.ids["provider"][0], "residential", "x", 1, "Riverside", ["p"])
        with self.assertRaises(m.Denied):
            m.moderation_queue(self.db, self.ids["owner"][0])
        with self.assertRaises(m.Denied):
            m.send_inquiry(self.db, self.ids["owner"][0], 1, "hi")

    def test_edit_only_own(self):
        lid = m.post_listing(self.db, self.ids["owner"][0], "commercial", "Shop", 900, "Hillcrest", ["p"])
        with self.assertRaises(m.Denied):
            m.edit_listing(self.db, self.ids["owner"][1], lid, price=1)
        m.edit_listing(self.db, self.ids["owner"][0], lid, price=800)
        self.assertEqual(m.search(self.db, "commercial", 800, 800, "Hillcrest")[-1][0], lid)

    def test_validation_edges(self):
        o = self.ids["owner"][0]
        for args in (("", 100, ["p"]), ("t", 0, ["p"]), ("t", 100, [])):
            with self.assertRaises(ValueError):
                m.post_listing(self.db, o, "student", args[0], args[1], "Riverside", args[2])
        with self.assertRaises(ValueError):
            m.send_inquiry(self.db, self.ids["renter"][0], 1, "   ")

    def test_moderation_hides_and_inbox(self):
        r, a = self.ids["renter"][0], self.ids["admin"][0]
        rid = m.report(self.db, r, 3, "spam")
        m.moderate(self.db, a, rid, hide=True)
        self.assertNotIn(3, [x[0] for x in m.search(self.db)])
        self.assertEqual(m.moderation_queue(self.db, a), [])
        with self.assertRaises(ValueError):
            m.send_inquiry(self.db, r, 3, "hi")


def main():
    build()
    res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert res.wasSuccessful()
    flow = json.loads((OUT / "flow.json").read_text())
    assert flow["listing5_status"] == "hidden" and flow["owner_inbox"], flow
    n = res.testsRun + 1
    print("POC_CHECKS_PASSED %d" % n)


if __name__ == "__main__":
    main()

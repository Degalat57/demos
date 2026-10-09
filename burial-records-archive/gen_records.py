#!/usr/bin/env python3
"""Generate deterministic synthetic data for the Historic Burial Records Archive demo.

Writes:
  data/records.json            200 synthetic records
  data/scans/<id>.svg          one ledger-page scan per record
  data/sample-import.csv       25 rows, exactly 4 with deliberate problems
  data/sample-import-clean.csv 10 valid rows
"""
import csv
import datetime
import json
import os
import random

random.seed(1927)

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
SCANS = os.path.join(DATA, "scans")
os.makedirs(SCANS, exist_ok=True)

MALE = ["James", "John", "William", "Robert", "Joseph", "George", "Charles",
        "Thomas", "Henry", "Edward", "Frank", "Walter", "Arthur", "Harold",
        "Albert", "Samuel", "Louis", "Clarence", "Willie", "Daniel", "Earnest",
        "Herman", "Floyd", "Otis", "Leroy", "Elijah", "Moses", "Aaron", "Booker",
        "Junius", "Roosevelt", "Ezekiel", "Columbus", "Rubin", "Nathaniel",
        "Cornelius"]
FEMALE = ["Mary", "Elizabeth", "Sarah", "Margaret", "Nancy", "Annie", "Emma",
          "Alice", "Florence", "Minnie", "Ida", "Bertha", "Clara", "Edna",
          "Ella", "Fannie", "Grace", "Helen", "Irene", "Lula", "Maude",
          "Myrtle", "Nellie", "Ollie", "Rosa", "Ruth", "Sallie", "Susie",
          "Velma", "Viola", "Carrie", "Dora", "Eula", "Hattie", "Lillie",
          "Mattie", "Pearlie", "Effie", "Beulah", "Dorothy", "Elnora",
          "Octavia", "Julia", "Amanda", "Frances", "Louisa", "Rebecca",
          "Rachel", "Adeline", "Josephine", "Rosalee", "Clementine",
          "Magnolia", "Catherine", "Evalina", "Cornelia", "Isabella",
          "Wilhelmina"]
SURNAMES = ["Johnson", "Thompson", "Smith", "Williams", "Brown", "Jones",
            "Davis", "Miller", "Wilson", "Anderson", "Taylor", "Thomas",
            "Moore", "Jackson", "Martin", "Lee", "Harris", "Clark", "Lewis",
            "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott",
            "Green", "Baker", "Adams", "Nelson", "Hill", "Campbell",
            "Mitchell", "Roberts", "Turner", "Phillips", "Parker", "Evans",
            "Edwards", "Collins", "Stewart", "Morris", "Rogers", "Reed",
            "Cook", "Morgan", "Bell", "Murphy", "Bailey", "Cooper",
            "Richardson", "Cox", "Howard", "Ward", "Brooks", "Watson",
            "Powell", "Long", "Patterson", "Hughes", "Sanders", "Price",
            "Bennett", "Wood", "Barnes", "Ross", "Henderson", "Coleman",
            "Jenkins", "Perry", "Bishop", "Hollingsworth", "Pinkston",
            "Carothers", "Whitfield", "Buford"]
SUR_VARIANTS = {"Johnson": "Johnston", "Thompson": "Thomson", "Smith": "Smyth",
                "Clark": "Clarke", "Rogers": "Rodgers", "Martin": "Martyn",
                "Stewart": "Stuart"}
GIV_VARIANTS = {"Mattie": "Matty", "Willie": "Willy", "Pearlie": "Pearl",
                "Lillie": "Lilly", "Nellie": "Nelly", "Maude": "Maud"}

COUNTY_TOWNS = {
    "Ashford": ["Millbrook", "Oakdale", "Cedar Bend", "Kingsley"],
    "Briarwood": ["Fernhill", "Heron Point", "Lakeview"],
    "Calder": ["Pinecrest", "Marlow", "Dunmore"],
    "Elmhurst": ["Willow Creek", "Hartwell", "Stonebridge"],
    "Fairhaven": ["Ridgeway", "Brookfield", "Corbin"],
    "Glenmoor": ["Haddon", "Ashby", "Thornton"],
    "Hollis": ["Silver Fork", "Dalton", "Easton"],
    "Ivydale": ["Maplewood", "Granger", "Fenwick"],
    "Juniper": ["Bellmont", "Carver", "Linden"],
    "Kestrel": ["Kestrel", "White Ash", "Dunbar"],
    "Lowell": ["Rivertown", "Ashton", "Holloway"],
}
CEMETERIES = ["Mt. Zion Cemetery (fictional)",
              "Rose Hill Cemetery (fictional)",
              "Evergreen Rest Cemetery (fictional)",
              "Shady Grove Cemetery (fictional)",
              "Pleasant Valley Cemetery (fictional)",
              "St. Matthew's Cemetery (fictional)",
              "New Hope Cemetery (fictional)",
              "Fairview Cemetery (fictional)"]
NOTES = ["Cause of death listed as pneumonia.",
         "Informant was a neighbor.",
         "Record partially water-damaged.",
         "Burial in family plot.",
         "Grave location unmarked in ledger.",
         "Handwriting unclear; transcribed as best possible.",
         "Funeral handled by local undertaker.",
         "Payment recorded as received in full.",
         "Child of informant; age estimated.",
         "Moved from another county shortly before death."]
TRANSCRIBERS = ["Volunteer A", "Volunteer A", "Volunteer A", "Volunteer B"]

FIELDS = ["record_id", "surname", "given_names", "maiden_name", "sex",
          "age_at_death", "birth_date", "death_date", "burial_date", "county",
          "place_of_death", "cemetery", "funeral_cost", "informant",
          "ledger_book", "ledger_page", "notes", "transcriber", "scan"]


def rand_date(year):
    return datetime.date(year, 1, 1) + datetime.timedelta(days=random.randint(0, 364))


def maybe_variant(surname, given):
    if random.random() < 0.10:
        if surname in SUR_VARIANTS:
            return SUR_VARIANTS[surname], given
        if given in GIV_VARIANTS:
            return surname, GIV_VARIANTS[given]
        key = random.choice(list(SUR_VARIANTS.keys()))
        return SUR_VARIANTS[key], given
    return surname, given


def make_record(year, seq, used_ids):
    rid = "HBR-%d-%04d" % (year, seq)
    while rid in used_ids:
        seq += 1
        rid = "HBR-%d-%04d" % (year, seq)
    used_ids.add(rid)

    sex = random.choice(["M", "F"])
    given = random.choice(MALE if sex == "M" else FEMALE)
    surname = random.choice(SURNAMES)
    surname, given = maybe_variant(surname, given)
    if sex == "F" and random.random() < 0.35:
        maiden = random.choice(SURNAMES)
    else:
        maiden = ""

    death = rand_date(year)
    burial = death + datetime.timedelta(days=random.randint(0, 5))
    if random.random() < 0.75:
        age = random.randint(0, 95)
        byear = year - age
        r = random.random()
        if r < 0.6:
            birth = "%04d-%02d-%02d" % (byear, random.randint(1, 12), random.randint(1, 28))
        elif r < 0.85:
            birth = str(byear)
        else:
            birth = ""
    else:
        age = ""
        birth = str(random.randint(1840, 1950)) if random.random() < 0.5 else ""

    county = random.choice(list(COUNTY_TOWNS.keys()))
    town = random.choice(COUNTY_TOWNS[county])
    cost = "$%d.%02d" % (random.randint(15, 120), random.randint(0, 99)) if random.random() < 0.8 else ""
    informant = "%s %s" % (random.choice(FEMALE + MALE), random.choice(SURNAMES))
    notes = random.choice(NOTES) if random.random() < 0.6 else ""

    return {
        "record_id": rid,
        "surname": surname,
        "given_names": given,
        "maiden_name": maiden,
        "sex": sex,
        "age_at_death": age,
        "birth_date": birth,
        "death_date": death.isoformat(),
        "burial_date": burial.isoformat(),
        "county": county,
        "place_of_death": town,
        "cemetery": random.choice(CEMETERIES),
        "funeral_cost": cost,
        "informant": informant,
        "ledger_book": "Book %d" % random.randint(1, 12),
        "ledger_page": random.randint(1, 400),
        "notes": notes,
        "transcriber": random.choice(TRANSCRIBERS),
        "scan": "scans/%s.svg" % rid,
        "synthetic": True,
    }


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def scan_svg(rec):
    fields = [
        ("Record No.", rec["record_id"]),
        ("Name", "%s, %s" % (rec["surname"], rec["given_names"])),
        ("Maiden name", rec["maiden_name"] or "-"),
        ("Sex", rec["sex"]),
        ("Age", str(rec["age_at_death"]) if rec["age_at_death"] != "" else "-"),
        ("Born", rec["birth_date"] or "-"),
        ("Died", rec["death_date"]),
        ("Buried", rec["burial_date"]),
        ("County", rec["county"]),
        ("Place of death", rec["place_of_death"]),
        ("Cemetery", rec["cemetery"]),
        ("Funeral cost", rec["funeral_cost"] or "-"),
        ("Informant", rec["informant"]),
        ("Notes", rec["notes"] or "-"),
    ]
    parts = []
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1100" viewBox="0 0 800 1100">')
    parts.append('<defs><pattern id="paper" width="8" height="8" patternUnits="userSpaceOnUse">')
    parts.append('<rect width="8" height="8" fill="#f7f3ea"/>')
    parts.append('<circle cx="2" cy="3" r="0.5" fill="#e3dcc8" opacity="0.6"/>')
    parts.append('<circle cx="6" cy="7" r="0.4" fill="#e3dcc8" opacity="0.5"/>')
    parts.append('</pattern></defs>')
    parts.append('<rect width="800" height="1100" fill="url(#paper)"/>')
    parts.append('<rect x="30" y="30" width="740" height="1040" fill="none" stroke="#b9ae95" stroke-width="2"/>')
    parts.append('<text x="400" y="90" text-anchor="middle" font-family="Georgia, \'Times New Roman\', serif" font-size="30" fill="#2b2622">Historic Burial Records</text>')
    parts.append('<text x="400" y="128" text-anchor="middle" font-family="Georgia, \'Times New Roman\', serif" font-size="20" fill="#2f5d50">%s, Page %s</text>' % (esc(rec["ledger_book"]), esc(rec["ledger_page"])))
    parts.append('<text x="400" y="160" text-anchor="middle" font-family="Georgia, \'Times New Roman\', serif" font-size="14" fill="#8a2020">SYNTHETIC SAMPLE - not a real record</text>')
    parts.append('<line x1="60" y1="180" x2="740" y2="180" stroke="#8a7a5c" stroke-width="2"/>')
    y0, dy = 240, 54
    for i, (label, value) in enumerate(fields):
        y = y0 + i * dy
        parts.append('<text x="70" y="%d" font-family="Georgia, serif" font-size="15" fill="#6b6357">%s</text>' % (y - 8, esc(label)))
        parts.append('<line x1="60" y1="%d" x2="740" y2="%d" stroke="#c9bfa4" stroke-width="1"/>' % (y + 10, y + 10))
        parts.append('<text x="250" y="%d" font-family="\'Segoe Script\', \'Bradley Hand\', cursive" font-size="19" fill="#2b2622">%s</text>' % (y, esc(value)))
    parts.append('<text x="400" y="1040" text-anchor="middle" font-family="Georgia, serif" font-size="13" fill="#6b6357">Transcribed by %s - SYNTHETIC SAMPLE</text>' % esc(rec["transcriber"]))
    parts.append('<text transform="translate(400,560) rotate(-30)" text-anchor="middle" font-family="Georgia, serif" font-size="96" font-weight="bold" fill="#c0392b" opacity="0.16">SYNTHETIC SAMPLE</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def main():
    used_ids = set()
    records = []
    for _ in range(200):
        year = random.randint(1900, 1965)
        records.append(make_record(year, random.randint(1, 9999), used_ids))

    with open(os.path.join(DATA, "records.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    for rec in records:
        with open(os.path.join(SCANS, rec["record_id"] + ".svg"), "w", encoding="utf-8") as f:
            f.write(scan_svg(rec))

    # 25 new rows for the sample import; 4 get deliberate problems.
    sample = []
    for i in range(25):
        year = random.randint(1900, 1965)
        sample.append(make_record(year, 9001 + i, used_ids))
    sample[3]["surname"] = ""
    sample[9]["death_date"] = "1931-02-30"
    sample[14]["county"] = "Atlantis"
    sample[20]["record_id"] = records[0]["record_id"]

    clean = []
    for i in range(10):
        year = random.randint(1900, 1965)
        clean.append(make_record(year, 9501 + i, used_ids))

    def write_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(FIELDS)
            for r in rows:
                w.writerow([str(r[k]) if r[k] != "" else "" for k in FIELDS])

    write_csv(os.path.join(DATA, "sample-import.csv"), sample)
    write_csv(os.path.join(DATA, "sample-import-clean.csv"), clean)
    print("Wrote %d records, %d scans, 2 sample CSVs to data/" % (len(records), len(records)))


if __name__ == "__main__":
    main()

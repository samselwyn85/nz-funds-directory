"""Weekly import of awarded NZ government contracts (MBIE open data).

Source: "New Zealand government procurement open data" published by MBIE,
https://www.mbie.govt.nz/cross-government-functions/new-zealand-government-procurement-and-property/open-data
These are the contract award notices agencies post on GETS, released as open
data (Crown copyright, CC BY 4.0, attribution to MBIE). MBIE updates the files
quarterly, so this runs weekly and skips the work when nothing has changed.

We do NOT read live tenders from gets.govt.nz itself: GETS terms of use
(clause 3.2(i)(e)) ban robots from copying or indexing GETS data. The site
links people to GETS searches instead.

Output: site/data/awards.json with the last 12 months of awarded contracts:
RFx ID, agency, title, tender type, awarded date, amount (when published),
winning business names, regions and a work category (building & construction,
roading & civil, and so on). Supplier addresses and NZBNs are left out.

Standard library only.
  python3 scripts/fetch_awards.py              # normal weekly run
  python3 scripts/fetch_awards.py --dir DIR    # use CSVs already saved in DIR
"""
import csv
import datetime as dt
import hashlib
import html
import io
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "data" / "awards.json"
BASE = "https://www.mbie.govt.nz/assets/Data-Files/NZGPP-GETS-Open-Data/"
PAGE = "https://www.mbie.govt.nz/cross-government-functions/new-zealand-government-procurement-and-property/open-data"
FILES = {"awards": "gets-award-notices.csv", "suppliers": "gets-supplier-data.csv",
         "regions": "gets-region-by-tender.csv", "categories": "gets-product-categories.csv"}
UA = "PunaPuteaOpenData/1.0 (+free public funding directory; downloads MBIE open data weekly)"
NZ = dt.timezone(dt.timedelta(hours=13))
MONTHS_BACK = 12

# First match wins, so the more specific groups come first. Matched against the
# tender's UNSPSC category names first (set by the agency), then against the title.
CATEGORIES = [
    ("Roading & civil works", r"\broad(s|ing)?\b|highway|pavement|bridge|\bslip\b|culvert|stormwater|wastewater|"
     r"water ?main|pipe(line|s)?\b|sewer|\bcivil\b|drainage|reseal|resurfac|footpath|kerb|tunnel|seawall|"
     r"earthworks|retaining wall|intersection|cycleway|\brail\b|reservoir|treatment plant|heavy construction|"
     r"thoroughfare"),
    ("Building & construction", r"\bbuild(ing|s)?\b|construct|contractor|\broof|refurbish|renovat|fit-?out|demoli|"
     r"carpentr|plumb|electrical|window|joinery|re-?paint|painting|\bhvac\b|boiler|fa[cç]ade|cladding|"
     r"earthquake|seismic|strengthen|classroom|\bgym\b|toilet|housing|new build|lining|weathertight|"
     r"modular|relocatable|\bblock\b|\bhall\b|pavilion|architect|structures"),
    ("Facilities & maintenance", r"maintenance|cleaning|facilit(y|ies) management|grounds|mowing|security services|"
     r"waste|recycling|\bpest|vegetation|\btrees?\b|arbor|wilding|landscap|environmental services"),
    ("Health & social services", r"health|\bcare\b|social|mental|disabilit|rehabilit|youth|family|wh[aā]nau|"
     r"counsell|support services|residential|aged|medical|pharma|drugs"),
    ("IT & digital", r"software|digital|\bict\b|\bit\b|\berp\b|payroll|cloud|platform|\bdata\b|cyber|"
     r"network|telecom|website|information technology"),
    ("Transport & fleet", r"\bbus(es)?\b|vehicle|fleet|transport services|ferry|aviation"),
    ("Consultancy & professional", r"consult|advis|design services|engineering services|professional|\baudit|legal|"
     r"evaluation|research|review|survey|valuation|planning|project management|management and business"),
]
CAT_RE = [(name, re.compile(rx, re.I)) for name, rx in CATEGORIES]
NULLS = {"", "null", "none", "n/a", "[none]"}


def category(title, unspsc):
    for text in (" ".join(unspsc), title):
        for name, rx in CAT_RE:
            if rx.search(text):
                return name
    return "Other"


def nz_date(s):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
    if not m:
        return None
    try:
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def clean(s):
    s = html.unescape((s or "").strip())
    return "" if s.lower() in NULLS else s


def fetch(name):
    req = urllib.request.Request(BASE + name, headers={"User-Agent": UA, "Accept": "text/csv,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8-sig", "replace")


def rows(text):
    reader = csv.reader(io.StringIO(text))
    head = [h.strip() for h in next(reader)]
    return [dict(zip(head, r)) for r in reader if r]


def grouped(table, value):
    out = {}
    for r in table:
        v = clean(r.get(value))
        if v:
            out.setdefault(r.get("RFx ID", "").strip(), [])
            if v not in out[r["RFx ID"].strip()]:
                out[r["RFx ID"].strip()].append(v)
    return out


def build(texts, now):
    awards = rows(texts["awards"])
    suppliers = grouped(rows(texts["suppliers"]), "Business Name")
    regions = grouped(rows(texts["regions"]), "Region")
    cats = grouped(rows(texts["categories"]), "UNSPC Description")

    # The newest real award date sets the 12-month window (the files lag by a
    # quarter). A few notices carry dates after the report date: ignore those.
    report = max((r.get("Report Date", "") for r in awards), default="")
    report_day = dt.date(int(report[:4]), int(report[4:6]), int(report[6:8])) if re.fullmatch(r"\d{8}", report) else now.date()
    dated = [(nz_date(r.get("Awarded Date")), r) for r in awards if r.get("Award Type", "").strip() == "Awarded"]
    dated = [(d, r) for d, r in dated if d and d <= report_day]
    if not dated:
        raise ValueError("no awarded contracts found in the award notices file")
    newest = max(d for d, _ in dated)
    start = newest.replace(year=newest.year - 1) + dt.timedelta(days=1)

    out, seen = [], set()
    for d, r in dated:
        rfx = r.get("RFx ID", "").strip()
        if d < start or rfx in seen:
            continue
        seen.add(rfx)
        try:
            amount = float(clean(r.get("Awarded Amount")) or 0) or None
        except ValueError:
            amount = None
        unspsc = cats.get(rfx, [])
        out.append({
            "rfxId": rfx,
            "agency": clean(r.get("Posting Agency")),
            "title": clean(r.get("Title")),
            "type": clean(r.get("RFx Type")),
            "awarded": d.isoformat(),
            "amount": round(amount) if amount else None,
            "suppliers": [s for s in suppliers.get(rfx, []) if s.lower() != "multiple suppliers"] or
                         (["Multiple suppliers"] if suppliers.get(rfx) else []),
            "regions": [x.replace("Manawatu-Wanganui", "Manawatū-Whanganui") for x in regions.get(rfx, [])],
            "category": category(clean(r.get("Title")), unspsc),
        })
    out.sort(key=lambda a: (a["awarded"], a["rfxId"]), reverse=True)
    return {"source": "New Zealand government procurement open data (GETS award notices), MBIE",
            "sourceUrl": PAGE, "licence": "Crown copyright, CC BY 4.0, attributed to MBIE",
            "reportDate": report_day.isoformat(), "from": start.isoformat(), "to": newest.isoformat(),
            "updated": now.strftime("%Y-%m-%d"), "awards": out}


def main(argv):
    now = dt.datetime.now(NZ)
    prev = {}
    try:
        prev = json.loads(OUT.read_text())
    except (OSError, ValueError):
        pass
    try:
        if "--dir" in argv:
            d = pathlib.Path(argv[argv.index("--dir") + 1])
            texts = {k: (d / f).read_text(encoding="utf-8-sig") for k, f in FILES.items()}
        else:
            texts = {k: fetch(f) for k, f in FILES.items()}
    except (urllib.error.URLError, OSError) as e:
        print("could not download MBIE open data, keeping the current list:", e)
        return 0
    digest = hashlib.sha256("".join(texts[k] for k in sorted(texts)).encode()).hexdigest()[:16]
    if prev.get("digest") == digest:
        print("MBIE open data unchanged since", prev.get("updated"))
        return 0
    data = build(texts, now)
    data["digest"] = digest
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    counts = {}
    for a in data["awards"]:
        counts[a["category"]] = counts.get(a["category"], 0) + 1
    print(f"wrote {len(data['awards'])} awarded contracts ({data['from']} to {data['to']}):", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

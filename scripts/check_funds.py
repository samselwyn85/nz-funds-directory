"""Nightly checker: visits every funder page and records what changed.

For each fund in site/data/funds.json it:
  1. Fetches the page (following redirects) and records the link health:
     ok, moved (redirected to a different path), broken (404/410/DNS/timeout),
     or blocked (the site refused automated visits; a person should look).
  2. Hashes the visible text and compares it with last night's hash, so a
     changed page is flagged.
  3. Looks for closing dates near words like "close", "deadline", "due" and
     for "applications are open/closed" wording.
Every change becomes an event in site/data/changes.json (newest last) and a
line in the fund's own history. Curated fields (name, summary, sectors...)
are never overwritten: anything that needs judgement is flagged needsReview.

Standard library only. Run: python3 scripts/check_funds.py
"""
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from email.utils import format_datetime
from xml.sax.saxutils import escape as xesc

ROOT = pathlib.Path(__file__).resolve().parent.parent
FUNDS = ROOT / "site" / "data" / "funds.json"
CHANGES = ROOT / "site" / "data" / "changes.json"
STATE = ROOT / "data" / "check_state.json"
FEED = ROOT / "site" / "feed.xml"
SITE_URL = "https://samselwyn85.github.io/nz-funds-directory/"
KIND = {"new_date": "New closing date", "round_open": "Round open", "page_changed": "Page updated",
        "link_moved": "Page moved", "link_broken": "Link broken", "link_ok": "Link fixed"}
UA = "PunaPuteaLinkChecker/1.0 (+public funding directory; checks once a night)"
NZ = dt.timezone(dt.timedelta(hours=13))

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9
DATE_WORDS = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?,?\s+(20\d\d)\b", re.I)
DATE_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d\d)\b")
KEYWORDS = re.compile(r"clos(e|es|ing)|deadline|due|applications?|round", re.I)
OPEN_RE = re.compile(r"applications?\s+(are\s+)?(now\s+)?open\b|round\s+is\s+(now\s+)?open|now\s+accepting\s+applications", re.I)
CLOSED_RE = re.compile(r"applications?\s+(are\s+)?(now\s+)?closed\b|round\s+(is\s+)?(now\s+)?closed|not\s+currently\s+accepting", re.I)


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "en-NZ,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(3_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")
            return r.status, r.geturl(), body, None
    except urllib.error.HTTPError as e:
        return e.code, url, "", f"HTTP {e.code}"
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
        return None, url, "", str(getattr(e, "reason", e))


def visible_text(page):
    page = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)[^>]*>.*?</\1>", " ", page)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", page))
    # drop things that change on every load (times, counters, tokens)
    text = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\s*(am|pm)?\b", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def find_deadlines(text, today):
    found = set()
    for m in KEYWORDS.finditer(text):
        window = text[m.start(): m.start() + 140]
        for d, mon, y in DATE_WORDS.findall(window):
            try:
                found.add(dt.date(int(y), MONTHS[mon.lower().rstrip(".")], int(d)))
            except ValueError:
                pass
        for d, mon, y in DATE_NUM.findall(window):  # NZ order: day/month/year
            try:
                found.add(dt.date(int(y), int(mon), int(d)))
            except ValueError:
                pass
    return sorted(x for x in found if today <= x <= today + dt.timedelta(days=400))


def link_status(code, start_url, final_url, err):
    if code is None:
        return "broken"
    if code in (401, 403, 406, 429, 503):  # refused automated visits
        return "blocked"
    if code >= 400:
        return "broken"
    a, b = urllib.parse.urlsplit(start_url), urllib.parse.urlsplit(final_url)
    same = a.netloc.removeprefix("www.") == b.netloc.removeprefix("www.") and a.path.rstrip("/") == b.path.rstrip("/")
    return "ok" if same else "moved"


def main(only=None):
    data = json.loads(FUNDS.read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    changes = json.loads(CHANGES.read_text()) if CHANGES.exists() else []
    now = dt.datetime.now(NZ)
    today = now.date()
    stamp = now.isoformat(timespec="seconds")
    new_events = []

    def event(f, kind, text, review=False):
        e = {"date": today.isoformat(), "fund": f["id"], "name": f["name"], "kind": kind, "text": text, "url": f["url"], "needsReview": review}
        new_events.append(e)
        f.setdefault("history", []).append({"date": e["date"], "text": text})
        f["history"] = f["history"][-20:]

    for f in data["funds"]:
        if only and f["id"] not in only:
            continue
        code, final, body, err = fetch(f["url"])
        status = link_status(code, f["url"], final, err)
        prev = state.get(f["id"], {})
        f["lastChecked"] = stamp

        before = f.get("linkStatus") or "unchecked"
        if status != before and not (before == "unchecked" and status == "ok"):
            msg = {"ok": "Link is working again",
                   "moved": f"Page has moved to {final}",
                   "broken": f"Link is broken ({err or code})",
                   "blocked": f"Site refused our checker ({code}); needs a manual look"}[status]
            event(f, "link_" + status, msg, review=status != "ok")
        f["linkStatus"] = status
        if status == "moved":
            f["suggestedUrl"] = final

        if body:
            text = visible_text(body)
            digest = hashlib.sha256(text.encode()).hexdigest()
            if prev.get("hash") and prev["hash"] != digest:
                event(f, "page_changed", "The funder updated this page", review=True)

            dates = find_deadlines(text, today)
            nxt = dates[0].isoformat() if dates else None
            if nxt and nxt != f.get("nextDeadline"):
                event(f, "new_date", f"New closing date found: {dates[0].strftime('%-d %B %Y')}", review=True)
                f["nextDeadline"] = nxt
            elif f.get("nextDeadline") and f["nextDeadline"] < today.isoformat():
                f["nextDeadline"] = nxt

            round_status = "open" if OPEN_RE.search(text) else "closed" if CLOSED_RE.search(text) else "unknown"
            if round_status == "open" and f.get("roundStatus") != "open":
                event(f, "round_open", "Applications look to be open now", review=True)
            f["roundStatus"] = round_status
            state[f["id"]] = {"hash": digest, "status": status, "checked": stamp}
        else:
            state[f["id"]] = {**prev, "status": status, "checked": stamp}
        print(f"{status:8} {f['id']}", file=sys.stderr)

    data["updated"] = stamp
    FUNDS.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))
    CHANGES.write_text(json.dumps((changes + new_events)[-1000:], indent=1, ensure_ascii=False))
    write_feed((changes + new_events)[-1000:], now)
    counts = {}
    for f in data["funds"]:
        counts[f["linkStatus"]] = counts.get(f["linkStatus"], 0) + 1
    print(json.dumps({"checked": stamp, "links": counts, "newEvents": len(new_events)}))


def write_feed(events, now):
    """RSS feed of the latest changes, so anyone can follow updates in a news reader for free."""
    items = []
    for e in [x for x in events if x["kind"] in KIND][-50:][::-1]:
        when = dt.datetime.fromisoformat(e["date"]).replace(tzinfo=NZ)
        title = f"{e['name']}: {KIND[e['kind']]}"
        link = f"{SITE_URL}#fund-{e['fund']}"
        items.append(f"<item><title>{xesc(title)}</title><link>{xesc(link)}</link><guid isPermaLink=\"false\">{xesc(e['fund'] + '-' + e['kind'] + '-' + e['date'])}</guid>"
                     f"<pubDate>{format_datetime(when)}</pubDate><description>{xesc(e['text'])}</description></item>")
    FEED.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
                    f"<title>Puna Pūtea: what's changed</title><link>{SITE_URL}#updates</link>"
                    "<description>New rounds, closing dates and page changes across New Zealand funders, checked nightly.</description>"
                    f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>" + "".join(items) + "</channel></rss>\n")


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)

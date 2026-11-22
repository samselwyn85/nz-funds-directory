"""Weekly subscriber email: what changed in the directory since the last one.

Reads site/data/changes.json, groups events since the last digest by sector,
and writes the email to out/digest.html (always, so you can preview it).

Sending is through Buttondown (subscribers, confirmations and unsubscribe
links are handled there). Nothing is emailed unless both are set:
  BUTTONDOWN_API_KEY   the API key from Buttondown settings
  DIGEST_MODE          "draft" (default: saved in Buttondown for you to press
                       Send) or "send" (goes straight out to subscribers)
Run: python3 scripts/send_digest.py
"""
import datetime as dt
import html
import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
FUNDS = json.loads((ROOT / "site" / "data" / "funds.json").read_text())["funds"]
CHANGES_PATH = ROOT / "site" / "data" / "changes.json"
LAST = ROOT / "data" / "last_digest.json"
SITE_URL = os.environ.get("SITE_URL", "https://samselwyn85.github.io/nz-funds-directory/")
LABEL = {"new_date": "New closing date", "round_open": "Round open", "page_changed": "Page updated",
         "link_moved": "Page moved", "link_broken": "Link broken", "link_ok": "Back online"}
SHOW = {"new_date", "round_open", "page_changed", "link_moved"}  # broken links go to the editor, not subscribers


def main():
    changes = json.loads(CHANGES_PATH.read_text()) if CHANGES_PATH.exists() else []
    since = json.loads(LAST.read_text())["date"] if LAST.exists() else "0000"
    fresh = [c for c in changes if c["date"] > since and c["kind"] in SHOW]
    if not fresh:
        print("No changes since", since, "- no digest this week.")
        return
    by_id = {f["id"]: f for f in FUNDS}
    groups = {}
    for c in fresh:
        f = by_id.get(c["fund"])
        if not f:
            continue
        groups.setdefault(f["sectors"][0], {}).setdefault(c["fund"], []).append(c)

    today = dt.date.today()
    subject = f"Funding changes this week: {len(fresh)} updates across {sum(len(v) for v in groups.values())} funds"
    parts = [f"<p>Kia ora,</p><p>Here's what changed in New Zealand funding since your last update.</p>"]
    for sector in sorted(groups):
        parts.append(f"<h2>{html.escape(sector)}</h2><ul>")
        for fid, evs in groups[sector].items():
            f = by_id[fid]
            bits = "; ".join(f"<b>{LABEL.get(e['kind'], e['kind'])}</b>: {html.escape(e['text'])}" for e in evs)
            parts.append(f"<li><a href=\"{SITE_URL}#fund-{fid}\">{html.escape(f['name'])}</a> ({html.escape(f['funder'])})<br>{bits}</li>")
        parts.append("</ul>")
    parts.append(f"<p>Search every fund: <a href=\"{SITE_URL}\">{SITE_URL}</a></p>"
                 "<p>Always confirm dates on the funder's own page before applying.</p>")
    body = "\n".join(parts)

    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    (out / "digest.html").write_text(f"<h1>{html.escape(subject)}</h1>\n{body}")
    print("Wrote out/digest.html:", subject)

    key = os.environ.get("BUTTONDOWN_API_KEY")
    if not key:
        print("BUTTONDOWN_API_KEY not set: preview only, nothing sent.")
        return
    mode = os.environ.get("DIGEST_MODE", "draft")
    payload = {"subject": subject, "body": body, "status": "about_to_send" if mode == "send" else "draft"}
    req = urllib.request.Request("https://api.buttondown.com/v1/emails", data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Token {key}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        print("Buttondown:", r.status, "mode:", mode)
    LAST.parent.mkdir(exist_ok=True)
    LAST.write_text(json.dumps({"date": today.isoformat()}))


if __name__ == "__main__":
    main()

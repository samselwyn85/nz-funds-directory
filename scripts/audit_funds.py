"""Audits site/data/funds.json so the directory stays correct.

Data checks (always run, no network):
  - every fund has the required fields with the right types
  - funder type, sectors, regions, who-can-apply and how-to-apply use only the
    values the website's filters know (read from site/app.html, so they stay in sync)
  - ids are unique and URL-safe, names are unique, website addresses are valid
    http(s) URLs with no spaces, and the same page is not listed twice for one funder
  - summaries are present, plain and a sensible length

Link checks (python3 scripts/audit_funds.py --links, needs internet):
  - visits every website address; fails on any broken link (404, 410, DNS,
    connection or SSL errors). A site that still times out after a longer retry is
    reported as "slow" and does not fail. Sites that refuse automated visits (401/403/406/429/503) are reported
    as "blocked" and do not fail the audit, because a person can still open them.

Exit code 0 means every check passed. Run: python3 scripts/audit_funds.py [--links]
"""
import concurrent.futures as cf
import datetime
import json
import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
FUNDS = ROOT / "site" / "data" / "funds.json"
APP = ROOT / "site" / "app.html"

REQUIRED = {"id": str, "name": str, "funder": str, "funderType": str, "sectors": list, "regions": list,
            "eligible": list, "howToApply": str, "amount": str, "url": str, "summary": str,
            "roundStatus": str, "linkStatus": str, "verified": bool}
LINK_STATES = {"ok", "moved", "broken", "blocked", "unchecked"}
ROUND_STATES = {"open", "closed", "unknown"}
GENERIC_NAME = re.compile(r"^(community |council )?(funding|grants?)((,| and| &)? (funding|grants?|sponsorship|scholarships|awards))*( streams| opportunities| fund| scheme)?$", re.I)


def allowed_values():
    js = APP.read_text(encoding="utf-8")
    out = {}
    for name in ("SECTORS", "REGIONS", "TYPES", "WHEN", "WHO"):
        m = re.search(rf"const {name}\s*=\s*\[(.*?)\];", js, re.S)
        if not m:
            raise SystemExit(f"could not find {name} in app.html")
        out[name] = set(re.findall(r'"([^"]+)"', m.group(1)))
    # "Closing in 30 days" is computed from nextDeadline, never stored
    out["HOW"] = out["WHEN"] - {"Closing in 30 days"}
    out["REGIONS"] |= {"Nationwide"}
    return out


def check_data(funds):
    errors = []
    allowed = allowed_values()
    err = lambda f, msg: errors.append(f"{f.get('id', '?')}: {msg}")
    ids, names, pages = set(), set(), set()
    for f in funds:
        if not isinstance(f, dict):
            errors.append(f"entry is not an object: {f!r:.60}")
            continue
        bad = [k for k, typ in REQUIRED.items() if not isinstance(f.get(k), typ)]
        bad += [k for k, typ in REQUIRED.items() if typ is list and k not in bad
                and not all(isinstance(v, str) for v in f[k])]
        for key in bad:
            err(f, f"missing or wrong type for '{key}'")
        if bad:
            continue
        if f["id"] in ids:
            err(f, "duplicate id")
        ids.add(f["id"])
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", f["id"]):
            err(f, "id is not lowercase-and-dashes")
        if GENERIC_NAME.match(f["name"]):
            err(f, f"name '{f['name']}' is too vague; include the funder")
        if f["name"].lower() in names:
            err(f, f"duplicate name '{f['name']}'")
        names.add(f["name"].lower())
        if f["funderType"] not in allowed["TYPES"]:
            err(f, f"unknown funder type '{f['funderType']}'")
        for key, allow in (("sectors", "SECTORS"), ("regions", "REGIONS"), ("eligible", "WHO")):
            vals = f[key]
            if not vals:
                err(f, f"'{key}' is empty")
            for v in vals:
                if v not in allowed[allow]:
                    err(f, f"unknown {key[:-1]} '{v}'")
            if len(set(vals)) != len(vals):
                err(f, f"'{key}' has repeats")
        if "Nationwide" in f["regions"] and len(f["regions"]) > 1:
            err(f, "regions mix Nationwide with specific regions")
        if f["howToApply"] not in allowed["HOW"]:
            err(f, f"unknown how-to-apply '{f['howToApply']}'")
        try:
            u = urllib.parse.urlsplit(f["url"])
            port = u.port  # raises ValueError for a port that is not a number from 0 to 65535
        except ValueError:
            err(f, f"bad website address '{f['url']}'")
            continue
        if u.scheme not in ("http", "https") or not u.netloc or "." not in u.netloc or re.search(r"\s", f["url"]):
            err(f, f"bad website address '{f['url']}'")
        host = (u.hostname or "").removeprefix("www.")
        if port and port != {"http": 80, "https": 443}.get(u.scheme):
            host += f":{port}"
        page = (f["funder"].lower(), host + u.path.rstrip("/"), u.query)
        if page in pages:
            err(f, "same funder and page listed twice")
        pages.add(page)
        s = f["summary"].strip()
        if not 20 <= len(s) <= 320:
            err(f, f"summary should be 20-320 characters (is {len(s)})")
        if re.search(r"\b(TODO|TBC|lorem|xxx)\b", s, re.I):
            err(f, "summary has placeholder text")
        if f["linkStatus"] not in LINK_STATES:
            err(f, f"unknown link status '{f['linkStatus']}'")
        if f["roundStatus"] not in ROUND_STATES:
            err(f, f"unknown round status '{f['roundStatus']}'")
        nd = f.get("nextDeadline")
        if nd is not None:
            try:
                ok = bool(re.fullmatch(r"20\d\d-\d\d-\d\d", str(nd))) and bool(datetime.date.fromisoformat(nd))
            except ValueError:
                ok = False
            if not ok:
                err(f, f"nextDeadline '{nd}' is not a real YYYY-MM-DD date")
    return errors


def check_links(funds):
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_funds import fetch, link_status

    timed_out = lambda code, e: code is None and "timed out" in str(e)

    def one(f):
        code, final, _, e = fetch(f["url"], body=False)
        status = link_status(code, f["url"], final, e)
        if status == "broken":
            first_timeout = timed_out(code, e)
            code, final, _, e = fetch(f["url"], timeout=60, body=False)  # one longer retry for a slow site
            status = link_status(code, f["url"], final, e)
            if status == "broken" and first_timeout and timed_out(code, e):
                status = "slow"  # timed out twice; a dead site fails DNS/connect instead
        return f, code, final, e, status

    results = {"ok": [], "moved": [], "blocked": [], "slow": [], "broken": []}
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        for f, code, final, e, status in pool.map(one, funds):
            results[status].append((f, code, final, e))
    for f, code, final, e in results["moved"]:
        print(f"moved    {f['id']}: {f['url']} -> {final}")
    for f, code, final, e in results["blocked"]:
        print(f"blocked  {f['id']}: {f['url']} ({code})")
    for f, code, final, e in results["slow"]:
        print(f"slow     {f['id']}: {f['url']} (timed out twice; not counted as broken)")
    for f, code, final, e in results["broken"]:
        print(f"BROKEN   {f['id']}: {f['url']} ({e or code})")
    print("links: " + ", ".join(f"{k} {len(v)}" for k, v in results.items()))
    return [f"{f['id']}: broken link {f['url']} ({e or code})" for f, code, final, e in results["broken"]]


def main():
    data = json.loads(FUNDS.read_text(encoding="utf-8"))
    funds = data.get("funds") if isinstance(data, dict) else None
    if not isinstance(funds, list) or not funds:
        sys.exit("FAIL funds.json has no 'funds' list, or it is empty")
    errors = check_data(funds)
    print(f"data: {len(funds)} funds, {len(errors)} problems")
    if "--links" in sys.argv:
        if errors:
            print("links: skipped until the data problems below are fixed")
        else:
            errors += check_links(funds)
    for e in errors:
        print("FAIL", e)
    if errors:
        sys.exit(1)
    print("All audit checks passed.")


if __name__ == "__main__":
    main()

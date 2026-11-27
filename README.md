# Puna Pūtea: every New Zealand fund in one place

A free, searchable directory of NZ funding across all sectors (government,
gaming trusts, community trusts, councils, philanthropy, corporate) that keeps
itself up to date. "Puna Pūtea" is a working name.

## What's here

| Part | File | What it does |
|---|---|---|
| Website | `site/app.html` | Search, sidebar filters (sector, region, funder type, when to apply, who can apply), fund pages, saved funds, a three-question eligibility match and a public "What's changed" log. Free for everyone, no login. |
| Fund list | `site/data/funds.json` | One record per fund. Starter list of 50 real NZ funders, built by `scripts/seed_funds.py`. |
| Nightly checker | `scripts/check_funds.py` | Visits every funder page, records broken or moved links, page changes, closing dates and "applications open" wording. Writes `site/data/changes.json` and the RSS feed `site/feed.xml`. |
| Tenders page | `site/app.html` (`#tenders`) | Links to GETS searches for open tenders (construction, building, roofing, roading, maintenance and more), plus a searchable list of contracts awarded in the last 12 months, filterable by work type (incl. all building work) and region. |
| Tenders import | `scripts/fetch_awards.py` | Weekly download of MBIE's open data of GETS award notices (CC BY 4.0) into `site/data/awards.json`. Skips when the files haven't changed. |
| Schedules | `.github/workflows/` | Nightly check (3am NZ), weekly tenders refresh (Monday 4:30am NZ) and publishing the site to GitHub Pages. |

## Turning it on

1. **Hosting:** Settings → Pages → Source: GitHub Actions. The site appears at
   `https://<user>.github.io/<repo>/`. (Free for public repos.)
2. Run "Nightly fund check" once from the Actions tab to fill in link health.

## Run locally

```
python3 scripts/seed_funds.py      # rebuild the starter list
python3 scripts/check_funds.py     # check all pages now
python3 scripts/build_site.py && python3 -m http.server -d site
```

## Data rules

- The checker never overwrites names, summaries or criteria. Anything that
  needs judgement is logged with `needsReview: true` for a person to confirm.
- Dates are read as NZ day/month/year.
- A site that refuses automated visits is marked `blocked`, not broken.
- Live tenders are never copied from gets.govt.nz: GETS terms of use
  (clause 3.2(i)(e)) ban robots from copying or indexing GETS data. The site
  links to GETS searches instead, and only uses MBIE's published open data
  (awarded contracts), credited to MBIE under CC BY 4.0.

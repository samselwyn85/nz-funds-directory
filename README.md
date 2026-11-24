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
| Schedules | `.github/workflows/` | Nightly check (3am NZ) and publishing the site to GitHub Pages. |

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

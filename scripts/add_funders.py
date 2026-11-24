"""Adds funders from the official and curated NZ funder lists to site/data/funds.json.

Unlike seed_funds.py, this never wipes the file: it only adds funds that are
not already listed (matched by id or by website domain), and it corrects a
few website addresses where an official list gives the right one. Nightly
history, link status and dates on existing funds are kept.

Sources (read 24 Nov 2026):
  DIA   https://www.dia.govt.nz/Services-Casino-and-Non-Casino-Gaming-List-of-Society-Websites
        (all 32 class 4 gaming societies, list last updated Sept 2025)
  JRM   https://www.jrmckenzie.org.nz/other-funders
  TIN   https://tindall.org.nz/other-funding/
  CFA   https://communityfoundations.org.nz/regions (18 community foundations)

Funders whose areas or focus could not be confirmed from those lists are
marked needsReview so a person can check them. Run: python3 scripts/add_funders.py
"""
import json
import pathlib
import re
import urllib.parse

from seed_funds import slug

ROOT = pathlib.Path(__file__).resolve().parent.parent
FUNDS = ROOT / "site" / "data" / "funds.json"

NATION = ["Nationwide"]
GROUPS = ["Community groups", "Charities"]
GAMING_ELIG = GROUPS + ["Schools"]
GAMING_SECT = ["Community", "Sport & recreation"]
GAMING_SUMMARY = ("Gaming machine (pokie) trust. By law it gives grants to community, sport and "
                  "charitable groups, mostly in the areas where its venues are.")
GAMING_CHECK = " Check the funder's site for the areas it covers."

# (name, funder, type, subtype, sectors, regions, eligible, how_to_apply, url, summary, source, needs_review)
ROWS = []


def add(name, funder, ftype, sub, sectors, regions, elig, how, url, summary, source, review=False):
    ROWS.append((name, funder, ftype, sub, sectors, regions, elig, how, url, summary, source, review))


# ---- Gaming trusts: every class 4 society on DIA's list not already listed ----
def gaming(name, funder, url, regions=None, sectors=None, extra=""):
    known = regions is not None
    add(name, funder, "Gaming trust", "Class 4 society", sectors or GAMING_SECT, regions or NATION,
        GAMING_ELIG, "Check funder", url,
        GAMING_SUMMARY + (" " + extra if extra else "") + ("" if known else GAMING_CHECK), "DIA", not known)


gaming("Air Rescue Services grants", "Air Rescue Services Limited", "https://www.airrescueservices.co.nz",
       sectors=["Health & wellbeing", "Community"])
gaming("Blue Waters Community Trust grants", "Blue Waters Community Trust", "https://bluewaterscommunitytrust.baanalyser.com/start")
gaming("Bluesky Community Trust grants", "Bluesky Community Trust Limited", "https://www.bluesky.org.nz")
gaming("Constellation Communities Trust grants", "Constellation Communities Trust Limited", "http://constellationtrust.org.nz/")
gaming("Dragon Community Trust grants", "Dragon Community Trust Limited", "https://www.dragon.org.nz")
gaming("First Light Community Foundation grants", "First Light Community Foundation Limited", "https://www.firstlightfoundation.co.nz")
gaming("Grassroots Trust Central grants", "Grassroots Trust Central Limited", "https://www.grassrootstrustcentral.co.nz/")
gaming("ILT Foundation grants", "ILT Foundation", "https://www.iltfoundation.org.nz", regions=["Southland"],
       extra="Funded by the Invercargill Licensing Trust's venues.")
gaming("Kiwi Gaming Foundation grants", "Kiwi Gaming Foundation", "https://www.kiwigaming.org.nz")
gaming("Mainland Foundation grants", "Mainland Foundation Limited", "https://www.mainlandfoundation.co.nz")
gaming("Manukau Counties Community Facilities Charitable Trust grants",
       "Manukau Counties Community Facilities Charitable Trust", "https://www.maxserv.co.nz/mccfct", regions=["Auckland"])
gaming("Milestone Foundation grants", "Milestone Foundation Limited", "http://www.milestonefoundation.co.nz")
gaming("One Foundation grants", "One Foundation Limited", "https://www.onefoundation.nz/")
gaming("Oxford Sports Trust grants", "Oxford Sports Trust Inc", "http://www.oxfordsportstrust.org.nz",
       sectors=["Sport & recreation"])
gaming("Pelorus Trust grants", "Pelorus Trust", "https://www.pelorustrust.net.nz")
gaming("Rano Community Trust grants", "Rano Community Trust Limited", "https://rano.org.nz/")
gaming("Redwood Trust grants", "Redwood Trust Incorporated", "http://www.redwoodtrust.org.nz")
gaming("Akarana Community Trust grants", "The Akarana Community Trust Limited", "https://www.akaranacommunitytrust.co.nz",
       regions=["Auckland"])
gaming("Bendigo Valley Sports and Charity Foundation grants", "The Bendigo Valley Sports and Charity Foundation",
       "https://www.bendigovalley.co.nz")
gaming("North and South Trust grants", "The North and South Trust Limited", "https://www.nstl.co.nz")
gaming("Trust Aoraki grants", "Trust Aoraki Limited", "https://www.trustaoraki.co.nz")
gaming("Trust House Foundation grants", "Trust House Foundation", "https://trusthouse.co.nz")
gaming("We Care Community Trust grants", "We Care Community Trust Limited", "https://wecare.org.nz")
gaming("Youthtown grants", "Youthtown Incorporated", "https://youthtowntrust.org.nz/",
       sectors=["Education & youth", "Sport & recreation"])

# ---- Community trusts missing from the 12 ----
add("Whanganui Community Foundation grants", "Whanganui Community Foundation", "Community trust", "Regional community trust",
    ["Community"], ["Manawatū-Whanganui"], GROUPS, "Set rounds", "https://www.whanganuicommunityfoundation.org.nz",
    "One of the 12 regional community trusts. Grants for community organisations in the Whanganui district.", "JRM")
add("West Coast Community Trust grants", "West Coast Community Trust", "Community trust", "Regional community trust",
    ["Community"], ["West Coast"], GROUPS, "Set rounds", "https://www.wccomtrust.org.nz",
    "One of the 12 regional community trusts. Grants for community initiatives across Buller, Grey and Westland.", "JRM")
add("Community Trust Mid & South Canterbury grants", "Community Trust Mid & South Canterbury", "Community trust",
    "Regional community trust", ["Community"], ["Canterbury"], GROUPS, "Set rounds", "https://www.comtrust.org.nz",
    "One of the 12 regional community trusts. Community, cultural and social grants in Mid and South Canterbury.", "JRM")

# ---- Energy trusts and energy companies with community grants (JRM list) ----
def energy(name, funder, ftype, regions, url, area, review=False):
    sub = "Energy trust" if ftype == "Community trust" else "Energy company"
    add(name, funder, ftype, sub, ["Community"], regions, GROUPS + ["Schools"], "Check funder", url,
        f"Community grants from an electricity {'trust' if sub == 'Energy trust' else 'company'} for groups in {area}.",
        "JRM", review)


energy("WEL Energy Trust grants", "WEL Energy Trust", "Community trust", ["Waikato"],
       "https://www.welenergytrust.co.nz/grants/quick-response-grants/", "the WEL Networks area of Waikato")
energy("Central Energy Trust community grants", "Central Energy Trust", "Community trust", ["Manawatū-Whanganui"],
       "https://www.centralenergytrust.org.nz/community-grants", "Manawatū and Tararua")
energy("Trust Horizon funding", "Trust Horizon", "Community trust", ["Bay of Plenty"],
       "https://www.trusthorizon.org.nz/funding", "the Eastern Bay of Plenty")
energy("Network Tasman Trust community grants", "Network Tasman Trust", "Community trust", ["Tasman", "Nelson"],
       "https://www.networktasmantrustgrants.org.nz/community-grants", "the Network Tasman area")
energy("Taranaki Electricity Trust grants", "Taranaki Electricity Trust", "Community trust", ["Taranaki"],
       "https://www.taranakielectricitytrust.co.nz/grants/", "parts of Taranaki")
energy("Alpine Energy community funding", "Alpine Energy", "Corporate", ["Canterbury"],
       "https://www.alpineenergy.co.nz/corporate/community-funding/sponsorship", "South Canterbury")
energy("Meridian Energy community fund", "Meridian Energy", "Corporate", NATION,
       "https://www.meridianenergy.co.nz/community-support/fund", "communities across New Zealand")
energy("MainPower community fund", "MainPower", "Corporate", ["Canterbury"],
       "https://www.mainpower.co.nz/community-support/community-fund", "North Canterbury")
energy("Centralines community funding", "Centralines", "Corporate", ["Hawke's Bay"],
       "https://www.centralines.co.nz/tell-me-about/community/our-community-partnerships/applying-for-funding/",
       "Central Hawke's Bay")

# ---- Community foundations (CFA list; Acorn is already listed) ----
CF = [
    ("Northland Community Foundation", "http://www.northlandcommunityfoundation.org.nz", ["Northland"], "Northland"),
    ("Auckland Foundation", "http://www.aucklandfoundation.org.nz", ["Auckland"], "Auckland"),
    ("Momentum Waikato Community Foundation", "http://www.momentumwaikato.nz", ["Waikato"], "Waikato"),
    ("Eastern Bay Community Foundation", "https://www.ebcf.nz/", ["Bay of Plenty"], "the Eastern Bay of Plenty"),
    ("Geyser Community Foundation", "http://www.geysercf.org.nz", ["Bay of Plenty", "Waikato"], "Rotorua and Taupō"),
    ("Sunrise Foundation", "http://www.sunrisefoundation.org.nz", ["Gisborne"], "Tairāwhiti Gisborne"),
    ("Taranaki Foundation", "https://taranakifoundation.org.nz/", ["Taranaki"], "Taranaki"),
    ("Hawke's Bay Foundation", "http://www.hawkesbayfoundation.org.nz", ["Hawke's Bay"], "Hawke's Bay"),
    ("Te Awa Community Foundation", "http://www.teawafoundation.org.nz", ["Manawatū-Whanganui"], "the Horizons region"),
    ("Nikau Foundation", "http://www.nikaufoundation.nz", ["Wellington"], "the Wellington region"),
    ("Top of the South Community Foundation", "https://www.topsouthfoundation.org.nz/", ["Tasman", "Nelson", "Marlborough"],
     "Tasman, Nelson and Marlborough"),
    ("Kura Tāwhiti Canterbury Community Foundation", "https://www.kuratawhiticcf.org.nz/", ["Canterbury"], "Christchurch"),
    ("Advance Ashburton Community Foundation", "http://www.advanceashburton.org.nz", ["Canterbury"], "Ashburton"),
    ("Aoraki Foundation", "http://www.aorakifoundation.co.nz", ["Canterbury"], "South Canterbury"),
    ("45South Community Foundation", "https://www.45south.org/", ["Otago"], "Central Otago and Queenstown"),
    ("Clutha Foundation", "https://www.cluthafoundation.org.nz/", ["Otago"], "the Clutha district"),
    ("Southland Foundation", "https://www.southlandfoundation.org.nz/", ["Southland"], "Southland"),
]
for name, url, regions, area in CF:
    add(name + " grants", name, "Philanthropic", "Community foundation", ["Community"], regions, GROUPS, "Set rounds", url,
        f"Local community foundation that grants from donated endowment funds to groups in {area}.", "CFA")

# ---- Government funds ----
add("Ethnic Communities Development Fund", "Ministry for Ethnic Communities", "Government", "", ["Community", "Arts & culture"],
    NATION, GROUPS, "Set rounds", "https://www.ethniccommunities.govt.nz/funding/",
    "Funding for ethnic community groups' projects, events and capability.", "JRM")
add("Ministry of Youth Development funding", "Ministry of Youth Development", "Government", "", ["Education & youth"],
    NATION, GROUPS, "Set rounds", "https://www.myd.govt.nz/funding/",
    "Funding for youth development programmes and youth-led projects.", "JRM")
add("Ministry for Pacific Peoples funding", "Ministry for Pacific Peoples", "Government", "", ["Community", "Arts & culture"],
    NATION, GROUPS + ["Individuals"], "Set rounds", "https://www.mpp.govt.nz/programmes-and-funding/",
    "Funding programmes for Pacific communities, languages and enterprise.", "TIN")
add("NZ Film Commission funding", "New Zealand Film Commission", "Government", "", ["Arts & culture", "Media"],
    NATION, ["Businesses", "Individuals"], "Set rounds", "https://www.nzfilm.co.nz/",
    "Development, production and marketing funding for New Zealand films and filmmakers.", "TIN")
add("Ministry for the Environment funding", "Ministry for the Environment", "Government", "", ["Environment"],
    NATION, GROUPS + ["Businesses"], "Set rounds", "https://environment.govt.nz/what-you-can-do/funding/",
    "The Ministry's environmental funds, including community environment and waste funds.", "TIN")

# ---- Family and private foundations ----
def phil(name, url, summary, regions=NATION, sectors=None, source="TIN", review=False):
    add(name, name, "Philanthropic", "Private foundation", sectors or ["Community"], regions, GROUPS, "Check funder", url,
        summary, source, review)


phil("NEXT Foundation", "https://www.nextfoundation.org.nz",
     "Private foundation investing in environmental and education projects with long-term impact.",
     sectors=["Environment", "Education & youth"])
phil("Len Reynolds Trust", "http://www.lenreynoldstrust.co.nz", "Family charitable trust giving community grants.", review=True)
phil("The Lindsay Foundation", "https://www.lindsayfoundation.co.nz/our-focus",
     "Supports people and organisations making a positive difference in New Zealand.", source="JRM")
phil("Wayne Francis Charitable Trust", "https://www.wfct.org.nz",
     "Family charitable trust funding community, youth and environment projects.", regions=["Canterbury"], review=True)
phil("Clare Foundation", "https://clare.nz/", "Private foundation funding community wellbeing initiatives.", review=True)
phil("The Wright Family Foundation", "https://wrightfamilyfoundation.org.nz/en-us/",
     "Family foundation focused on education and helping New Zealanders reach their potential.",
     sectors=["Education & youth", "Community"])
phil("Hynds Foundation", "https://www.hyndsfoundation.nz/", "Family foundation funding community projects.", review=True)
phil("DV Bryant Trust", "https://www.bryanttrust.co.nz/", "Charitable trust giving community grants, mainly in Waikato.",
     regions=["Waikato"], review=True)
phil("The Wilberforce Foundation", "https://www.wilberforce.org.nz/",
     "Private foundation funding community and social projects.", review=True)
phil("Whakatupu Aotearoa Foundation", "https://whakatupuaotearoa.org.nz/",
     "Private foundation supporting community and Māori development.", review=True)
phil("Rule Foundation", "https://www.rulefoundation.nz/",
     "Supports rainbow communities and takatāpui to flourish and pursue systemic change.", source="JRM")
phil("Catalytic Foundation", "https://catalytic.org.nz/",
     "Private foundation backing projects that tackle the root causes of social and environmental problems.", review=True)

# ---- Corporate foundations ----
def corp(name, funder, url, summary, sectors=None, regions=NATION, source="TIN", review=False):
    add(name, funder, "Corporate", "Corporate foundation", sectors or ["Community"], regions, GROUPS, "Check funder", url,
        summary, source, review)


corp("Spark Foundation grants", "Spark Foundation", "https://www.spark.co.nz/online/about/sustainability/spark-foundation/funding",
     "Grants that improve digital equity, for digitech thinkers and creators.", sectors=["Education & youth", "Community"],
     source="JRM")
corp("Te Rourou (One NZ Foundation)", "Te Rourou, One Aotearoa Foundation", "https://terourou.one.nz/",
     "One NZ's foundation. Runs occasional funding rounds for particular kinds of mahi.", source="JRM")
corp("ANZ New Zealand Staff Foundation", "ANZ Bank New Zealand",
     "https://www.anz.co.nz/about-us/corporate-responsibility/community/staff-foundation/",
     "Community grants chosen by ANZ staff; has given over $9 million since 2000.", source="JRM")
corp("Simplicity Foundation", "Simplicity", "https://simplicity.kiwi/about-us/our-foundation",
     "Funds environment, youth development, education, homelessness and hunger, mainly through long-term partners.",
     sectors=["Environment", "Education & youth", "Community"], source="JRM")
corp("Milford Foundation", "Milford Asset Management", "https://milfordfoundation.co.nz/",
     "Corporate foundation giving grants to community organisations.", review=True)
corp("SkyCity Auckland Community Trust", "SkyCity", "https://skycityauckland.co.nz/about-us/community-trust/",
     "Community grants for groups in Auckland.", regions=["Auckland"])
corp("BNZ Foundation", "BNZ", "https://www.bnz.co.nz/about-us/sustainability/bnz-foundation",
     "BNZ's foundation supporting community organisations.", review=True)
corp("Fisher & Paykel Healthcare Foundation", "Fisher & Paykel Healthcare", "https://www.fphcare.com/nz/corporate/fph-foundation/",
     "Corporate foundation supporting health, education and community projects.",
     sectors=["Health & wellbeing", "Education & youth"], review=True)

# Corrections to existing listings where an official list gives the right address.
URL_FIXES = {
    "lion-foundation-grants": "https://lionfoundation.nz",                    # DIA
    "four-winds-foundation-grants": "https://www.fourwindsfoundation.co.nz",  # DIA
    "aotearoa-gaming-trust-grants": "https://www.agt.nz",                     # DIA
    "trillian-trust-grants": "https://www.trillian.nz",                       # DIA
    "the-trusts-community-foundation-grants": "https://www.ttcfltd.org.nz",   # DIA
    "hugh-green-foundation": "https://www.hgg.co.nz",                         # Tindall
    "perpetual-guardian-foundation": "https://www.perpetualguardian.co.nz/philanthropy/grant-seekers/grants-open-upcoming/",
    "public-trust-grants": "https://www.publictrust.co.nz/grants/?query=&type=organisation",
    "te-puni-kokiri-funding": "https://www.tpk.govt.nz/en/nga-putea-me-nga-ratonga",
    "tect-community-grants": "https://www.tect.org.nz/funding-faqs/",
    "ministry-for-culture-and-heritage-funds": "https://www.mch.govt.nz/our-work/apply-funding",
}


def domain(url):
    host = urllib.parse.urlsplit(url).netloc.lower()
    return re.sub(r"^www\.", "", host)


def main():
    data = json.loads(FUNDS.read_text())
    funds = data["funds"]
    fixed = 0
    for f in funds:
        new = URL_FIXES.get(f["id"])
        if new and f["url"] != new:
            f["url"] = new
            f["linkStatus"] = "unchecked"
            f.setdefault("history", []).append({"date": "2026-11-24", "text": "Website address corrected from an official funder list"})
            fixed += 1
    ids = {f["id"] for f in funds}
    # Only funder-specific domains count as duplicates; shared portals can host several funds.
    shared = {"communitymatters.govt.nz", "creativenz.govt.nz"}
    domains = {domain(f["url"]) for f in funds} - shared
    added = 0
    for name, funder, ftype, sub, sectors, regions, elig, how, url, summary, source, review in ROWS:
        fid = slug(name)
        if fid in ids or domain(url) in domains:
            continue
        funds.append({
            "id": fid, "name": name, "funder": funder, "funderType": ftype, "funderSubtype": sub,
            "sectors": sectors, "regions": regions, "eligible": elig, "howToApply": how, "amount": "Varies",
            "url": url, "summary": summary, "nextDeadline": None, "roundStatus": "unknown", "lastChecked": None,
            "linkStatus": "unchecked", "verified": False, "needsReview": review, "source": source,
        })
        ids.add(fid)
        domains.add(domain(url))
        added += 1
    FUNDS.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"added {added} funds, corrected {fixed} addresses, {len(funds)} funds in total")


if __name__ == "__main__":
    main()

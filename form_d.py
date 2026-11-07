# form_d.py
#
# Step 7: look for recent fundraising in SEC Form D filings.
#   A Form D is a short notice a private company files with the SEC after it
#   sells shares, for example in a venture round. EDGAR's full-text search
#   finds them by name or keyword, and each filing has a primary_doc.xml with
#   the details we want (issuer name, state, industry, amount raised).
#
#   Two searches, both over the last 12 months:
#     1. Each company name in companies.csv -> form_d.csv
#     2. The keyword "security"             -> candidates.csv (possible new
#        companies to look at; they are NOT added to companies.csv)
#
# Run it with:
#   export SEC_USER_AGENT="Your Name your.email@example.com"
#   python3 form_d.py

import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import pandas as pd
import requests

SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
# Each filing lives in a folder named after its accession number (the
# filing's ID) with the dashes removed.
FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/primary_doc.xml"

# The SEC requires every automated request to say who is making it, with a
# name and email in the User-Agent header. Requests without it get blocked.
# We read it from an environment variable (a setting your terminal passes to
# programs) so the email isn't saved in the code, since this repo is public.
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "")
HEADERS = {"User-Agent": SEC_USER_AGENT}

KEYWORD = "security"

# The last 12 months. EDGAR ignores a date range with only one end set, so we
# always send both a start date and an end date.
END_DATE = date.today()
START_DATE = END_DATE - timedelta(days=365)

# Form D industry types we drop because they aren't the kind of operating
# company we're looking for: funds, real estate and banking. The form sorts
# its types into groups, and we drop every type in two of them:
#   - "Banking & Financial Services", which also holds pooled investment
#     funds, insurance and "Investing" (mostly holding companies)
#   - "Real Estate", where "Commercial", "Construction" and "Residential"
#     all mean real estate
DROPPED_INDUSTRY_GROUPS = [
    # Banking & Financial Services
    "Commercial Banking",
    "Insurance",
    "Investing",
    "Investment Banking",
    "Pooled Investment Fund",  # venture, hedge and private equity funds, SPVs
    "Other Banking and Financial Services",
    # Real Estate
    "Commercial",
    "Construction",
    "REITS and Finance",
    "Residential",
    "Other Real Estate",
]

# Words at the end of a legal name that we ignore when comparing names, so
# "7AI, Inc." matches "7AI". "l" and "p" catch "L.P.", which becomes "l p"
# once the dots are removed.
LEGAL_ENDINGS = ["inc", "incorporated", "llc", "corp", "corporation", "co",
                 "company", "ltd", "limited", "lp", "l", "p"]

COLUMNS = ["issuer_name", "filing_date", "form", "state", "industry_group",
           "total_offering_amount", "total_amount_sold", "cik", "accession"]


def sec_get(url, params=None):
    """Download a URL from the SEC. The SEC allows at most 10 requests a
    second, so we pause briefly before each one. If the request fails for a
    temporary reason, wait two seconds and try once more.
    Returns the response, or None if both tries failed."""
    for attempt in [1, 2]:
        time.sleep(0.2)
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=20)
        except requests.RequestException:
            response = None

        # Same rule as fetch_jobs.py: only retry when there was no answer,
        # too many requests (429) or a server error (500 and up).
        temporary_problem = (
            response is None
            or response.status_code == 429
            or response.status_code >= 500
        )
        if not temporary_problem:
            return response
        if attempt == 1:
            time.sleep(2)
    return None


def search_form_d(query):
    """Return every Form D search hit for a query over the last 12 months.
    EDGAR sends at most 100 hits per page, so we keep asking for the next
    page (using "from", the number of hits to skip) until we have them all."""
    hits = []
    while True:
        params = {
            "q": query,
            "forms": "D",  # also returns D/A, an amendment to an earlier Form D
            "dateRange": "custom",
            "startdt": START_DATE.isoformat(),  # e.g. "2025-11-06"
            "enddt": END_DATE.isoformat(),
            "from": len(hits),
        }
        response = sec_get(SEARCH_URL, params)
        if response is None or response.status_code != 200:
            print(f"  search failed for {query}")
            return hits

        data = response.json()
        page = data["hits"]["hits"]
        hits += page
        total = data["hits"]["total"]["value"]
        if len(page) == 0 or len(hits) >= total:
            return hits


def read_filing(hit):
    """Fetch the primary_doc.xml for one search hit and return a dict with
    the columns in COLUMNS, or None if it couldn't be loaded."""
    info = hit["_source"]
    accession = info["adsh"]  # e.g. "0002006522-25-000002"
    cik = info["ciks"][0].lstrip("0")  # the URL uses the CIK without leading zeros
    url = FILING_URL.format(cik=cik, folder=accession.replace("-", ""))

    response = sec_get(url)
    if response is None or response.status_code != 200:
        print(f"  couldn't load {url}")
        return None

    # findtext() follows a path of tags down the XML and returns the text
    # inside the last one, or "" if any tag along the way is missing.
    root = ET.fromstring(response.content)
    return {
        "issuer_name": root.findtext("primaryIssuer/entityName", "").strip(),
        "filing_date": info["file_date"],
        "form": info["form"],
        "state": root.findtext("primaryIssuer/issuerAddress/stateOrCountry", "").strip(),
        "industry_group": root.findtext("offeringData/industryGroup/industryGroupType", "").strip(),
        # Amounts are in dollars, or "Indefinite" if the company didn't set one.
        "total_offering_amount": root.findtext("offeringData/offeringSalesAmounts/totalOfferingAmount", "").strip(),
        "total_amount_sold": root.findtext("offeringData/offeringSalesAmounts/totalAmountSold", "").strip(),
        "cik": cik,
        "accession": accession,
    }


def read_filings(hits):
    """Read every hit's filing and drop funds, real estate and banking.
    Returns a list of dicts and how many filings were dropped."""
    filings = []
    dropped = 0
    for hit in hits:
        filing = read_filing(hit)
        if filing is None:
            continue
        if filing["industry_group"] in DROPPED_INDUSTRY_GROUPS:
            dropped += 1
            continue
        filings.append(filing)
    return filings, dropped


def simple_name(name):
    """Lowercase a name, turn punctuation into spaces and drop legal endings,
    so "7AI, Inc." becomes "7ai" and "Doppel Inc." becomes "doppel"."""
    words = re.sub(r"[^a-z0-9]", " ", name.lower()).split()
    while words and words[-1] in LEGAL_ENDINGS:
        words.pop()
    return " ".join(words)


def name_match(company, issuer):
    """Compare a company name from companies.csv with a Form D issuer name.
      "exact"   -> same name once legal endings are dropped ("Doppel" vs "Doppel Inc.")
      "partial" -> the company name appears inside the issuer name as whole
                   words ("Socket" vs "Socket Mobile, Inc."), which may or
                   may not be the same company
      "none"    -> neither"""
    company = simple_name(company)
    issuer = simple_name(issuer)
    if company == issuer:
        return "exact"
    # Adding spaces at both ends makes this a whole-word check, so "neo"
    # matches "neo agent" but not "neon".
    if f" {company} " in f" {issuer} ":
        return "partial"
    return "none"


def search_company_names():
    """Search Form D filings for each company name and write form_d.csv,
    with a match column saying how well the issuer name fits."""
    companies = pd.read_csv("companies.csv", dtype=str, keep_default_na=False)

    rows = []
    for name in companies["name"]:
        # Quotes make EDGAR search for the whole name as one phrase.
        hits = search_form_d(f'"{name}"')
        filings, dropped = read_filings(hits)
        for filing in filings:
            match = name_match(name, filing["issuer_name"])
            rows.append({"searched_name": name, "match": match, **filing})
        print(f"{name}: {len(hits)} hits, {dropped} dropped as fund/real estate/banking, {len(filings)} kept")

    form_d = pd.DataFrame(rows, columns=["searched_name", "match"] + COLUMNS)
    form_d = form_d.sort_values(["searched_name", "filing_date"])
    form_d.to_csv("form_d.csv", index=False)
    print(f"\nWrote {len(form_d)} filings to form_d.csv.")
    return form_d


def search_keyword():
    """Search Form D filings for KEYWORD and write candidates.csv: one row per
    issuer (its latest filing), leaving out companies already in companies.csv."""
    companies = pd.read_csv("companies.csv", dtype=str, keep_default_na=False)
    known = [simple_name(name) for name in companies["name"]]

    hits = search_form_d(KEYWORD)
    filings, dropped = read_filings(hits)
    print(f'"{KEYWORD}": {len(hits)} hits, {dropped} dropped as fund/real estate/banking, {len(filings)} kept')

    candidates = pd.DataFrame(filings, columns=COLUMNS)
    already_listed = candidates["issuer_name"].apply(simple_name).isin(known)
    print(f"Left out {already_listed.sum()} filings from companies already in companies.csv")
    candidates = candidates[~already_listed]

    # A company can file a Form D and then amendments (D/A), so keep only its
    # most recent filing. CIK is the SEC's ID for the company.
    candidates = candidates.sort_values("filing_date", ascending=False)
    candidates = candidates.drop_duplicates("cik")
    candidates = candidates.sort_values("issuer_name")
    candidates.to_csv("candidates.csv", index=False)
    print(f"Wrote {len(candidates)} companies to candidates.csv.")
    return candidates


if __name__ == "__main__":
    if SEC_USER_AGENT == "":
        print("Set SEC_USER_AGENT to your name and email first, for example:")
        print('  export SEC_USER_AGENT="Your Name your.email@example.com"')
        sys.exit(1)  # stop here; exit code 1 means "something went wrong"

    print(f"Searching Form D filings from {START_DATE} to {END_DATE}\n")
    search_company_names()
    print()
    search_keyword()

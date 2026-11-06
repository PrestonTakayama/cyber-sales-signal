# fetch_jobs.py
#
# Step 2 (this part): work out which job board each company uses.
#   For each company in companies.csv without a slug (the short ID a job
#   board uses for that company, like "dropzoneai" in
#   job-boards.greenhouse.io/dropzoneai), we try two methods:
#     1. Website links: look for Greenhouse/Lever/Ashby links on the
#        company's homepage, /careers and /jobs pages.
#     2. Guessing: try the company name and domain name as slugs.
#   Every slug is checked against the job board's API before we save it,
#   and results go in the board_type and slug columns.
#
# Step 3: pull every open role from each working board into jobs.csv, with
#   columns company, title, department, location, source (the board type).
#
# Run it with:
#   python3 fetch_jobs.py find   -> finds job boards (Step 2)
#   python3 fetch_jobs.py        -> pulls jobs into jobs.csv (Step 3)

import re
import sys
import time
from urllib.parse import unquote

import pandas as pd
import requests

# Public job board endpoints. "{slug}" gets swapped for the company's slug.
BOARD_URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}

# Patterns that find a job board link in a page's HTML and capture the slug
# (the part in parentheses). Examples each one matches:
#   greenhouse: job-boards.greenhouse.io/dropzoneai/jobs/123
#               boards.greenhouse.io/embed/job_board?for=dropzoneai
#   lever:      jobs.lever.co/acme/1a2b3c
#   ashby:      jobs.ashbyhq.com/keycard-labs
LINK_PATTERNS = {
    "greenhouse": r"(?:boards|job-boards|boards-api)\.greenhouse\.io/"
                  r"(?:v1/boards/|embed/job_(?:board|app)(?:/js)?\?for=)?([\w-]+)",
    "lever": r"(?:jobs|api)\.lever\.co/(?:v0/postings/)?([\w.-]+)",
    "ashby": r"(?:jobs|api)\.ashbyhq\.com/(?:posting-api/job-board/)?([\w.%-]+)",
}

# Postings that aren't real openings, like "Join our Sales Talent Pool" or
# "Don't see a role that fits? Apply here." Any title containing one of these
# phrases (in any capitalization) is left out of jobs.csv.
PLACEHOLDER_PHRASES = ["talent pool", "general application", "apply here", "don't see"]

# Placeholder postings whose titles don't give them away, found by reading
# the posting itself. Each entry is (company, title).
KNOWN_PLACEHOLDERS = [
    ("Empirical Security", "Empiricist"),  # "we're staffed up, but tell us what you'd like to do"
]

# Some websites block requests that don't look like they come from a browser.
# This header says we're a browser-compatible client and names the project.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; insight-sourcing student project)"}


def get_with_one_retry(url):
    """Download a URL. If the request fails for a temporary reason, wait two
    seconds and try one more time (never more than once).
    Returns the response, or None if both tries failed."""
    for attempt in [1, 2]:
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
        except requests.RequestException:
            response = None  # no answer at all: timeout, no internet, etc.

        # A 404 is a real answer ("no board here"), so we only retry when there
        # was no answer or the server had a temporary problem
        # (429 = "too many requests", 500 and up = server error).
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


def board_exists(board_type, slug):
    """Ask the job board's API whether this slug is a real board."""
    response = get_with_one_retry(BOARD_URLS[board_type].format(slug=slug))
    return response is not None and response.status_code == 200


# ---------- Method 1: links on the company's own website ----------

def find_board_from_website(website):
    """Fetch the homepage, /careers and /jobs, look for job board links, and
    return (board_type, slug) for the first one the API confirms.
    Returns ("", "") if none is found."""
    # Turn "dropzone.ai" into "https://dropzone.ai" (and leave full URLs alone).
    if not website.startswith("http"):
        website = "https://" + website
    website = website.rstrip("/")

    for page in ["", "/careers", "/jobs"]:
        response = get_with_one_retry(website + page)
        if response is None or response.status_code != 200:
            continue  # page doesn't exist or didn't load

        # Some sites hide links inside JavaScript, where "/" is written "\/".
        html = response.text.replace("\\/", "/")

        for board_type, pattern in LINK_PATTERNS.items():
            # set() removes duplicates, since the same link often appears
            # many times on one page.
            for slug in set(re.findall(pattern, html)):
                slug = unquote(slug)  # turns "%20" back into a space, etc.
                if board_exists(board_type, slug):
                    return board_type, slug
    return "", ""


# ---------- Method 2: guess the slug ----------

def guess_slugs(name, website):
    """Return a list of slugs to try, e.g. ("Dropzone AI", "dropzone.ai")
    gives ["dropzoneai", "dropzone"]."""
    # Company name, lowercased, keeping only letters and digits.
    from_name = "".join(ch for ch in name.lower() if ch.isalnum())

    # Domain name: strip any "https://" or "www." and keep the part before
    # the first dot.
    domain = website.lower()
    domain = domain.replace("https://", "").replace("http://", "").replace("www.", "")
    from_domain = domain.split(".")[0]

    guesses = [from_name]
    if from_domain != from_name:
        guesses.append(from_domain)
    return guesses


def find_board_by_guessing(name, website):
    """Try every slug guess on every job board and stop at the first hit.
    Returns (board_type, slug, had_error). board_type and slug are "" if
    nothing was found. had_error is True if some request never got an
    answer, so a miss might not be a real miss."""
    had_error = False
    for slug in guess_slugs(name, website):
        for board_type, url_template in BOARD_URLS.items():
            response = get_with_one_retry(url_template.format(slug=slug))
            if response is None:
                had_error = True
            elif response.status_code == 200:
                return board_type, slug, had_error
    return "", "", had_error


# ---------- Run both methods over companies.csv ----------

def find_all_boards():
    """Fill in board_type and slug for every company in companies.csv that
    doesn't have a slug yet. Rows with a slug are left alone.
    A board_type of "none" means a guessed slug turned out to belong to a
    different company, so for those rows we only try the website method."""
    # dtype=str and keep_default_na=False make pandas read every cell as text
    # and empty cells as "" (instead of NaN, pandas' "missing" marker).
    companies = pd.read_csv("companies.csv", dtype=str, keep_default_na=False)
    for column in ["board_type", "slug"]:
        if column not in companies.columns:
            companies[column] = ""

    errors = []
    for i, row in companies.iterrows():
        if row["slug"] != "":
            print(f"{row['name']}: already set ({row['board_type']}/{row['slug']}), skipping")
            continue

        # Website links go first: they come from the company itself, while a
        # guessed slug can belong to a different company with the same name.
        board_type, slug = find_board_from_website(row["website"])
        method = "website link"

        if board_type == "" and row["board_type"] != "none":
            board_type, slug, had_error = find_board_by_guessing(row["name"], row["website"])
            method = "guess"
            if board_type == "" and had_error:
                errors.append(row["name"])

        if board_type:
            companies.loc[i, "board_type"] = board_type
            companies.loc[i, "slug"] = slug
            print(f"{row['name']}: {board_type}/{slug} (found by {method})")
        else:
            print(f"{row['name']}: not found")

    companies.to_csv("companies.csv", index=False)

    # Count only real boards, not blanks or rows marked "none".
    hits = companies["board_type"].isin(list(BOARD_URLS.keys())).sum()
    total = len(companies)
    print(f"\nFound a board for {hits} of {total} companies ({hits / total:.0%}).")
    if errors:
        print("These misses had requests that never got an answer, so try them again:")
        print(", ".join(errors))


# ---------- Step 3: pull every open role ----------
# Each job board names its fields differently, so each one gets a small
# function that turns its data into the same shape: a list of dicts with
# title, department and location.
# We write `job.get("x") or ""` so a missing or empty field becomes "".

def jobs_from_greenhouse(data):
    jobs = []
    for job in data["jobs"]:
        # A Greenhouse job can be in several departments, so join their names.
        departments = [d["name"] for d in job.get("departments") or []]
        location = job.get("location") or {}
        jobs.append({
            "title": job.get("title") or "",
            "department": ", ".join(departments),
            "location": location.get("name") or "",
        })
    return jobs


def jobs_from_lever(data):
    jobs = []
    for job in data:  # Lever returns a plain list of postings
        categories = job.get("categories") or {}
        jobs.append({
            "title": job.get("text") or "",  # Lever calls the title "text"
            "department": categories.get("department") or categories.get("team") or "",
            "location": categories.get("location") or "",
        })
    return jobs


def jobs_from_ashby(data):
    jobs = []
    for job in data["jobs"]:
        jobs.append({
            "title": job.get("title") or "",
            "department": job.get("department") or "",
            "location": job.get("location") or "",
        })
    return jobs


def is_placeholder(company, title):
    """True if a posting is a talent pool or general application rather than
    a real opening."""
    # Swap curly apostrophes (’) for straight ones (') so "don’t see" matches too.
    lowered = title.lower().replace("’", "'")
    for phrase in PLACEHOLDER_PHRASES:
        if phrase in lowered:
            return True
    return (company, title) in KNOWN_PLACEHOLDERS


def fetch_all_jobs():
    """Pull every open role from each company with a working board and
    write them all to jobs.csv. Placeholder postings are skipped."""
    companies = pd.read_csv("companies.csv", dtype=str, keep_default_na=False)

    all_jobs = []
    failed = []
    skipped = []
    for _, row in companies.iterrows():
        board_type = row["board_type"]
        if board_type not in BOARD_URLS:
            continue  # blank or "none": no board to read

        url = BOARD_URLS[board_type].format(slug=row["slug"])
        if board_type == "greenhouse":
            # Without content=true, Greenhouse leaves out each job's department.
            url += "?content=true"

        response = get_with_one_retry(url)
        if response is None or response.status_code != 200:
            print(f"{row['name']}: couldn't load {board_type}/{row['slug']}")
            failed.append(row["name"])
            continue

        data = response.json()
        if board_type == "greenhouse":
            jobs = jobs_from_greenhouse(data)
        elif board_type == "lever":
            jobs = jobs_from_lever(data)
        else:
            jobs = jobs_from_ashby(data)

        kept = 0
        for job in jobs:
            title = job["title"].strip()  # strip() removes stray spaces
            if is_placeholder(row["name"], title):
                skipped.append(f"{row['name']}: {title}")
                continue
            all_jobs.append({
                "company": row["name"],
                "title": title,
                "department": job["department"].strip(),
                "location": job["location"].strip(),
                "source": board_type,
            })
            kept += 1
        print(f"{row['name']}: {kept} roles")

    # Passing columns= keeps the column order fixed (and works even if empty).
    jobs_table = pd.DataFrame(all_jobs, columns=["company", "title", "department", "location", "source"])
    jobs_table.to_csv("jobs.csv", index=False)

    print(f"\nWrote {len(jobs_table)} roles from {jobs_table['company'].nunique()} companies to jobs.csv.")
    if skipped:
        print(f"Skipped {len(skipped)} placeholder postings:")
        for posting in skipped:
            print("  " + posting)
    if failed:
        print("Couldn't load these boards, so try again later:", ", ".join(failed))


if __name__ == "__main__":
    # sys.argv is the list of words typed after "python3" on the command line,
    # so sys.argv[1] is the first word after the file name, if there is one.
    if len(sys.argv) > 1 and sys.argv[1] == "find":
        find_all_boards()
    else:
        fetch_all_jobs()

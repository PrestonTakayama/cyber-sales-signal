# rank.py
#
# Step 4: tag every role in jobs.csv as Sales, Engineering or Other based on
#   its title (not its department), and save the tag in a "category" column
#   in jobs.csv.
#
# Step 5: score each company by its sales hiring and write ranked.csv,
#   sorted from highest score to lowest. Prints the top 10.
#
# Step 7: companies that filed a Form D in the last 12 months (listed in
#   form_d.csv, written by form_d.py) get raised_recently = True, and their
#   score is multiplied by RAISED_BONUS.
#
# Run it with:  python3 rank.py   (after python3 form_d.py)

import pandas as pd

# A title counts as Sales if it contains any of these phrases.
# All matching is lowercase, so "Account Executive" matches "account executive".
SALES_PHRASES = [
    "account executive",
    "account director",
    "regional vice president",
    "sales",  # also covers "Sales Engineer", "Sales Ops" and "Sales Enablement"
    "sdr",
    "bdr",
    "business development",
    "revenue",  # also covers "Revenue Operations" and "Revenue Marketing"
    "go-to-market",
    "partnerships",
    "channel",
    "demand generation",
    "growth marketing",
    "solutions architect",
    "solutions engineer",  # the same pre-sales job as a Sales Engineer
]

# ...unless it also contains one of these, which are never Sales.
NOT_SALES_PHRASES = [
    "customer success",
    "technical account manager",
    "brand marketing",
    "content marketing",
    "product marketing",
]

# Post-sales roles look after existing customers, so they're always Other,
# even if the title also contains a Sales or Engineering word.
POST_SALES_PHRASES = ["post-sales", "post sales"]

# Anything that isn't Sales counts as Engineering if it contains one of these.
ENGINEERING_PHRASES = [
    "engineer",  # also covers "engineering" and Forward Deployed Engineers
    "developer",
    "software",
    "security researcher",
    "data",
]

# Forward Deployed Engineers are counted separately in ranked.csv as an
# early-stage signal. They stay tagged Engineering and don't affect the score.
FDE_PHRASE = "forward deployed"

# A company that raised money recently has its score multiplied by this.
RAISED_BONUS = 1.25

# form_d.csv marks each filing's issuer name as an "exact", "partial" or
# "none" match for the company we searched for. Only exact matches count,
# plus the partial matches below, which were checked by hand against the
# officer names on the filing. Each entry is (company, Form D issuer name).
CONFIRMED_PARTIAL_MATCHES = [
    ("XBOW", "XBow Holding Inc."),  # officers include XBOW's CEO, Oege de Moor
]


def contains_any(text, phrases):
    """True if any phrase in the list appears somewhere in the text."""
    for phrase in phrases:
        if phrase in text:
            return True
    return False


def tag_title(title):
    """Return "Sales", "Engineering" or "Other" for a job title.
    Post-sales is checked first, then Sales, so "Sales Engineer" is Sales
    but "Solutions Architect - Post-Sales" is Other."""
    title = title.lower()
    if contains_any(title, POST_SALES_PHRASES):
        return "Other"
    if contains_any(title, SALES_PHRASES) and not contains_any(title, NOT_SALES_PHRASES):
        return "Sales"
    if contains_any(title, ENGINEERING_PHRASES):
        return "Engineering"
    return "Other"


def tag_jobs():
    """Add a category column to jobs.csv, print how many roles got each tag,
    and return the tagged table."""
    jobs = pd.read_csv("jobs.csv", dtype=str, keep_default_na=False)
    # .apply() runs tag_title on every title and collects the answers.
    jobs["category"] = jobs["title"].apply(tag_title)
    jobs.to_csv("jobs.csv", index=False)

    print("Roles per category:")
    print(jobs["category"].value_counts().to_string())
    return jobs


def raised_recently_companies():
    """Return the names of companies that filed a Form D in the last 12
    months (counted back from when form_d.py last ran)."""
    form_d = pd.read_csv("form_d.csv", dtype=str, keep_default_na=False)
    raised = []
    for _, row in form_d.iterrows():
        exact = row["match"] == "exact"
        confirmed = (row["searched_name"], row["issuer_name"]) in CONFIRMED_PARTIAL_MATCHES
        if exact or confirmed:
            raised.append(row["searched_name"])
    return raised


def rank_companies(jobs, raised):
    """Build one row per company with its role counts and score, sorted by
    score from highest to lowest. raised is the list of companies that
    raised money recently."""
    rows = []
    # groupby("company") splits the jobs table into one smaller table per
    # company, so company_jobs holds only that company's roles.
    for company, company_jobs in jobs.groupby("company"):
        total_roles = len(company_jobs)
        sales_roles = (company_jobs["category"] == "Sales").sum()
        sales_share = sales_roles / total_roles
        raised_recently = company in raised
        score = sales_roles * (1 + sales_share)
        if raised_recently:
            score = score * RAISED_BONUS
        fde_count = company_jobs["title"].str.lower().str.contains(FDE_PHRASE).sum()

        rows.append({
            "company": company,
            "total_roles": total_roles,
            "sales_roles": int(sales_roles),
            "sales_share": round(sales_share, 3),
            "score": round(score, 2),
            "fde_count": int(fde_count),  # not part of the score
            "raised_recently": raised_recently,
        })

    ranked = pd.DataFrame(rows)
    return ranked.sort_values("score", ascending=False)


if __name__ == "__main__":
    jobs = tag_jobs()

    raised = raised_recently_companies()
    # sorted(set(...)) removes repeats (a company can file more than once).
    print("\nRaised recently (score x 1.25):", ", ".join(sorted(set(raised))))

    ranked = rank_companies(jobs, raised)
    ranked.to_csv("ranked.csv", index=False)

    print(f"\nWrote {len(ranked)} companies to ranked.csv. Top 10:")
    print(ranked.head(10).to_string(index=False))

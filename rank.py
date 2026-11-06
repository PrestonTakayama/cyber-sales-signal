# rank.py
#
# Step 4: tag every role in jobs.csv as Sales, Engineering or Other based on
#   its title (not its department), and save the tag in a "category" column
#   in jobs.csv.
#
# Step 5: score each company by its sales hiring and write ranked.csv,
#   sorted from highest score to lowest. Prints the top 10.
#
# Run it with:  python3 rank.py

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


def rank_companies(jobs):
    """Build one row per company with its role counts and score, sorted by
    score from highest to lowest."""
    rows = []
    # groupby("company") splits the jobs table into one smaller table per
    # company, so company_jobs holds only that company's roles.
    for company, company_jobs in jobs.groupby("company"):
        total_roles = len(company_jobs)
        sales_roles = (company_jobs["category"] == "Sales").sum()
        sales_share = sales_roles / total_roles
        score = sales_roles * (1 + sales_share)
        fde_count = company_jobs["title"].str.lower().str.contains(FDE_PHRASE).sum()

        rows.append({
            "company": company,
            "total_roles": total_roles,
            "sales_roles": int(sales_roles),
            "sales_share": round(sales_share, 3),
            "score": round(score, 2),
            "fde_count": int(fde_count),  # not part of the score
        })

    ranked = pd.DataFrame(rows)
    return ranked.sort_values("score", ascending=False)


if __name__ == "__main__":
    jobs = tag_jobs()

    ranked = rank_companies(jobs)
    ranked.to_csv("ranked.csv", index=False)

    print(f"\nWrote {len(ranked)} companies to ranked.csv. Top 10:")
    print(ranked.head(10).to_string(index=False))

# compare.py
#
# Step 8: compare the current jobs.csv and ranked.csv with an earlier saved
#   snapshot, to see which companies added or dropped sales roles.
#
# Run it with:
#   python3 compare.py save 2026-11-09   -> copy the current jobs.csv and
#                                           ranked.csv into snapshots/2026-11-09/
#                                           (use the date the data was pulled)
#   python3 compare.py                   -> compare the newest snapshot with the
#                                           current files and write changes.csv
#
# The order matters: save the old data first, then rerun fetch_jobs.py,
# form_d.py and rank.py, then compare.

import os
import shutil
import sys
from collections import Counter

import pandas as pd

from rank import tag_title

SNAPSHOT_FOLDER = "snapshots"
FILES_TO_SAVE = ["jobs.csv", "ranked.csv"]


def save_snapshot(date):
    """Copy the current jobs.csv and ranked.csv into snapshots/<date>/."""
    folder = os.path.join(SNAPSHOT_FOLDER, date)
    if os.path.exists(folder):
        print(f"{folder} already exists, so nothing was copied.")
        return
    os.makedirs(folder)
    for name in FILES_TO_SAVE:
        shutil.copy(name, os.path.join(folder, name))
    print(f"Saved {' and '.join(FILES_TO_SAVE)} to {folder}")


def newest_snapshot():
    """Return the date of the most recent snapshot folder. Dates are written
    year-month-day, so sorting them as text puts the newest one last."""
    if not os.path.exists(SNAPSHOT_FOLDER):
        return None
    dates = sorted(
        name for name in os.listdir(SNAPSHOT_FOLDER)
        if os.path.isdir(os.path.join(SNAPSHOT_FOLDER, name))
    )
    if not dates:
        return None
    return dates[-1]


def load_sales_roles(path):
    """Read a jobs.csv and return two things: every role, and only the Sales
    ones. Roles are tagged again with the current rule from rank.py, so an
    old snapshot and a new one are always tagged the same way, even if the
    rule changed in between."""
    jobs = pd.read_csv(path, dtype=str, keep_default_na=False)
    jobs["category"] = jobs["title"].apply(tag_title)
    sales = jobs[jobs["category"] == "Sales"]
    return jobs, sales


def load_ranks(path):
    """Read a ranked.csv and return {company: rank}. The file is already
    sorted by score, so a company's row number is its rank."""
    ranked = pd.read_csv(path, dtype=str, keep_default_na=False)
    ranks = {}
    for position, company in enumerate(ranked["company"], start=1):
        ranks[company] = position
    return ranks


def company_roles(sales, company):
    """Return one company's sales roles as a list of (title, location)."""
    rows = sales[sales["company"] == company]
    return list(zip(rows["title"], rows["location"]))


def roles_not_in(roles, other_roles):
    """Return the roles whose title isn't in other_roles. Roles are matched
    on title only, because a company sometimes rewrites a posting's location
    ("United States" to "United States - Remote") without it being a new
    job. A Counter is used because the same title can be posted more than
    once: if a title is posted three times now and once before, two of the
    three count as new."""
    left_over = Counter(title for title, location in other_roles)
    result = []
    # Roles posted in the same place as before are matched up first, so the
    # ones left over are the ones in new places.
    same_place_first = sorted(roles, key=lambda role: role not in other_roles)
    for title, location in same_place_first:
        if left_over[title] > 0:
            left_over[title] -= 1
        else:
            result.append((title, location))
    return result


def describe(roles):
    """Turn a list of (title, location) into readable text, like
    "Account Executive (Boston, MA); Sales Engineer (Remote)"."""
    parts = []
    for title, location in sorted(roles):
        parts.append(f"{title} ({location})" if location else title)
    return "; ".join(parts)


def compare(before_date):
    """Compare the snapshot from before_date with the current files and
    return one row per company."""
    folder = os.path.join(SNAPSHOT_FOLDER, before_date)
    jobs_before, sales_before = load_sales_roles(os.path.join(folder, "jobs.csv"))
    jobs_now, sales_now = load_sales_roles("jobs.csv")
    ranks_before = load_ranks(os.path.join(folder, "ranked.csv"))
    ranks_now = load_ranks("ranked.csv")

    # Every company that shows up in either pull.
    companies = sorted(set(jobs_before["company"]) | set(jobs_now["company"]))

    rows = []
    for company in companies:
        before = company_roles(sales_before, company)
        now = company_roles(sales_now, company)
        # Titles posted now that weren't posted at the snapshot, and titles
        # from the snapshot that are no longer posted.
        new_roles = roles_not_in(now, before)
        closed_roles = roles_not_in(before, now)

        sales_roles_before = len(before)
        sales_roles_now = len(now)

        rows.append({
            "company": company,
            "sales_roles_before": sales_roles_before,
            "sales_roles_now": sales_roles_now,
            "sales_change": sales_roles_now - sales_roles_before,
            "total_roles_before": int((jobs_before["company"] == company).sum()),
            "total_roles_now": int((jobs_now["company"] == company).sum()),
            # A blank rank means the company wasn't ranked in that pull.
            "rank_before": ranks_before.get(company, ""),
            "rank_now": ranks_now.get(company, ""),
            "new_sales_roles": describe(new_roles),
            "closed_sales_roles": describe(closed_roles),
        })

    changes = pd.DataFrame(rows)
    # Biggest increase in sales roles first. Ties go to the company with
    # more sales roles open now.
    return changes.sort_values(
        ["sales_change", "sales_roles_now"], ascending=[False, False]
    )


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "save":
        save_snapshot(sys.argv[2])
    elif len(sys.argv) == 1:
        before_date = newest_snapshot()
        if before_date is None:
            print("No snapshot found. Run: python3 compare.py save YYYY-MM-DD")
            sys.exit(1)

        changes = compare(before_date)
        changes.to_csv("changes.csv", index=False)

        short = changes[[
            "company", "sales_roles_before", "sales_roles_now",
            "sales_change", "rank_before", "rank_now",
        ]]
        moved = short[short["sales_change"] != 0]
        print(f"Compared with the snapshot from {before_date}.")
        print(f"{len(moved)} of {len(changes)} companies changed their sales role count:\n")
        if len(moved) > 0:
            print(moved.to_string(index=False))
        print("\nWrote changes.csv")
    else:
        print("Usage: python3 compare.py            (compare with the newest snapshot)")
        print("       python3 compare.py save DATE  (save the current files as a snapshot)")

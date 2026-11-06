# cyber-sales-signal

A small sourcing tool for growth equity. It starts from a list of private, venture-backed cybersecurity companies that raised a Series A, B or C in the last two years. It pulls every open role from their public job boards (Greenhouse, Lever and Ashby), tags each role by its title, and ranks the companies by how much sales hiring they're doing right now. Sales hiring is the signal because it's one of the clearest outside signs of product-market fit. A company adds account executives, sales engineers and channel managers only when its product sells repeatably, since each new rep is expensive and has to pay for themselves. A company still searching for fit hires mostly engineers. So a large and growing sales team, especially as a share of all open roles, suggests demand has shown up and the company is scaling to meet it.

## Tagging rule

Every role is tagged **Sales**, **Engineering** or **Other** from its job title only (not its department). Matching ignores capitalization, and the checks run in this order:

1. **Post-sales goes to Other.** Any title containing "post-sales" is Other.
2. **Sales.** The title contains any of: account executive, account director, regional vice president, sales, SDR, BDR, business development, revenue, go-to-market, partnerships, channel, demand generation, growth marketing, solutions architect.
   - Sales Engineers and Solutions Architects count as Sales.
   - Sales support roles (Sales Ops, Revenue Ops, Sales Enablement, Revenue Marketing) count as Sales.
   - Customer Success, Technical Account Manager, and brand, content or product marketing roles never count as Sales, even if they contain a word above.
3. **Engineering.** The title contains any of: engineer, developer, software, security researcher, data.
4. **Other.** Everything else.

Each company is then scored as:

```
sales_share = sales_roles / total_roles
score       = sales_roles * (1 + sales_share)
```

## How to run it

You need Python 3 and two packages:

```bash
python3 -m pip install requests pandas
```

Then run these from the project folder:

```bash
python3 fetch_jobs.py find   # find the job board for companies with no slug yet
python3 fetch_jobs.py        # pull every open role into jobs.csv
python3 rank.py              # tag each role and write ranked.csv (prints the top 10)
```

The first command is only needed after you add companies. To add one, put a new `name,website` row in `companies.csv` and run all three. The finder looks for job board links on the company's homepage, `/careers` and `/jobs` pages first, then tries guessing the slug from the name and domain. A guessed slug can belong to a different company with the same name. If that happens, set `board_type` to `none` for that row, or fill in the correct `board_type` (`greenhouse`, `lever` or `ashby`) and `slug` by hand.

| File | What's in it |
|---|---|
| `companies.csv` | The company list, plus each company's `board_type` and `slug` |
| `jobs.csv` | Every open role: company, title, department, location, source (the job board), category |
| `ranked.csv` | One row per company: total_roles, sales_roles, sales_share, score, fde_count, sorted by score |

## What it found

## Notes

This tool only reads Greenhouse, Lever and Ashby job boards. Companies that use other hiring systems are left blank in `companies.csv`, including:

- Comeet
- Rippling
- Workday
- Workable
- BambooHR

Talent pool and general application postings (like "Don't see a role that fits? Apply here.") are excluded from `jobs.csv`, since they aren't real openings.

Sales support roles (Sales Ops, Revenue Ops, Sales Enablement, Revenue Marketing) count as Sales, because companies only hire them once there are enough reps to support.

Forward Deployed Engineers (FDEs) are tagged Engineering, not Sales. An FDE is usually an early-stage build hire, not a sales hire. `ranked.csv` counts them in a separate `fde_count` column as an early-stage signal, and they don't affect the score.

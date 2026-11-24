# cyber-sales-signal

A small sourcing tool for growth equity that ranks private cybersecurity companies by how much sales hiring they're doing right now. It reads open roles from public job boards (Greenhouse, Lever and Ashby) and currently ranks 28 of the 56 companies in `companies.csv`.

## What it found on November 9
Doppel came first with 18 of its 26 openings in sales (69%), followed by 7AI with 20 of 45. I didn't know much about Doppel going in, but once I read up on it and saw it had raised a Series C a year ago, the result made sense. Of the 59 sales openings across Doppel, 7AI, and Cogent, 33 were for account executives, mostly covering U.S. regions, and just one was for an SDR. My guess is they already know who they're selling to and have leads coming in, so they need people who can close. Cogent had the most sales openings (21) and was the only one of the three hiring for sales ops (3), which suggests its sales team is already big enough to need more support.

Halcyon came in 17th out of 28 with six openings, three of them for account executives in Chicago, Boston, and Charlotte, so it probably already has people covering other cities. That made me realize a company can rank low even if it already has a big sales team. I was surprised that only 28 of 56 companies could be ranked and that three of the five I picked to learn about were missing. The tool couldn't read Upwind's job board, Spur had no public board, and Sublime had nothing posted.

Most of the top 10 lead with AI, but in a market this crowded it takes more than sticking AI into something to make it good. I'd start with 7AI, which has openings for 12 account executives and six sales engineers, because I think getting AI to do the work of an entire security operations team is harder than it sounds. I'd look at the competition and talk to customers about what they use 7AI for and whether they've kept paying for it.

## What changed by November 23

Daylight Security made the biggest jump, going from 14th to 2nd. Its sales openings increased from 5 on November 9 to 21 on November 23, including 11 account executive roles. It also announced an $80M Series B on November 10, just one day after my first pull.

7AI moved into first place, with 21 of its 45 openings in sales. Doppel dropped from 1st to 4th as its sales openings fell from 18 to 15. Its November 2025 Form D also passed the 12-month cutoff, so it lost the 25% bonus.

## Current ranking

Top 10 from `ranked.csv`, in score order. Share is sales roles as a percentage of all open roles. Change is sales roles now minus sales roles on November 9, from `changes.csv`.

Last updated: November 23, 2026

| Company | Total roles | Sales roles | Share | Change since Nov 9 | Raised recently |
|---|---|---|---|---|---|
| 7AI | 45 | 21 | 47% | +1 | Yes |
| Daylight Security | 34 | 21 | 62% | +16 | No |
| Cogent Security | 54 | 21 | 39% | 0 | No |
| Doppel | 23 | 15 | 65% | -3 | No |
| HiddenLayer | 19 | 14 | 74% | -1 | No |
| Endor Labs | 43 | 16 | 37% | +3 | No |
| Zafran | 36 | 15 | 42% | 0 | No |
| AegisAI | 24 | 11 | 46% | 0 | No |
| Neo | 19 | 9 | 47% | 0 | No |
| Socket | 23 | 7 | 30% | -1 | Yes |

## Why sales hiring

Sales hiring is one of the clearest outside signs that a company has product-market fit. Sales reps are expensive, and each one has to bring in more than they cost, so a company hires a lot of them only once its product sells again and again. A company still looking for fit hires mostly engineers. So many open sales roles, especially as a share of all open roles, suggest customers are buying and the company is growing to keep up.

## Tagging rule and score

Every role is tagged **Sales**, **Engineering** or **Other** from its job title only (not its department). Matching ignores capitalization, and the checks run in this order:

1. **Post-sales goes to Other.** Any title containing "post-sales" is Other.
2. **Sales.** The title contains any of: account executive, account director, regional vice president, sales, SDR, BDR, business development, revenue, go-to-market, partnerships, alliances, channel, demand generation, growth marketing, solutions architect, solutions engineer.
   - Sales Engineers, Solutions Engineers and Solutions Architects count as Sales.
   - Sales support roles (Sales Ops, Revenue Ops, Sales Enablement, Revenue Marketing) count as Sales.
   - Customer Success, Technical Account Manager, and brand, content, product or technical marketing roles never count as Sales, even if they contain a word above.
3. **Engineering.** The title contains any of: engineer, developer, software, security researcher, data.
4. **Other.** Everything else.

Each company is then scored as:

```
sales_share = sales_roles / total_roles
score       = sales_roles * (1 + sales_share)
score       = score * 1.25    (only if raised_recently)
```

`raised_recently` is true when the company filed a Form D with the SEC in the last 12 months. A Form D is the notice a private company files after selling shares, for example in a venture round.

## Notes

This tool only reads Greenhouse, Lever and Ashby job boards. 28 of the 56 companies in `companies.csv` aren't ranked. 10 use hiring systems the tool can't read (8 of them Comeet, 1 Rippling and 1 JazzHR), 5 post jobs only on their own site, 11 had no listings I could find, and 2 have a board with no open roles.

Talent pool and general application postings (like "Don't see a role that fits? Apply here.") are excluded from `jobs.csv`, since they aren't real openings.

Job postings aren't hires. The tool only sees who is hiring now, not how big a team already is.

Tagging is by title only, so a few roles land in the wrong bucket. Halcyon's "Senior Deal Desk Lead" works on pricing and contracts for sales deals, but the title has no Sales word, so it's tagged Other. The Sales list has "go-to-market" but not "GTM", so Doppel's "Program Manager, GTM Enablement" is tagged Other, even though enablement counts as Sales.

Sales support roles (Sales Ops, Revenue Ops, Sales Enablement, Revenue Marketing) count as Sales, because companies only hire them once there are enough reps to support.

Forward Deployed Engineers (FDEs) are tagged Engineering, not Sales. An FDE is usually an early-stage build hire, not a sales hire. `ranked.csv` counts them in a separate `fde_count` column as an early-stage signal, and they don't affect the score.

A "No" under raised recently can mean the Form D wasn't found. Cogent Security shows No even though it announced a Series A in February 2026, and Daylight Security shows No even though it announced a Series B on November 10, 2026.

The 12 months is a hard cutoff. Doppel's Form D was filed on November 21, 2025, so it lost the bonus two days before the November 23 pull. With the bonus it would be third.

The score is weighted toward count. A v2 could weight share more heavily, which would move focused companies like HiddenLayer up.

The list is 56 private, venture-backed cybersecurity companies, mostly US-based, most of which announced a Series A, B or C between November 2024 and November 2026. I used an AI assistant to draft the first 50 and check them against news reports. I cut 4, added Spur, Oligo and Daylight, and added 7 more from the Form D search, which were picked for filing a raise of $5M or more in the last 12 months.

This is two pulls, November 9 and November 23. Two weeks is short, so a change of one or two roles doesn't mean much. A role that's gone could have been filled or taken down, and the tool can't tell which.

## How to run it

You need Python 3 and two packages:

```bash
python3 -m pip install requests pandas
```

Then run these from the project folder:

```bash
python3 fetch_jobs.py find   # find the job board for companies with no slug yet
python3 fetch_jobs.py        # pull every open role into jobs.csv
python3 form_d.py            # search SEC Form D filings into form_d.csv and candidates.csv
python3 rank.py              # tag each role and write ranked.csv (prints the top 10)
```

To see what changed since the last pull, save the current files before you rerun the commands above, then compare:

```bash
python3 compare.py save 2026-11-23   # copy jobs.csv and ranked.csv into snapshots/2026-11-23/
python3 compare.py                   # after rerunning, compare with the newest snapshot and write changes.csv
```

A sales role counts as new when its title wasn't posted in the snapshot. Roles are matched on title only, because companies sometimes reword a posting's location without it being a new job.

The first command is only needed after you add companies. To add one, put a new `name,website` row in `companies.csv` and run all four. The finder looks for job board links on the company's homepage, `/careers` and `/jobs` pages first, then tries guessing the slug from the name and domain. A guessed slug can belong to a different company with the same name. If that happens, set `board_type` to `none` for that row, or fill in the correct `board_type` (`greenhouse`, `lever` or `ashby`) and `slug` by hand.

`form_d.py` searches SEC EDGAR for Form D filings from the last 12 months, once for each company name and once for the keyword "security". The SEC requires a name and email in every request. `form_d.py` reads them from an environment variable, so they aren't saved in the code. Set it in your terminal before running `form_d.py` (add the line to `~/.zshrc` to keep it for every new terminal):

```bash
export SEC_USER_AGENT="Your Name your.email@example.com"
```

Each filing's issuer name is marked as an `exact`, `partial` or `none` match for the company name searched. Only exact matches count toward `raised_recently`. A partial match counts only after you check it by hand and add it to `CONFIRMED_PARTIAL_MATCHES` in `rank.py`.

| File | What's in it |
|---|---|
| `companies.csv` | The company list, plus each company's `board_type` and `slug` |
| `jobs.csv` | Every open role: company, title, department, location, source (the job board), category |
| `form_d.csv` | Form D filings found by searching each company name: issuer, filing date, state, industry group, total offering amount, amount sold, and how well the issuer name matches |
| `candidates.csv` | Companies found by the "security" keyword search that aren't in `companies.csv` yet, one row per company (its latest filing) |
| `ranked.csv` | One row per company: total_roles, sales_roles, sales_share, score, fde_count, raised_recently, sorted by score |
| `snapshots/` | The `jobs.csv` and `ranked.csv` from an earlier pull, in a folder named for the date |
| `changes.csv` | One row per company: sales roles and rank at the last snapshot and now, plus the sales roles that are new and the ones no longer posted |

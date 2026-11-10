# cyber-sales-signal

A small sourcing tool for growth equity. It starts from a list of private, venture-backed cybersecurity companies that raised a Series A, B or C in the last two years. It pulls every open role from their public job boards (Greenhouse, Lever and Ashby), tags each role by its title, and ranks the companies by how much sales hiring they're doing right now. Sales hiring is the signal because it's one of the clearest outside signs of product-market fit. A company adds account executives, sales engineers and channel managers only when its product sells repeatably, since each new rep is expensive and has to pay for themselves. A company still searching for fit hires mostly engineers. So a large sales team, especially as a share of all open roles, suggests demand has shown up and the company is scaling to meet it.

## Tagging rule

Every role is tagged **Sales**, **Engineering** or **Other** from its job title only (not its department). Matching ignores capitalization, and the checks run in this order:

1. **Post-sales goes to Other.** Any title containing "post-sales" is Other.
2. **Sales.** The title contains any of: account executive, account director, regional vice president, sales, SDR, BDR, business development, revenue, go-to-market, partnerships, channel, demand generation, growth marketing, solutions architect, solutions engineer.
   - Sales Engineers, Solutions Engineers and Solutions Architects count as Sales.
   - Sales support roles (Sales Ops, Revenue Ops, Sales Enablement, Revenue Marketing) count as Sales.
   - Customer Success, Technical Account Manager, and brand, content or product marketing roles never count as Sales, even if they contain a word above.
3. **Engineering.** The title contains any of: engineer, developer, software, security researcher, data.
4. **Other.** Everything else.

Each company is then scored as:

```
sales_share = sales_roles / total_roles
score       = sales_roles * (1 + sales_share)
score       = score * 1.25    (only if raised_recently)
```

`raised_recently` is true when the company filed a Form D with the SEC in the last 12 months. A Form D is the notice a private company files after selling shares, for example in a venture round.

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

## Current ranking

Top 10 from `ranked.csv` as of November 7, 2026, in score order. Share is sales roles as a percentage of all open roles.

| Company | Total roles | Sales roles | Share | Raised recently |
|---|---|---|---|---|
| Doppel | 27 | 18 | 67% | Yes |
| 7AI | 45 | 19 | 42% | Yes |
| Cogent Security | 52 | 21 | 40% | No |
| HiddenLayer | 20 | 15 | 75% | No |
| Zafran | 32 | 14 | 44% | No |
| Endor Labs | 36 | 13 | 36% | No |
| Armadin | 27 | 9 | 33% | Yes |
| Socket | 27 | 8 | 30% | Yes |
| Obsidian Security | 15 | 5 | 33% | Yes |
| Fable Security | 8 | 4 | 50% | Yes |

## What it found
Doppel came first with 18 of its 26 openings in sales (69%), followed by 7AI with 20 of 45. I didn't know much about Doppel going in, but once I read up on it and saw it had raised a Series C a year ago, the result made sense. Of the 59 sales openings across Doppel, 7AI, and Cogent, 33 were for account executives, mostly covering U.S. regions, and just one was for an SDR. My guess is they already know who they're selling to and have leads coming in, so they need people who can close. Cogent had the most sales openings (21) and was the only one of the three hiring for sales ops (3), which suggests its sales team is already big enough to need more support.

Halcyon came in 17th out of 28 with six openings, three of them for account executives in Chicago, Boston, and Charlotte, so it probably already has people covering other cities. That made me realize a company can rank low even if it already has a big sales team. I was surprised that only 28 of 56 companies could be ranked and that three of the five I picked to learn about were missing. The tool couldn't read Upwind's job board, Spur had no public board, and Sublime had nothing posted.

Most of the top 10 lead with AI, but in a market this crowded it takes more than sticking AI into something to make it good. I'd start with 7AI, which has openings for 12 account executives and six sales engineers, because I think getting AI to do the work of an entire security operations team is harder than it sounds. I'd look at the competition and talk to customers about what they use 7AI for and whether they've kept paying for it.

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

The score is weighted toward count. A v2 could weight share more heavily, which would move focused companies like HiddenLayer up.

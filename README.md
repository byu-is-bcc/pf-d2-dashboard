# D2 — The Dashboard Someone Opens

**Portfolio Factory · Data & Analytics · Practitioner tier · 15 to 25 hours · Builds on D1**

> **Prerequisite: [Project 000](https://github.com/byu-is-bcc/pf-000-portfolio-site).** Build your site first. This project ships with an entry on it.

> **Intended prior: [D1 — Ask It In SQL](https://github.com/byu-is-bcc/pf-d1-ask-it-in-sql).** Point this dashboard at the database you built there. If you are entering cold, the shipped seed is the same library extract D1 uses, already modeled into four tables.

A stranger opens a URL. No account. No VPN. No "ask me for access." The numbers on the page came from a database that refreshed on a schedule, and at least one quality gate has actually fired. That is the bar.

---

## Replace everything above this line with your own README

The template below is what a finished version looks like. Delete the instructions, keep the shape.

---

## What this project is

A query file answers questions for you. A dashboard answers them for someone else, tomorrow, without you in the room.

That is the difference between D1 and D2, and it is the difference between analysis and a product. The SQL skills do not change. What changes is the audience, the deployment, and the fact that the data has to keep being true after you stop looking at it.

**Why this rung exists.** Analyst and BI postings name dashboards, scheduled refreshes, and data quality in the same breath as SQL. A notebook that never left your laptop does not speak that language. A public URL that a recruiter can open between meetings does.

| The posting says | You do it here |
|---|---|
| "Dashboarding" / "BI" | A Streamlit (or Evidence, or Tableau Public) page a stranger opens |
| "SQL for reporting" | Every number on the page comes from a `.sql` file in `queries/` |
| "Data quality" / "monitoring" | Gates that run on every refresh, with at least one that has fired |
| "ETL" / "pipelines" | A scheduled refresh that fetch → build → gate → records the result |
| "Stakeholder communication" | Chart titles that state findings, not axis names — the D0 rule, live |

The claim you earn: **I put a live dashboard in front of real data, kept it current, and made sure bad data could not quietly redraw it.** Every word of that is checkable against this repository and the URL.

---

## Start here

```bash
git clone <your-repo-url> && cd <your-repo>
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/build_seed_db.py
streamlit run app.py
```

The page opens. It looks unfinished on purpose: the title, the question, the reader, and the accent are all unset, the headline query returns NULL, and every chart title is still an axis label. That is the assignment, visible.

Then see the list:

```bash
python scripts/check_decisions.py
```

Nine findings. Work them down. CI has two jobs for the same reason: `smoke` stays green (scaffolding works), `dashboard` stays red until you finish (the decisions are made).

---

## Which data you use

**If you did D1, point this at your database.**

```bash
DASHBOARD_DB=/path/to/your/d1.db streamlit run app.py
```

Or set `DASHBOARD_DB` in the Streamlit Cloud secrets / environment. Your D1 queries become the panels. That is the intended path through the ladder.

**If you are starting cold, use the shipped seed.** `data/library_loans.csv` is the same 20,000-row library extract D1 ships. `scripts/build_seed_db.py` builds the four-table database. The page already runs against it.

**Better than either: connect a source that changes.** A static extract refreshes into the same numbers forever, which makes the scheduled pipeline a costume. A feed that updates overnight is why the refresh exists. See the `TODO` in `fetch()` inside `scripts/refresh.py`.

Whatever you pick, say so in `MAKE_IT_YOURS.md`. A reviewer has to know whether they are looking at your D1 work, a found source, or the seed everyone else also has.

---

## The work

### 1. Decide what the page is for

Open `MAKE_IT_YOURS.md` before you touch a chart. Five decisions: the question, the reader, the data, what leads (and what you cut), the accent, and one quality gate that is yours.

Fill in the matching values at the top of `app.py`: `TITLE`, `QUESTION`, `READER`, `ACCENT`, and the order of `SECTIONS`. Until those are set, the page says it is a template and the charts render gray. That is intentional — the same mechanism Project 000 uses with `--accent`.

### 2. Write the queries the page runs on

Every number comes from `queries/*.sql`. Nothing is hardcoded in `app.py`, and nothing is read from a CSV at page load.

| File | Job |
|---|---|
| `queries/headline.sql` | The one number. Ships returning NULL. Write it. |
| `queries/kpis.sql` | Four summary metrics |
| `queries/loans_by_month.sql` | The seasonality chart |
| `queries/returns_by_patron_type.sql` | The returns chart |

Rename, delete, add. A dashboard whose SQL is still named after the library seed while the page is about something else is a tell.

**Chart titles state findings.** This is the D0 rule carried forward. `"Loans per month, September 2024 to August 2026"` describes axes. `"July volume is less than half of October — summer staffing on a term-time pattern is the cost"` is a title. The helper in `app.py` marks placeholder titles until you replace them; `check_decisions.py` fails while any remain.

### 3. Put it on the public internet

Deploy so a stranger opens it with no account.

**Default: [Streamlit Community Cloud](https://streamlit.io/cloud).** Free, watches the repo, redeploys on push. Connect the repository, set the main file to `app.py`, deploy. Evidence.dev is also fine and keeps the artifact in the repo. Tableau Public is explicitly allowed if that is the tool you already know — say so in the README and still keep the quality-gate and refresh evidence in this repository.

The test: paste the URL into a private/incognito window, or ask someone who has never seen the project to open it. If they hit a login, it is not done.

### 4. Refresh on a schedule, with gates that fire

`.github/workflows/refresh.yml` runs `scripts/refresh.py` once a day:

1. **fetch** — pull the source (`fetch()` is the seam you own)
2. **build** — rebuild `data/seed.db`
3. **gate** — run `scripts/checks.py`
4. **record** — write `data/refresh_state.json`, including failures

Step 4 happens whether or not step 3 passed. A pipeline that dies silently leaves yesterday's numbers on the page with no warning, which is worse than showing nothing. The dashboard reads that state file and surfaces a red banner when a blocking gate failed.

Eight core gates ship finished (row counts, nulls, orphans, date order, unexpected categories). Write `check_your_own_gate()` in `scripts/checks.py` and set `max_data_age_days` in `checks.toml`. Those two are why the `dashboard` CI job starts red.

**Proof that a gate has fired:** run `python scripts/checks.py --demo-failure` and watch it exit non-zero, or point the pipeline at deliberately broken data once and commit the `refresh_state.json` that recorded the failure. A gate that has never failed is a comment, not a gate.

---

## What you hand in

| File / thing | What it is |
|---|---|
| Public URL | A stranger opens it. No account. |
| `README.md` | Your write-up. Claim in the first line. Link to the live dashboard. |
| `MAKE_IT_YOURS.md` | Five decisions, answered. Every `TODO` gone. |
| `app.py` DECIDE block | Title, question, reader, accent, section order — set |
| `queries/` | SQL the page actually runs, including a real headline |
| `checks.toml` + your gate | Recency threshold set; `check_your_own_gate()` written |
| `data/refresh_state.json` | Evidence the scheduled refresh has run (pass or recorded fail) |
| Site entry | On your Project 000 site. Not optional. |

---

## Your claim

The first line of your finished README. One sentence, with a number and a URL.

**Not:** "Built an interactive dashboard to visualize library data using Streamlit."

**Yes:** "Live at `<URL>`: summer checkout volume runs 47% below term-time across five branches, refreshed nightly, with a gate that hides the page when loan rows drop more than 10% between runs."

The URL is load-bearing. Without it, this is a local Streamlit script, and local Streamlit scripts are not Practitioner-tier artifacts.

---

## How to verify this

Same list an alumni reviewer will use. Do it yourself first.

- [ ] A stranger opens the public URL with no account, in a window that is not already logged into anything of yours
- [ ] `python scripts/smoke_test.py` exits 0
- [ ] `python scripts/check_decisions.py` exits 0
- [ ] Every chart title is a finding with a number in it, not an axis label
- [ ] The headline number is real (not the NULL the template ships)
- [ ] `data/refresh_state.json` shows at least one scheduled (or manually triggered) run
- [ ] At least one quality gate has actually fired — demo failure, or a real one you recorded
- [ ] `check_your_own_gate()` is written and `max_data_age_days` is set
- [ ] No `.db` committed; no secrets in git history
- [ ] **The anti-sameness gate below**

### The anti-sameness gate

This is **not yet** — not finished, and it will not pass review — if all four of these are still true at once:

- the dashboard is built on the shipped library seed, unchanged, *and*
- the question it answers is the one the template implies rather than one you chose, *and*
- `SECTIONS` is still in the order it shipped in, *and*
- the only quality gates are the eight that came with the template

Any one of them alone is fine. Using the seed because the library question is the one you wanted to answer is a decision. Leaving all four because you never opened `MAKE_IT_YOURS.md` is not.

`scripts/check_decisions.py` enforces the mechanical half. The rest is for a human, and a reviewer opening your URL next to this template can tell in about four seconds.

---

## Deploy notes

**Streamlit Community Cloud**

1. Push this repository to GitHub (your fork / your copy from the template).
2. [share.streamlit.io](https://share.streamlit.io) → New app → pick the repo → main file `app.py`.
3. If you use `DASHBOARD_DB` or any API key for `fetch()`, put them in the app's Secrets — never in the repo.

**Evidence / Tableau Public**

Allowed. Keep this repository as the place the refresh script, the gates, and `MAKE_IT_YOURS.md` live, and link the published workbook from your README. The verification bar does not change: stranger, no account, refresh history, a gate that has fired.

**GitHub Actions**

- `ci.yml` — `smoke` must stay green; `dashboard` is red until you finish.
- `refresh.yml` — daily pipeline. After you push, check the Actions tab once and confirm a run has a `refresh_state.json` commit or artifact you can point at.

---

## Resume one-liners

Written after you have the real URL and the real numbers:

- Deployed a public dashboard at `<URL>` over a `<N>`-row database, with every panel driven by committed SQL rather than hardcoded values.
- Built a daily refresh pipeline (fetch → rebuild → quality gates → record) so a failed run surfaces on the page instead of silently serving stale numbers.
- Defined `<N>` data quality gates including one domain-specific check, and verified at least one gate fires on deliberately broken input.
- Designed the page around a single stated question for a named reader, with chart titles that state findings rather than axis names.

---

## Who hires for this

Analyst and analytics-engineer roles at **Zions Bancorporation**, **Pattern**, **Qualtrics**, **Domo**, **Lucid**, and teams that describe themselves as BI or revenue operations. "SQL plus a dashboard somebody else opens" is the shape of the junior half of that market.

Those names illustrate the kind of work, not a target list. 73% of the companies that hired BYU IS students in the last five years hired exactly one.

---

## Where people get stuck

**"It looks fine locally and broken on Streamlit Cloud."** Usually a path assumption (`data/seed.db` not built) or a package missing from `requirements.txt`. The Cloud install is only what is in that file. Add a build step or commit a documented startup command; do not commit the `.db`.

**"The refresh does nothing because the seed never changes."** Correct. That is why `fetch()` has a TODO. Point it at something that moves, or accept that your proof of the pipeline is a recorded `--demo-failure` plus a manual run that writes `refresh_state.json`.

**"I do not know what my headline number should be."** Go back to D1's Q11–Q13, or to the test from D0: would someone do something differently after reading it? "20,000 loans" fails. A rate, a gap, or a cost implication passes.

**"My dashboard looks like everyone else's."** Open `MAKE_IT_YOURS.md`. The anti-sameness gate is not a vibe check; it is four concrete conditions.

---

## What comes next

**D3 — The Standing Report** is the Advanced rung: the same artifact, in front of a real user or organization for long enough that the numbers have to stay honest. D2 proves the page exists. D3 proves somebody needed it.

---

## License

MIT. The template is yours to modify. The work you do with it is yours.

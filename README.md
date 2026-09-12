# job-application-assistant

*[中文说明](README.zh-CN.md)*

A Claude / Codex skill for **personal** job hunting: find companies hiring for a role, vet them (financial health, legal disputes, employee reviews) before you apply, track every application in one place, and get help filling out application forms — with a human confirming every real submission.

This is a tool for one person managing their own job search, not a recruiting SaaS product. There's no server, no account, no cloud sync — everything lives in a local JSON file on your machine.

## What it looks like

**Application ledger** — every company you've applied to, current status, and a risk badge from due diligence, at a glance.

![Application dashboard](docs/dashboard-screenshot.png)

**Company due-diligence report** — legal/judicial risk, employee sentiment, and social-media mentions, compiled into one page before you decide whether to keep pursuing a role.

![Company background report](docs/company-report-screenshot.png)

Both pages are self-contained static HTML — no server, generated fresh from your own data every time you run the scripts.

## What it does

- **Find openings** — searches job aggregators for companies hiring for a given role, then prefers each company's own official careers page over the aggregator listing (`scripts/search_target_companies.py`, `scripts/find_career_page.py`).
- **Vet the company first** — pulls together public signal on financial health, legal disputes, and employee sentiment (知乎/企查查/天眼查/裁判文书网/看准网/小红书/抖音) into a sourced, balanced report before you invest time applying (`references/company_due_diligence.md`, `scripts/due_diligence_report.py`).
- **Fill application forms, carefully** — a Playwright-based helper that fills known ATS forms (Greenhouse, Lever, Workday, …), always in a *visible* browser window so you can solve any CAPTCHA yourself, and never submits without an explicit confirmation step (`scripts/ats_form_filler.py`).
- **Track everything locally** — a JSON-backed CLI tracker with duplicate detection, follow-up reminders, and a generated HTML dashboard (`scripts/track_applications.py`).

See [`SKILL.md`](SKILL.md) for the full step-by-step workflow this skill follows, and [`references/`](references/) for the design notes behind each piece (including which existing open-source auto-apply tools this borrowed patterns from, and deliberately did *not* borrow).

## Non-negotiable ground rules

- Never auto-submits an application without the user explicitly confirming that specific batch.
- Never attempts to solve or bypass a CAPTCHA — it stops and hands control back to you.
- Never fabricates resume experience or invents due-diligence findings; everything is sourced.
- Doesn't fire off applications in a tight, unattended loop — batches with review checkpoints instead.

## Install

This is packaged as a **Claude Skill** (`SKILL.md` + `scripts/` + `references/`). To use it:

1. In Claude (desktop or web), go to **Settings → Capabilities → Skills** and upload this folder (or the packaged `.skill` file, if you have one).
2. For Claude Code / Codex, drop this folder into your skills directory as documented by that tool.

### Python dependencies

The tracking and report scripts (`track_applications.py`, `due_diligence_report.py`) have **no dependencies** beyond the Python standard library.

The search and form-filling scripts need:

```bash
pip install -r requirements.txt
playwright install chromium   # only if you'll use ats_form_filler.py
```

## Quick start (CLI)

```bash
# Track an application
python scripts/track_applications.py add \
  --company "Acme Corp" --role "Frontend Engineer" \
  --channel official_site --url "https://acme.com/careers/123" \
  --status submitted

# Check you haven't already applied before starting a new one
python scripts/track_applications.py check --company "Acme Corp"

# See what needs following up on
python scripts/track_applications.py followups --days 7

# Attach a due-diligence report to a company
python scripts/due_diligence_report.py --input acme_findings.json \
  --out acme_report.html --format html
python scripts/track_applications.py diligence \
  --company "Acme Corp" --role "Frontend Engineer" \
  --risk medium --report acme_report.html --summary "1 labor dispute judgment"

# Generate the dashboard
python scripts/track_applications.py dashboard --out dashboard.html
```

Full command reference is in each script's `--help` and docstring.

## Disclaimer

This is a personal productivity tool, not legal, financial, or career advice. Due-diligence reports aggregate public information and social-media commentary — verify anything that actually matters (a specific lawsuit, a company's registration status) against the primary source before acting on it. You are responsible for complying with the terms of service of any site this tool interacts with.

## License

MIT — see [LICENSE](LICENSE).

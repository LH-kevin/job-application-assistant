# job-application-assistant

**A personal job-search AI Skill for Claude / Codex**

*[中文](README.md)*

<p align="center">
  <img src="docs/readme-hero.png" alt="job-application-assistant — a personal AI Skill for job hunting" width="100%">
</p>

> **In one sentence:** let AI help you **find target companies → vet them before applying → carefully assist with application forms → track every application**, while every real submission still requires your confirmation.

This is a **personal job-search** Skill for Claude / Codex, not a recruiting SaaS product.  
There is no server, no account system, and no cloud sync. Your application data stays in a local JSON file on your machine.

---

## Understand it in 30 seconds

### 1. Install the Skill in Claude / Codex

- **Claude (desktop / web):** go to `Settings → Capabilities → Skills`, then upload this project folder or a packaged `.skill` file.
- **Claude Code / Codex:** place this project in the skills directory used by that tool.

### 2. Tell it what kind of role you want

For example:

```text
Help me find companies hiring for AI Agent development roles.
Prefer each company's official careers page.
Before I apply, run company due diligence.
After I confirm, help me fill the application form
and add the application to my tracker.
```

### 3. The Skill moves the process forward

```text
Find openings
    ↓
Choose target companies
    ↓
Run company due diligence
    ↓
Decide whether to continue
    ↓
Assist with the application form
    ↓
You confirm the real submission
    ↓
Track the application + follow up
```

**Less repetitive copying, less manual research, and less scattered tracking.**

---

## What it helps you do

|  | Capability | What you get |
|---|---|---|
| 🔎 | **Find openings** | Search for companies hiring for a target role and prefer each company's **official careers page** |
| 🏢 | **Vet before you apply** | Collect public signals on financial health, legal/judicial risk, employee sentiment, and social-media commentary |
| 📝 | **Assist with ATS forms** | Help fill common ATS forms in a visible browser, including Greenhouse, Lever, and Workday |
| 📊 | **Track applications** | Keep company, role, channel, status, risk label, and follow-up information in one place |
| 🔁 | **Detect duplicates** | Check whether you have already applied to the same company |
| 🔒 | **Keep data local** | No account, no server, no cloud sync; your application records stay on your machine |

---

## What the output looks like

### Application ledger

See every application, current status, channel, last update, and due-diligence risk label at a glance.

<p align="center">
  <img src="docs/dashboard-screenshot.png" alt="Application dashboard" width="100%">
</p>

### Company due-diligence report

Before deciding whether to keep applying or interviewing, consolidate legal/judicial risk, employee sentiment, and public social-media commentary into one report.

<p align="center">
  <img src="docs/company-report-screenshot.png" alt="Company due-diligence report" width="78%">
</p>

Both pages are self-contained static HTML. No server is required, and the pages are regenerated from your own local data.

---

## Why this is not a one-click auto-apply tool

The project deliberately keeps **human confirmation** in the loop.

- **No automatic submission:** every real batch requires explicit confirmation.
- **No CAPTCHA bypass:** the workflow stops and hands control back to you.
- **No fabricated resume experience:** it does not invent facts to make you look more qualified.
- **No fabricated due-diligence findings:** findings must be sourced.
- **No unattended high-volume applying:** the workflow uses review checkpoints instead.

The goal is not to maximize application volume. The goal is to make your job search **more informed, controllable, and easier to follow through**.

---

## Install

The project is packaged as a **Claude Skill**:

```text
SKILL.md
scripts/
references/
```

### Claude

1. Open Claude.
2. Go to `Settings → Capabilities → Skills`.
3. Upload this project folder or a packaged `.skill` file.

### Claude Code / Codex

Place the project into the skills directory documented by the tool you use.

---

## Python dependencies

The tracking and report-generation scripts:

- `scripts/track_applications.py`
- `scripts/due_diligence_report.py`

use only the Python standard library.

The search and ATS form-assistance scripts require:

```bash
pip install -r requirements.txt
playwright install chromium
```

Chromium is only needed if you use `ats_form_filler.py`.

---

## Quick CLI demo

```bash
# Track an application
python scripts/track_applications.py add \
  --company "Acme Corp" --role "Frontend Engineer" \
  --channel official_site --url "https://acme.com/careers/123" \
  --status submitted

# Check whether you already applied
python scripts/track_applications.py check --company "Acme Corp"

# See applications that need follow-up
python scripts/track_applications.py followups --days 7

# Attach a due-diligence report
python scripts/due_diligence_report.py --input acme_findings.json \
  --out acme_report.html --format html

python scripts/track_applications.py diligence \
  --company "Acme Corp" --role "Frontend Engineer" \
  --risk medium --report acme_report.html --summary "1 labor dispute judgment"

# Generate the dashboard
python scripts/track_applications.py dashboard --out dashboard.html
```

See each script's `--help` output and docstring for the full command reference.

---

## Workflow and design notes

See [`SKILL.md`](SKILL.md) for the full step-by-step workflow.

See [`references/`](references/) for the design notes behind each module, including which open-source auto-apply patterns were studied and which ones were deliberately not adopted.

---

## Data and privacy

This is a **local-first personal job-search tool**:

- no server
- no account system
- no cloud sync
- application data stored in a local JSON file
- real submissions require human confirmation

---

## Disclaimer

This is a personal productivity tool, not legal, financial, or career advice.

Due-diligence reports aggregate public information and social-media commentary. Verify any information that materially affects your decision—such as a specific lawsuit or company registration status—against a primary or authoritative source before acting.

You are responsible for complying with the terms of service of any site this tool interacts with.

---

## License

MIT — see [LICENSE](LICENSE).

---

If this project improves your job-search workflow, consider giving it a **Star**, opening an **Issue**, or sharing your feedback.

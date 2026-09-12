---
name: job-application-assistant
description: Search for companies actively hiring for a user-specified job title/role, locate their official career pages, run a background/reputation check on companies of interest (financial health, legal/labor disputes, employee reviews across 知乎/企查查/天眼查/小红书/抖音 etc.), tailor resume/cover letter materials to each opening, and assist with filling out application forms on company websites (with human confirmation before final submission). Use this whenever the user asks to find job openings, search for hiring companies, apply for jobs on company websites, do a job search + apply workflow, mass-apply to positions, check out or vet a company before applying, or mentions "投简历", "找工作", "校招/社招", "海投", "官网投递", "背调", "公司靠谱吗", "员工评价", "劳动仲裁", "帮我投递简历给招xx的公司", even if they don't use the word "skill".
---

# Job Application Assistant

Automates the *research and preparation* side of a job search — finding companies
hiring for a role and getting application materials submission-ready — while
treating the actual "submit" click as a human-in-the-loop action, since it sends
data to a third-party system on the user's behalf.

## Non-negotiable ground rules

1. **Never auto-submit without explicit per-batch confirmation.** Fill the form,
   show the user what will be sent (company, role, resume version, cover letter),
   and only submit after they say go. Confirming once for a batch of N companies
   is fine if the user explicitly asks for that — but always show the list first.
2. **Prefer the company's own official career page over third-party job boards**
   when both exist — it's usually the more precise/authoritative application
   channel and less likely to be filtered by an aggregator's ATS noise.
3. **Never try to defeat CAPTCHAs, login walls, or anti-bot checks.** Stop and
   hand control back to the user (or a browser tool that pauses for it) when one
   appears.
4. **Respect volume.** Don't fire off dozens of applications back-to-back in a
   tight loop — this looks like spam to ATS anti-abuse systems and produces
   low-quality, unreviewed submissions. Batch in small groups (5–10) with review
   checkpoints.
5. **Never fabricate experience.** Tailoring a resume means re-ordering,
   re-emphasizing, and rewording *real* content to match a JD's keywords — not
   inventing skills or titles the user doesn't have.
6. **Due-diligence findings must be sourced and balanced.** When reporting
   on a company's reputation/legal risk, attribute claims to where they came
   from, weigh official records (裁判文书网, 国家企业信用信息公示系统) above
   single social-media posts, and don't present one-off complaints as
   settled fact — see `references/company_due_diligence.md`.

## Workflow

### Step 0 — Gather inputs
Ask (or infer from context) if missing:
- Target job title/role (required) — e.g. "前端工程师", "Product Manager"
- Location / remote preference
- Any must-have filters: industry, company size, seniority, salary floor
- Whether the user has a resume file already (docx/pdf) — if not, offer to help
  draft one first; a tailored resume needs a base to tailor from.

If ambiguous, pick sensible defaults and state them rather than blocking.

### Step 1 — Find companies + openings
Run `scripts/search_target_companies.py` (requires network — see script header)
or, if network tools/connectors are available in this session (web_search,
a job-board MCP connector), search directly:
- Query aggregator sources (LinkedIn Jobs, Indeed, 智联招聘/BOSS直聘/拉勾网 as
  regionally appropriate) for `<role> <location>` to build a candidate list of
  companies + specific posting URLs.
- De-duplicate by company.

Present the candidate list to the user before going further — let them cut
companies they're not interested in.

### Step 1.5 — Company due diligence (背调)
For each company the user wants to proceed with (or upfront for the whole
shortlist, if the user prefers), pull together public signal on financial
health, legal risk, and employee sentiment before spending time tailoring
materials for it. Follow `references/company_due_diligence.md` for the
per-source query templates (工商/裁判文书, 知乎, 看准网/脉脉, 小红书, 抖音)
and how to weigh official records vs. social commentary.

Run the searches with `web_search` (or an equivalent tool in this session),
compile the findings into the JSON shape documented in
`scripts/due_diligence_report.py`, then run it to produce a report — write
it into the **same output folder** you'll later put the applications
dashboard in, so the relative link between them works:

    python scripts/due_diligence_report.py --input <company>_findings.json \
        --out <company>_report.html --format html

Then attach a short risk summary to the tracker so it surfaces in the main
dashboard instead of sitting in a disconnected file:

    python scripts/track_applications.py diligence \
        --company "<company>" --role "<role>" \
        --risk low|medium|high --report <company>_report.html \
        --summary "<one-line summary>"

`diligence` creates a minimal tracker record if one doesn't exist yet —
useful for vetting a company before deciding whether to even apply. The
dashboard (`track_applications.py dashboard`) then shows a 背调 risk badge
per row with a link straight to the full report, plus a "高风险公司" count
in the summary cards — so the two views (all applications, and how risky
each company looked) live side by side without merging into one bloated
file.

Surface any red flags (劳动仲裁记录, 失信被执行人, repeated/corroborated
complaints about unpaid wages or excessive overtime) prominently and let the
user decide whether to still apply — don't silently filter companies out,
and don't state unverified social-media claims as settled fact.

### Step 2 — Find each company's official career page
For each approved company, run `scripts/find_career_page.py <company_name>`
to locate `careers.<company>.com` / `<company>.com/careers` / `/jobs` style
pages, distinguishing it from the aggregator listing found in Step 1.
Fall back to the aggregator listing only if no official page is found.

### Step 3 — Tailor materials per company
Before starting a new company, run
`scripts/track_applications.py check --company "<name>"` — if there's
already a record, show the user its status instead of duplicating work
(mirrors how established auto-apply tools skip already-applied companies).

For each opening:
- Read the JD (fetch the posting page).
- If the docx skill is available and the user wants a Word resume, use it to
  produce a tailored version (see `/mnt/skills/public/docx/SKILL.md`) —
  reorder bullet points and adjust the summary to mirror the JD's key
  requirements/keywords, using only the user's real experience.
- Keep a base resume version untouched; tailored copies go in per-company
  files so the user can compare.

### Step 4 — Fill the application form
- Identify the ATS platform behind the career page using
  `references/ats_platforms.md` (Greenhouse/Lever/Workday/SmartRecruiters/
  iCIMS/自建系统 all have recognizable URL or DOM fingerprints).
- If a browser automation tool is available in this session (e.g. a connected
  browsing MCP), use it to open the form and fill the known fields (name,
  email, phone, resume upload, cover letter, standard EEO/optional questions)
  using `scripts/ats_form_filler.py` as a reference for field-mapping per ATS.
- If running `scripts/ats_form_filler.py` directly, always let it run with a
  **visible** browser (its default) — never pass `--headless` unless you're
  sure the form has no bot-check. Headless hides any CAPTCHA from the user
  entirely, which just looks like the script hanging. The script detects
  common CAPTCHA/challenge markers and pauses at the terminal for the user
  to solve it by hand in the visible window; it never tries to bypass one.
- If no browser tool is available, fill and describe the form fields inline
  and hand the user a checklist + direct link to finish manually.
- **Stop before clicking submit.** Show the filled summary and wait for
  explicit "submit" / "投递" confirmation from the user. Only then re-run
  with `--confirm-submit`.

### Step 5 — Track results
After each confirmed submission (or manual completion), log it with
`scripts/track_applications.py add` — company, role, date, channel (official
site / aggregator), ATS, status, link, notes. This becomes the running
record the user can query later:
- `list [--status ...]` — filtered raw list
- `stats` — totals by status/channel, this-week count
- `followups --days N` — submitted applications stale for N+ days, good
  candidates for a polite check-in message
- `dashboard --out dashboard.html` — self-contained HTML dashboard (summary
  cards + status breakdown + full table, with a 背调 risk badge/link per row
  if due-diligence info was attached in Step 1.5) the user can open in a
  browser; use this whenever they ask to "整理/查看/汇总投递数据" or want an
  overview rather than a raw list
- `export --out applications.csv` — for opening in Excel/Google Sheets

See `references/similar_projects.md` for the prior art these tracker
features and the confirm-before-submit / CAPTCHA-handling design were
checked against.

## Reference files
- `references/ats_platforms.md` — how to recognize each major ATS and what
  fields it typically exposes, for building selector-based automation.
- `scripts/search_target_companies.py` — network search helper (needs an
  environment with internet access; will no-op with a clear error otherwise).
- `scripts/find_career_page.py` — heuristics for finding the *official*
  careers page vs. an aggregator mirror.
- `scripts/ats_form_filler.py` — Playwright-based template for filling common
  ATS forms; requires `playwright` installed and a real browser context, and
  always pauses before the final submit action.
- `scripts/track_applications.py` — CSV/JSON application tracker with
  duplicate-detection, stats, follow-up reminders, and an HTML dashboard.
- `scripts/due_diligence_report.py` — turns compiled company-background
  findings into a shareable Markdown/HTML report (basic info, legal risk,
  employee/social sentiment, red flags).
- `references/company_due_diligence.md` — per-source search-query templates
  (知乎/企查查/天眼查/裁判文书网/看准网/小红书/抖音) and how to weigh and
  present what comes back.
- `references/similar_projects.md` — survey of comparable open-source
  projects and what this skill deliberately borrowed vs. avoided from them.

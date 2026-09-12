# Similar Open-Source Projects — What We Borrowed

A quick survey of existing GitHub projects in this space, and which ideas
made it into this skill (in our own words/implementation — no code copied).

## Auto_job_applier_linkedIn (GodsScion, ~2.8k stars)
https://github.com/GodsScion/Auto_job_applier_linkedIn

- **Pause-before-submit as a first-class setting** — confirms our own
  "never auto-submit without confirmation" rule is a common, expected
  pattern in this space, not an unusual restriction.
- **`safe_mode` / `click_interval`** — randomized delay between actions to
  avoid looking like a bot and to avoid overwhelming a site. → adopted as
  the "batch in small groups (5–10) with review checkpoints" rule in
  SKILL.md; `ats_form_filler.py` should add explicit delays if you extend
  it to handle multiple applications in one run.
- **Skip already-applied / blacklisted companies** — before filling a new
  application, check whether you've already got a record for that company.
  → adopted as the new `track_applications.py check --company` subcommand;
  wire it into Step 4 of the workflow before opening a new form.
- **Local-only data, no cloud upload** — matches our tracker's design
  (plain JSON on disk, CSV/HTML export, nothing sent anywhere).
- **A dedicated "Applied Jobs history" view in a local control panel** →
  adopted as `track_applications.py dashboard`, which generates a
  self-contained HTML page (summary cards + status bar chart + full table)
  instead of a running Flask app, to keep this skill dependency-light.

## simonfong6/auto-apply
https://github.com/simonfong6/auto-apply

- Confirms Greenhouse/Lever/Workday/Jobvite as the right set of major ATS
  platforms to target first — matches `references/ats_platforms.md`.

## Pickle-Pixel/ApplyPilot
https://github.com/Pickle-Pixel/ApplyPilot

- **Explicit "stages 1–5 only" mode**: discover → score-against-resume →
  tailor resume → write cover letter → fill form, with submission left as
  a manual last step. This is essentially the mode we default to; treat
  full autonomous submission as something only offered when the user
  explicitly asks for a batch to go all the way through, and even then
  always with the review checkpoint from Step 4 of SKILL.md.
- **"Never fabricates" experience when tailoring a resume** — same
  constraint we already state under "Non-negotiable ground rules".

## Commercial "Job Application Tracker" spreadsheet templates (Gumroad/Etsy)
Many independent listings converge on the same shape, which is a useful
signal for what a tracker needs regardless of implementation:

- Dashboard summary (totals, by status, by channel/source, by week)
- Duplicate detection when logging a job you may have already tracked
- Follow-up reminders based on days-since-last-update
- A separate notes/company-research field

All four are now in `track_applications.py` (`stats`, `add`'s duplicate
warning, `followups`, and the `--notes` field respectively).

## What we deliberately did NOT borrow
- Fully unattended multi-hundred-application "spray and pray" runs (some
  tools advertise "apply to 100+ jobs in under an hour"). This conflicts
  with our accuracy/quality and anti-spam principles — see SKILL.md's
  ground rules. Low-quality, unreviewed applications also just perform
  worse for the user.
- CAPTCHA-solving services/bypass techniques that some auto-apply tools
  integrate. We stop and hand control back to a human instead — see the
  CAPTCHA handling in `ats_form_filler.py`.

#!/usr/bin/env python3
"""
track_applications.py

Local tracker for job applications — no network required. Stores records in
a JSON file (default: ./applications.json). No cloud upload, no account
needed: everything stays on the user's machine (same privacy stance as most
open-source job-apply tools — see references/similar_projects.md).

Usage:
    # Add/update a record (adding an existing company+role updates it and
    # warns you it's a duplicate, so you don't double-apply by accident)
    python track_applications.py add \
        --company "Acme Corp" --role "Frontend Engineer" \
        --channel official_site --ats greenhouse \
        --url "https://boards.greenhouse.io/acme/jobs/12345" \
        --status submitted

    # List everything / filter by status
    python track_applications.py list
    python track_applications.py list --status pending

    # Quick summary counts (by status / channel / this week)
    python track_applications.py stats

    # Which submitted applications have had no status change in N days
    # (a candidate for a follow-up email)
    python track_applications.py followups --days 10

    # Self-contained HTML dashboard you can open in a browser
    python track_applications.py dashboard --out dashboard.html

    # Export to CSV (e.g. to import into Google Sheets/Excel)
    python track_applications.py export --out applications.csv

    # Check before applying whether you already have a record for a company
    # (mirrors the "skip already-applied companies" pattern from
    # Auto_job_applier_linkedIn)
    python track_applications.py check --company "Acme Corp"

    # Attach a due-diligence finding (from due_diligence_report.py) to a
    # company's record so it shows up as a risk badge + link in the
    # dashboard, instead of living in a separate, disconnected file
    python track_applications.py diligence \
        --company "Acme Corp" --role "Frontend Engineer" \
        --risk medium --report acme_report.html \
        --summary "1起劳动仲裁判决，知乎评价偏负面，小红书入职体验尚可"
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta

DB_PATH_DEFAULT = "applications.json"

STATUS_ORDER = ["pending", "filled", "submitted", "interview", "offer", "rejected"]

# Design tokens — sourced directly from the approved HTML demo
# (page-a-applications.html / page-b-company-report.html). These are now
# the visual source of truth; see SKILL.md / this file's cmd_dashboard()
# docstring for the design brief.
BG = "#F2F2EF"
PANEL = "#F8F8F5"
INK = "#161616"
MUTED = "#6F706B"
LINE = "#CBCBC5"
LINE_STRONG = "#AFAFA8"
GREEN = "#315C47"
GREEN_SOFT = "#DDE7E0"
RED = "#B94335"
RED_SOFT = "#F1DEDA"
AMBER = "#9B6B20"
AMBER_SOFT = "#EEE4CF"
BLUE = "#34506E"
BLUE_SOFT = "#DEE6ED"
MONO = '"Cascadia Code","SFMono-Regular",Consolas,"Liberation Mono",monospace'
SANS = 'Inter,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif'

STATUS_COLORS = {
    "pending": MUTED,
    "filled": BLUE,
    "submitted": GREEN,
    "interview": BLUE,
    "offer": GREEN,
    "rejected": "#777777",
}
STATUS_LABEL_ZH = {
    "pending": "待处理",
    "filled": "已填表",
    "submitted": "已投递",
    "interview": "面试中",
    "offer": "已获Offer",
    "rejected": "已拒绝",
}
RISK_COLORS = {"low": GREEN, "medium": AMBER, "high": RED}
RISK_SOFT = {"low": GREEN_SOFT, "medium": AMBER_SOFT, "high": RED_SOFT}
RISK_LABEL_ZH = {"low": "低风险", "medium": "中风险", "high": "高风险"}
RISK_LABEL_EN = {"low": "LOW", "medium": "MED", "high": "HIGH"}


def load_db(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(path: str, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _key(company: str, role: str) -> tuple[str, str]:
    return (company.strip().lower(), role.strip().lower())


def cmd_add(args):
    records = load_db(args.db)
    key_fields = _key(args.company, args.role)
    for r in records:
        if _key(r["company"], r["role"]) == key_fields:
            print(
                f"⚠️  Duplicate: you already have a record for "
                f"{r['company']} / {r['role']} (current status: {r.get('status')})."
                f" Updating it instead of creating a new one."
            )
            r.update(
                {
                    "channel": args.channel or r.get("channel"),
                    "ats": args.ats or r.get("ats"),
                    "url": args.url or r.get("url"),
                    "status": args.status or r.get("status"),
                    "notes": args.notes or r.get("notes", ""),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            save_db(args.db, records)
            print(f"Updated existing record for {args.company} / {args.role}")
            return

    now = datetime.now(timezone.utc).isoformat()
    records.append(
        {
            "company": args.company,
            "role": args.role,
            "channel": args.channel,
            "ats": args.ats,
            "url": args.url,
            "status": args.status or "pending",
            "notes": args.notes,
            "created_at": now,
            "updated_at": now,
        }
    )
    save_db(args.db, records)
    print(f"Added record for {args.company} / {args.role}")


def cmd_check(args):
    """Look up whether a company already has a record — call this before
    starting a new application to avoid re-applying to the same company."""
    records = load_db(args.db)
    matches = [
        r for r in records if args.company.strip().lower() in r["company"].strip().lower()
    ]
    if not matches:
        print(f"No existing record for '{args.company}' — clear to apply.")
        return
    print(f"Found {len(matches)} existing record(s) for '{args.company}':")
    for r in matches:
        print(f"  - {r['role']}  [{r.get('status')}]  {r.get('url','')}")


def cmd_diligence(args):
    """Attach a due-diligence summary (produced by due_diligence_report.py)
    to an existing company/role record so the dashboard can show a risk
    badge + link instead of leaving the report as a disconnected file. If
    no matching record exists yet, creates a minimal one — useful when
    you're vetting a company before deciding to apply at all."""
    records = load_db(args.db)
    key_fields = _key(args.company, args.role)
    now = datetime.now(timezone.utc).isoformat()
    due_diligence = {
        "risk": args.risk,
        "report": args.report,
        "summary": args.summary,
        "checked_at": now,
    }
    for r in records:
        if _key(r["company"], r["role"]) == key_fields:
            r["due_diligence"] = due_diligence
            r["updated_at"] = now
            save_db(args.db, records)
            print(f"Attached due-diligence info to {args.company} / {args.role}")
            return

    records.append(
        {
            "company": args.company,
            "role": args.role,
            "channel": "",
            "ats": "",
            "url": "",
            "status": "pending",
            "notes": "",
            "created_at": now,
            "updated_at": now,
            "due_diligence": due_diligence,
        }
    )
    save_db(args.db, records)
    print(
        f"No existing record for {args.company} / {args.role} — created one "
        f"with the due-diligence info attached."
    )


def cmd_list(args):
    records = load_db(args.db)
    if args.status:
        records = [r for r in records if r.get("status") == args.status]
    if not records:
        print("No matching records.")
        return
    for r in records:
        print(
            f"- [{r.get('status','?'):10}] {r['company']:<25} {r['role']:<30} "
            f"({r.get('channel','?')}/{r.get('ats','-')})  {r.get('url','')}"
        )


def cmd_stats(args):
    records = load_db(args.db)
    if not records:
        print("No records yet.")
        return

    total = len(records)
    by_status = Counter(r.get("status", "unknown") for r in records)
    by_channel = Counter(r.get("channel", "unknown") or "unknown" for r in records)

    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    this_week = sum(
        1
        for r in records
        if _parse_dt(r.get("created_at")) and _parse_dt(r.get("created_at")) >= one_week_ago
    )

    print(f"Total applications tracked: {total}")
    print(f"Added in the last 7 days:   {this_week}")
    print("\nBy status:")
    for status in STATUS_ORDER:
        if by_status.get(status):
            print(f"  {status:10} {by_status[status]}")
    for status, count in by_status.items():
        if status not in STATUS_ORDER:
            print(f"  {status:10} {count}")
    print("\nBy channel:")
    for channel, count in by_channel.most_common():
        print(f"  {channel:15} {count}")


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _stale_submitted(records, days):
    """Shared by cmd_followups (CLI) and cmd_dashboard (follow-up notice bar)
    so the "needs a follow-up" rule lives in exactly one place."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stale = []
    for r in records:
        if r.get("status") != "submitted":
            continue
        updated = _parse_dt(r.get("updated_at"))
        if updated and updated <= cutoff:
            days_ago = (datetime.now(timezone.utc) - updated).days
            stale.append((days_ago, r))
    stale.sort(reverse=True)
    return stale


def cmd_followups(args):
    """Applications in 'submitted' status that haven't been updated in
    --days days — good candidates for a polite follow-up message."""
    records = load_db(args.db)
    stale = _stale_submitted(records, args.days)
    if not stale:
        print(f"No submitted applications older than {args.days} days without an update.")
        return
    print(f"Applications with no update for {args.days}+ days (follow-up candidates):")
    for days_ago, r in stale:
        print(f"  - {r['company']} / {r['role']}  ({days_ago} days ago)  {r.get('url','')}")


def cmd_export(args):
    records = load_db(args.db)
    if not records:
        print("Nothing to export.")
        return
    fields = [
        "company",
        "role",
        "channel",
        "ats",
        "url",
        "status",
        "notes",
        "created_at",
        "updated_at",
    ]
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in fields})
    print(f"Exported {len(records)} records to {args.out}")


def cmd_dashboard(args):
    """Self-contained HTML dashboard — "Personal Job Ops Console" visual
    direction (approved HTML demo: page-a-applications.html). Industrial/
    terminal feel: horizontal metric strip (not KPI cards), dense scannable
    rows, monospace for numbers/labels, hairline borders only. No JS
    framework, no network calls — open directly in a browser.

    Data contract is unchanged from the previous version — this function
    only changes how the same `records` are rendered.
    """
    records = load_db(args.db)
    total = len(records)
    by_status = Counter(r.get("status", "unknown") for r in records)
    high_risk = sum(
        1 for r in records if (r.get("due_diligence") or {}).get("risk") == "high"
    )
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    this_week = sum(
        1 for r in records
        if _parse_dt(r.get("created_at")) and _parse_dt(r.get("created_at")) >= one_week_ago
    )
    followups = _stale_submitted(records, 7)

    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def fmt_date(iso):
        dt = _parse_dt(iso)
        return dt.strftime("%Y.%m.%d") if dt else "—"

    def metric(value, label, extra_class="", delta=""):
        delta_html = f'<div class="delta">{esc(delta)}</div>' if delta else ""
        return (
            f'<div class="metric {extra_class}"><div class="value">{value:02d}</div>'
            f'<div class="label">{esc(label)}</div>{delta_html}</div>'
        )

    metrics_html = (
        metric(total, "总投递数 / ALL APPLICATIONS", "primary", f"+{this_week} THIS WEEK" if this_week else "")
        + metric(by_status.get("pending", 0), "待处理")
        + metric(by_status.get("submitted", 0), "已投递")
        + metric(by_status.get("interview", 0), "面试中")
        + metric(by_status.get("offer", 0), "已获 Offer")
        + metric(by_status.get("rejected", 0), "已拒绝")
        + metric(this_week, "本周新增")
        + metric(high_risk, "高风险公司", "risk")
    )

    notice_html = ""
    if followups:
        notice_html = (
            '<div class="notice"><div><strong>FOLLOW-UP SIGNAL</strong>　'
            f'有 <strong>{len(followups)}</strong> 个岗位超过 7 天没有更新，'
            "建议今天检查是否需要跟进。</div>"
            '<div class="hint">RULE / NO UPDATE ≥ 7 DAYS</div></div>'
        )

    def row_html(r):
        status = r.get("status", "pending")
        status_label = STATUS_LABEL_ZH.get(status, status)
        status_css = {
            "pending": "pending", "submitted": "applied", "interview": "interview",
            "offer": "offer", "rejected": "rejected", "filled": "pending",
        }.get(status, "pending")

        dd = r.get("due_diligence")
        if dd and dd.get("risk") in RISK_COLORS:
            risk = dd["risk"]
            title_attr = f' title="{esc(dd.get("summary",""))}"' if dd.get("summary") else ""
            risk_html = f'<span class="risk {risk}"{title_attr}>{RISK_LABEL_EN[risk]}</span>'
        else:
            risk_html = '<span class="risk none">—</span>'

        report = (dd or {}).get("report")
        report_link = (
            f'<a class="icon-link" href="{esc(report)}" target="_blank" title="背调报告">R</a>'
            if report else ""
        )
        job_link = (
            f'<a class="icon-link" href="{esc(r.get("url",""))}" target="_blank" title="职位链接">↗</a>'
            if r.get("url") else ""
        )

        return f'''<article class="row">
      <div class="cell"><span class="status {status_css}"><span class="dot"></span>{status_label}</span></div>
      <div class="cell"><div class="company">{esc(r["company"])}</div><div class="role">{esc(r["role"])}</div></div>
      <div class="cell channel">{esc(r.get("channel","") or "—")}</div>
      <div class="cell">{risk_html}</div>
      <div class="cell date created">{fmt_date(r.get("created_at"))}</div>
      <div class="cell date">{fmt_date(r.get("updated_at"))}</div>
      <div class="cell links">{job_link}{report_link}</div>
    </article>'''

    ordered = sorted(records, key=lambda r: r.get("updated_at", ""), reverse=True)
    rows_html = "\n".join(row_html(r) for r in ordered)
    body_html = (
        rows_html if records
        else '<p class="empty">还没有记录。用 <code>track_applications.py add</code> 添加第一条投递。</p>'
    )

    year, week, _ = datetime.now().isocalendar()

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>投递记录看板</title>
<style>
:root{{
  --bg:{BG}; --panel:{PANEL}; --ink:{INK}; --muted:{MUTED};
  --line:{LINE}; --line-strong:{LINE_STRONG};
  --green:{GREEN}; --green-soft:{GREEN_SOFT};
  --red:{RED}; --red-soft:{RED_SOFT};
  --amber:{AMBER}; --amber-soft:{AMBER_SOFT};
  --blue:{BLUE}; --blue-soft:{BLUE_SOFT};
  --mono:{MONO}; --sans:{SANS};
}}
*{{box-sizing:border-box}}
html{{background:var(--bg);color:var(--ink);font-family:var(--sans)}}
body{{margin:0;min-height:100vh;background:var(--bg)}}
a{{color:inherit;text-decoration:none}}
code{{font-family:var(--mono)}}
.shell{{max-width:1440px;margin:0 auto;padding:30px 34px 54px}}
.topbar{{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;border-bottom:1px solid var(--line-strong);padding-bottom:18px}}
.eyebrow{{font:700 11px/1.2 var(--mono);letter-spacing:.14em;color:var(--muted);text-transform:uppercase}}
h1{{font-size:34px;line-height:1.05;letter-spacing:-.035em;margin:9px 0 0;font-weight:700}}
.top-meta{{text-align:right;font:600 12px/1.5 var(--mono);color:var(--muted)}}
.metrics{{display:grid;grid-template-columns:1.4fr repeat(7,minmax(96px,1fr));border-bottom:1px solid var(--line-strong)}}
.metric{{min-height:112px;padding:22px 18px;border-right:1px solid var(--line)}}
.metric:first-child{{padding-left:0}}.metric:last-child{{border-right:0}}
.metric .value{{font:700 31px/1 var(--mono);letter-spacing:-.04em}}
.metric.primary .value{{font-size:48px}}
.metric .label{{font-size:12px;color:var(--muted);margin-top:10px}}
.metric .delta{{font:700 11px/1.3 var(--mono);margin-top:8px;color:var(--green)}}
.metric.risk .value{{color:var(--red)}}
.notice{{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:14px 0;border-bottom:1px solid var(--line);font-size:13px}}
.notice strong{{font-weight:700}}
.notice .hint{{font:600 11px/1.4 var(--mono);color:var(--muted)}}
.list-head{{display:grid;grid-template-columns:110px 1.7fr 1.1fr 100px 100px 130px 92px;padding:14px 0 10px;border-bottom:1px solid var(--line-strong);font:700 10px/1.2 var(--mono);letter-spacing:.09em;color:var(--muted);text-transform:uppercase}}
.row{{display:grid;grid-template-columns:110px 1.7fr 1.1fr 100px 100px 130px 92px;align-items:center;min-height:86px;border-bottom:1px solid var(--line);position:relative;transition:.16s ease}}
.row:hover{{background:#EDEDE8;box-shadow:inset 3px 0 0 var(--ink)}}
.cell{{padding:14px 12px 14px 0;min-width:0}}
.company{{font-weight:720;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.role{{font-size:12px;color:var(--muted);margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.status{{display:inline-flex;align-items:center;gap:7px;font:700 11px/1 var(--mono);white-space:nowrap}}
.dot{{width:7px;height:7px;border:1px solid currentColor;border-radius:50%}}
.status.interview{{color:var(--blue)}}.status.applied{{color:var(--green)}}
.status.pending{{color:var(--muted)}}.status.offer{{color:var(--green)}}.status.rejected{{color:#777}}
.risk{{display:inline-block;padding:5px 7px;border:1px solid currentColor;font:700 10px/1 var(--mono);letter-spacing:.04em}}
.risk.high{{color:var(--red);background:var(--red-soft)}}
.risk.medium{{color:var(--amber);background:var(--amber-soft)}}
.risk.low{{color:var(--green);background:var(--green-soft)}}
.risk.none{{color:var(--muted);background:transparent}}
.channel{{font-size:12px}}
.date{{font:600 11px/1.3 var(--mono);color:var(--muted)}}
.links{{display:flex;justify-content:flex-end;gap:7px}}
.icon-link{{width:30px;height:30px;border:1px solid var(--line-strong);display:grid;place-items:center;font:700 12px/1 var(--mono)}}
.icon-link:hover{{border-color:var(--ink);background:var(--ink);color:#fff}}
.empty{{padding:40px 0;color:var(--muted);font-size:13px}}
.footer{{display:flex;justify-content:space-between;gap:20px;padding-top:18px;font:600 10px/1.5 var(--mono);color:var(--muted)}}
@media (max-width:1100px){{
  .metrics{{grid-template-columns:repeat(4,1fr)}}
  .metric:first-child{{padding-left:18px}}
  .metric{{border-bottom:1px solid var(--line)}}
  .list-head{{display:none}}
  .row{{grid-template-columns:100px 1.5fr 1fr 90px 90px 92px}}
  .row .created{{display:none}}
}}
@media (max-width:760px){{
  .shell{{padding:22px 16px 40px}}
  .topbar{{flex-direction:column}}
  .top-meta{{text-align:left}}
  .metrics{{grid-template-columns:repeat(2,1fr)}}
  .metric.primary .value{{font-size:40px}}
  .notice{{align-items:flex-start;flex-direction:column}}
  .row{{display:grid;grid-template-columns:1fr 84px;gap:0;padding:12px 0}}
  .row .cell{{padding:5px 10px 5px 0}}
  .row .cell:nth-child(1){{grid-column:1/2}}
  .row .cell:nth-child(2){{grid-column:1/2}}
  .row .cell:nth-child(3){{grid-column:1/2}}
  .row .cell:nth-child(4),.row .cell:nth-child(5),.row .cell:nth-child(6){{display:none}}
  .row .links{{grid-column:2/3;grid-row:1/4;align-self:center}}
  .footer{{flex-direction:column}}
}}
</style>
</head>
<body>
<main class="shell">
  <header class="topbar">
    <div>
      <div class="eyebrow">Job Application Assistant / Personal Job Ops</div>
      <h1>投递记录看板</h1>
    </div>
    <div class="top-meta">
      {year} / WEEK {week:02d}<br>生成时间 {datetime.now().strftime('%m.%d · %H:%M')}
    </div>
  </header>

  <section class="metrics" aria-label="投递概览">
    {metrics_html}
  </section>

  {notice_html}

  <section>
    <div class="list-head">
      <div>STATUS</div><div>COMPANY / ROLE</div><div>CHANNEL</div><div>RISK</div><div>CREATED</div><div>UPDATED</div><div style="text-align:right">LINKS</div>
    </div>
    {body_html}
  </section>

  <footer class="footer">
    <span>PERSONAL USE ONLY · APPLICATION LEDGER</span>
    <span>{total} RECORDS · 数据仅保存在本地，不上传任何服务器</span>
  </footer>
</main>
</body>
</html>"""

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard written to {args.out} — open it in a browser.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DB_PATH_DEFAULT, help="Path to JSON store")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("--company", required=True)
    p_add.add_argument("--role", required=True)
    p_add.add_argument("--channel", default="", help="official_site | aggregator")
    p_add.add_argument("--ats", default="")
    p_add.add_argument("--url", default="")
    p_add.add_argument("--notes", default="")
    p_add.add_argument(
        "--status", default="pending", help="pending|filled|submitted|interview|offer|rejected"
    )
    p_add.set_defaults(func=cmd_add)

    p_check = sub.add_parser("check", help="Check if a company already has a record before applying")
    p_check.add_argument("--company", required=True)
    p_check.set_defaults(func=cmd_check)

    p_diligence = sub.add_parser(
        "diligence", help="Attach a due-diligence risk summary + report link to a record"
    )
    p_diligence.add_argument("--company", required=True)
    p_diligence.add_argument("--role", required=True)
    p_diligence.add_argument(
        "--risk", required=True, choices=["low", "medium", "high"], help="Overall risk level"
    )
    p_diligence.add_argument(
        "--report", default="", help="Path to the report file from due_diligence_report.py "
        "(relative to the dashboard's output folder, so the link works when opened)"
    )
    p_diligence.add_argument("--summary", default="", help="One-line summary shown as a tooltip")
    p_diligence.set_defaults(func=cmd_diligence)

    p_list = sub.add_parser("list")
    p_list.add_argument("--status", default="")
    p_list.set_defaults(func=cmd_list)

    p_stats = sub.add_parser("stats", help="Summary counts by status/channel/this week")
    p_stats.set_defaults(func=cmd_stats)

    p_followups = sub.add_parser("followups", help="Submitted applications with no update in N days")
    p_followups.add_argument("--days", type=int, default=10)
    p_followups.set_defaults(func=cmd_followups)

    p_dashboard = sub.add_parser("dashboard", help="Generate a self-contained HTML dashboard")
    p_dashboard.add_argument("--out", default="dashboard.html")
    p_dashboard.set_defaults(func=cmd_dashboard)

    p_export = sub.add_parser("export")
    p_export.add_argument("--out", default="applications.csv")
    p_export.set_defaults(func=cmd_export)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

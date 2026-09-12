#!/usr/bin/env python3
"""
due_diligence_report.py

Render a structured company due-diligence report (Markdown or HTML) from
findings JSON. This script does NOT search the web itself — see
references/company_due_diligence.md for the query templates. The calling
agent should run those searches (via web_search or similar), compile what
it finds into the JSON shape below, then call this script to produce a
clean, shareable report.

No network required here — purely local formatting, so it works in any
sandbox including ones without internet access.

Input JSON shape (all fields optional except "company"):
{
  "company": "Acme Corp",
  "role": "Frontend Engineer",                 // optional, ties it to a specific opening
  "risk": "medium",                             // optional: low|medium|high — shown as a
                                                 // stamp on the report; keep this in sync
                                                 // with the --risk you pass to
                                                 // track_applications.py diligence
  "basic_info": {
    "founded": "2015",
    "registered_capital": "5000万人民币",
    "legal_rep": "张三",
    "funding_stage": "C轮",
    "source": "企查查/天眼查"
  },
  "legal_risks": [
    {"type": "劳动争议判决", "summary": "2023年因未足额支付加班费被判赔偿",
     "source": "中国裁判文书网", "url": "https://...", "date": "2023-06"}
  ],
  "employee_reviews": [
    {"platform": "知乎", "sentiment": "negative",
     "summary": "多位回答提到加班较多，管理层沟通不畅", "url": "https://..."}
  ],
  "social_mentions": [
    {"platform": "小红书", "sentiment": "positive",
     "summary": "多篇入职体验贴反馈团队氛围不错", "url": "https://..."}
  ],
  "red_flags": ["近一年有2起劳动仲裁判决", "股权结构半年内变更3次"],
  "overall_notes": "整体口碑中性偏负面，建议面试时重点确认加班与薪酬发放节奏。"
}

Usage:
    python due_diligence_report.py --input acme_findings.json --out acme_report.md
    python due_diligence_report.py --input acme_findings.json --out acme_report.html --format html
"""
import argparse
import json
import re
import sys
from datetime import datetime

SENTIMENT_LABEL = {
    "positive": "正面 🟢",
    "negative": "负面 🔴",
    "neutral": "中性 ⚪",
}


def load_findings(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_markdown(data: dict) -> str:
    company = data.get("company", "未知公司")
    role = data.get("role", "")
    lines = [f"# {company} 背调报告", ""]
    if role:
        lines.append(f"_关联岗位：{role}_")
    lines.append(f"_生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    lines.append("")
    lines.append(
        "> 本报告基于公开信息（工商登记、裁判文书、社交媒体讨论）整理，"
        "仅供参考，不构成法律或财务建议；社交媒体评价为个人观点，"
        "请结合来源权威性自行判断。"
    )
    lines.append("")

    red_flags = data.get("red_flags", [])
    if red_flags:
        lines.append("## ⚠️ 重点风险提示")
        for flag in red_flags:
            lines.append(f"- {flag}")
        lines.append("")

    basic = data.get("basic_info", {})
    if basic:
        lines.append("## 基本信息")
        for key, label in [
            ("founded", "成立时间"),
            ("registered_capital", "注册资本"),
            ("legal_rep", "法定代表人"),
            ("funding_stage", "融资阶段"),
        ]:
            if basic.get(key):
                lines.append(f"- **{label}**：{basic[key]}")
        if basic.get("source"):
            lines.append(f"- _数据来源：{basic['source']}_")
        lines.append("")

    legal = data.get("legal_risks", [])
    if legal:
        lines.append("## 法律 / 司法风险")
        for item in legal:
            date = f"（{item['date']}）" if item.get("date") else ""
            lines.append(f"- **{item.get('type','')}**{date}：{item.get('summary','')}")
            if item.get("source") or item.get("url"):
                src = item.get("source", "")
                url = item.get("url", "")
                lines.append(f"  - 来源：{src} {url}".strip())
        lines.append("")
    else:
        lines.append("## 法律 / 司法风险")
        lines.append("未检索到明显司法风险记录（不代表不存在，建议自行到国家企业信用信息公示系统核实）。")
        lines.append("")

    reviews = data.get("employee_reviews", [])
    if reviews:
        lines.append("## 员工口碑")
        for item in reviews:
            sentiment = SENTIMENT_LABEL.get(item.get("sentiment", "neutral"), "")
            lines.append(f"- [{item.get('platform','')}] {sentiment} {item.get('summary','')}")
            if item.get("url"):
                lines.append(f"  - {item['url']}")
        lines.append("")

    social = data.get("social_mentions", [])
    if social:
        lines.append("## 社交媒体口碑（小红书/抖音等）")
        lines.append("_注意甄别官方营销内容与真实员工/用户反馈。_")
        for item in social:
            sentiment = SENTIMENT_LABEL.get(item.get("sentiment", "neutral"), "")
            lines.append(f"- [{item.get('platform','')}] {sentiment} {item.get('summary','')}")
            if item.get("url"):
                lines.append(f"  - {item['url']}")
        lines.append("")

    notes = data.get("overall_notes")
    if notes:
        lines.append("## 综合建议")
        lines.append(notes)
        lines.append("")

    return "\n".join(lines)


def render_html(data: dict) -> str:
    """Rendered as an "Editorial Intelligence" report — approved HTML demo:
    page-b-company-report.html. Serif display type, a prominent risk hero
    (not a small badge), numbered evidence sections, a closing verdict
    block. Same underlying `data` contract as before — only the rendering
    changed."""
    INK, MUTED, LINE, LINE_STRONG = "#101010", "#6E6E68", "#D5D4CE", "#AFAEA7"
    PAPER, PAGE_BG = "#FAFAF7", "#EDEDE9"
    RED, RED_SOFT, GREEN = "#B94335", "#F1DEDA", "#315C47"
    AMBER = "#8B6C1A"
    MONO = '"Cascadia Code","SFMono-Regular",Consolas,"Liberation Mono",monospace'
    SANS = 'Inter,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif'
    SERIF = '"Noto Serif SC","Source Han Serif SC","Songti SC",Georgia,serif'

    RISK_COLORS = {"low": GREEN, "medium": AMBER, "high": RED}
    RISK_SOFT = {"low": "#DDE7E0", "medium": "#EEE4CF", "high": RED_SOFT}
    RISK_LABEL_EN = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH"}
    RISK_LABEL_ZH = {"low": "低", "medium": "中", "high": "高"}
    # Derived decision label from the risk field — a display transform of
    # existing data, not a new fact. No risk => no decision block (nothing
    # to derive it from).
    DECISION = {
        "low": ("PROCEED", "建议：可按正常节奏推进。"),
        "medium": ("PROCEED WITH CAUTION", "建议：可继续推进，但需重点核实下方红旗提示中的问题。"),
        "high": ("RECONSIDER", "建议：谨慎对待，最好先获得更多信息确认后再决定是否继续。"),
    }
    SENTIMENT_LABEL_EN = {"positive": "POSITIVE", "negative": "NEGATIVE", "neutral": "NEUTRAL"}
    SENTIMENT_CLASS = {"positive": "", "negative": "negative", "neutral": ""}

    company = data.get("company", "未知公司")
    role = data.get("role", "")
    risk = data.get("risk", "")

    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Risk hero — the report's single most important visual element.
    riskbox_html = ""
    if risk in RISK_COLORS:
        n_legal = len(data.get("legal_risks", []))
        n_red_flags = len(data.get("red_flags", []))
        n_negative = sum(
            1 for i in data.get("employee_reviews", []) + data.get("social_mentions", [])
            if i.get("sentiment") == "negative"
        )
        basis_parts = []
        if n_red_flags:
            basis_parts.append(f"{n_red_flags} 条重点风险提示")
        if n_legal:
            basis_parts.append(f"{n_legal} 条法律/司法记录")
        if n_negative:
            basis_parts.append(f"{n_negative} 条负面口碑")
        basis = "、".join(basis_parts) if basis_parts else "以下公开信息"
        riskbox_html = f'''<aside class="riskbox">
      <div class="label">OVERALL RISK</div>
      <div class="risk" style="color:{RISK_COLORS[risk]}">{RISK_LABEL_EN[risk]}</div>
      <div class="cn">综合风险：{RISK_LABEL_ZH[risk]}</div>
      <p>本判断基于{esc(basis)}综合得出，详见下方各节证据；请结合来源权威性自行判断，不作为最终结论。</p>
    </aside>'''

    # Red flags — existing field from before this UI pass. The approved
    # demo doesn't have an explicit slot for this, so it's folded into the
    # risk-hero basis text above AND kept as its own compact list here
    # (styled with the demo's own .tag language) so no data is dropped.
    red_flags = data.get("red_flags", [])
    red_flags_html = ""
    if red_flags:
        tags = "".join(f'<span class="tag high" style="margin:0 8px 8px 0;">{esc(f)}</span>' for f in red_flags)
        red_flags_html = f'<div class="disclaimer" style="border-top:none;"><div style="font:800 10px/1.2 {MONO};letter-spacing:.1em;color:{MUTED};text-transform:uppercase;margin-bottom:10px;">重点风险提示</div>{tags}</div>'

    # Lede / executive note — derived from the first sentence of
    # overall_notes (real data), not a separately-invented field.
    lede_html = ""
    notes = data.get("overall_notes", "")
    if notes:
        first_sentence = re.split(r"(?<=[。！])", notes.strip())[0]
        lede_html = f'''<section class="lede">
      <div class="index">EXECUTIVE NOTE</div>
      <p>{esc(first_sentence)}</p>
    </section>'''

    def section(num, tag, title, inner):
        return f'''<section class="section">
      <div class="section-num">{num}<span>{tag}</span></div>
      <div>
        <h2>{title}</h2>
        {inner}
      </div>
    </section>'''

    # 01 — basic info facts grid
    basic = data.get("basic_info", {})
    fact_defs = [
        ("founded", "Founded"), ("registered_capital", "Registered Capital"),
        ("legal_rep", "Legal Representative"), ("funding_stage", "Funding"),
    ]
    facts = [(label, basic[key]) for key, label in fact_defs if basic.get(key)]
    basic_section = ""
    if facts:
        facts_html = "".join(
            f'<div class="fact"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>'
            for k, v in facts
        )
        source_note = (
            f'<div class="muted" style="font:600 11px/1.4 {MONO};margin-top:10px;">数据来源：{esc(basic["source"])}</div>'
            if basic.get("source") else ""
        )
        basic_section = section("01", "THE COMPANY", "基本信息", f'<div class="facts">{facts_html}</div>{source_note}')

    # 02 — legal / judicial risk signals
    legal = data.get("legal_risks", [])
    if legal:
        signal_rows = []
        for item in legal:
            src = ""
            if item.get("url"):
                src = f'<div class="source"><a href="{esc(item["url"])}" target="_blank">{esc(item.get("source","SOURCE"))} ↗</a></div>'
            elif item.get("source"):
                src = f'<div class="source">{esc(item["source"])}</div>'
            signal_rows.append(f'''<div class="signal">
        <div class="tagwrap"><span class="tag high">RISK</span></div>
        <div class="date">{esc(item.get("date","—"))}</div>
        <div class="summary"><h3>{esc(item.get("type",""))}</h3><p>{esc(item.get("summary",""))}</p></div>
        {src}
      </div>''')
        legal_inner = "\n".join(signal_rows)
    else:
        legal_inner = '<p class="muted">未检索到明显司法风险记录（不代表不存在，建议自行到国家企业信用信息公示系统核实）。</p>'
    legal_section = section("02", "LEGAL SIGNALS", "法律与司法风险", legal_inner)

    def quote_block(item):
        sentiment = item.get("sentiment", "neutral")
        link = f'<a href="{esc(item["url"])}" target="_blank">查看原文 ↗</a>' if item.get("url") else ""
        return f'''<div class="quote">
        <div class="source-line"><span>{esc(item.get("platform",""))}</span>
        <span class="sentiment {SENTIMENT_CLASS.get(sentiment,"")}">{SENTIMENT_LABEL_EN.get(sentiment,"")}</span></div>
        <blockquote>{esc(item.get("summary",""))}</blockquote>
        <div class="source-line"><span class="muted">摘要来自公开来源，需注意个体样本偏差。</span>{link}</div>
      </div>'''

    reviews = data.get("employee_reviews", [])
    reviews_section = ""
    if reviews:
        reviews_section = section("03", "EMPLOYEE VOICE", "员工口碑", "\n".join(quote_block(i) for i in reviews))

    social = data.get("social_mentions", [])
    social_section = ""
    if social:
        social_section = section("04", "SOCIAL SIGNALS", "社交媒体口碑", "\n".join(quote_block(i) for i in social))

    # Verdict — uses the real overall_notes field; decision block derived
    # from the risk field (hidden if no risk was provided, since there's
    # nothing to derive it from).
    verdict_html = ""
    if notes or risk in DECISION:
        decision_html = ""
        if risk in DECISION:
            big, small = DECISION[risk]
            decision_html = f'<div class="decision"><div class="big" style="color:{RISK_COLORS[risk]}">{big}</div><div class="small">{esc(small)}</div></div>'
        verdict_html = f'''<section class="verdict">
      <div>
        <div class="kicker">THE VERDICT</div>
        <h2>综合建议</h2>
        <p>{esc(notes) if notes else "暂无综合建议，请结合以上信息自行判断。"}</p>
      </div>
      {decision_html}
    </section>'''

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{esc(company)} — 公司背调报告</title>
<style>
:root{{
  --paper:{PAPER}; --ink:{INK}; --muted:{MUTED}; --line:{LINE}; --line-strong:{LINE_STRONG};
  --red:{RED}; --red-soft:{RED_SOFT}; --green:{GREEN};
  --mono:{MONO}; --sans:{SANS}; --serif:{SERIF};
}}
*{{box-sizing:border-box}}
html{{background:{PAGE_BG};color:var(--ink)}}
body{{margin:0;font-family:var(--sans);background:{PAGE_BG}}}
a{{color:inherit;text-decoration:none;border-bottom:1px solid currentColor}}
.page{{max-width:1180px;margin:26px auto;background:var(--paper);min-height:100vh;padding:38px 54px 72px;box-shadow:0 8px 30px rgba(0,0,0,.04)}}
.masthead{{display:flex;justify-content:space-between;gap:24px;border-bottom:2px solid var(--ink);padding-bottom:16px}}
.brand{{font:800 12px/1 var(--mono);letter-spacing:.15em;text-transform:uppercase}}
.issue{{text-align:right;font:600 11px/1.55 var(--mono);color:var(--muted)}}
.hero{{display:grid;grid-template-columns:1.6fr .8fr;gap:42px;padding:42px 0 34px;border-bottom:1px solid var(--line-strong)}}
.kicker{{font:800 11px/1 var(--mono);letter-spacing:.13em;color:var(--muted);text-transform:uppercase;margin-bottom:18px}}
h1{{font-family:var(--serif);font-size:54px;line-height:1.04;letter-spacing:-.045em;margin:0;max-width:720px}}
.subhead{{font-size:16px;color:var(--muted);margin-top:16px}}
.riskbox{{align-self:start;border:1px solid var(--ink);padding:18px 20px 20px;position:sticky;top:24px}}
.riskbox .label{{font:800 10px/1 var(--mono);letter-spacing:.12em;color:var(--muted)}}
.riskbox .risk{{font:800 50px/.95 var(--mono);letter-spacing:-.05em;margin-top:18px}}
.riskbox .cn{{font-family:var(--serif);font-weight:700;font-size:22px;margin-top:8px}}
.riskbox p{{font-size:12px;line-height:1.65;color:var(--muted);margin:20px 0 0;padding-top:14px;border-top:1px solid var(--line)}}
.disclaimer{{padding:13px 0;border-bottom:1px solid var(--line);font-size:12px;color:var(--muted);line-height:1.6}}
.lede{{display:grid;grid-template-columns:160px 1fr;gap:28px;padding:34px 0 6px}}
.lede .index{{font:800 12px/1 var(--mono);letter-spacing:.08em}}
.lede p{{font-family:var(--serif);font-size:23px;line-height:1.6;margin:0;max-width:760px}}
.section{{display:grid;grid-template-columns:160px 1fr;gap:28px;padding:40px 0;border-top:1px solid var(--line-strong)}}
.section-num{{font:800 34px/1 var(--mono);letter-spacing:-.05em}}
.section-num span{{display:block;font:800 10px/1.3 var(--mono);letter-spacing:.12em;color:var(--muted);margin-top:8px}}
.section h2{{font-family:var(--serif);font-size:32px;line-height:1.1;margin:0 0 22px;letter-spacing:-.025em}}
.muted{{color:var(--muted)}}
.facts{{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--ink);border-bottom:1px solid var(--ink)}}
.fact{{padding:18px 16px;border-right:1px solid var(--line)}}.fact:last-child{{border-right:0}}
.fact .k{{font:800 10px/1.2 var(--mono);letter-spacing:.08em;color:var(--muted);text-transform:uppercase}}
.fact .v{{font-family:var(--serif);font-size:22px;margin-top:10px}}
.signal{{display:grid;grid-template-columns:110px 100px 1fr 140px;gap:16px;padding:18px 0;border-top:1px solid var(--line);align-items:start}}
.signal:first-of-type{{border-top:1px solid var(--ink)}}
.tag{{font:800 10px/1 var(--mono);padding:5px 6px;border:1px solid currentColor;display:inline-block}}
.tag.high{{color:var(--red);background:var(--red-soft)}}
.signal .date{{font:700 11px/1.4 var(--mono);color:var(--muted)}}
.signal h3{{font-size:14px;margin:0 0 6px}}
.signal p{{font-size:13px;line-height:1.7;color:#3D3D39;margin:0}}
.source{{font:800 10px/1.2 var(--mono);text-align:right}}
.source a{{border-bottom:0}}.source a:hover{{text-decoration:underline}}
.quote{{padding:24px 0;border-top:1px solid var(--ink)}}.quote:first-of-type{{border-top:0}}
.quote .source-line{{display:flex;justify-content:space-between;gap:16px;font:800 10px/1.3 var(--mono);letter-spacing:.05em;color:var(--muted)}}
.quote blockquote{{font-family:var(--serif);font-size:19px;line-height:1.7;margin:16px 0 10px}}
.sentiment{{font:800 10px/1 var(--mono)}}.sentiment.negative{{color:var(--red)}}
.verdict{{display:grid;grid-template-columns:1fr 220px;gap:28px;background:#EFEFEA;border-top:2px solid var(--ink);padding:28px 30px}}
.verdict h2{{margin:0 0 14px}}.verdict p{{font-family:var(--serif);font-size:19px;line-height:1.75;margin:0}}
.decision{{border-left:1px solid var(--line-strong);padding-left:22px}}
.decision .big{{font:800 26px/1.15 var(--mono)}}
.decision .small{{font-size:12px;color:var(--muted);line-height:1.6;margin-top:12px}}
.footer{{display:flex;justify-content:space-between;gap:18px;padding-top:24px;margin-top:44px;border-top:1px solid var(--ink);font:600 10px/1.5 var(--mono);color:var(--muted)}}
@media (max-width:860px){{
  .page{{margin:0;padding:28px 20px 52px}}
  .hero{{grid-template-columns:1fr}}
  .riskbox{{position:static}}
  .lede,.section{{grid-template-columns:1fr}}
  .lede .index{{margin-bottom:-12px}}
  .facts{{grid-template-columns:repeat(2,1fr)}}
  .fact:nth-child(2){{border-right:0}}
  .fact:nth-child(-n+2){{border-bottom:1px solid var(--line)}}
  .signal{{grid-template-columns:90px 1fr}}
  .signal .date{{grid-column:1/2}}.signal .summary{{grid-column:2/3}}
  .signal .source{{grid-column:2/3;text-align:left}}.signal .tagwrap{{grid-column:1/2}}
  .verdict{{grid-template-columns:1fr}}
  .decision{{border-left:0;border-top:1px solid var(--line-strong);padding:18px 0 0}}
  .footer{{flex-direction:column}}h1{{font-size:42px}}
}}
</style>
</head>
<body>
<article class="page">
  <header class="masthead">
    <div class="brand">Job Application Assistant / Company Intelligence</div>
    <div class="issue">生成时间 {datetime.now().strftime('%Y.%m.%d / %H:%M')}<br>PERSONAL RESEARCH FILE</div>
  </header>

  <section class="hero">
    <div>
      <div class="kicker">Company Background Report</div>
      <h1>{esc(company)}</h1>
      {f'<div class="subhead">关联岗位：{esc(role)}</div>' if role else ''}
    </div>
    {riskbox_html}
  </section>

  <div class="disclaimer">免责声明：本报告基于公开来源与平台信息汇总，仅用于个人求职决策参考，不构成法律、财务或投资建议。公开信息可能存在延迟、缺失或上下文不完整。</div>
  {red_flags_html}
  {lede_html}
  {basic_section}
  {legal_section}
  {reviews_section}
  {social_section}
  {verdict_html}

  <footer class="footer"><span>PERSONAL USE ONLY · PUBLIC-SOURCE RESEARCH</span><span>JOB-APPLICATION-ASSISTANT / COMPANY DOSSIER</span></footer>
</article>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="Path to findings JSON")
    parser.add_argument("--out", required=True, help="Output file path")
    parser.add_argument("--format", choices=["markdown", "html"], default="markdown")
    args = parser.parse_args()

    try:
        data = load_findings(args.input)
    except FileNotFoundError:
        print(f"Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {args.input}: {e}", file=sys.stderr)
        sys.exit(1)

    if not data.get("company"):
        print("Findings JSON must include a 'company' field.", file=sys.stderr)
        sys.exit(1)

    content = render_html(data) if args.format == "html" else render_markdown(data)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()

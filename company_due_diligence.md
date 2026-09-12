# Company Due Diligence (背调) — Sources, Query Templates & Interpretation

Purpose: before (or right after) finding a company hiring for the target
role, pull together publicly available signal on the company's financial
health, legal risk, and employee sentiment — so the user can decide whether
it's worth applying/continuing, not just chase any open posting.

## How to run this step
This relies on `web_search` (or an equivalent search tool) in the calling
agent's session, run live against each source below — NOT a local scraper.
Most of these sites are JS-heavy, aggressively anti-bot, or login-walled, so
scraping them from a script is unreliable and easy to get blocked on. Search
queries against them (via a general search engine) surface the same public
content far more robustly.

For each candidate company, run a small batch of queries (don't skip
categories — a company can look fine on one channel and be a red flag on
another):

### 1. 工商 / 法律风险 (authoritative — check these first)
- `<公司全称> 企查查`
- `<公司全称> 天眼查 被执行人`
- `<公司全称> 司法风险 失信被执行人`
- `<公司全称> 劳动争议 裁判文书`
- `<公司全称> 股权冻结`

Prefer citing the **primary public registries** over secondary aggregators
when a specific claim matters:
- 国家企业信用信息公示系统 (gsxt.gov.cn) — official registration status,
  administrative penalties
- 中国裁判文书网 (wenshu.court.gov.cn) — actual court judgments, including
  labor disputes (劳动争议) filed against the company
- 中国执行信息公开网 (shixin.court.gov.cn) — 失信被执行人 (defaulting on
  court judgments) records
企查查/天眼查 mostly re-package the same registry + judgment data with a
nicer UI — fine as a starting point, but if a specific lawsuit or default
matters to the user's decision, try to confirm against the primary source.

### 2. 员工口碑 / 工作体验
- `<公司全称> 知乎 靠谱吗`
- `<公司全称> 知乎 员工 评价`
- `<公司全称> 看准网` or `<公司全称> Kanzhun review`（看准网/BOSS直聘企业版）
- `<公司全称> 脉脉`
- `<公司全称> 小红书 入职 感受`
- `<公司全称> 小红书 吐槽`

### 3. 综合口碑 / 品牌
- `<公司全称> 抖音 员工日常`（多为官方账号/营销内容，权重放低，主要看评论区真实反馈）
- `<公司全称> 加班 猝死 舆情`（仅在有具体线索时补充搜索，不要预设结论）
- `<公司全称> 融资历史`（用于判断财务健康度/现金流风险，尤其是早期创业公司）

## How to interpret and present findings

- **Cite sources.** Every claim in the report should be attributable to a
  specific source (知乎回答/企查查记录/裁判文书号/小红书帖子), not stated as
  bare fact. Follow the same copyright-safe paraphrasing approach used
  elsewhere — summarize in your own words, don't reproduce long quotes.
- **Weight primary/official records above social commentary.** A 裁判文书网
  labor-dispute judgment is a fact; a single 知乎 complaint is one person's
  account and may be biased, outdated, or exaggerated — note that distinction
  explicitly in the report rather than presenting both with equal confidence.
- **Watch for astroturfing.** 抖音/小红书 company-branded content and posts
  that read like recruiting marketing aren't independent employee sentiment
  — flag this rather than counting it toward "positive reviews."
- **Small sample ≠ trend.** One or two negative reviews out of a large
  company is normal noise; a consistent pattern across multiple independent
  sources (esp. combined with an actual court record) is the real signal.
- **This is not legal or financial advice.** Present findings as information
  to weigh, not a verdict — the user makes the final call on whether to
  apply/accept an offer.

## Red-flag checklist (surface these prominently if found)
- [ ] 失信被执行人 / 被强制执行 records
- [ ] Multiple 劳动争议 (labor dispute) judgments, especially repeated ones
      over wages/overtime/unpaid social insurance
- [ ] Frequent legal-entity or equity changes in a short period (可能预示
      资金链或控制权问题)
- [ ] Recurring, specific employee complaints about unpaid wages, excessive
      unpaid overtime (996/007), or forced resignation practices — especially
      when corroborated across more than one independent source/platform
- [ ] Recent large-scale layoffs or funding collapse reported in press/社媒

## Known limitation: 小红书/抖音 coverage is incomplete by design

This workflow uses a general search engine (`web_search`), never a logged-in
scraper — see "How to run this step" above for why. The tradeoff: **general
search engines index 小红书/抖音 content very poorly**, so a company can have
real posts/comments on those platforms that a `web_search` pass simply won't
surface, even with well-formed queries.

- 小红书 in particular gates most content behind login, and even public posts
  are inconsistently crawled by external search engines — a note the user
  found by searching directly inside the 小红书 app may not turn up here.
- 抖音 comments (where real sentiment usually lives, as opposed to the
  official account's video captions) are almost never indexed at all.

**Do not treat an empty result from these two sources as "no findings" —
treat it as "not covered by this method."** If the user has already found
relevant posts themselves (by searching inside the app), the right move is
to have them share the content or link directly, then fold it into the
report's 社交媒体口碑 section attributed as **user-provided**, not
Claude-sourced — same sourcing discipline as everything else in this file.

Logging in as the user to search 小红书/抖音 directly is a possible
technical fix but is deliberately out of scope here: it risks the user's
account (aggressive anti-automation risk-control, possible bans) and would
require building and maintaining login/cookie persistence and anti-scraping
workarounds — a different, riskier kind of tool than the rest of this skill.

## Output format
Feed structured findings into `scripts/due_diligence_report.py` to produce
a shareable Markdown/HTML report per company (see that script's `--help`).
Keep each section short — a due-diligence report is a decision aid, not an
exhaustive dossier.

# Common ATS Platforms — Fingerprints & Field Notes

Use this to identify which system is behind a company's application form
before trying to automate it. Fingerprints are based on URL patterns and
common DOM markers; always verify against the live page since companies
customize heavily.

## Greenhouse
- URL pattern: `boards.greenhouse.io/<company-slug>` or embedded widget on
  the company's own domain (`<company>.com/careers` loading a Greenhouse iframe).
- Public API: `https://boards-api.greenhouse.io/v1/boards/<token>/jobs` returns
  open jobs as JSON — prefer this over scraping HTML when available.
- Typical fields: first_name, last_name, email, phone, resume (file), cover
  letter (file, often optional), LinkedIn URL, custom questions (EEO,
  work authorization) defined per-company.

## Lever
- URL pattern: `jobs.lever.co/<company-slug>/<posting-id>`
- Typical fields: name, email, phone, resume (file), LinkedIn/portfolio URLs,
  a few custom questions. Application form is usually a single page.

## Workday
- URL pattern: `<company>.wd1.myworkdayjobs.com` / `wd5` / etc (the number
  varies by Workday data center/tenant).
- Multi-step wizard (My Information → My Experience → Application Questions →
  Voluntary Disclosures → Review). Often requires account creation first.
- Heaviest to automate reliably — selectors are tenant-specific and the UI is
  React-driven with dynamic `data-automation-id` attributes. Budget extra
  time to record real selectors via a browser tool's inspector before
  attempting unattended fills.

## SmartRecruiters
- URL pattern: `jobs.smartrecruiters.com/<company>/<posting-id>`
- Typical fields: name, email, phone, resume upload, sometimes a short
  screening questionnaire.

## iCIMS
- URL pattern: `<company>.icims.com` or `careers-<company>.icims.com`
- Older, more varied markup; often multi-step with account creation.

## BambooHR (careers pages)
- URL pattern: `<company>.bamboohr.com/jobs/`
- Usually simple single-page forms: name, email, phone, resume upload.

## Workable
- URL pattern: `apply.workable.com/<company>/j/<posting-id>`
- Single-page form, generally straightforward to automate.

## 国内常见渠道
- **智联招聘 / 前程无忧(51job) / 猎聘**：聚合平台，非公司官网；投递走平台内
  简历投递流程，通常需要平台账号登录。适合作为 Step 1 的候选来源，但按
  第 2 步的逻辑应优先寻找公司官网/自建招聘系统作为更精准的投递渠道。
- **BOSS直聘**：以"聊天"为主要投递方式（与招聘人员在线沟通后发送简历），
  不是传统表单，不适合脚本化自动填表；建议引导用户手动完成对话式投递，
  或仅用它来发现在招岗位/联系人信息。
- **企业自建招聘系统**（如大厂自有 `careers.<company>.com`）：字段和流程
  因公司而异，需逐一查看后为其单独写 selector 映射，可仿照本文件的结构
  为常用目标公司积累一份 `references/company_specific/<company>.md`。

## General approach for an unrecognized ATS
1. Open the form and inspect field `name`/`id`/`data-*` attributes.
2. Identify: name field(s), email, phone, resume upload `input[type=file]`,
   cover letter upload (if separate), and the submit control.
3. Add a new entry to `ATS_FIELD_MAP` in `scripts/ats_form_filler.py`.
4. Test the fill (not the submit) first, and always let the human review the
   screenshot before authorizing `--confirm-submit`.

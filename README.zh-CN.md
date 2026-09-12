# job-application-assistant

*[English](README.md)*

一个给 Claude / Codex 用的**个人求职**技能(Skill)：按岗位关键词找正在招聘的公司、在投递前先做背景调查（财务健康度、法律纠纷、员工评价）、把所有投递记录集中管理，并在需要时协助填写投递表单——但每一次真正的"提交"都需要你本人确认。

这是给**一个人**管理自己求职过程用的工具，不是招聘 SaaS 产品。没有服务器、没有账号体系、不联网同步——所有数据都保存在你本机的一份 JSON 文件里。

## 效果长这样

**投递记录看板** —— 一眼看清所有投递过的公司、当前状态，以及背调给出的风险标签。

![投递看板](docs/dashboard-screenshot.png)

**公司背调报告** —— 在决定要不要继续投递/面试前，把法律/司法风险、员工口碑、社交媒体评价汇总成一份报告。

![公司背调报告](docs/company-report-screenshot.png)

两个页面都是自包含的静态 HTML —— 没有服务器，每次运行脚本都会用你自己的真实数据重新生成。

## 它能做什么

- **找岗位** —— 按岗位关键词搜索招聘聚合平台上正在招聘的公司，并优先寻找每家公司的**官网**招聘页而不是聚合平台的转载页面（`scripts/search_target_companies.py`、`scripts/find_career_page.py`）。
- **先背调再投递** —— 从知乎/企查查/天眼查/裁判文书网/看准网/小红书/抖音等渠道汇总公司的财务健康度、法律纠纷、员工口碑等公开信息，生成一份标注来源、观点平衡的报告，投入时间投递之前先看一眼（`references/company_due_diligence.md`、`scripts/due_diligence_report.py`）。
- **谨慎地协助填表** —— 一个基于 Playwright 的辅助脚本，帮你填写常见 ATS 平台（Greenhouse、Lever、Workday 等）的申请表单，始终用**可见的**浏览器窗口打开以便你自己解决验证码，并且在没有明确确认之前绝不会点击提交（`scripts/ats_form_filler.py`）。
- **本地统一管理** —— 一个基于 JSON 文件的命令行追踪工具，支持重复投递检测、跟进提醒，以及生成 HTML 看板（`scripts/track_applications.py`）。

完整的分步工作流程见 [`SKILL.md`](SKILL.md)；每个模块背后的设计考量（包括参考了哪些现有开源自动投递工具的思路、又刻意没有采用哪些）见 [`references/`](references/) 目录。

## 不可协商的原则

- 任何一批投递在没有得到用户明确确认之前，绝不会自动提交。
- 遇到验证码绝不尝试破解或绕过——脚本会停下来，把控制权交还给你。
- 绝不编造简历经历，也绝不编造背调发现——所有内容都必须有来源。
- 不会在无人值守的情况下连续密集投递——而是分批处理，每批之间留出人工检查的节点。

## 安装

这是打包成 **Claude Skill** 的形式（`SKILL.md` + `scripts/` + `references/`）。使用方式：

1. 在 Claude（桌面端或网页端）中，进入 **设置 → Capabilities → Skills**，上传这个文件夹（或者已经打包好的 `.skill` 文件）。
2. 如果是 Claude Code / Codex，按照对应工具的文档把这个文件夹放进 skills 目录即可。

### Python 依赖

记录追踪和报告生成这两个脚本（`track_applications.py`、`due_diligence_report.py`）**不需要任何第三方依赖**，标准库就够用。

搜索和自动填表这两个脚本需要：

```bash
pip install -r requirements.txt
playwright install chromium   # 只有用到 ats_form_filler.py 时才需要
```

## 快速上手（命令行）

```bash
# 记录一条投递
python scripts/track_applications.py add \
  --company "Acme Corp" --role "Frontend Engineer" \
  --channel official_site --url "https://acme.com/careers/123" \
  --status submitted

# 投递新公司前，先查一下是否已经投过
python scripts/track_applications.py check --company "Acme Corp"

# 看看有哪些需要跟进
python scripts/track_applications.py followups --days 7

# 给某家公司挂上背调报告
python scripts/due_diligence_report.py --input acme_findings.json \
  --out acme_report.html --format html
python scripts/track_applications.py diligence \
  --company "Acme Corp" --role "Frontend Engineer" \
  --risk medium --report acme_report.html --summary "1起劳动仲裁判决"

# 生成看板
python scripts/track_applications.py dashboard --out dashboard.html
```

完整的命令参数说明见各脚本自带的 `--help` 和文件头部的说明文档。

## 免责声明

这是一个个人效率工具，不构成法律、财务或职业规划建议。背调报告汇总的是公开信息和社交媒体上的评论——如果某条信息真的会影响你的决定（比如某起具体的诉讼、公司的注册状态），请在采取行动前自行到权威信源核实。使用本工具与任何网站交互时，你需要自行遵守该网站的服务条款。

## 许可协议

MIT —— 详见 [LICENSE](LICENSE)。

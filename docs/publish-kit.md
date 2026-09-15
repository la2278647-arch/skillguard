# SkillGuard 一键发布包（Publish Kit）

> 平台发布凭据的替代方案：所有文案与物料已备齐，登录各平台后**复制粘贴**即可发布。
> 本文件汇总全部发布内容与步骤，配合 `docs/promotion/` 下的详细文案使用。

---

## 📦 物料清单

| 物料 | 路径 | 用途 |
|------|------|------|
| 掘金深度文 | `docs/promotion/juejin_article.md` | 掘金首发 |
| V2EX 帖子 | `docs/promotion/v2ex_zhihu.md`（前半） | V2EX 分享创造 |
| 知乎回答 | `docs/promotion/v2ex_zhihu.md`（后半） | 知乎问答 |
| Twitter thread | `docs/promotion/english_posts.md`（前半） | X/推特 |
| HN Show HN | `docs/promotion/english_posts.md`（Show HN 段） | Hacker News |
| Reddit 帖子 | `docs/promotion/english_posts.md`（Reddit 段） | r/ClaudeAI 等 |
| 生态质量报告 | `docs/promotion/ECOSYSTEM_REPORT.md` | 数据支撑材料 |
| 可视化报告截图 | `docs/promotion/report-screenshot.png` | 配图 |
| 项目 Logo | `docs/logo.svg` | 配图 |

## 🔗 核心链接（所有帖子通用 CTA）

- Repository: https://github.com/la2278647-arch/skillguard
- Docs: https://la2278647-arch.github.io/skillguard/
- Ecosystem report: https://la2278647-arch.github.io/skillguard/ecosystem-report/
- Install: `pip install https://github.com/la2278647-arch/skillguard/releases/download/v0.5.0/skillguard-0.5.0-py3-none-any.whl`

## 📝 发布步骤

### 1. 掘金（juejin.cn）
1. 登录掘金 → 创作者中心 → 写文章
2. 粘贴 `juejin_article.md` 全文（Markdown 直接支持）
3. 标题建议：《我用 218 个测试，给 AI Agent 的 Skills 建了一条质检流水线》
4. 配图：报告截图 + Logo
5. 标签：AI / 开源 / 开发者工具 / Claude
6. 发布后参与「玩 Android 每月征文」等活动提高曝光

### 2. V2EX（v2ex.com）
1. 登录 → 「分享创造」节点 → 发帖
2. 粘贴 v2ex_zhihu.md 前半部分
3. 标题：SkillGuard —— 给 AI Agent 的 Skills 做质检的开源工具
4. 保持简洁，突出"能用"而非"好看"

### 3. 知乎（zhihu.com）
1. 搜索问题《如何评估和选择高质量的 AI Agent Skills？》
2. 或创建问题后自答
3. 粘贴 v2ex_zhihu.md 后半部分
4. 回答末尾附 GitHub 链接与生态报告

### 4. Twitter/X
1. 将 english_posts.md 的 thread 部分逐条发布（10 条）
2. 配图：报告截图 + Logo
3. 话题：#AgentSkills #ClaudeCode #OpenSource #DevTools
4. @相关大 V 可增加曝光（superpowers、anthropics 等生态账号）

### 5. Hacker News（news.ycombinator.com）
1. 登录 → Submit
2. 标题：Show HN: SkillGuard – Quality gates for AI agent skills
3. URL: https://github.com/la2278647-arch/skillguard
4. 正文用 english_posts.md 的 Show HN 段（HN 评论需用代码块引用）

### 6. Reddit（r/ClaudeAI、r/OpenAI、r/artificial）
1. 登录 Reddit → r/ClaudeAI → Submit
2. 标题：We have 200k+ star skill repos but zero tooling to verify a skill is safe — I built SkillGuard
3. 正文用 english_posts.md 的 Reddit 段
4. 回复评论建立讨论（这是 Reddit 的核心互动方式）

## ⏰ 最佳发布时间

| 平台 | 最佳时间（UTC+8） |
|------|------------------|
| 掘金 | 工作日 9:00-11:00 / 20:00-22:00 |
| V2EX | 工作日 10:00-12:00 |
| 知乎 | 晚间 20:00-23:00 |
| Twitter | 22:00-24:00（对应美东上午） |
| HN | 22:00-24:00（对应美东上午 9-11 点，HN 流量高峰） |
| Reddit | 21:00-23:00 |

## 📊 发布后数据记录

发布后回到 `docs/promotion/FEEDBACK_TRACKING.md` 填写实际数据：
- 各平台浏览/赞/评论
- GitHub Star 增量
- Release 下载量

---

_生成时间: 2026-09 · 配套工具: [SkillGuard](https://github.com/la2278647-arch/skillguard)_


# 教程：从零构建高质量 Agent Skill（全流程）

> 目标读者：想用 Claude Code / Codex / Cursor 但还不熟悉 Skill 规范的新手，以及想提升 Skill 质量的进阶用户。
> 本教程用 SkillGuard 走完「创建 → 检查 → 测试 → 评分 → 发布 → 徽章 → CI 门禁」完整链路。

---

## 前置准备

```bash
# 安装 SkillGuard（GitHub Release 直装或 PyPI）
pip install https://github.com/la2278647-arch/skillguard/releases/download/v0.7.0/skillguard-0.7.0-py3-none-any.whl

# 验证
skillguard --version
```

---

## 第 1 步：初始化 Skill 骨架

```bash
skillguard init my-code-review --name my-code-review --framework claude-code
cd my-code-review
```

生成的骨架：

```
my-code-review/
├── SKILL.md          # 元数据 + 说明文档
└── tests/
    └── smoke.sh      # 冒烟测试（验证 SKILL.md 存在且非空）
```

---

## 第 2 步：编写 SKILL.md

编辑 `SKILL.md`，填写真实内容。规范要求 **front-matter 元数据 + 结构化正文**：

```markdown
---
name: my-code-review
description: 用工程最佳实践审查代码变更，识别 bug、安全风险与可维护性问题
version: 1.0.0
framework: claude-code
tags:
  - code-review
  - quality
---

# My Code Review

## 用途

审查 git diff 或 PR 中的代码变更，输出结构化审查意见：
- Bug 与逻辑错误
- 安全风险
- 可维护性问题

## 使用方式

当用户请求"review 这个 PR / 审查这段代码"时激活。审查步骤：
1. 读取 diff 与相关上下文
2. 逐文件检查（错误处理、边界条件、安全、性能）
3. 按严重级别输出意见（blocker / major / minor / nit）

## 注意事项

- 只审查 diff，不重写代码
- 意见必须有具体证据（行号/代码引用）
- 不输出恭维性评论
```

---

## 第 3 步：添加辅助脚本（可选但推荐）

```bash
mkdir scripts
```

`scripts/summary.sh` —— 汇总审查统计：

```bash
#!/usr/bin/env bash
# 汇总审查结果统计
set -euo pipefail
echo "=== 审查统计 ==="
grep -c "\[blocker\]" "$1" 2>/dev/null || echo "blocker: 0"
grep -c "\[major\]" "$1" 2>/dev/null || echo "major: 0"
```

---

## 第 4 步：添加测试

测试放在 `tests/` 或 `test/`，支持 `.sh` / `.py` / `.js` / `.ts`。

`tests/smoke.sh` —— 验证关键文件存在：

```bash
#!/usr/bin/env bash
set -euo pipefail
test -f "$(dirname "$0")/../SKILL.md" && echo "SKILL.md 存在"
test -f "$(dirname "$0")/../scripts/summary.sh" && echo "summary.sh 存在"
```

---

## 第 5 步：运行质量检查

```bash
skillguard check .
```

输出：

```
🔍 SkillGuard 评估: my-code-review (v1.0.0, claude-code)
  综合评分: 100.0/100  ✅ 通过
  检查: 0 项 (🔴 0 / 🟡 0 / 🔵 0)
  测试: 1 项 (✅ 1 / ❌ 0)
```

若有不通过项，按输出指引修复（如补 front-matter、加 description、修脚本错误处理）。

---

## 第 6 步：生成可视化报告

```bash
# HTML 报告（雷达图 + 评分条）
skillguard check . --format html -o report.html

# 评分徽章（嵌入 README）
skillguard badge . -o badge.svg --markdown --repo-url https://github.com/you/my-code-review
```

将徽章加到你的 README：

```markdown
![SkillGuard](badge.svg)
```

---

## 第 7 步：团队加入自定义规范（可选）

创建 `skillguard.yml` 配置团队质量门槛：

```yaml
threshold: 80          # 门禁分数
test_timeout: 120      # 测试超时
rules:
  - SEC-001            # 只启用指定规则（示例）
```

或用插件系统共享团队检查规则（见 `examples/custom_rules.py`）：
- TODO/FIXME 遗留检测
- 必备章节检查
- 脚本错误处理检查

---

## 第 8 步：配置 CI 门禁

### GitHub Actions（授权 workflow scope 后启用）

复制 `templates/github-workflows/ci.yml` 到 `.github/workflows/`。

### 其他 CI（CircleCI / Azure，无需特殊权限）

- `.circleci/config.yml`：CircleCI 配置，添加项目即用
- `azure-pipelines.yml`：Azure Pipelines 配置

### 本地 / pre-commit（零依赖）

```bash
# pre-commit 钩子：提交前自动检查
ln -s ../../scripts/pre-commit .git/hooks/pre-commit
SKILLGUARD_THRESHOLD=80 git commit -m "update skill"
```

---

## 第 9 步：发布与传播

1. **推送 GitHub**，更新 README（含徽章 + 使用说明）
2. **生成生态报告**（如果你想给别人的 Skill 打分）：

```bash
skillguard bench https://github.com/anthropics/skills.git
```

3. 让 AI 代理直接检查（MCP）：

```bash
pip install "skillguard[mcp]"
claude mcp add skillguard -- skillguard mcp
# 对话中：用 check_skill 检查我的 skill 目录
```

---

## 质量检查清单

发布前用 SkillGuard 自查：

| 检查项 | 命令 | 通过标准 |
|--------|------|----------|
| 整体质量 | `skillguard check . --ci` | 退出码 0 |
| 安全 | `skillguard check . -r SEC-001 -r SEC-005` | 无 ERROR |
| 测试 | `skillguard check . --format json` | tests.passed == tests.total |
| 徽章 | `skillguard badge .` | 生成 SVG |
| 聚合 | `skillguard report .` | 有统计输出 |

---

## 下一步

- 完整 [API 参考](api.md) / [CLI 参考](cli.md)
- [自定义规则示例](../examples/custom_rules.py)
- [生态质量报告](ecosystem-report.md)
- [MCP 集成](mcp.md)
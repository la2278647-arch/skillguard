# SkillGuard 常见问题（FAQ）

> 覆盖安装、使用、安全、兼容性等高频问题。持续更新中。

---

## 安装

### Q1: 为什么 `pip install skillguard` 装不上？

如果项目尚未同步到 PyPI，或你看到版本过旧，请使用 GitHub Release 直接安装（当前可用、与 PyPI 等效）：

```bash
pip install https://github.com/la2278647-arch/skillguard/releases/download/v0.9.0/skillguard-0.9.0-py3-none-any.whl
```

也可以从 [Releases 页面](https://github.com/la2278647-arch/skillguard/releases) 手动下载 wheel 后安装：

```bash
pip install skillguard-0.9.0-py3-none-any.whl
```

### Q2: 支持哪些 Python 版本？

Python 3.10 / 3.11 / 3.12 / 3.13。最低要求 3.10。

### Q3: MCP 功能（AI 代理直调）如何安装？

```bash
pip install "skillguard[mcp]"
```

---

## 使用

### Q4: 什么是一个「合格的 Skill 目录」？

最少包含一个 `SKILL.md`（或 `skill.md`）文件，且推荐包含 YAML front-matter 元数据（name/description/version/framework/tags）。可选 `scripts/`（辅助脚本）与 `tests/` 或 `test/`（测试脚本，支持 .sh/.py/.js/.ts）。

### Q5: 为什么我的 Skill 评分低？

常见原因：
- **缺少 description**（SRC-003）——AI 不知道何时使用它
- **缺少测试**——scripts 定义但无 tests
- **安全规则命中**（SEC-\*）——脚本含危险命令
- **引用断裂**（REF-\*）——SKILL.md 引用了不存在的文件

运行 `skillguard check <dir> --format html -o report.html` 查看逐项问题与颜色编码。

### Q6: 如何让 AI 代理（Claude/Cursor/Codex）直接调用 SkillGuard？

```bash
pip install "skillguard[mcp]"
claude mcp add skillguard -- skillguard mcp
```

之后在对话中即可使用 `check_skill` / `scan_skills` / `bench_repo` 三个工具。详见 [MCP 集成](mcp.md)。

### Q7: 如何扫描一个远程仓库里的全部 Skills？

```bash
skillguard bench https://github.com/anthropics/skills.git
```

该命令会浅克隆仓库、扫描全部 Skill、输出聚合质量报告（平均分/通过率/评分分布）。

---

## 安全

### Q8: 运行 `skillguard check` 会执行 Skill 的脚本吗？

- **静态校验**（默认执行）：只读文件内容，**不会执行任何脚本**。安全。
- **沙箱测试**（`run_tests=True` 默认开启）：会把整个 Skill 目录**复制到临时目录**再运行测试脚本，脚本无法触碰你的源码目录。每个脚本有强制超时（默认 60s），并且测试环境会丢弃 `AWS_`/`OPENAI_`/`TOKEN` 等敏感环境变量。

如需完全跳过测试执行：`skillguard check <dir> --no-tests`。

### Q9: SkillGuard 能检测哪些安全问题？

33 条安全规则（SEC-001..025），覆盖：
- 破坏性命令：rm -rf、mkfs、dd 到 /dev/、数据库高危命令
- 凭据泄露：API Key、GitHub Token、私钥、云平台密钥
- 远程执行：curl|sh、eval、远程模块导入
- 供应链：npx --yes、npm i -g
- 权限提升：sudo、su -、doas

完整清单见 [质量规则](rules.md)。

### Q10: 我的 Skill 脚本里确实需要 `sudo`，会被误报吗？

SEC-009（sudo）等规则是 **INFO 级提示**，不会导致检查失败。只有 ERROR 级（如 rm -rf、硬编码密钥）会阻塞门禁。你也可以用 `-r` 参数只启用指定规则。

---

## 兼容性

### Q11: 支持哪些 AI 代理框架？

框架无关。通过 front-matter 的 `framework` 字段标注（generic/claude-code/codex/cursor），但检查逻辑对所有框架一致。

### Q12: Skill 脚本支持哪些语言？

测试脚本（tests/）支持：bash(.sh)、Python(.py)、JavaScript(.js)、TypeScript(.ts)。辅助脚本（scripts/）额外支持更多后缀。

### Q13: 能检查 `.agents/`、`.claude/` 等隐藏目录下的 Skills 吗？

**可以**。批量扫描只跳过 VCS（.git 等）与依赖目录（node_modules、.venv 等），`.agents`、`.claude` 等隐藏目录正是 Skills 常见存放位置，会被正常扫描。

---

## 自定义与团队

### Q14: 团队如何统一质量门槛？

创建 `skillguard.yml`（当前目录自动发现）：

```yaml
threshold: 80
test_timeout: 120
rules:
  - SEC-001
```

或用插件系统共享自定义规则，见 [自定义规则示例](../examples/custom_rules.py)。

### Q15: 如何在提交前自动检查？

- **pre-commit 框架**：项目提供 `.pre-commit-hooks.yaml`，添加几行配置即可
- **原生 git hook**：`ln -s ../../scripts/pre-commit .git/hooks/pre-commit`

详见 [CI 集成](ci.md)。

### Q16: `scan` 和 `report` 命令有什么区别？

- `scan`：轻量扫描（静态校验 + 评分），快速排查看板
- `report`：完整评估（含沙箱测试）+ 聚合报告，适合团队总览与 CI 归档

---

## 其他

### Q17: 如何贡献新安全规则？

参考 [CONTRIBUTING.md](../CONTRIBUTING.md)：在 `validator.py` 的 `DANGEROUS_PATTERNS` 添加规则 + 在测试中加入用例 + 更新 rules.md。

### Q18: 遇到 bug 或安全问题如何报告？

- 普通 Bug：使用 [Bug Report 模板](https://github.com/la2278647-arch/skillguard/issues/new?template=bug_report.yml)
- 安全问题：通过 [Security Advisory](https://github.com/la2278647-arch/skillguard/security/advisories/new) 私密报告，见 [SECURITY.md](../SECURITY.md)

---

_文档版本：0.9.0 · 有更多问题？欢迎提 [Issue](https://github.com/la2278647-arch/skillguard/issues)_
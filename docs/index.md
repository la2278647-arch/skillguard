# SkillGuard

**Agent Skills 质量保障与测试框架** — 为 Claude Code / Codex / Cursor 等 AI 编码代理的 Skills 提供静态校验、沙箱测试、质量评分与 CI 集成。

## 为什么需要 SkillGuard？

Agent Skills 生态爆发式增长，但**没有标准工具验证 Skill 是否有效、安全、可维护**。SkillGuard 填补空白：

- 🧹 静态校验（结构/引用/安全扫描）
- 🏜️ 沙箱测试执行（隔离副本，杜绝触碰源目录）
- 🔢 五维质量评分（0-100）+ CI 门禁
- 📄 JSON / Markdown / HTML 多格式报告

## 快速开始

```bash
pip install skillguard
skillguard init my-skill --name my-skill --framework claude-code
skillguard check my-skill --ci
```

## 作为 Python 库

```python
from skillguard import SkillGuard, Config

report = SkillGuard(Config(skill_dir="my-skill")).run()
print(report.overall_score, report.passed)
```

完整文档见 [API 参考](api.md)、[CLI 参考](cli.md)、[架构说明](architecture.md)、[质量规则](rules.md)、[CI 集成](ci.md)。

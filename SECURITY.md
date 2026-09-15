# 安全政策（Security Policy）

SkillGuard 是 Agent Skills 的质量保障工具，它扫描的 Skill 可能包含恶意或危险内容。我们希望安全研究者和用户能够安全地报告漏洞与疑虑。

## 支持的版本

| 版本 | 支持状态 |
|------|----------|
| 0.4.x | ✅ 支持（最新） |
| 0.3.x | ✅ 支持 |
| 0.2.x | ⚠️ 仅安全修复 |
| 0.1.x | ❌ 不再支持 |

## 报告漏洞（Reporting a Vulnerability）

请**不要**创建公开 Issue 报告安全漏洞。请通过以下方式私密报告：

1. **首选**：GitHub Security Advisory -> [New draft advisory](https://github.com/la2278647-arch/skillguard/security/advisories/new)
2. 或发送邮件至项目维护者（GitHub 资料页可见）

请在报告中包含：

- 漏洞类型与影响范围
- 复现步骤（最小化示例）
- 受影响版本
- 建议的修复方案（如有）

我们会在 **48 小时内**确认收到报告，并尽快评估与修复。修复完成前不会公开漏洞细节。

## 安全设计说明

SkillGuard 自身采用以下安全设计：

- **沙箱测试隔离**：测试脚本在 Skill 目录副本中运行，无法触碰源目录
- **环境变量净化**：测试环境丢弃 `AWS_`/`OPENAI_`/`TOKEN` 等敏感前缀变量
- **强制超时**：每个测试脚本有默认超时（60s），防失控
- **报告转义**：HTML 报告转义所有动态内容，防 XSS
- **正则黑名单**：内置 23 条安全模式（SEC-001..015），检测危险命令与密钥泄露

## 使用 SkillGuard 扫描第三方 Skills 的注意

当您使用 `skillguard check` / `scan` / `bench` 扫描**第三方 Skill** 时：

- 静态校验与评分不会执行 Skill 的脚本（安全）
- 运行测试（默认开启）会在沙箱副本中执行，但有 `rm -rf` 等危险模式的 Skill 已被 SEC-001 等规则标记
- 建议先运行 `skillguard check <dir> --no-tests` 做静态检查，确认无 ERROR 级安全规则后再运行测试

感谢您帮助 SkillGuard 变得更安全 🛡️
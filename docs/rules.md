# SkillGuard 质量规则参考

> 全部规则按前缀分类：`SRC`（结构）、`REF`（引用）、`SEC`（安全）、`DOC`（文档）。
> 严重级：🔴 error（必须修复）· 🟡 warning（建议修复）· 🔵 info（提示）

## 结构规则（SRC）

| 规则 | 严重级 | 说明 |
|------|--------|------|
| `SRC-001` | 🔴 | 缺少 SKILL.md / skill.md 入口文件 |
| `SRC-002` | 🔴 | SKILL.md 缺少 name 元数据 |
| `SRC-003` | 🟡 | 缺少 description（AI 无法理解用途） |
| `SRC-004` | 🔵 | scripts/ 存在非常规文件类型 |
| `SRC-005` | 🟡/🔴 | 入口文件过大（>40KB，建议拆分）或为空文件 |

## 引用完整性（REF）

| 规则 | 严重级 | 说明 |
|------|--------|------|
| `REF-001` | 🟡 | SKILL.md 引用的本地脚本/文件不存在 |
| `REF-002` | 🟡 | 引用了 scripts/ 但目录为空 |

## 安全规则（SEC）

| 规则 | 严重级 | 匹配模式 | 说明 |
|------|--------|----------|------|
| `SEC-001` | 🔴 | `rm -f`、`rm -rf /~`、`rm --recursive` | 破坏性删除 |
| `SEC-002` | 🔴 | `mkfs`、`dd if=...of=/dev/` | 磁盘级操作 |
| `SEC-003` | 🟡 | `chmod 777` | 权限过宽 |
| `SEC-004` | 🟡 | `curl\|sh`、`wget\|sh` | 远程管道执行 |
| `SEC-005` | 🔴 | `api_key` 后跟 16+ 位字符串 | 硬编码 API Key |
| `SEC-006` | 🟡 | `token` 后跟 20+ 位字符串 | 硬编码 Token |
| `SEC-007` | 🟡 | `git push --force` | 强制推送风险 |
| `SEC-008` | 🔴 | `eval $(...)` | 动态执行 |
| `SEC-009` | 🔵 | `sudo` | 权限提升操作 |

## 评分权重

| 维度 | 权重 | 规则映射 |
|------|------|----------|
| 结构完整性 structure | 25% | SRC |
| 文档清晰度 documentation | 20% | DOC |
| 安全性 safety | 30% | SEC |
| 可维护性 maintainability | 15% | REF + 脚本加分 |
| 实用性 usability | 10% | 缺失项扣分 + 测试加分 |

## 门禁判定

```
passed = (无 ERROR 检查) 且 (无失败测试) 且 (综合评分 ≥ threshold)
```

默认 `threshold = 60`，可通过 `--threshold` 调整。

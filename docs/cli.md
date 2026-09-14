# SkillGuard CLI 参考

> 版本：0.1.0

## 全局选项

| 选项 | 说明 |
|------|------|
| `--version` | 显示版本号 |
| `--help` | 显示帮助 |

## 命令：`check`

检查一个 Skill 目录的质量。这是最核心的命令。

```bash
skillguard check [OPTIONS] SKILL_DIR
```

`SKILL_DIR` 默认为当前目录 `.`。

### 选项

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--rules TEXT` | `-r` | 全部规则 | 启用指定规则（可多次），如 `-r SEC-001 -r SRC-003` |
| `--no-tests` | — | 关闭 | 跳过测试执行 |
| `--skip-safety` | — | 关闭 | 跳过安全模式扫描 |
| `--timeout INT` | — | `60` | 测试超时秒数 |
| `--threshold FLOAT` | — | `60.0` | 质量门禁分数（0-100） |
| `--format [json\|markdown\|html]` | — | `json` | 报告格式 |
| `--output PATH` | `-o` | 仅打印 | 报告输出路径 |
| `--ci` | — | 关闭 | CI 模式：未通过时退出码 1 |

### 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 评估完成（非 CI 模式无论结果如何）；或 CI 模式通过 |
| `1` | CI 模式未通过质量门禁 |
| `2` | 配置错误 / 目录无有效 Skill |

### 示例

```bash
# 基础检查（打印摘要）
skillguard check .

# 只做静态校验，不跑测试
skillguard check my-skill --no-tests

# 跳过安全扫描
skillguard check my-skill --skip-safety

# 导出 HTML 报告
skillguard check my-skill --format html -o report.html

# 导出 Markdown 报告（适合 PR 评论）
skillguard check my-skill --format markdown -o report.md

# CI 门禁：分数低于 80 或存在 ERROR 即失败
skillguard check my-skill --ci --threshold 80

# 只启用指定规则
skillguard check my-skill -r SEC-001 -r SEC-005

# 调整测试超时为 120 秒
skillguard check my-skill --timeout 120
```

### 摘要输出示例

```
🔍 SkillGuard 评估: my-skill (v0.1.0, claude-code)
  综合评分: 67.0/100  ❌ 未通过
  检查: 4 项 (🔴 2 / 🟡 1 / 🔵 1)
    🔴 [SEC-001] 检测到危险模式: ... (scripts/nuke.sh)
    🔴 [SEC-005] 检测到危险模式: ... (scripts/nuke.sh)
    🔵 [SEC-009] 检测到危险模式: ... (scripts/nuke.sh)
    🟡 [SRC-003] SKILL.md 缺少 description（AI 无法理解用途） (SKILL.md)
  测试: 1 项 (✅ 1 / ❌ 0)
📄 报告已写入: report.html
```

## 命令：`init`

初始化一个 SkillGuard 兼容的 Skill 项目骨架。

```bash
skillguard init [OPTIONS] SKILL_DIR
```

`SKILL_DIR` 默认为当前目录 `.`。

### 选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--name TEXT` | 目录名 | Skill 名称 |
| `--framework [generic\|claude-code\|codex\|cursor]` | `generic` | 目标框架 |

### 创建的内容

```
my-skill/
├── SKILL.md          # 带 YAML front-matter 的模板
└── tests/
    └── smoke.sh      # 冒烟测试（验证 SKILL.md 存在且非空）
```

### 示例

```bash
# 在当前目录初始化
skillguard init

# 指定名称与框架
skillguard init my-skill --name my-skill --framework codex

# 初始化后立即检查
skillguard init demo --framework claude-code
skillguard check demo
```

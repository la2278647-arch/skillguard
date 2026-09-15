# SkillGuard CLI 参考

> 版本：0.7.0

## 全局选项

| 选项 | 说明 |
|------|------|
| `--version` | 显示版本号 |
| `--help` | 显示帮助 |

## 命令：`report`

生成**多 Skill 聚合质量报告**（团队/仓库级总览）——对目录树中全部 Skill 执行完整评估（含沙箱测试），输出聚合统计与明细。

```bash
skillguard report ROOT_DIR
```

### 选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--depth INT` | `3` | 扫描深度 |
| `--format [json\|markdown\|html]` | `markdown` | 报告格式 |
| `--output PATH` | `-o` | 报告输出路径 |
| `--no-tests` | 关闭 | 跳过测试执行（加速） |

### 聚合统计

- Skill 数量 / 平均分 / 通过率
- 累计问题（error/warning 总数）
- 评分分布（90-100 / 75-89 / 60-74 / 40-59 / 0-39）
- 每个 Skill 的分数/状态/问题数/测试结果明细

### 示例

```bash
# Markdown 聚合报告（默认）
skillguard report ./skills

# HTML 报告（适合分享）
skillguard report . --format html -o report.html

# JSON（供 CI 消费）
skillguard report . --format json -o report.json --no-tests
```

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

## 命令：`bench`

对远程 GitHub 仓库执行**生态质量基准扫描**：克隆仓库 → 扫描全部 Skill → 输出聚合质量报告（平均分、通过率、评分分布、Top 排行）。

```bash
skillguard bench REPO_URL
```

### 选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--depth INT` | `2` | 扫描深度 |
| `--max-skills INT` | `200` | 最多扫描的 Skill 数 |
| `--threshold FLOAT` | `60.0` | 质量门禁分数 |
| `--top INT` | `10` | 排行榜显示条数 |
| `--json PATH` | 无 | JSON 报告输出路径 |

### 示例

```bash
# 扫描 Anthropic 官方 Skills
skillguard bench https://github.com/anthropics/skills.git

# 扫描社区仓库并导出 JSON
skillguard bench https://github.com/obra/superpowers.git --max-skills 50 --json bench.json
```

### 输出示例

```
📊 生态质量报告: https://github.com/anthropics/skills.git
  扫描到 15 个 Skill | 平均分 98.5 | 通过率 100%
  累计问题: 🔴 0 error / 🟡 1 warning
  评分分布: 90-100:15  75-89:0  60-74:0  40-59:0  0-39:0

  Top 8 排行:
     1. [ 99.5] ✅ skill-creator                (errors:0)
     2. [ 99.5] ✅ webapp-testing               (errors:0)
     ...
```

---

## 命令：`completion`

输出指定 shell 的自动补全脚本。

```bash
skillguard completion bash      # bash
skillguard completion zsh       # zsh
skillguard completion fish      # fish
skillguard completion powershell # PowerShell
```

### 示例（bash）

```bash
skillguard completion bash > /etc/bash_completion.d/skillguard
source /etc/bash_completion.d/skillguard
```

## 命令：`doctor`

检查 SkillGuard 运行环境是否健康（bash/git/python 检测）。

```bash
skillguard doctor
```

输出示例：

```
🏥 SkillGuard Doctor — v0.2.0
  系统: Windows 10
  Python: 3.10.11
  Shell: C:\WINDOWS\system32\bash.EXE
  Git: /usr/bin/git
  ✅ 环境健康
```

---

## 命令：`schema`

输出 QualityReport 的 JSON Schema，或校验报告文件是否符合 Schema。

```bash
# 输出 Schema（供 CI / 工具链集成）
skillguard schema

# 校验报告文件
skillguard schema report.json
```

输出示例（校验模式）：

```
✅ report.json 符合 SkillGuard JSON Schema
```

---

## 命令：`config`

管理 SkillGuard 配置文件（YAML/TOML）。

```bash
# 生成配置模板
skillguard config --init

# 显示当前生效配置
skillguard config --show [--skill-dir DIR]
```

### 配置文件支持

`check` 命令支持通过 `--config` 指定配置文件，或自动发现（当前目录及父目录中的 `skillguard.yml` / `skillguard.yaml` / `skillguard.toml`）。

```yaml
# skillguard.yml 示例
threshold: 70        # 质量门禁分数
test_timeout: 60     # 测试超时（秒）
skip_safety: false   # 是否跳过安全扫描
run_tests: true      # 是否运行测试
report_format: json  # 报告格式
rules:               # 启用规则（默认全部）
  - SEC-001
```

优先级：`--config` 显式指定 > 自动发现 > 命令行默认值。

---

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

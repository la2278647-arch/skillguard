# SkillGuard 架构说明

> 版本：0.1.0

## 1. 总体架构

SkillGuard 采用**分层流水线**架构，单一数据流（管道式）贯穿全流程：

```
┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ parser  │──▶│ validator│──▶│  runner  │──▶│ scoring  │──▶│ reporting│
│ 加载    │   │ 静态校验  │   │ 沙箱测试  │   │ 质量评分  │   │ 报告输出  │
└─────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
     │              │             │              │              │
     ▼              ▼             ▼              ▼              ▼
  SkillInfo    CheckResult[]  TestResult[]   ScoreBreakdown   JSON/MD/HTML
```

`engine.py` 的 `SkillGuard.run()` 是编排器，按固定顺序调用各阶段，最终产出 `QualityReport`。

## 2. 模块职责

| 模块 | 职责 | 关键不变量 |
|------|------|-----------|
| `config.py` | 不可变配置模型 | 构造时校验参数合法性 |
| `parser.py` | 解析 SKILL.md 元数据、发现脚本 | 元数据解析失败回退键值格式，绝不抛异常 |
| `validator.py` | 结构/引用/安全静态检查 | 输出按严重级排序；单文件读取失败跳过 |
| `runner.py` | 沙箱测试执行 | **测试在 Skill 目录副本中运行**；强制超时；净化环境变量 |
| `scoring.py` | 五维评分 + 门禁判定 | 纯函数，无副作用；分数封顶 0-100 |
| `reporting.py` | 渲染 JSON/Markdown/HTML | HTML 转义所有用户输入，防 XSS |
| `engine.py` | 编排与门禁 | `run()` = 完整流程；`validate()` = 仅静态 |
| `models.py` | 纯数据模型 | 全部可序列化，`QualityReport.from_dict` 可恢复 |
| `cli.py` | 命令行入口 | Windows 强制 UTF-8；CI 模式退出码语义 |

## 3. 设计决策

### 3.1 为什么测试要在沙箱副本中运行？

**背景**：测试脚本可能包含 `rm`、写文件等操作，且通过 `$0` 可回溯到脚本所在目录。

**决策**：`runner.py` 将整个 Skill 目录 `copytree` 到临时目录，脚本在副本中运行，源目录零风险。

**权衡**：复制大目录有开销，但 Skill 通常很小（KB 级）；安全收益远大于性能成本。

### 3.2 为什么评分采用扣分制？

**背景**：加分制下"信息缺失"无法体现——100 分的 Skill 缺 tags 还是 100 分。

**决策**：满分 100 起步，按规则严重级扣分（ERROR 30-50、WARNING 10-15、INFO 2-3），缺失项（无 tags/无脚本/版本不规范）扣分，测试全过加分（封顶 100）。

**效果**：分数真实反映质量差距，可配置阈值做 CI 门禁。

### 3.3 安全扫描为何用正则？

**背景**：Skill 脚本是任意文本，无 AST 可依赖（可能是 bash/python/js 混合）。

**决策**：17 条经过精心设计的正则模式（`DANGEROUS_PATTERNS`），覆盖：
- 破坏性命令：`rm -rf`、`mkfs`、`dd if=...of=/dev/`
- 权限提升：`sudo`、`chmod 777`
- 远程执行：`curl | sh`、`wget | sh`、`eval $(...)`
- 密钥泄露：`api_key`、`token` 硬编码
- 危险 git 操作：`git push --force`

**局限**：正则可能误报/漏报，设计为 WARNING 级为主的提示而非绝对判定。

### 3.4 为什么支持三种报告格式？

| 格式 | 消费方 | 场景 |
|------|--------|------|
| JSON | CI、脚本、工具 | 机器可读，结构化数据 |
| Markdown | 人类 | PR 评论、README 内嵌 |
| HTML | 人类（分享） | 自包含单文件，带样式，可离线打开 |

## 4. 数据流详解

### 4.1 `run()` 完整流程

```
1. load_skill(skill_path)
   ├── 找 SKILL.md / skill.md（向上/指定目录）
   ├── 解析 YAML front-matter（失败回退键值注释）
   └── 发现 scripts/ 脚本 → SkillInfo

2. run_static_checks(skill_path, skill)
   ├── 结构检查：入口存在、名称、描述、脚本目录、体积
   ├── 引用检查：SKILL.md 引用的本地文件是否存在
   └── 安全扫描：对全部文本文件跑 17 条危险模式

3. run_test_scripts(skill_path, [])
   ├── 发现 tests/、test/ 下 .sh/.py/.js/.ts
   ├── copytree 整个 Skill 目录到临时目录
   └── 逐个运行，记录 通过/失败/超时/错误

4. score_skill(skill, checks, tests)
   └── 五维扣分制 → ScoreBreakdown + overall

5. evaluate_passed(report, threshold)
   └── 无 ERROR + 无失败测试 + 分数 ≥ threshold → passed
```

### 4.2 门禁判定

```
passed = (error_count == 0)
      and (failed_tests == 0)
      and (overall_score >= threshold)
```

## 5. 安全设计

| 层面 | 措施 |
|------|------|
| **测试隔离** | Skill 目录副本中运行；源目录只读 |
| **超时控制** | 每个脚本强制超时（默认 60s），防失控 |
| **环境净化** | 丢弃 `AWS_`/`OPENAI_`/`TOKEN` 等敏感前缀变量 |
| **报告安全** | HTML 报告转义所有动态内容，防 XSS |
| **文件容错** | 不可读文件跳过，不中断整个评估 |

## 6. 扩展点

### 6.1 新增安全规则

在 `validator.py` 的 `DANGEROUS_PATTERNS` 追加元组：

```python
("SEC-010", r"\bcurl\s+-k\b", Severity.WARNING),
```

### 6.2 新增报告格式

在 `reporting.py` 添加渲染函数并注册到 `render_report()` 的分发。

### 6.3 自定义 CLI

在 `cli.py` 用 `@main.command()` 添加新命令，复用 `SkillGuard` 引擎。

## 7. 测试策略

- **单元测试**：每个模块独立测试（parser/validator/runner/scoring/reporting）
- **集成测试**：`tests/test_engine.py` 用真实 Skill 目录跑完整流程
- **CLI 测试**：`click.testing.CliRunner` 端到端
- **覆盖率**：99.45%（pytest-cov 门禁 ≥ 95%）
- **质量门禁**：ruff 全部通过

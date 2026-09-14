# SkillGuard API 参考

> 版本：0.1.0 · 适用 Python ≥ 3.10

SkillGuard 提供两种使用方式：**CLI**（`skillguard` 命令）与 **Python 库**（`skillguard` 包）。本文档覆盖 Python API。

---

## 快速示例

```python
from skillguard import SkillGuard, Config
from skillguard.models import QualityReport

# 1. 配置
config = Config(
    skill_dir="path/to/skill",   # 必填：Skill 目录
    run_tests=True,              # 是否运行沙箱测试（默认 True）
    test_timeout=60,             # 测试超时（秒）
    skip_safety=False,           # 是否跳过安全扫描
    report_format="json",        # json / markdown / html
    threshold=60.0,              # CI 质量门禁分数
)

# 2. 执行
guard = SkillGuard(config)
report: QualityReport = guard.run()

# 3. 消费结果
print(report.overall_score)          # 综合评分 0-100
print(report.passed)                 # 是否通过门禁
print(report.error_count())          # 错误级检查数
print(report.failed_tests())         # 失败测试数
for check in report.checks:
    print(check.rule_id, check.severity, check.message)
```

---

## 类：`Config`

不可变配置对象（`frozen dataclass`）。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `skill_dir` | `str` | `"."` | 目标 Skill 目录路径 |
| `rules` | `tuple[str, ...]` | `()` | 启用的规则 ID 列表；空 = 全部内置规则 |
| `run_tests` | `bool` | `True` | 是否在沙箱中运行测试脚本 |
| `test_timeout` | `int` | `60` | 单个测试脚本超时秒数（必须 > 0） |
| `skip_safety` | `bool` | `False` | 是否跳过安全模式扫描 |
| `report_format` | `str` | `"json"` | 报告格式：`json` / `markdown` / `html` |
| `report_output` | `str \| None` | `None` | 报告输出路径 |
| `threshold` | `float` | `60.0` | 质量门禁分数（0-100） |

**方法**：

- `Config.with_overrides(**kwargs) -> Config` — 返回应用部分覆盖的新配置（不修改原对象）。
- 属性 `skill_path: Path` — 解析后的绝对路径。

**异常**：`ValueError` — 参数非法时抛出（timeout ≤ 0、threshold 越界、格式不支持）。

```python
c = Config(skill_dir="s", threshold=80)
c2 = c.with_overrides(run_tests=False)   # threshold 仍为 80
```

---

## 类：`SkillGuard`

主入口类。

### `SkillGuard(config: Config | None = None)`

构造器。`config` 缺省时使用 `Config()`。

### `run() -> QualityReport`

执行完整评估流程：

1. **加载**：解析 `SKILL.md` 元数据（YAML front-matter 优先，键值注释回退）
2. **校验**：静态检查（结构/引用/安全），除非 `skip_safety`
3. **测试**：发现 `tests/`、`test/` 目录脚本（.sh/.py/.js/.ts），复制整个 Skill 目录到沙箱后运行
4. **评分**：五维评分 + 综合分
5. **门禁**：`evaluate_passed()` 判定

**异常**：`ValueError` — 目录不含有效 `SKILL.md`/`skill.md` 时抛出。

### `validate() -> QualityReport`

仅执行静态校验（不运行测试）。仍计算评分，但门禁判定只基于分数阈值。

### `render(report: QualityReport, fmt: str | None = None) -> str`

将报告渲染为字符串。`fmt` 缺省使用配置的 `report_format`。

### `export(report: QualityReport, output: str | Path) -> Path`

将报告写入文件。格式按扩展名推断：`.json` / `.md` / `.markdown` / `.html`；其他扩展名回退到配置格式。返回写入路径。

---

## 数据模型（`skillguard.models`）

### `SkillInfo`

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | Skill 名称（元数据缺失时用目录名） |
| `description` | `str` | 描述 |
| `version` | `str` | 版本号 |
| `framework` | `str` | 目标框架：`generic` / `claude-code` / `codex` / `cursor` |
| `author` | `str` | 作者 |
| `tags` | `list[str]` | 标签列表 |
| `entrypoint` | `str` | 入口文件名 |
| `has_scripts` | `bool` | 是否存在脚本 |
| `script_count` | `int` | 脚本数量 |

### `CheckResult`

| 字段 | 类型 | 说明 |
|------|------|------|
| `rule_id` | `str` | 规则 ID（如 `SEC-001`） |
| `severity` | `Severity` | `error` / `warning` / `info` |
| `message` | `str` | 问题描述 |
| `file` | `str` | 相关文件 |
| `line` | `int \| None` | 行号 |

方法：`to_dict()`。

### `Severity`（枚举）

- `Severity.ERROR` — 必须修复
- `Severity.WARNING` — 建议修复
- `Severity.INFO` — 提示

### `TestResult`

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 测试脚本相对路径 |
| `outcome` | `TestOutcome` | `passed` / `failed` / `skipped` / `error` |
| `duration_ms` | `float` | 耗时（毫秒） |
| `detail` | `str` | 输出详情（截断 500 字符） |

### `ScoreBreakdown`

五维评分（各 0-100）：

- `structure` — 结构完整性
- `documentation` — 文档清晰度
- `safety` — 安全性
- `maintainability` — 可维护性
- `usability` — 实用性

### `QualityReport`

| 字段 | 类型 | 说明 |
|------|------|------|
| `skill` | `SkillInfo` | Skill 信息 |
| `version` | `str` | 工具版本 |
| `timestamp` | `str` | ISO 时间戳 |
| `checks` | `list[CheckResult]` | 检查结果 |
| `tests` | `list[TestResult]` | 测试结果 |
| `score` | `ScoreBreakdown` | 分项评分 |
| `overall_score` | `float` | 综合评分 |
| `passed` | `bool` | 是否通过门禁 |

**方法**：

- `error_count() / warning_count() / info_count()` — 各级检查数量
- `passed_tests() / failed_tests()` — 测试统计
- `to_dict() -> dict` — 序列化为字典
- `to_json(indent=2) -> str` — 序列化为 JSON（UTF-8 保留中文）
- `from_dict(data) -> QualityReport` — 从字典恢复

---

## 底层模块（进阶使用）

| 模块 | 函数 | 说明 |
|------|------|------|
| `skillguard.parser` | `load_skill(dir) -> SkillInfo \| None` | 加载 Skill |
| | `parse_skill_metadata(entry) -> dict` | 解析元数据 |
| | `discover_scripts(dir) -> list[Path]` | 发现脚本 |
| | `find_skill_dir(start) -> Path \| None` | 向上查找 Skill 目录 |
| `skillguard.validator` | `run_static_checks(dir, skill, skip_safety=False) -> list[CheckResult]` | 静态校验 |
| `skillguard.runner` | `run_test_scripts(dir, scripts, timeout=60) -> list[TestResult]` | 沙箱测试 |
| `skillguard.scoring` | `score_skill(skill, checks, tests) -> tuple[ScoreBreakdown, float]` | 评分 |
| | `evaluate_passed(report, threshold) -> bool` | 门禁判定 |
| `skillguard.reporting` | `render_report(report, fmt) -> str` | 渲染报告 |
| | `write_report(report, output, fmt) -> Path` | 写入报告 |

---

## 错误处理

| 场景 | 行为 |
|------|------|
| 目录无 `SKILL.md` | `run()`/`validate()` 抛 `ValueError` |
| 配置非法 | `Config` 构造抛 `ValueError` |
| 测试脚本超时 | 对应 `TestResult.outcome == ERROR` |
| 测试脚本启动失败 | 对应 `TestResult.outcome == ERROR`，`detail` 含原因 |
| 安全扫描文件不可读 | 跳过该文件，不中断 |

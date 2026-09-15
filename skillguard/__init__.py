"""SkillGuard — Agent Skills 质量保障与测试框架。

SkillGuard 为 Claude Code / Codex / Cursor 等 AI 编码代理的 Skills 提供：
- 静态校验（结构、引用完整性、安全模式扫描）
- 沙箱测试执行
- 质量评分与改进建议
- 多格式评估报告（JSON / Markdown / HTML）
- CI 集成质量门禁

公共 API：

    from skillguard import SkillGuard, Config
    from skillguard.models import SkillInfo, CheckResult, Severity, QualityReport

    guard = SkillGuard(Config(skill_dir="path/to/skill"))
    report = guard.run()          # 完整评估（校验+测试+评分）
    report = guard.validate()     # 仅静态校验
"""

from __future__ import annotations

from .config import Config
from .engine import SkillGuard
from .models import (
    CheckResult,
    QualityReport,
    Severity,
    SkillInfo,
    TestOutcome,
)
from .version import __version__

__all__ = [
    "CheckResult",
    "Config",
    "QualityReport",
    "Severity",
    "SkillGuard",
    "SkillInfo",
    "TestOutcome",
    "__version__",
]

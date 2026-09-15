"""数据模型：SkillGuard 的核心领域对象。

所有模型均为纯数据类（不持有运行时对象），可安全序列化为 JSON。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    """检查问题的严重级别。"""

    ERROR = "error"      # 必须修复：Skill 无法正常工作
    WARNING = "warning"  # 建议修复：可能存在问题
    INFO = "info"        # 提示信息


class TestOutcome(str, Enum):
    """测试执行结果。"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class CheckResult:
    """单条静态检查结果。"""

    rule_id: str
    severity: Severity
    message: str
    file: str = ""
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }


@dataclass
class TestResult:
    """单条测试执行结果。"""

    name: str
    outcome: TestOutcome
    duration_ms: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "outcome": self.outcome.value,
            "duration_ms": round(self.duration_ms, 2),
            "detail": self.detail,
        }


@dataclass
class SkillInfo:
    """Skill 的基础信息（从 SKILL.md 元数据解析）。"""

    name: str
    description: str = ""
    version: str = "0.0.0"
    framework: str = "unknown"  # claude-code / codex / cursor / generic
    author: str = ""
    tags: list[str] = field(default_factory=list)
    entrypoint: str = ""        # SKILL.md 或 scripts/*.sh 等
    has_scripts: bool = False
    script_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreBreakdown:
    """质量评分的分项明细。"""

    structure: float = 0.0      # 结构完整性
    documentation: float = 0.0  # 文档清晰度
    safety: float = 0.0         # 安全性
    maintainability: float = 0.0  # 可维护性
    usability: float = 0.0      # 实用性

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualityReport:
    """一次完整评估的输出报告。"""

    skill: SkillInfo
    version: str
    timestamp: str
    checks: list[CheckResult] = field(default_factory=list)
    tests: list[TestResult] = field(default_factory=list)
    score: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    overall_score: float = 0.0
    passed: bool = False

    # ------------------------------------------------------------------
    # 便捷统计
    # ------------------------------------------------------------------
    def error_count(self) -> int:
        return sum(1 for c in self.checks if c.severity == Severity.ERROR)

    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.severity == Severity.WARNING)

    def info_count(self) -> int:
        return sum(1 for c in self.checks if c.severity == Severity.INFO)

    def passed_tests(self) -> int:
        return sum(1 for t in self.tests if t.outcome == TestOutcome.PASSED)

    def failed_tests(self) -> int:
        return sum(1 for t in self.tests if t.outcome == TestOutcome.FAILED)

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "skill": self.skill.to_dict(),
            "tool": "skillguard",
            "tool_version": self.version,
            "timestamp": self.timestamp,
            "summary": {
                "checks": {
                    "total": len(self.checks),
                    "errors": self.error_count(),
                    "warnings": self.warning_count(),
                    "infos": self.info_count(),
                },
                "tests": {
                    "total": len(self.tests),
                    "passed": self.passed_tests(),
                    "failed": self.failed_tests(),
                },
                "score": {
                    "overall": round(self.overall_score, 2),
                    "breakdown": self.score.to_dict(),
                },
                "passed": self.passed,
            },
            "checks": [c.to_dict() for c in self.checks],
            "tests": [t.to_dict() for t in self.tests],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityReport:
        """从 dict 恢复报告（用于测试与外部消费）。"""
        skill = SkillInfo(**data["skill"])
        checks = [
            CheckResult(
                rule_id=c["rule_id"],
                severity=Severity(c["severity"]),
                message=c["message"],
                file=c.get("file", ""),
                line=c.get("line"),
            )
            for c in data.get("checks", [])
        ]
        tests = [
            TestResult(
                name=t["name"],
                outcome=TestOutcome(t["outcome"]),
                duration_ms=t.get("duration_ms", 0.0),
                detail=t.get("detail", ""),
            )
            for t in data.get("tests", [])
        ]
        score = ScoreBreakdown(**data["summary"]["score"]["breakdown"])
        summary = data["summary"]
        return cls(
            skill=skill,
            version=data.get("tool_version", ""),
            timestamp=data.get("timestamp", ""),
            checks=checks,
            tests=tests,
            score=score,
            overall_score=summary["score"]["overall"],
            passed=summary.get("passed", False),
        )


def now_iso() -> str:
    """返回当前 UTC 时间的 ISO 字符串。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_dir_path(report: QualityReport) -> Path:
    """从报告反推 Skill 目录（辅助函数，供测试使用）。"""
    return Path(report.skill.name)

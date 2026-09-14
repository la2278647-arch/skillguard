"""测试：数据模型。"""

from __future__ import annotations

import json
from pathlib import Path

from skillguard.models import (
    CheckResult,
    QualityReport,
    ScoreBreakdown,
    Severity,
    SkillInfo,
    TestOutcome,
    TestResult,
    now_iso,
)


class TestSeverity:
    def test_values(self) -> None:
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"

    def test_from_value(self) -> None:
        assert Severity("error") is Severity.ERROR


class TestCheckResult:
    def test_to_dict(self) -> None:
        r = CheckResult("SEC-001", Severity.ERROR, "危险", file="a.sh", line=3)
        d = r.to_dict()
        assert d["rule_id"] == "SEC-001"
        assert d["severity"] == "error"
        assert d["file"] == "a.sh"
        assert d["line"] == 3

    def test_to_dict_defaults(self) -> None:
        r = CheckResult("SRC-001", Severity.INFO, "msg")
        d = r.to_dict()
        assert d["file"] == ""
        assert d["line"] is None


class TestTestResult:
    def test_to_dict(self) -> None:
        t = TestResult("smoke.sh", TestOutcome.PASSED, duration_ms=12.345, detail="ok")
        d = t.to_dict()
        assert d["name"] == "smoke.sh"
        assert d["outcome"] == "passed"
        assert d["duration_ms"] == 12.35  # 四舍五入

    def test_defaults(self) -> None:
        t = TestResult("x", TestOutcome.SKIPPED)
        assert t.duration_ms == 0.0
        assert t.detail == ""


class TestSkillInfo:
    def test_to_dict(self) -> None:
        s = SkillInfo(name="demo", tags=["a", "b"])
        d = s.to_dict()
        assert d["name"] == "demo"
        assert d["tags"] == ["a", "b"]
        assert d["version"] == "0.0.0"
        assert d["script_count"] == 0


class TestScoreBreakdown:
    def test_defaults_zero(self) -> None:
        b = ScoreBreakdown()
        assert b.structure == 0.0
        assert b.documentation == 0.0
        assert b.safety == 0.0
        assert b.maintainability == 0.0
        assert b.usability == 0.0

    def test_to_dict(self) -> None:
        b = ScoreBreakdown(structure=10, safety=20)
        d = b.to_dict()
        assert d["structure"] == 10
        assert d["safety"] == 20


class TestQualityReport:
    def _make_report(self) -> QualityReport:
        return QualityReport(
            skill=SkillInfo(name="demo", version="1.0.0"),
            version="0.1.0",
            timestamp="2024-01-01T00:00:00+00:00",
            checks=[
                CheckResult("SEC-001", Severity.ERROR, "bad"),
                CheckResult("SRC-003", Severity.WARNING, "warn"),
                CheckResult("SRC-004", Severity.INFO, "info"),
            ],
            tests=[
                TestResult("t1", TestOutcome.PASSED),
                TestResult("t2", TestOutcome.FAILED),
                TestResult("t3", TestOutcome.PASSED),
            ],
            score=ScoreBreakdown(structure=80, safety=50),
            overall_score=70.0,
            passed=False,
        )

    def test_counts(self) -> None:
        r = self._make_report()
        assert r.error_count() == 1
        assert r.warning_count() == 1
        assert r.info_count() == 1
        assert r.passed_tests() == 2
        assert r.failed_tests() == 1

    def test_to_dict_roundtrip(self) -> None:
        r = self._make_report()
        data = r.to_dict()
        assert data["tool"] == "skillguard"
        assert data["summary"]["checks"]["total"] == 3
        assert data["summary"]["score"]["overall"] == 70.0
        restored = QualityReport.from_dict(data)
        assert restored.skill.name == "demo"
        assert restored.error_count() == 1
        assert restored.passed_tests() == 2
        assert restored.overall_score == 70.0
        assert restored.score.structure == 80.0

    def test_to_json_valid(self) -> None:
        r = self._make_report()
        parsed = json.loads(r.to_json())
        assert parsed["summary"]["passed"] is False


class TestNowIso:
    def test_format(self) -> None:
        ts = now_iso()
        assert "+00:00" in ts or "Z" in ts
        assert len(ts) >= 19

    def test_skill_dir_path_helper(self) -> None:
        from skillguard.models import skill_dir_path

        report = QualityReport(skill=SkillInfo(name="helper-skill"), version="v", timestamp="t")
        assert skill_dir_path(report) == Path("helper-skill")

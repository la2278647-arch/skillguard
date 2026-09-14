"""测试：报告生成器。"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillguard.models import (
    CheckResult,
    QualityReport,
    ScoreBreakdown,
    Severity,
    SkillInfo,
    TestOutcome,
    TestResult,
)
from skillguard.reporting import render_report, write_report


def _sample_report() -> QualityReport:
    return QualityReport(
        skill=SkillInfo(name="demo", description="示例", version="1.0.0", framework="claude-code"),
        version="0.1.0",
        timestamp="2024-06-01T10:00:00+00:00",
        checks=[
            CheckResult("SEC-001", Severity.ERROR, "危险命令", file="a.sh"),
            CheckResult("SRC-003", Severity.WARNING, "缺描述", file="SKILL.md"),
        ],
        tests=[
            TestResult("tests/ok.sh", TestOutcome.PASSED, duration_ms=5.0, detail="ok"),
            TestResult("tests/bad.sh", TestOutcome.FAILED, duration_ms=8.0, detail="boom"),
        ],
        score=ScoreBreakdown(structure=80, documentation=90, safety=50, maintainability=85, usability=70),
        overall_score=72.5,
        passed=False,
    )


class TestRenderJson:
    def test_renders(self) -> None:
        out = render_report(_sample_report(), "json")
        assert '"skill"' in out
        assert '"overall": 72.5' in out
        assert '"passed": false' in out

    def test_unicode_preserved(self) -> None:
        out = render_report(_sample_report(), "json")
        assert "示例" in out  # ensure_ascii=False


class TestRenderMarkdown:
    def test_renders_sections(self) -> None:
        out = render_report(_sample_report(), "markdown")
        assert "# SkillGuard 评估报告" in out
        assert "## 检查明细" in out
        assert "## 测试结果" in out
        assert "## 评分明细" in out
        assert "72.5" in out
        assert "SEC-001" in out

    def test_empty_checks_ok(self) -> None:
        report = _sample_report()
        report.checks = []
        out = render_report(report, "markdown")
        assert "0" in out


class TestRenderHtml:
    def test_renders(self) -> None:
        out = render_report(_sample_report(), "html")
        assert "<!DOCTYPE html>" in out
        assert "SkillGuard 评估报告" in out
        assert 'class="badge pass"' not in out
        assert 'class="badge fail"' in out
        assert "结构完整性" in out
        assert "demo" in out

    def test_escapes_html(self) -> None:
        report = _sample_report()
        report.skill = SkillInfo(name="<script>alert(1)</script>")
        out = render_report(report, "html")
        assert "<script>alert" not in out
        assert "&lt;script&gt;" in out

    def test_passed_badge(self) -> None:
        report = _sample_report()
        report.passed = True
        out = render_report(report, "html")
        assert 'class="badge pass"' in out


class TestWriteReport:
    def test_writes_file(self, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "report.json"
        result = write_report(_sample_report(), out, "json")
        assert result == out
        assert out.exists()
        assert '"skill"' in out.read_text(encoding="utf-8")

    def test_writes_markdown(self, tmp_path: Path) -> None:
        out = tmp_path / "report.md"
        write_report(_sample_report(), out, "markdown")
        assert "# SkillGuard" in out.read_text(encoding="utf-8")

    def test_invalid_format(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            render_report(_sample_report(), "xml")

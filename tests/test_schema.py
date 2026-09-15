"""测试：JSON Schema 输出与校验。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from skillguard.cli import schema_cmd
from skillguard.models import (
    CheckResult,
    QualityReport,
    ScoreBreakdown,
    Severity,
    SkillInfo,
    TestOutcome,
    TestResult,
)
from skillguard.schema import QUALITY_REPORT_SCHEMA


def _report_dict() -> dict:
    report = QualityReport(
        skill=SkillInfo(name="demo", version="1.0.0", framework="claude-code", tags=["a"]),
        version="0.1.0",
        timestamp="2026-09-15T00:00:00+00:00",
        checks=[
            CheckResult("SEC-001", Severity.ERROR, "bad", file="x.sh"),
            CheckResult("SRC-003", Severity.WARNING, "warn", file="SKILL.md", line=3),
        ],
        tests=[TestResult("t.sh", TestOutcome.PASSED, duration_ms=5.0, detail="ok")],
        score=ScoreBreakdown(structure=80, documentation=90, safety=50, maintainability=85, usability=70),
        overall_score=75.0,
        passed=False,
    )
    return report.to_dict()


class TestSchemaContent:
    def test_required_top_level_keys(self) -> None:
        assert set(QUALITY_REPORT_SCHEMA["required"]) == {
            "skill", "tool", "tool_version", "timestamp", "summary", "checks", "tests"
        }

    def test_tool_const(self) -> None:
        assert QUALITY_REPORT_SCHEMA["properties"]["tool"]["const"] == "skillguard"

    def test_severity_enum(self) -> None:
        sev = QUALITY_REPORT_SCHEMA["properties"]["checks"]["items"]["properties"]["severity"]
        assert sev["enum"] == ["error", "warning", "info"]


class TestSchemaValidation:
    def test_valid_report_passes(self) -> None:
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema 未安装")
        jsonschema.validate(_report_dict(), QUALITY_REPORT_SCHEMA)

    def test_missing_field_fails(self) -> None:
        try:
            import jsonschema
            from jsonschema import ValidationError
        except ImportError:
            pytest.skip("jsonschema 未安装")
        data = _report_dict()
        del data["summary"]
        with pytest.raises(ValidationError):
            jsonschema.validate(data, QUALITY_REPORT_SCHEMA)


class TestSchemaCLI:
    def test_output_schema(self) -> None:
        runner = CliRunner()
        result = runner.invoke(schema_cmd, [])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["title"] == "SkillGuard Quality Report"

    def test_validate_valid_report(self, tmp_path: Path) -> None:
        runner = CliRunner()
        f = tmp_path / "report.json"
        f.write_text(json.dumps(_report_dict(), ensure_ascii=False), encoding="utf-8")
        result = runner.invoke(schema_cmd, [str(f)])
        assert result.exit_code == 0
        assert "符合" in result.output

    def test_validate_invalid_json(self, tmp_path: Path) -> None:
        runner = CliRunner()
        f = tmp_path / "bad.json"
        f.write_text("{not json", encoding="utf-8")
        result = runner.invoke(schema_cmd, [str(f)])
        assert result.exit_code == 2

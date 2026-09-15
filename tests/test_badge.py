"""测试：评分徽章生成器。"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from skillguard.badge import _hex_color, _score_color, badge_markdown, render_badge, write_badge
from skillguard.cli import badge
from skillguard.models import QualityReport, ScoreBreakdown, SkillInfo


def _report(score: float, passed: bool = True) -> QualityReport:
    return QualityReport(
        skill=SkillInfo(name="demo", version="1.0.0"),
        version="0.1.0",
        timestamp="t",
        score=ScoreBreakdown(),
        overall_score=score,
        passed=passed,
    )


class TestScoreColor:
    def test_thresholds(self) -> None:
        assert _score_color(95) == "brightgreen"
        assert _score_color(80) == "green"
        assert _score_color(65) == "yellowgreen"
        assert _score_color(50) == "yellow"
        assert _score_color(20) == "red"

    def test_boundaries(self) -> None:
        assert _score_color(90) == "brightgreen"
        assert _score_color(89.9) == "green"
        assert _score_color(75) == "green"
        assert _score_color(74.9) == "yellowgreen"
        assert _score_color(60) == "yellowgreen"
        assert _score_color(59.9) == "yellow"
        assert _score_color(40) == "yellow"
        assert _score_color(39.9) == "red"

    def test_hex_map(self) -> None:
        assert _hex_color("brightgreen") == "#4c1"
        assert _hex_color("red") == "#e05d44"


class TestRenderBadge:
    def test_contains_score(self) -> None:
        svg = render_badge(95.0, passed=True)
        assert svg.startswith("<svg")
        assert "95/100" in svg
        assert "✅" in svg
        assert "#4c1" in svg  # 高分绿色

    def test_failed_badge(self) -> None:
        svg = render_badge(30.0, passed=False)
        assert "❌" in svg
        assert "#e05d44" in svg  # 低分红色

    def test_label_default(self) -> None:
        svg = render_badge(80.0)
        assert "skillguard" in svg

    def test_custom_label(self) -> None:
        svg = render_badge(80.0, label="my-skill")
        assert "my-skill" in svg

    def test_escapes_html(self) -> None:
        svg = render_badge(80.0, label='<script>x</script>')
        assert "<script>" not in svg
        assert "&lt;script&gt;" in svg

    def test_plastic_style(self) -> None:
        svg = render_badge(80.0, style="plastic")
        assert "linearGradient" in svg


class TestWriteBadge:
    def test_writes_file(self, tmp_path: Path) -> None:
        out = tmp_path / "badge.svg"
        result = write_badge(_report(88.0), out)
        assert result == out
        assert out.exists()
        assert "88/100" in out.read_text(encoding="utf-8")

    def test_markdown_snippet(self) -> None:
        md = badge_markdown("badge.svg")
        assert "![SkillGuard](badge.svg)" in md

    def test_markdown_with_link(self) -> None:
        md = badge_markdown("badge.svg", "https://github.com/x/y")
        assert "[![SkillGuard](badge.svg)](https://github.com/x/y)" in md


class TestBadgeCLI:
    def test_generates_badge(self, good_skill: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        out = tmp_path / "b.svg"
        result = runner.invoke(badge, [str(good_skill), "-o", str(out)])
        assert result.exit_code == 0
        assert "徽章已生成" in result.output
        assert out.exists()

    def test_markdown_output(self, good_skill: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        out = tmp_path / "b.svg"
        result = runner.invoke(badge, [str(good_skill), "-o", str(out), "--markdown"])
        assert result.exit_code == 0
        assert "README 嵌入片段" in result.output
        assert "![SkillGuard]" in result.output

    def test_invalid_skill(self, tmp_path: Path) -> None:
        runner = CliRunner()
        empty = tmp_path / "empty"
        empty.mkdir()
        result = runner.invoke(badge, [str(empty)])
        assert result.exit_code == 2

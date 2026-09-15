"""测试：聚合报告（多 Skill 质量总览）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from skillguard.cli import report_cmd
from skillguard.reporting import aggregate_summary, render_aggregate


def _items() -> list[dict]:
    """构造 3 个 Skill 的聚合数据。"""
    return [
        {
            "path": "a", "name": "alpha", "score": 95.0, "passed": True,
            "errors": 0, "warnings": 1, "tests": 2, "tests_passed": 2,
        },
        {
            "path": "b", "name": "beta", "score": 70.0, "passed": True,
            "errors": 0, "warnings": 4, "tests": 1, "tests_passed": 1,
        },
        {
            "path": "c", "name": "gamma", "score": 30.0, "passed": False,
            "errors": 3, "warnings": 2, "tests": 0, "tests_passed": 0,
        },
    ]


class TestAggregateSummary:
    def test_counts(self) -> None:
        s = aggregate_summary(_items())
        assert s["skill_count"] == 3
        assert s["total_errors"] == 3
        assert s["total_warnings"] == 7
        assert s["total_tests"] == 3

    def test_avg_score(self) -> None:
        s = aggregate_summary(_items())
        assert abs(s["avg_score"] - 65.0) < 0.01

    def test_pass_rate(self) -> None:
        s = aggregate_summary(_items())
        assert abs(s["pass_rate"] - 0.67) < 0.01

    def test_distribution(self) -> None:
        s = aggregate_summary(_items())
        assert s["score_distribution"] == {"90-100": 1, "75-89": 0, "60-74": 1, "40-59": 0, "0-39": 1}

    def test_empty(self) -> None:
        s = aggregate_summary([])
        assert s["skill_count"] == 0
        assert s["avg_score"] == 0.0

    def test_all_five_buckets(self) -> None:
        """覆盖全部 5 个评分分档（90+/75-89/60-74/40-59/0-39）。"""
        items = _items() + [
            {"path": "d", "name": "delta", "score": 80.0, "passed": True,
             "errors": 0, "warnings": 0, "tests": 0, "tests_passed": 0},
            {"path": "e", "name": "epsilon", "score": 45.0, "passed": False,
             "errors": 2, "warnings": 0, "tests": 0, "tests_passed": 0},
        ]
        s = aggregate_summary(items)
        assert s["score_distribution"] == {
            "90-100": 1, "75-89": 1, "60-74": 1, "40-59": 1, "0-39": 1,
        }
        assert s["skill_count"] == 5


class TestRenderAggregate:
    def test_json(self) -> None:
        out = render_aggregate(_items(), "json")
        import json

        parsed = json.loads(out)
        assert parsed["summary"]["skill_count"] == 3
        assert len(parsed["skills"]) == 3

    def test_markdown(self) -> None:
        out = render_aggregate(_items(), "markdown", title="团队 Skill 质量")
        assert "# 团队 Skill 质量" in out
        assert "Skill 明细" in out
        assert "alpha" in out
        assert "gamma" in out
        assert "通过率" in out

    def test_html(self) -> None:
        out = render_aggregate(_items(), "html")
        assert "<!DOCTYPE html>" in out
        assert "Skill 数量" in out
        assert "alpha" in out
        assert "gamma" in out

    def test_escapes_html(self) -> None:
        items = _items()
        items[0]["name"] = "<script>x</script>"
        out = render_aggregate(items, "html")
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError):
            render_aggregate(_items(), "xml")


class TestReportCLI:
    def _make_tree(self, tmp_path: Path) -> Path:
        for name in ("a", "b"):
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: d\nversion: 1.0.0\n---\n# {name}\n",
                encoding="utf-8",
            )
        return tmp_path

    def test_report_default(self, tmp_path: Path) -> None:
        tree = self._make_tree(tmp_path)
        result = CliRunner().invoke(report_cmd, [str(tree)])
        assert result.exit_code == 0
        assert "聚合报告" in result.output
        assert "2 个 Skill" in result.output

    def test_report_json_output(self, tmp_path: Path) -> None:
        tree = self._make_tree(tmp_path)
        out = tmp_path / "agg.json"
        result = CliRunner().invoke(report_cmd, [str(tree), "--format", "json", "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert '"skill_count": 2' in out.read_text(encoding="utf-8")

    def test_report_html_output(self, tmp_path: Path) -> None:
        tree = self._make_tree(tmp_path)
        out = tmp_path / "agg.html"
        result = CliRunner().invoke(report_cmd, [str(tree), "--format", "html", "-o", str(out)])
        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in out.read_text(encoding="utf-8")

    def test_report_empty(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(report_cmd, [str(tmp_path)])
        assert result.exit_code == 0
        assert "未在目录树中发现" in result.output

    def test_report_with_workers(self, tmp_path: Path) -> None:
        """--workers 参数应正常传递并工作。"""
        tree = self._make_tree(tmp_path)
        out = tmp_path / "agg.json"
        result = CliRunner().invoke(report_cmd, [str(tree), "--workers", "2", "--format", "json", "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert '"skill_count": 2' in out.read_text(encoding="utf-8")
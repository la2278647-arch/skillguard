"""SkillGuard 核心引擎：编排校验、测试、评分与报告。"""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .models import QualityReport, now_iso
from .parser import load_skill
from .reporting import render_report, write_report
from .runner import run_test_scripts
from .scoring import evaluate_passed, score_skill
from .validator import run_static_checks
from .version import __version__


class SkillGuard:
    """SkillGuard 主入口。

    Usage:
        guard = SkillGuard(Config(skill_dir="path/to/skill"))
        report = guard.run()          # 完整评估
        report = guard.validate()     # 仅静态校验
        guard.export(report, "report.html")  # 导出报告文件
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def run(self) -> QualityReport:
        """执行完整评估：加载 → 校验 → 测试 → 评分 → 门禁判定。"""
        skill_path = self.config.skill_path
        skill = load_skill(skill_path)
        if skill is None:
            raise ValueError(
                f"未在 {skill_path} 找到有效的 Skill 目录（需要 SKILL.md 或 skill.md）"
            )

        checks = run_static_checks(skill_path, skill, skip_safety=self.config.skip_safety)
        tests = []
        if self.config.run_tests:
            tests = run_test_scripts(skill_path, [], timeout=self.config.test_timeout)

        score_breakdown, overall = score_skill(skill, checks, tests)
        report = QualityReport(
            skill=skill,
            version=__version__,
            timestamp=now_iso(),
            checks=checks,
            tests=tests,
            score=score_breakdown,
            overall_score=overall,
            passed=False,
        )
        report.passed = evaluate_passed(report, self.config.threshold)
        return report

    def validate(self) -> QualityReport:
        """仅执行静态校验（不运行测试、不评分门禁）。"""
        skill_path = self.config.skill_path
        skill = load_skill(skill_path)
        if skill is None:
            raise ValueError(f"未在 {skill_path} 找到有效的 Skill 目录")
        checks = run_static_checks(skill_path, skill, skip_safety=self.config.skip_safety)
        score_breakdown, overall = score_skill(skill, checks, [])
        report = QualityReport(
            skill=skill,
            version=__version__,
            timestamp=now_iso(),
            checks=checks,
            score=score_breakdown,
            overall_score=overall,
            passed=overall >= self.config.threshold,
        )
        return report

    # ------------------------------------------------------------------
    # 输出
    # ------------------------------------------------------------------
    def render(self, report: QualityReport, fmt: str | None = None) -> str:
        """渲染报告为指定格式字符串。"""
        return render_report(report, fmt or self.config.report_format)

    def export(self, report: QualityReport, output: str | Path) -> Path:
        """将报告写入文件（按扩展名推断格式）。"""
        out = Path(output)
        fmt = out.suffix.lstrip(".")
        if fmt not in ("json", "md", "markdown", "html"):
            fmt = self.config.report_format
        if fmt == "markdown":
            fmt = "md"
        fmt_alias = {"md": "markdown"}
        return write_report(report, out, fmt_alias.get(fmt, fmt))

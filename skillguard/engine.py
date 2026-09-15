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
    # 批量扫描
    # ------------------------------------------------------------------
    def scan_directory(self, root: str | Path, max_depth: int = 3) -> list[dict]:
        """扫描目录树中的全部 Skill 目录，返回评估摘要列表。

        每个元素：
        {
            "path": str,          # Skill 目录相对路径
            "name": str,          # Skill 名称
            "score": float,       # 综合评分
            "passed": bool,       # 是否通过门禁
            "errors": int,        # ERROR 级检查数
            "warnings": int,      # WARNING 级检查数
            "tests": int,         # 测试数
            "tests_passed": int,  # 通过的测试数
        }
        """
        root_path = Path(root).resolve()
        results: list[dict] = []
        if not root_path.is_dir():
            raise ValueError(f"目录不存在: {root_path}")

        # BFS 限制深度
        from collections import deque

        queue: deque[Path] = deque([root_path])
        seen: set[Path] = set()
        depth_map: dict[Path, int] = {root_path: 0}

        while queue:
            current = queue.popleft()
            depth = depth_map.get(current, 0)
            if current in seen or depth > max_depth:
                continue
            seen.add(current)

            if current.is_dir() and not _is_skipped_dir(current):
                skill = load_skill(current)
                if skill is not None:
                    # 该目录本身是 Skill，不深入子目录
                    report = self._evaluate_lite(current, skill)
                    results.append(report)
                    continue
                if depth < max_depth:
                    for child in sorted(current.iterdir()):
                        if child.is_dir() and child not in seen:
                            depth_map[child] = depth + 1
                            queue.append(child)

        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def _evaluate_lite(self, skill_dir: Path, skill) -> dict:
        """轻量评估（不跑测试，仅静态 + 评分），用于批量扫描。"""
        checks = run_static_checks(skill_dir, skill, skip_safety=self.config.skip_safety)
        breakdown, overall = score_skill(skill, checks, [])
        from .models import QualityReport as _QR

        lite = _QR(
            skill=skill,
            version=__version__,
            timestamp=now_iso(),
            checks=checks,
            score=breakdown,
            overall_score=overall,
            passed=False,
        )
        lite.passed = lite.error_count() == 0 and overall >= self.config.threshold
        return {
            "path": str(skill_dir),
            "name": skill.name,
            "score": overall,
            "passed": lite.passed,
            "errors": lite.error_count(),
            "warnings": lite.warning_count(),
            "tests": 0,
            "tests_passed": 0,
        }

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


def _is_skipped_dir(path: Path) -> bool:
    """批量扫描时跳过的目录。"""
    name = path.name
    return name in {".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv", "site", "htmlcov", ".pytest_cache", ".ruff_cache", ".mypy_cache"} or name.startswith(".")

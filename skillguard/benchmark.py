"""生态质量基准（benchmark）：扫描远程仓库中的 Skills 并输出聚合质量报告。

用途：
1. 生态调研：了解一个 Skill 集合仓库的整体质量水平
2. 推广素材：生成可发布的「生态质量报告」（如超级仓库的 Skills 质量分布）
3. CI 门禁：对自有 Skills 集合做整体质量审计

实现：
- 浅克隆远程仓库到临时目录（避免拖入完整历史）
- 复用 scan_directory 批量扫描全部 Skill
- 聚合统计：平均分、通过率、安全违规 Top 问题、评分分布
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .engine import SkillGuard


@dataclass
class BenchSummary:
    """一次生态基准扫描的聚合结果。"""

    repo_url: str
    skill_count: int
    avg_score: float
    pass_rate: float
    total_errors: int
    total_warnings: int
    top_issues: list[dict[str, Any]] = field(default_factory=list)
    score_distribution: dict[str, int] = field(default_factory=dict)
    skills: list[dict[str, Any]] = field(default_factory=list)
    raw_report: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_url": self.repo_url,
            "skill_count": self.skill_count,
            "avg_score": round(self.avg_score, 2),
            "pass_rate": round(self.pass_rate, 2),
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "top_issues": self.top_issues,
            "score_distribution": self.score_distribution,
            "skills": self.skills,
        }


class BenchmarkRunner:
    """生态基准扫描执行器。"""

    def __init__(
        self,
        repo_url: str,
        depth: int = 2,
        max_skills: int = 200,
        threshold: float = 60.0,
        skip_safety: bool = False,
    ) -> None:
        self.repo_url = repo_url
        self.depth = depth
        self.max_skills = max_skills
        self.threshold = threshold
        self.skip_safety = skip_safety

    # ------------------------------------------------------------------
    # 克隆
    # ------------------------------------------------------------------
    def clone(self, target: Path, timeout: int = 300) -> Path:
        """浅克隆仓库到目标目录，返回仓库根目录。"""
        cmd = ["git", "clone", "--depth", "1", self.repo_url, str(target)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"克隆超时（>{timeout}s）: {self.repo_url}") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"克隆失败: {exc.stderr or exc}") from exc
        return target

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def run(self, keep_dir: Path | None = None) -> BenchSummary:
        """执行完整基准扫描。

        Args:
            keep_dir: 若提供，克隆保留在此目录（不清理）；否则用临时目录。

        Returns:
            BenchSummary 聚合报告。
        """
        cleanup = keep_dir is None
        work_dir = keep_dir or Path(tempfile.mkdtemp(prefix="skillguard-bench-"))
        try:
            if keep_dir is not None and (keep_dir / ".git").exists():
                repo_root = keep_dir  # 已有本地仓库，直接扫描
            else:
                repo_root = self.clone(work_dir)
            guard = SkillGuard(
                __import__("skillguard.config", fromlist=["Config"]).Config(
                    skill_dir=str(repo_root),
                    run_tests=False,
                    threshold=self.threshold,
                    skip_safety=self.skip_safety,
                )
            )
            results = guard.scan_directory(repo_root, max_depth=self.depth)
            if self.max_skills > 0:
                results = results[: self.max_skills]
            return self._aggregate(results)
        finally:
            if cleanup:
                shutil.rmtree(work_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 聚合
    # ------------------------------------------------------------------
    def _aggregate(self, results: list[dict[str, Any]]) -> BenchSummary:
        count = len(results)
        if count == 0:
            return BenchSummary(
                repo_url=self.repo_url,
                skill_count=0,
                avg_score=0.0,
                pass_rate=0.0,
                total_errors=0,
                total_warnings=0,
            )

        avg = sum(r["score"] for r in results) / count
        passed = sum(1 for r in results if r["passed"])
        total_errors = sum(r["errors"] for r in results)
        total_warnings = sum(r["warnings"] for r in results)

        # 评分分布
        dist = {"90-100": 0, "75-89": 0, "60-74": 0, "40-59": 0, "0-39": 0}
        for r in results:
            s = r["score"]
            if s >= 90:
                dist["90-100"] += 1
            elif s >= 75:
                dist["75-89"] += 1
            elif s >= 60:
                dist["60-74"] += 1
            elif s >= 40:
                dist["40-59"] += 1
            else:
                dist["0-39"] += 1

        summary = BenchSummary(
            repo_url=self.repo_url,
            skill_count=count,
            avg_score=avg,
            pass_rate=passed / count,
            total_errors=total_errors,
            total_warnings=total_warnings,
            score_distribution=dist,
            skills=results,
        )
        summary.raw_report = summary.to_dict()
        return summary


def benchmark_repo(
    repo_url: str,
    depth: int = 2,
    max_skills: int = 200,
    threshold: float = 60.0,
    keep_dir: Path | None = None,
) -> BenchSummary:
    """便捷函数：对远程仓库执行生态基准扫描。"""
    return BenchmarkRunner(
        repo_url=repo_url, depth=depth, max_skills=max_skills, threshold=threshold
    ).run(keep_dir=keep_dir)

"""测试：性能与规模化（performance & scale）。

验证工具在较大规模下的行为与性能特性，并保证性能基准脚本可运行。
"""

from __future__ import annotations

import time
from pathlib import Path

from skillguard import Config, SkillGuard


def _make_many_skills(tmp_path: Path, count: int) -> Path:
    """批量创建 Skill 目录。"""
    root = tmp_path / f"scale-{count}"
    for i in range(count):
        d = root / f"skill-{i:03d}"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: skill-{i:03d}\ndescription: d\nversion: 1.0.0\n---\n# s{i}\n",
            encoding="utf-8",
        )
    return root


class TestScale:
    def test_scan_50_skills(self, tmp_path: Path) -> None:
        """50 个 Skill 的目录扫描应快速完成且结果准确。"""
        root = _make_many_skills(tmp_path, 50)
        guard = SkillGuard(Config(skill_dir=str(root), run_tests=False))
        started = time.monotonic()
        results = guard.scan_directory(root)
        elapsed = time.monotonic() - started
        assert len(results) == 50
        # 50 个 Skill 扫描应 < 5 秒（含静态校验）
        assert elapsed < 5.0, f"扫描 50 个 Skill 耗时 {elapsed:.2f}s（超过 5s 上限）"

    def test_scan_200_skills(self, tmp_path: Path) -> None:
        """200 个 Skill 的目录扫描（更大规模冒烟）。"""
        root = _make_many_skills(tmp_path, 200)
        guard = SkillGuard(Config(skill_dir=str(root), run_tests=False))
        started = time.monotonic()
        results = guard.scan_directory(root)
        elapsed = time.monotonic() - started
        assert len(results) == 200
        assert elapsed < 10.0, f"扫描 200 个 Skill 耗时 {elapsed:.2f}s（超过 10s 上限）"

    def test_scan_sorted_stable(self, tmp_path: Path) -> None:
        """大规模扫描结果按分数降序且稳定。"""
        root = _make_many_skills(tmp_path, 30)
        guard = SkillGuard(Config(skill_dir=str(root), run_tests=False))
        results = guard.scan_directory(root)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        # 全部相同质量的 Skill 分数应一致
        assert len(set(scores)) == 1


class TestPerfScript:
    def test_perf_script_exists(self) -> None:
        script = Path(__file__).parents[1] / "scripts" / "perf-bench.sh"
        assert script.exists(), "perf-bench.sh 缺失"

    def test_perf_script_is_shell(self) -> None:
        script = Path(__file__).parents[1] / "scripts" / "perf-bench.sh"
        content = script.read_text(encoding="utf-8")
        assert content.startswith("#!/usr/bin/env bash")

    def test_benchmark_module_runs(self, tmp_path: Path) -> None:
        """benchmark 模块对本地仓库应可运行（规模化生态扫描冒烟）。"""
        import subprocess as sp

        from skillguard.benchmark import BenchmarkRunner

        root = _make_many_skills(tmp_path, 10)
        sp.run(["git", "init", "-q"], cwd=root, check=True)
        sp.run(["git", "add", "-A"], cwd=root, check=True)
        sp.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "i"],
            cwd=root,
            check=True,
        )
        runner = BenchmarkRunner(repo_url=str(root), max_skills=0)
        summary = runner.run(keep_dir=root)
        assert summary.skill_count == 10
        assert summary.avg_score > 0
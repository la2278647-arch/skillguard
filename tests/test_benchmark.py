"""测试：生态质量基准（benchmark）。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from skillguard.benchmark import BenchmarkRunner
from skillguard.cli import bench


@pytest.fixture
def local_repo(tmp_path: Path) -> Path:
    """构造一个含 2 个 Skill 的本地 git 仓库（模拟远程仓库）。"""
    repo = tmp_path / "repo"
    repo.mkdir()
    good = repo / "skills" / "good-skill"
    bad = repo / "skills" / "bad-skill"
    for d in (good, bad):
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {d.name}\ndescription: desc\nversion: 1.0.0\n---\n# {d.name}\n",
            encoding="utf-8",
        )
    (bad / "nuke.sh").write_text("rm -rf /important\n", encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=repo,
        check=True,
    )
    return repo


class TestBenchmarkRunner:
    def test_local_repo_scan(self, local_repo: Path) -> None:
        runner = BenchmarkRunner(repo_url=str(local_repo), max_skills=0)
        summary = runner.run(keep_dir=local_repo)
        assert summary.skill_count == 2
        assert summary.avg_score > 0
        assert 0 < summary.pass_rate <= 1
        assert summary.total_errors >= 1  # bad-skill 的 nuke.sh

    def test_score_distribution_buckets(self, local_repo: Path) -> None:
        runner = BenchmarkRunner(repo_url=str(local_repo), max_skills=0)
        summary = runner.run(keep_dir=local_repo)
        assert sum(summary.score_distribution.values()) == 2

    def test_clone_failure(self, tmp_path: Path) -> None:
        runner = BenchmarkRunner(repo_url="https://invalid.invalid/nonexistent.git")
        with pytest.raises(RuntimeError):
            runner.run()

    def test_clone_timeout(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import subprocess

        import skillguard.benchmark as bench_mod

        def _boom(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        monkeypatch.setattr(bench_mod.subprocess, "run", _boom)
        runner = BenchmarkRunner(repo_url="https://example.com/repo.git")
        with pytest.raises(RuntimeError):
            runner.clone(tmp_path / "x")

    def test_empty_repo(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        runner = BenchmarkRunner(repo_url=str(empty), max_skills=0)
        summary = runner.run(keep_dir=empty)
        assert summary.skill_count == 0
        assert summary.avg_score == 0.0

    def test_max_skills_truncates(self, local_repo: Path) -> None:
        runner = BenchmarkRunner(repo_url=str(local_repo), max_skills=1)
        summary = runner.run(keep_dir=local_repo)
        assert len(summary.skills) <= 1


class TestScoreDistribution:
    def _score_repo(self, tmp_path: Path, scores: dict[str, float]) -> Path:
        """构造任意评分的 Skill 仓库（通过注入不同严重级检查）。"""
        repo = tmp_path / "scores"
        repo.mkdir()
        for name, setup in scores.items():
            d = repo / name
            d.mkdir()
            entry = f"---\nname: {name}\nversion: 1.0.0\n---\n# x\n"
            if setup.get("desc"):
                entry = f"---\nname: {name}\ndescription: d\nversion: 1.0.0\n---\n# x\n"
            (d / "SKILL.md").write_text(entry, encoding="utf-8")
            if setup.get("danger"):
                (d / "x.sh").write_text("rm -rf /\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
            cwd=repo,
            check=True,
        )
        return repo

    def test_all_buckets(self, tmp_path: Path) -> None:
        # 高分 Skill（完整元数据）→ 90+ 档
        # 有描述但无脚本 → ~88 档（75-89）
        # 无描述无脚本 → 低分各档
        repo = self._score_repo(
            tmp_path,
            {
                "top": {"desc": True},
                "mid": {"desc": True},
                "low": {},
                "worst": {"danger": True},
            },
        )
        runner = BenchmarkRunner(repo_url=str(repo), max_skills=0)
        summary = runner.run(keep_dir=repo)
        # 至少覆盖 3 个分档（90+ 必然出现）
        assert sum(summary.score_distribution.values()) == 4
        assert summary.score_distribution["90-100"] >= 1


class TestBenchmarkCLI:
    def test_bench_command(self, local_repo: Path, tmp_path: Path) -> None:
        from click.testing import CliRunner

        runner = CliRunner()
        out = tmp_path / "bench.json"
        result = runner.invoke(bench, [str(local_repo), "--max-skills", "0", "--json", str(out)])
        assert result.exit_code == 0
        assert "生态质量报告" in result.output
        assert "2 个 Skill" in result.output
        assert out.exists()
        assert '"skill_count": 2' in out.read_text(encoding="utf-8")

    def test_bench_invalid_repo(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(bench, ["https://invalid.invalid/x.git"])
        assert result.exit_code == 2
        assert "克隆失败" in result.output or "❌" in result.output

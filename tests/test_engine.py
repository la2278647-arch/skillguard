"""测试：核心引擎与配置。"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillguard import SkillGuard
from skillguard.config import Config
from skillguard.engine import SkillGuard as EngineAlias


class TestConfig:
    def test_defaults(self) -> None:
        c = Config()
        assert c.skill_dir == "."
        assert c.rules == ()
        assert c.run_tests is True
        assert c.test_timeout == 60
        assert c.skip_safety is False
        assert c.report_format == "json"
        assert c.threshold == 60.0

    def test_invalid_timeout(self) -> None:
        with pytest.raises(ValueError):
            Config(test_timeout=0)

    def test_invalid_threshold(self) -> None:
        with pytest.raises(ValueError):
            Config(threshold=101)

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError):
            Config(report_format="xml")

    def test_skill_path_resolves(self, tmp_path: Path) -> None:
        c = Config(skill_dir=str(tmp_path))
        assert c.skill_path == tmp_path.resolve()

    def test_with_overrides_immutable(self) -> None:
        c = Config()
        c2 = c.with_overrides(threshold=80.0)
        assert c.threshold == 60.0
        assert c2.threshold == 80.0


class TestSkillGuard:
    def test_init_default_config(self) -> None:
        guard = SkillGuard()
        assert isinstance(guard.config, Config)

    def test_engine_alias_same(self) -> None:
        assert EngineAlias is SkillGuard

    def test_run_good_skill(self, good_skill: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(good_skill)))
        report = guard.run()
        assert report.skill.name == "good-skill"
        assert report.passed is True
        assert report.overall_score > 60
        assert report.passed_tests() == 1

    def test_run_bad_skill(self, bad_skill: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(bad_skill)))
        report = guard.run()
        assert report.passed is False
        assert report.error_count() >= 1
        assert any(c.rule_id.startswith("SEC-") for c in report.checks)

    def test_run_invalid_dir(self, empty_skill: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(empty_skill)))
        with pytest.raises(ValueError, match="SKILL.md"):
            guard.run()

    def test_validate_only_no_tests(self, good_skill: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(good_skill)))
        report = guard.validate()
        assert report.tests == []
        assert report.passed is True

    def test_validate_invalid_dir(self, empty_skill: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(empty_skill)))
        with pytest.raises(ValueError):
            guard.validate()

    def test_skip_tests_flag(self, good_skill: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(good_skill), run_tests=False))
        report = guard.run()
        assert report.tests == []

    def test_failed_test_blocks_pass(self, skill_with_tests: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(skill_with_tests)))
        report = guard.run()
        assert report.failed_tests() == 1
        assert report.passed is False

    def test_render_json_default(self, good_skill: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(good_skill)))
        report = guard.run()
        out = guard.render(report)
        assert out.startswith("{")

    def test_render_explicit_fmt(self, good_skill: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(good_skill)))
        report = guard.run()
        assert guard.render(report, "markdown").startswith("# ")

    def test_export_json(self, good_skill: Path, tmp_path: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(good_skill)))
        report = guard.run()
        out = tmp_path / "report.json"
        guard.export(report, out)
        assert out.exists()
        assert '"skill"' in out.read_text(encoding="utf-8")

    def test_export_md_extension(self, good_skill: Path, tmp_path: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(good_skill)))
        report = guard.run()
        out = tmp_path / "report.md"
        guard.export(report, out)
        assert "# SkillGuard" in out.read_text(encoding="utf-8")

    def test_export_html_extension(self, good_skill: Path, tmp_path: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(good_skill)))
        report = guard.run()
        out = tmp_path / "report.html"
        guard.export(report, out)
        assert "<!DOCTYPE html>" in out.read_text(encoding="utf-8")

    def test_export_unknown_ext_uses_config(self, good_skill: Path, tmp_path: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(good_skill), report_format="markdown"))
        report = guard.run()
        out = tmp_path / "report.txt"
        guard.export(report, out)
        assert "# SkillGuard" in out.read_text(encoding="utf-8")


class TestScanDirectory:
    def _make_tree(self, tmp_path: Path) -> tuple[Path, Path]:
        """构造 3 个 Skill 的目录树。"""
        good = tmp_path / "skills" / "good-skill"
        bad = tmp_path / "skills" / "bad-skill"
        nested = tmp_path / "skills" / "collection" / "nested-skill"
        for d in (good, bad, nested):
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(
                f"---\nname: {d.name}\ndescription: desc\nversion: 1.0.0\n---\n# {d.name}\n",
                encoding="utf-8",
            )
        # 坏 Skill 加入危险模式
        (bad / "nuke.sh").write_text("rm -rf /important\n", encoding="utf-8")
        return tmp_path, bad

    def test_finds_all_skills(self, tmp_path: Path) -> None:
        tree, _bad = self._make_tree(tmp_path)
        guard = SkillGuard(Config(skill_dir=str(tree)))
        results = guard.scan_directory(tree)
        assert len(results) == 3
        names = {r["name"] for r in results}
        assert names == {"good-skill", "bad-skill", "nested-skill"}

    def test_sorted_by_score(self, tmp_path: Path) -> None:
        tree, _ = self._make_tree(tmp_path)
        guard = SkillGuard(Config(skill_dir=str(tree)))
        results = guard.scan_directory(tree)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_bad_skill_flags_errors(self, tmp_path: Path) -> None:
        tree, _bad = self._make_tree(tmp_path)
        guard = SkillGuard(Config(skill_dir=str(tree)))
        results = guard.scan_directory(tree)
        bad_entry = next(r for r in results if r["name"] == "bad-skill")
        assert bad_entry["errors"] >= 1
        assert bad_entry["passed"] is False

    def test_depth_limit(self, tmp_path: Path) -> None:
        tree, _ = self._make_tree(tmp_path)
        guard = SkillGuard(Config(skill_dir=str(tree)))
        results = guard.scan_directory(tree, max_depth=2)
        # depth=2 时到达 skills/* 层：找到 good-skill 和 bad-skill，找不到 collection/nested-skill
        names = {r["name"] for r in results}
        assert "good-skill" in names
        assert "bad-skill" in names
        assert "nested-skill" not in names

    def test_skips_vcs_dirs(self, tmp_path: Path) -> None:
        tree, _ = self._make_tree(tmp_path)
        (tree / "skills" / ".git").mkdir()
        guard = SkillGuard(Config(skill_dir=str(tree)))
        results = guard.scan_directory(tree)
        assert len(results) == 3  # .git 被跳过，不产生干扰

    def test_empty_dir(self, tmp_path: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(tmp_path)))
        results = guard.scan_directory(tmp_path)
        assert results == []

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        guard = SkillGuard(Config(skill_dir=str(tmp_path)))
        with pytest.raises(ValueError):
            guard.scan_directory(tmp_path / "missing")

"""测试：规则注册表与插件系统。"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillguard.models import CheckResult, Severity, SkillInfo
from skillguard.rules import RuleRegistry, RuleSet, registry
from skillguard.validator import run_static_checks


def _skill() -> SkillInfo:
    return SkillInfo(name="s", description="d", version="1.0.0")


def _make_skill_dir(tmp_path: Path) -> Path:
    d = tmp_path / "plug-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: s\n---\n# x\n", encoding="utf-8")
    return d


class TestRuleRegistry:
    def test_register_and_run(self, tmp_path: Path) -> None:
        d = _make_skill_dir(tmp_path)

        def style_checker(skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
            return [CheckResult("CUS-001", Severity.WARNING, "自定义风格问题")]

        r = RuleRegistry()
        r.register("CUS", style_checker)
        results = r.run_custom(d, _skill())
        assert len(results) == 1
        assert results[0].rule_id == "CUS-001"
        assert r.has_custom() is True
        assert r.custom_prefixes() == ["CUS"]

    def test_register_conflicts_with_builtin(self) -> None:
        r = RuleRegistry()
        with pytest.raises(ValueError, match="冲突"):
            r.register("SEC", lambda a, b: [])  # type: ignore[arg-type]

    def test_register_invalid_prefix(self) -> None:
        r = RuleRegistry()
        with pytest.raises(ValueError):
            r.register("X", lambda a, b: [])  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            r.register("a-b", lambda a, b: [])  # type: ignore[arg-type]

    def test_unregister(self) -> None:
        r = RuleRegistry()
        r.register("CUS", lambda a, b: [])  # type: ignore[arg-type]
        assert r.has_custom() is True
        r.unregister("cus")  # 大小写不敏感
        assert r.has_custom() is False

    def test_register_isolation(self) -> None:
        """不同注册表实例互不影响；全局单例独立。"""
        r1, r2 = RuleRegistry(), RuleRegistry()
        r1.register("AAA", lambda a, b: [])  # type: ignore[arg-type]
        assert r1.has_custom() is True
        assert r2.has_custom() is False


class TestRuleSet:
    def test_compose_checkers(self, tmp_path: Path) -> None:
        d = _make_skill_dir(tmp_path)
        rs = RuleSet("combo")
        rs.add(lambda a, b: [CheckResult("CUS-001", Severity.INFO, "a")])
        rs.add(lambda a, b: [CheckResult("CUS-002", Severity.ERROR, "b")])
        results = rs.run_all(d, _skill())
        assert len(results) == 2
        assert {r.rule_id for r in results} == {"CUS-001", "CUS-002"}

    def test_chainable_add(self) -> None:
        rs = RuleSet("chain")
        assert rs.add(lambda a, b: []) is rs  # type: ignore[arg-type]


class TestPluginIntegration:
    def test_custom_rules_in_static_checks(self, tmp_path: Path) -> None:
        d = _make_skill_dir(tmp_path)
        (d / "notes.md").write_text("# TODO: 未来优化\n", encoding="utf-8")

        def checker(skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
            # 检查目录内是否包含 TODO 注释
            hits = []
            for p in skill_dir.rglob("*.md"):
                text = p.read_text(encoding="utf-8", errors="replace")
                if "TODO" in text:
                    hits.append(
                        CheckResult("CUS-100", Severity.WARNING, "发现 TODO", file=p.name)
                    )
            return hits

        registry.register("CUS", checker)
        try:
            results = run_static_checks(d, _skill())
            assert any(c.rule_id == "CUS-100" for c in results)
        finally:
            registry.unregister("CUS")

    def test_global_registry_usable(self) -> None:
        """全局单例 registry 可用且初始无自定义规则。"""
        assert registry.has_custom() is False


class TestScoringWithCustom:
    def test_custom_rule_penalizes_maintainability(self) -> None:
        from skillguard.scoring import score_skill

        checks = [CheckResult("CUS-001", Severity.ERROR, "自定义问题")]
        breakdown, overall = score_skill(_skill(), checks, [])
        assert breakdown.maintainability == 70.0  # 100 - 30(ERROR)
        assert overall < 100.0

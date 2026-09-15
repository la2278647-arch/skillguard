"""测试：自定义规则示例（插件系统演示）可用性。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from skillguard.rules import registry


@pytest.fixture
def custom_rules_module():
    """加载 examples/custom_rules.py 模块（不污染全局）。"""
    examples = Path(__file__).parents[1] / "examples" / "custom_rules.py"
    spec = importlib.util.spec_from_file_location("custom_rules_example", examples)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class TestExampleLoads:
    def test_module_importable(self, custom_rules_module) -> None:
        assert custom_rules_module is not None

    def test_register_functions_exist(self, custom_rules_module) -> None:
        assert hasattr(custom_rules_module, "register_custom_rules")
        assert hasattr(custom_rules_module, "no_todo_leftovers")
        assert hasattr(custom_rules_module, "has_required_sections")
        assert hasattr(custom_rules_module, "scripts_check_error_handling")


class TestRules:
    def test_todo_detected(self, custom_rules_module, tmp_path: Path) -> None:
        d = tmp_path / "s"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\nname: s\n---\n# s\nTODO: 待完善\n", encoding="utf-8"
        )
        results = custom_rules_module.no_todo_leftovers(d, None)  # type: ignore[arg-type]
        assert any(r.rule_id == "CUS-001" for r in results)
        assert results[0].line == 5

    def test_missing_sections(self, custom_rules_module, tmp_path: Path) -> None:
        d = tmp_path / "s"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: s\n---\n# s\n", encoding="utf-8")
        results = custom_rules_module.has_required_sections(d, None)  # type: ignore[arg-type]
        assert len(results) == 3  # 三个章节都缺
        assert all(r.rule_id == "CUS-002" for r in results)

    def test_script_no_set_e(self, custom_rules_module, tmp_path: Path) -> None:
        d = tmp_path / "s"
        (d / "scripts").mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: s\n---\n# s\n", encoding="utf-8")
        (d / "scripts" / "run.sh").write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")
        results = custom_rules_module.scripts_check_error_handling(d, None)  # type: ignore[arg-type]
        assert any(r.rule_id == "CUS-003" for r in results)

    def test_script_with_set_e_ok(self, custom_rules_module, tmp_path: Path) -> None:
        d = tmp_path / "s"
        (d / "scripts").mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: s\n---\n# s\n", encoding="utf-8")
        (d / "scripts" / "run.sh").write_text(
            "#!/usr/bin/env bash\nset -e\necho hi\n", encoding="utf-8"
        )
        results = custom_rules_module.scripts_check_error_handling(d, None)  # type: ignore[arg-type]
        assert results == []

    def test_register_idempotent(self, custom_rules_module) -> None:
        custom_rules_module.register_custom_rules()
        first = dict(registry._custom_checkers)
        custom_rules_module.register_custom_rules()  # 再次注册不报错
        assert registry._custom_checkers == first
        registry.unregister("CUS")


class TestRegistration:
    def test_registered_prefix(self, custom_rules_module) -> None:
        custom_rules_module.register_custom_rules()
        try:
            assert "CUS" in registry.custom_prefixes()
        finally:
            registry.unregister("CUS")
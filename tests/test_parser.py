"""测试：Skill 目录解析。"""

from __future__ import annotations

from pathlib import Path

from skillguard.parser import (
    discover_scripts,
    find_skill_dir,
    load_skill,
    parse_skill_metadata,
)


class TestParseMetadata:
    def test_yaml_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text(
            "---\nname: my-skill\ndescription: 描述\nversion: 1.2.3\nframework: codex\ntags: [a, b]\n---\n# Body\n",
            encoding="utf-8",
        )
        meta = parse_skill_metadata(f)
        assert meta["name"] == "my-skill"
        assert meta["description"] == "描述"
        assert meta["version"] == "1.2.3"
        assert meta["framework"] == "codex"
        assert meta["tags"] == ["a", "b"]

    def test_keyvalue_fallback(self, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text("# name: fallback-skill\n# description: 键值描述\n# Body content\n", encoding="utf-8")
        meta = parse_skill_metadata(f)
        assert meta["name"] == "fallback-skill"
        assert meta["description"] == "键值描述"

    def test_invalid_yaml_falls_back(self, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text("---\nname: [unclosed\n---\n# x\n", encoding="utf-8")
        # 不抛异常
        meta = parse_skill_metadata(f)
        assert isinstance(meta, dict)

    def test_no_metadata(self, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text("# Just a title\n\nbody\n", encoding="utf-8")
        assert parse_skill_metadata(f) == {}


class TestLoadSkill:
    def test_valid(self, good_skill: Path) -> None:
        skill = load_skill(good_skill)
        assert skill is not None
        assert skill.name == "good-skill"
        assert skill.framework == "claude-code"
        assert skill.has_scripts is True
        assert skill.script_count >= 1
        assert skill.tags == ["example", "demo"]

    def test_missing_entrypoint(self, empty_skill: Path) -> None:
        assert load_skill(empty_skill) is None

    def test_name_falls_back_to_dirname(self, tmp_path: Path) -> None:
        d = tmp_path / "no-name"
        d.mkdir()
        (d / "SKILL.md").write_text("---\ndescription: x\n---\n# x\n", encoding="utf-8")
        skill = load_skill(d)
        assert skill is not None
        assert skill.name == "no-name"

    def test_tags_string_variant(self, tmp_path: Path) -> None:
        d = tmp_path / "tag-skill"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: t\ntags: a, b, c\n---\n# x\n", encoding="utf-8")
        skill = load_skill(d)
        assert skill is not None
        assert skill.tags == ["a", "b", "c"]

    def test_tags_other_type_ignored(self, tmp_path: Path) -> None:
        d = tmp_path / "tag-skill"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: t\ntags: 42\n---\n# x\n", encoding="utf-8")
        skill = load_skill(d)
        assert skill is not None
        assert skill.tags == []


class TestDiscoverScripts:
    def test_scripts_dir(self, good_skill: Path) -> None:
        found = discover_scripts(good_skill)
        assert len(found) >= 1
        assert found[0].name == "run.sh"

    def test_scripts_dir_preferred(self, tmp_path: Path) -> None:
        d = tmp_path / "mix"
        d.mkdir()
        (d / "a.sh").write_text("x", encoding="utf-8")
        (d / "scripts").mkdir()
        (d / "scripts" / "b.py").write_text("x", encoding="utf-8")
        found = discover_scripts(d)
        assert [p.name for p in found] == ["b.py"]

    def test_empty(self, tmp_path: Path) -> None:
        assert discover_scripts(tmp_path) == []


class TestFindSkillDir:
    def test_finds_parent(self, tmp_path: Path) -> None:
        d = tmp_path / "proj" / "nested" / "deep"
        d.mkdir(parents=True)
        (tmp_path / "proj" / "SKILL.md").write_text("# x\n", encoding="utf-8")
        assert find_skill_dir(d) == (tmp_path / "proj").resolve()

    def test_none_when_absent(self, tmp_path: Path) -> None:
        d = tmp_path / "nowhere"
        d.mkdir()
        assert find_skill_dir(d) is None

"""测试：配置文件支持（YAML/TOML）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from skillguard.cli import check, config_cmd
from skillguard.config import Config
from skillguard.configfile import (
    build_config,
    config_to_dict,
    find_config_file,
    load_config_file,
)


class TestLoadConfigFile:
    def test_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "skillguard.yml"
        f.write_text("threshold: 80\nrun_tests: false\nrules:\n  - SEC-001\n", encoding="utf-8")
        data = load_config_file(f)
        assert data["threshold"] == 80
        assert data["run_tests"] is False
        assert data["rules"] == ["SEC-001"]

    def test_toml(self, tmp_path: Path) -> None:
        f = tmp_path / "skillguard.toml"
        f.write_text("threshold = 75\nrun_tests = false\nrules = ['SEC-001', 'SEC-005']\n", encoding="utf-8")
        data = load_config_file(f)
        assert data["threshold"] == 75
        assert data["run_tests"] is False
        assert data["rules"] == ["SEC-001", "SEC-005"]

    def test_yaml_top_level_list_rejected(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yml"
        f.write_text("- a\n- b\n", encoding="utf-8")
        with pytest.raises(ValueError):
            load_config_file(f)

    def test_toml_roundtrip(self, tmp_path: Path) -> None:
        f = tmp_path / "skillguard.toml"
        f.write_text("threshold = 75\nrun_tests = false\nrules = ['SEC-001']\n", encoding="utf-8")
        data = load_config_file(f)
        assert data["threshold"] == 75
        assert data["rules"] == ["SEC-001"]

    def test_unsupported_format(self, tmp_path: Path) -> None:
        f = tmp_path / "skillguard.ini"
        f.write_text("[x]", encoding="utf-8")
        with pytest.raises(ValueError):
            load_config_file(f)

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            load_config_file(tmp_path / "none.yml")


class TestFindConfigFile:
    def test_finds_in_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "skillguard.yml").write_text("threshold: 90\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert find_config_file(tmp_path) is not None

    def test_finds_in_parent(self, tmp_path: Path) -> None:
        (tmp_path / "skillguard.toml").write_text("threshold = 90\n", encoding="utf-8")
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        found = find_config_file(nested)
        assert found is not None

    def test_none_when_absent(self, tmp_path: Path) -> None:
        assert find_config_file(tmp_path) is None


class TestBuildConfig:
    def test_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)  # 无配置文件
        config = build_config(skill_dir=str(tmp_path))
        assert config.threshold == 60.0
        assert config.run_tests is True

    def test_auto_discovers(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "skillguard.yml").write_text("threshold: 88\nrun_tests: false\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        config = build_config(skill_dir=str(tmp_path))
        assert config.threshold == 88
        assert config.run_tests is False

    def test_explicit_path_wins(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "skillguard.yml").write_text("threshold: 88\n", encoding="utf-8")
        explicit = tmp_path / "custom.yml"
        explicit.write_text("threshold: 42\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        config = build_config(skill_dir=str(tmp_path), config_path=str(explicit))
        assert config.threshold == 42  # 显式路径优先

    def test_rules_normalization(self, tmp_path: Path) -> None:
        f = tmp_path / "skillguard.yml"
        f.write_text("rules: SEC-001, SEC-005\n", encoding="utf-8")
        config = build_config(skill_dir=str(tmp_path), config_path=str(f))
        assert config.rules == ("SEC-001", "SEC-005")

    def test_rules_none(self, tmp_path: Path) -> None:
        f = tmp_path / "skillguard.yml"
        f.write_text("rules: null\n", encoding="utf-8")
        config = build_config(skill_dir=str(tmp_path), config_path=str(f))
        assert config.rules == ()

    def test_rules_list_with_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "skillguard.yml"
        f.write_text("rules:\n  - SEC-001\n  - ''\n  - '  '\n", encoding="utf-8")
        config = build_config(skill_dir=str(tmp_path), config_path=str(f))
        assert config.rules == ("SEC-001",)

    def test_rules_invalid_type(self, tmp_path: Path) -> None:
        f = tmp_path / "skillguard.yml"
        f.write_text("rules: 42\n", encoding="utf-8")
        with pytest.raises(ValueError):
            build_config(skill_dir=str(tmp_path), config_path=str(f))


class TestConfigRoundtrip:
    def test_to_dict(self) -> None:
        c = Config(skill_dir="s", threshold=77, rules=("SEC-001",))
        d = config_to_dict(c)
        assert d["threshold"] == 77
        assert d["rules"] == ["SEC-001"]
        assert d["skill_dir"] == "s"


class TestConfigCLI:
    def test_config_init(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(config_cmd, ["--init"])
        assert result.exit_code == 0
        assert (tmp_path / "skillguard.yml").exists()

    def test_config_show(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(config_cmd, ["--show", "--skill-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "threshold" in result.output

    def test_check_with_config_file(self, good_skill: Path, tmp_path: Path) -> None:
        cfg = tmp_path / "skillguard.yml"
        cfg.write_text("threshold: 10\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(check, [str(good_skill), "--config", str(cfg)])
        assert result.exit_code == 0
        assert "综合评分" in result.output

    def test_config_cmd_no_args(self) -> None:
        runner = CliRunner()
        result = runner.invoke(config_cmd, [])
        assert result.exit_code == 2

    def test_config_show_with_invalid_skill_dir(self, tmp_path: Path) -> None:
        # 无配置文件的空目录：显示默认配置
        runner = CliRunner()
        result = runner.invoke(config_cmd, ["--show", "--skill-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "threshold" in result.output

    def test_config_init_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        assert runner.invoke(config_cmd, ["--init"]).exit_code == 0
        result = runner.invoke(config_cmd, ["--init"])
        assert result.exit_code == 0
        assert "已存在" in result.output

    def test_check_invalid_config(self, good_skill: Path, tmp_path: Path) -> None:
        cfg = tmp_path / "bad.yml"
        cfg.write_text("threshold: 200\n", encoding="utf-8")  # 超出范围
        runner = CliRunner()
        result = runner.invoke(check, [str(good_skill), "--config", str(cfg)])
        assert result.exit_code == 2

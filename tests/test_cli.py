"""测试：CLI 入口。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from skillguard.cli import check, completion, doctor, init, main, scan


class TestMain:
    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "skillguard" in result.output

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "check" in result.output
        assert "init" in result.output


class TestCheckCommand:
    def test_good_skill_passes(self, good_skill: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(check, [str(good_skill)])
        assert result.exit_code == 0
        assert "综合评分" in result.output
        assert "good-skill" in result.output

    def test_bad_skill_fails_ci(self, bad_skill: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(check, [str(bad_skill), "--ci"])
        assert result.exit_code == 1

    def test_bad_skill_ok_without_ci(self, bad_skill: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(check, [str(bad_skill)])
        assert result.exit_code == 0  # 非 CI 模式仅报告

    def test_invalid_dir(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(check, [str(tmp_path)])
        assert result.exit_code == 2  # 无 SKILL.md 报错

    def test_invalid_threshold_config(self, good_skill: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(check, [str(good_skill), "--threshold", "150"])
        assert result.exit_code == 2
        assert "配置错误" in result.output

    def test_output_json_file(self, good_skill: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        out = tmp_path / "r.json"
        result = runner.invoke(check, [str(good_skill), "--format", "json", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_markdown_format(self, good_skill: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(check, [str(good_skill), "--format", "markdown"])
        assert result.exit_code == 0

    def test_no_tests_flag(self, good_skill: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(check, [str(good_skill), "--no-tests"])
        assert result.exit_code == 0
        assert "测试: 0" not in result.output  # 无测试时摘要不打印测试行

    def test_threshold_option(self, good_skill: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(check, [str(good_skill), "--threshold", "99", "--ci"])
        # good_skill 分数可能 < 99 -> 失败
        assert result.exit_code in (0, 1)


class TestInitCommand:
    def test_init_creates_skeleton(self, tmp_path: Path) -> None:
        runner = CliRunner()
        target = tmp_path / "new-skill"
        result = runner.invoke(init, [str(target), "--name", "new-skill", "--framework", "claude-code"])
        assert result.exit_code == 0
        assert (target / "SKILL.md").exists()
        assert (target / "tests" / "smoke.sh").exists()
        content = (target / "SKILL.md").read_text(encoding="utf-8")
        assert "name: new-skill" in content
        assert "framework: claude-code" in content

    def test_init_idempotent(self, tmp_path: Path) -> None:
        runner = CliRunner()
        target = tmp_path / "existing"
        runner.invoke(init, [str(target)])
        result = runner.invoke(init, [str(target)])
        assert result.exit_code == 0
        assert "已存在" in result.output


class TestScanCommand:
    def test_scan_finds_skills(self, tmp_path: Path) -> None:
        for name in ("a", "b"):
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: d\n---\n# {name}\n", encoding="utf-8"
            )
        runner = CliRunner()
        result = runner.invoke(scan, [str(tmp_path)])
        assert result.exit_code == 0
        assert "扫描完成" in result.output
        assert "2 个 Skill" in result.output

    def test_scan_empty(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(scan, [str(tmp_path)])
        assert result.exit_code == 0
        assert "未在目录树中发现" in result.output

    def test_scan_invalid_threshold(self) -> None:
        """scan 阈值越界应报配置错误。"""
        runner = CliRunner()
        result = runner.invoke(scan, [".", "--threshold", "150"])
        assert result.exit_code == 2
        assert "配置错误" in result.output

    def test_scan_truncation_message(self, tmp_path: Path) -> None:
        """多于 top 数量的 Skill 应显示略过提示。"""
        for name in ("a", "b", "c"):
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: d\n---\n# {name}\n", encoding="utf-8"
            )
        runner = CliRunner()
        result = runner.invoke(scan, [str(tmp_path), "--top", "2"])
        assert result.exit_code == 0
        assert "略过" in result.output

    def test_scan_nonexistent_dir(self) -> None:
        """scan 不存在的目录应报错。"""
        runner = CliRunner()
        result = runner.invoke(scan, ["/definitely/not/exist"])
        assert result.exit_code == 2


class TestCompletionCommand:
    @pytest.mark.parametrize("shell", ["bash", "zsh", "fish", "powershell"])
    def test_generates_completion(self, shell: str) -> None:
        runner = CliRunner()
        result = runner.invoke(completion, [shell])
        assert result.exit_code == 0
        assert len(result.output) > 50  # 生成了补全脚本

    def test_invalid_shell(self) -> None:
        runner = CliRunner()
        result = runner.invoke(completion, ["tcsh"])
        assert result.exit_code == 2  # 非法 shell


class TestDoctorCommand:
    def test_doctor_runs(self) -> None:
        runner = CliRunner()
        result = runner.invoke(doctor)
        assert result.exit_code == 0
        assert "SkillGuard Doctor" in result.output
        assert "Python" in result.output

    def test_doctor_warns_missing_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """bash/git 缺失时 doctor 输出警告。"""
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "shutil":
                module = type(sys)("fake_shutil")
                module.which = lambda _: None  # type: ignore[attr-defined]
                return module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        runner = CliRunner()
        result = runner.invoke(doctor)
        assert result.exit_code == 0  # doctor 不因缺失退出非零
        assert "bash 缺失" in result.output
        assert "git 缺失" in result.output
        assert "存在缺失组件" in result.output

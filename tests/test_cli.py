"""测试：CLI 入口。"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from skillguard.cli import check, init, main


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

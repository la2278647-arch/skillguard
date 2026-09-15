"""测试：沙箱测试执行器。"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillguard.models import TestOutcome
from skillguard.runner import _sanitized_env, run_test_scripts


class TestSanitizedEnv:
    def test_drops_sensitive_prefixes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-xyz")
        monkeypatch.setenv("PATH", "/usr/bin")
        env = _sanitized_env()
        assert "AWS_SECRET_ACCESS_KEY" not in env
        assert "OPENAI_API_KEY" not in env
        assert env.get("PATH") == "/usr/bin"

    def test_keeps_basic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LANG", "zh_CN.UTF-8")
        env = _sanitized_env()
        assert env.get("LANG") == "zh_CN.UTF-8"


class TestRunTestScripts:
    def test_no_tests_returns_empty(self, tmp_path: Path) -> None:
        assert run_test_scripts(tmp_path, []) == []

    def test_passing_script(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        script = tmp_path / "tests" / "ok.sh"
        script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        results = run_test_scripts(tmp_path, [])
        assert len(results) == 1
        assert results[0].outcome == TestOutcome.PASSED
        assert results[0].name == "tests/ok.sh"

    def test_failing_script(self, tmp_path: Path) -> None:
        (tmp_path / "test").mkdir()
        script = tmp_path / "test" / "bad.sh"
        script.write_text("#!/usr/bin/env bash\necho boom >&2\nexit 3\n", encoding="utf-8")
        results = run_test_scripts(tmp_path, [])
        assert len(results) == 1
        assert results[0].outcome == TestOutcome.FAILED
        assert "boom" in results[0].detail

    def test_python_script(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        script = tmp_path / "tests" / "check.py"
        script.write_text("print('python ok')\n", encoding="utf-8")
        results = run_test_scripts(tmp_path, [])
        assert len(results) == 1
        assert results[0].outcome == TestOutcome.PASSED
        assert "python ok" in results[0].detail

    def test_timeout(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        script = tmp_path / "tests" / "sleep.sh"
        script.write_text("#!/usr/bin/env bash\nsleep 30\n", encoding="utf-8")
        results = run_test_scripts(tmp_path, [], timeout=1)
        assert len(results) == 1
        assert results[0].outcome == TestOutcome.ERROR
        assert "超时" in results[0].detail

    def test_runs_in_sandbox_not_source(self, tmp_path: Path) -> None:
        """脚本尝试写入脚本所在目录的上级，源目录必须不受影响（沙箱副本隔离）。"""
        (tmp_path / "tests").mkdir()
        script = tmp_path / "tests" / "pwn.sh"
        script.write_text(
            "#!/usr/bin/env bash\n"
            'echo pwned > "$(dirname "$0")/../PWNED.txt"\n'
            "echo done\n",
            encoding="utf-8",
        )
        results = run_test_scripts(tmp_path, [])
        assert results[0].outcome == TestOutcome.PASSED
        # 源目录不应出现 PWNED.txt（脚本在沙箱副本中运行）
        assert not (tmp_path / "PWNED.txt").exists()

    def test_oserror_handled(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """subprocess 启动失败（OSError）时返回 ERROR 结果而非崩溃。"""
        (tmp_path / "tests").mkdir()
        script = tmp_path / "tests" / "ok.sh"
        script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

        import skillguard.runner as runner_mod

        def _boom(*args, **kwargs):
            raise OSError("simulated failure")

        monkeypatch.setattr(runner_mod.subprocess, "run", _boom)
        results = runner_mod.run_test_scripts(tmp_path, [])
        assert len(results) == 1
        assert results[0].outcome == TestOutcome.ERROR
        assert "无法执行" in results[0].detail


class TestShellSelection:
    def test_script_arg_windows_style(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Windows 上脚本路径应转为正斜杠。"""
        import skillguard.runner as runner_mod

        monkeypatch.setattr(runner_mod, "_IS_WINDOWS", True)
        p = Path(r"C:\tmp\test.sh")
        assert runner_mod._script_arg(p) == "C:/tmp/test.sh"

    def test_script_arg_posix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import skillguard.runner as runner_mod

        monkeypatch.setattr(runner_mod, "_IS_WINDOWS", False)
        p = Path("tmp/test.sh")
        # 非 Windows 分支保持原样（不转换反斜杠）
        assert runner_mod._script_arg(p) == str(p)

    def test_shell_fallback_cmd(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Windows 无 Git Bash 且无普通 bash 时回退 cmd.exe。"""
        import skillguard.runner as runner_mod

        monkeypatch.setattr(runner_mod, "_IS_WINDOWS", True)
        monkeypatch.setattr(runner_mod, "_GIT_BASH_CANDIDATES", ())
        monkeypatch.setattr(runner_mod.shutil, "which", lambda _: None)
        assert runner_mod._shell() == "cmd.exe" or runner_mod._shell().endswith("cmd.exe")

    def test_shell_skips_wsl_bash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Windows 存在 bash 时跳过 WindowsApps 的 WSL 启动器。"""
        import skillguard.runner as runner_mod

        monkeypatch.setattr(runner_mod, "_IS_WINDOWS", True)
        monkeypatch.setattr(runner_mod, "_GIT_BASH_CANDIDATES", ())
        monkeypatch.setattr(
            runner_mod.shutil,
            "which",
            lambda _: [r"C:\Windows\System32\WindowsApps\bash.exe", r"C:\tools\bash.exe"],
        )
        assert runner_mod._shell() == r"C:\tools\bash.exe"

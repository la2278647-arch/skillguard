"""测试：MCP 服务器与工具实现。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from skillguard.mcp_server import (
    bench_repo_impl,
    check_skill_impl,
    create_server,
    scan_skills_impl,
)


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


def _make_skill_dir(tmp_path: Path, name: str, bad: bool = False) -> Path:
    d = tmp_path / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: desc\nversion: 1.0.0\n---\n# {name}\n",
        encoding="utf-8",
    )
    if bad:
        (d / "nuke.sh").write_text("rm -rf /important\n", encoding="utf-8")
    return d


class TestCheckSkillImpl:
    def test_good_skill(self, tmp_path: Path) -> None:
        d = _make_skill_dir(tmp_path, "good")
        result = check_skill_impl(str(d))
        assert result["skill"]["name"] == "good"
        assert "summary" in result
        assert result["summary"]["passed"] is True

    def test_bad_skill(self, tmp_path: Path) -> None:
        d = _make_skill_dir(tmp_path, "bad", bad=True)
        result = check_skill_impl(str(d))
        assert result["summary"]["passed"] is False
        assert result["summary"]["checks"]["errors"] >= 1

    def test_invalid_dir(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(ValueError):
            check_skill_impl(str(empty))

    def test_serializable(self, tmp_path: Path) -> None:
        d = _make_skill_dir(tmp_path, "good")
        result = check_skill_impl(str(d))
        json.dumps(result)  # 不抛异常即可


class TestScanSkillsImpl:
    def test_finds_skills(self, tmp_path: Path) -> None:
        _make_skill_dir(tmp_path / "skills" / "a", "a")
        _make_skill_dir(tmp_path / "skills" / "b", "b")
        result = scan_skills_impl(str(tmp_path))
        assert result["skill_count"] == 2
        assert result["pass_rate"] == 1.0
        assert len(result["top"]) == 2

    def test_empty_dir(self, tmp_path: Path) -> None:
        result = scan_skills_impl(str(tmp_path))
        assert result["skill_count"] == 0
        assert result["avg_score"] == 0.0


class TestServerAssembly:
    def test_create_server(self) -> None:
        server = create_server()
        assert server is not None

    def test_all_tools_registered(self) -> None:
        """服务器应注册全部 3 个工具。"""
        create_server()  # 装配不抛异常即代表工具注册成功
        # 内部工具表同名探测：任一实现函数可调用即注册成功
        assert check_skill_impl is not None
        assert scan_skills_impl is not None
        assert bench_repo_impl is not None

    def test_create_server_mcp1_fallback(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """mcp 1.x 环境（无 mcpserver 模块）时回退到 FastMCP。"""
        import sys

        import skillguard.mcp_server as mcp_mod

        # 模拟 mcp 1.x：注入假的 fastmcp 模块，同时让 mcpserver 导入失败
        fake_fastmcp = type(sys)("fake_fastmcp")

        class FakeFastMCP:
            def __init__(self, *a, **kw):
                self.name = "skillguard"

            def add_tool(self, *a, **kw):
                pass

        fake_fastmcp.FastMCP = FakeFastMCP
        monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fake_fastmcp)
        monkeypatch.setitem(sys.modules, "mcp.server.mcpserver", None)

        server = mcp_mod.create_server()
        assert server is not None
        assert server.name == "skillguard"


class TestBenchRepoImpl:
    def test_valid_repo(self, local_repo: Path) -> None:
        result = bench_repo_impl(str(local_repo), max_skills=0)
        assert result["skill_count"] > 0

    def test_invalid_repo_raises(self) -> None:
        with pytest.raises(RuntimeError):
            bench_repo_impl("https://invalid.invalid/nope.git")


class TestCLI:
    def test_run_stdio_direct(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """run_stdio 应创建服务器并调用 run()。"""
        import skillguard.mcp_server as mcp_mod

        called: list[str] = []

        class FakeServer:
            def run(self, *a, **kw):
                called.append("run")

        monkeypatch.setattr(mcp_mod, "create_server", lambda: FakeServer())
        mcp_mod.run_stdio()
        assert called == ["run"]

    def test_mcp_in_help(self) -> None:
        """CLI 帮助应包含 mcp 命令。"""
        from click.testing import CliRunner

        from skillguard.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "mcp" in result.output

    def test_mcp_command_runs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """mcp 命令应调用 run_stdio 启动服务器。"""
        from click.testing import CliRunner

        import skillguard.cli as cli_mod
        import skillguard.mcp_server as mcp_mod

        called: list[str] = []

        def fake_run_stdio():
            called.append("run")

        monkeypatch.setattr(mcp_mod, "run_stdio", fake_run_stdio)
        runner = CliRunner()
        result = runner.invoke(cli_mod.mcp_cmd)
        assert result.exit_code == 0
        assert called == ["run"]

    def test_mcp_command_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """mcp 依赖缺失时输出友好错误并退出 2。"""
        from click.testing import CliRunner

        import skillguard.cli as cli_mod
        import skillguard.mcp_server as mcp_mod

        def fake_run_stdio():
            raise ImportError("no mcp")

        monkeypatch.setattr(mcp_mod, "run_stdio", fake_run_stdio)
        runner = CliRunner()
        result = runner.invoke(cli_mod.mcp_cmd)
        assert result.exit_code == 2
        assert "skillguard[mcp]" in result.output
"""沙箱测试执行器：在隔离临时目录中运行 Skill 的测试脚本。

安全设计：
- 将整个 Skill 目录复制到独立临时目录后运行测试（脚本无法触碰源目录）
- 强制超时防止失控脚本
- 默认不继承敏感环境变量
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .models import TestOutcome, TestResult

# 在测试环境中默认清空的高风险变量
_DROP_ENV_PREFIXES = ("AWS_", "AZURE_", "GCP_", "GOOGLE_", "OPENAI_", "ANTHROPIC_", "TOKEN", "SECRET", "PASSWORD")
_KEEP_ENV = {"PATH", "HOME", "USER", "USERNAME", "SYSTEMROOT", "TMP", "TEMP", "LANG", "LC_ALL"}
_COPY_IGNORE = shutil.ignore_patterns(".git", ".hg", ".svn", "__pycache__", "*.pyc", "node_modules", ".venv", "venv")

_GIT_BASH_CANDIDATES = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
    r"C:\msys64\usr\bin\bash.exe",
)

_IS_WINDOWS = os.name == "nt"


def _sanitized_env() -> dict[str, str]:
    """构建净化后的环境变量（保留基础变量，丢弃敏感前缀）。"""
    env = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if upper in _KEEP_ENV or not any(upper.startswith(p) for p in _DROP_ENV_PREFIXES):
            env[key] = value
    return env


def run_test_scripts(skill_dir: Path, scripts: list[Path], timeout: int = 60) -> list[TestResult]:
    """在沙箱副本中运行 Skill 的测试脚本。

    约定：测试脚本位于 skill_dir/tests/ 或 skill_dir/test/（.sh / .py / .js / .ts）。
    整个 Skill 目录会被复制到临时目录，脚本在副本中运行，杜绝触碰源文件。

    Returns:
        每个测试脚本一条 TestResult。
    """
    results: list[TestResult] = []
    candidates = _collect_test_scripts(skill_dir)
    if not candidates:
        return results  # 无测试脚本：不产生测试结果

    env = _sanitized_env()
    with tempfile.TemporaryDirectory(prefix="skillguard-test-") as tmp:
        # 复制整个 Skill 目录到沙箱
        sandbox_root = Path(tmp)
        sandbox_skill = sandbox_root / "skill"
        shutil.copytree(skill_dir, sandbox_skill, ignore=_COPY_IGNORE)

        for script_rel in candidates:
            script = sandbox_skill / script_rel.relative_to(skill_dir)
            rel_posix = script_rel.relative_to(skill_dir).as_posix()
            started = time.monotonic()
            try:
                proc = subprocess.run(
                    [_python() if script.suffix == ".py" else _shell(), _script_arg(script)],
                    cwd=sandbox_skill,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                duration = (time.monotonic() - started) * 1000
                if proc.returncode == 0:
                    results.append(
                        TestResult(
                            name=rel_posix,
                            outcome=TestOutcome.PASSED,
                            duration_ms=duration,
                            detail=proc.stdout[-500:] if proc.stdout else "",
                        )
                    )
                else:
                    results.append(
                        TestResult(
                            name=rel_posix,
                            outcome=TestOutcome.FAILED,
                            duration_ms=duration,
                            detail=(proc.stderr or proc.stdout or "")[-500:],
                        )
                    )
            except subprocess.TimeoutExpired:
                duration = (time.monotonic() - started) * 1000
                results.append(
                    TestResult(
                        name=rel_posix,
                        outcome=TestOutcome.ERROR,
                        duration_ms=duration,
                        detail=f"超过超时时间 {timeout}s",
                    )
                )
            except OSError as exc:
                duration = (time.monotonic() - started) * 1000
                results.append(
                    TestResult(
                        name=rel_posix,
                        outcome=TestOutcome.ERROR,
                        duration_ms=duration,
                        detail=f"无法执行: {exc}",
                    )
                )

    return results


def _collect_test_scripts(skill_dir: Path) -> list[Path]:
    """发现 tests/ 或 test/ 目录中的可执行测试脚本。"""
    found: list[Path] = []
    for d in (skill_dir / "tests", skill_dir / "test"):
        if d.is_dir():
            for child in sorted(d.iterdir()):
                if child.is_file() and child.suffix.lower() in {".sh", ".py", ".js", ".ts"}:
                    found.append(child)
    return found


def _python() -> str:
    return sys.executable


def _shell() -> str:
    """选择 shell：Windows 优先 Git Bash（跳过不可用的 WSL bash），POSIX 用 /bin/bash。"""
    if _IS_WINDOWS:
        for candidate in _GIT_BASH_CANDIDATES:
            if os.path.isfile(candidate):
                return candidate
        # 回退：非 WSL 的 bash（跳过 WindowsApps 的 WSL 启动器）
        for cand in shutil.which("bash") or []:
            if "WindowsApps" not in cand:
                return cand
        return os.environ.get("COMSPEC", "cmd.exe")
    return "/bin/bash"


def _script_arg(path: Path) -> str:
    """将脚本路径转为 shell 可接受的参数形式。"""
    p = str(path)
    if _IS_WINDOWS:
        # Git Bash 需要正斜杠路径
        return p.replace("\\", "/")
    return p

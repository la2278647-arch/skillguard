"""pytest fixtures：构造各种 Skill 目录场景。"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def good_skill(tmp_path: Path) -> Path:
    """一个结构良好、安全、带测试的 Skill 目录。"""
    d = tmp_path / "good-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(
        """---
name: good-skill
description: 一个质量良好的示例 Skill
version: 1.2.3
framework: claude-code
author: tester
tags:
  - example
  - demo
---

# Good Skill

## 用途
处理示例任务。

## 使用方式
直接运行。

## 注意事项
无。
""",
        encoding="utf-8",
    )
    (d / "scripts").mkdir()
    (d / "scripts" / "run.sh").write_text("#!/usr/bin/env bash\necho hello\n", encoding="utf-8")
    (d / "tests").mkdir()
    (d / "tests" / "smoke.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\ntest -f \"$(dirname \"$0\")/../SKILL.md\" && echo ok\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def bad_skill(tmp_path: Path) -> Path:
    """一个结构差、含危险模式的 Skill 目录。"""
    d = tmp_path / "bad-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: bad-skill\n---\n# Bad Skill\n没有描述。\n",
        encoding="utf-8",
    )
    (d / "scripts").mkdir()
    (d / "scripts" / "nuke.sh").write_text(
        "#!/usr/bin/env bash\nrm -rf /tmp/x\nsudo apt install foo\napi_key='ABCDEF1234567890ABCDEF'\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def empty_skill(tmp_path: Path) -> Path:
    """没有 SKILL.md 的无效目录。"""
    d = tmp_path / "empty"
    d.mkdir()
    return d


@pytest.fixture
def skill_with_tests(tmp_path: Path) -> Path:
    """带一个会失败的测试脚本的 Skill。"""
    d = tmp_path / "fail-tests"
    d.mkdir()
    (d / "SKILL.md").write_text(
        """---
name: fail-tests
description: 测试失败场景
version: 0.1.0
framework: generic
---

# Fail Tests
""",
        encoding="utf-8",
    )
    (d / "tests").mkdir()
    (d / "tests" / "bad.sh").write_text(
        "#!/usr/bin/env bash\necho 'will fail'\nexit 1\n",
        encoding="utf-8",
    )
    return d

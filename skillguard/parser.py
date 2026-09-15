"""Skill 目录解析：读取 SKILL.md 元数据并发现脚本。

支持两种常见 SKILL.md 元数据格式：
1. YAML front-matter（--- 分隔的 YAML 块）
2. 简易键值注释（`# name: xxx`）
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .models import SkillInfo

# 常见入口文件名
ENTRYPOINT_NAMES = ("SKILL.md", "skill.md", "agent.md", "AGENT.md")
# 可执行脚本扩展名
SCRIPT_EXTS = {".sh", ".py", ".js", ".ts", ".mjs", ".cjs", ".rb", ".pl"}

_YAML_FRONT_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_KEYVAL_RE = re.compile(r"^\s*#\s*([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$")


def find_skill_dir(start: Path) -> Path | None:
    """从 start 向上查找包含 SKILL.md 的目录，找不到返回 None。"""
    current = start.resolve()
    for candidate in (current, *current.parents):
        for name in ENTRYPOINT_NAMES:
            if (candidate / name).is_file():
                return candidate
    return None


def parse_skill_metadata(entrypoint: Path) -> dict[str, object]:
    """解析 SKILL.md 的元数据（front-matter 优先，其次键值注释）。"""
    text = entrypoint.read_text(encoding="utf-8", errors="replace")
    meta: dict[str, object] = {}

    fm = _YAML_FRONT_RE.match(text)
    if fm:
        try:
            parsed = yaml.safe_load(fm.group(1)) or {}
            if isinstance(parsed, dict):
                meta.update(parsed)
        except yaml.YAMLError:
            pass  # 交给键值解析回退

    # 键值注释回退 / 补充
    if not meta:
        for line in text.splitlines():
            m = _KEYVAL_RE.match(line)
            if m:
                meta[m.group(1)] = m.group(2).strip()

    return meta


def _normalize_tags(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return []


def load_skill(skill_dir: Path) -> SkillInfo | None:
    """加载 Skill 目录，返回 SkillInfo；目录无效时返回 None。"""
    skill_dir = skill_dir.resolve()
    entrypoint = None
    for name in ENTRYPOINT_NAMES:
        p = skill_dir / name
        if p.is_file():
            entrypoint = p
            break
    if entrypoint is None:
        return None

    meta = parse_skill_metadata(entrypoint)
    scripts = discover_scripts(skill_dir)
    return SkillInfo(
        name=str(meta.get("name") or skill_dir.name),
        description=str(meta.get("description", "")),
        version=str(meta.get("version", "0.0.0")),
        framework=str(meta.get("framework", "generic")),
        author=str(meta.get("author", "")),
        tags=_normalize_tags(meta.get("tags", [])),
        entrypoint=entrypoint.name,
        has_scripts=len(scripts) > 0,
        script_count=len(scripts),
    )


def discover_scripts(skill_dir: Path) -> list[Path]:
    """发现 Skill 目录下的可执行脚本（scripts/ 子目录优先，其次根目录）。"""
    found: list[Path] = []
    scripts_dir = skill_dir / "scripts"
    search_dirs = [scripts_dir] if scripts_dir.is_dir() else [skill_dir]
    for d in search_dirs:
        for child in sorted(d.iterdir()):
            if child.is_file() and child.suffix.lower() in SCRIPT_EXTS:
                found.append(child)
    return found

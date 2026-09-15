"""静态校验引擎：结构、引用完整性、安全模式扫描。

规则 ID 约定：
- SRC-*  ：结构 (structure)
- REF-*  ：引用完整性 (reference)
- SEC-*  ：安全模式 (security)
- DOC-*  ：文档规范 (documentation)
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import CheckResult, Severity, SkillInfo

# ----------------------------------------------------------------------
# 安全模式：高风险的命令/模式
# ----------------------------------------------------------------------
DANGEROUS_PATTERNS: list[tuple[str, str, Severity]] = [
    (
        "SEC-001",
        r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)+|rm\s+-rf\s+[/~]|rm\s+--?recursive",
        Severity.ERROR,
    ),
    ("SEC-002", r"\bmkfs\b|\bdd\s+if=.*of=/dev/", Severity.ERROR),
    ("SEC-003", r"\bchmod\s+777\b", Severity.WARNING),
    ("SEC-004", r"\bcurl\s+[^|]*\|[^|]*sh\b|\bwget\s+[^|]*\|[^|]*sh\b", Severity.WARNING),
    ("SEC-005", r"['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", Severity.ERROR),
    ("SEC-006", r"token\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]", Severity.WARNING),
    ("SEC-007", r"\bgit\s+push\s+--force\b", Severity.WARNING),
    ("SEC-008", r"\beval\s+['\"]?\$?\(", Severity.ERROR),
    ("SEC-009", r"\bsudo\b", Severity.INFO),
]

# 引用完整性：常见的本地文件/脚本引用模式
_REFERENCE_PATTERNS = [
    re.compile(r"`?\.?/?(?:scripts|bin|tools)/[A-Za-z0-9_\-./]+`?"),
    re.compile(r"`?[A-Za-z0-9_\-]+\.(?:sh|py|js|ts|rb|pl)`?"),
]

_ENTRY_NAMES = ("SKILL.md", "skill.md")


def _find_entry(skill_dir: Path) -> Path | None:
    """独立发现入口文件（不依赖 SkillInfo.entrypoint，增强健壮性）。"""
    for name in _ENTRY_NAMES:
        p = skill_dir / name
        if p.is_file():
            return p
    return None


def run_static_checks(skill_dir: Path, skill: SkillInfo, skip_safety: bool = False) -> list[CheckResult]:
    """执行全部静态检查（内置 + 已注册的自定义规则），返回按严重级排序的结果。"""
    results: list[CheckResult] = []
    results.extend(_structure_checks(skill_dir, skill))
    results.extend(_reference_checks(skill_dir, skill))
    if not skip_safety:
        results.extend(_safety_checks(skill_dir))
    # 自定义规则（插件系统）
    from .rules import registry

    results.extend(registry.run_custom(skill_dir, skill))
    results.sort(key=lambda r: (r.severity.value != Severity.ERROR.value, r.severity.value))
    return results


# ----------------------------------------------------------------------
# 结构检查
# ----------------------------------------------------------------------
def _structure_checks(skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
    results: list[CheckResult] = []

    # SRC-001：入口文件存在
    entry = _find_entry(skill_dir)
    if entry is None:
        results.append(
            CheckResult("SRC-001", Severity.ERROR, "缺少 SKILL.md 入口文件", file=skill_dir.name)
        )
        return results

    # SRC-002：有名称
    if not skill.name:
        results.append(CheckResult("SRC-002", Severity.ERROR, "SKILL.md 缺少 name 元数据", file=entry.name))

    # SRC-003：有描述
    if not skill.description:
        results.append(CheckResult("SRC-003", Severity.WARNING, "SKILL.md 缺少 description（AI 无法理解用途）", file=entry.name))

    # SRC-004：脚本目录存在性
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        non_script = [p.name for p in scripts_dir.iterdir() if p.is_file() and p.suffix.lower() not in {
            ".sh", ".py", ".js", ".ts", ".mjs", ".cjs", ".rb", ".pl", ".md", ".txt", ".json", ".yaml", ".yml",
        }]
        if non_script:
            results.append(
                CheckResult(
                    "SRC-004",
                    Severity.INFO,
                    f"scripts/ 中存在非常规文件: {', '.join(non_script[:5])}",
                    file="scripts",
                )
            )

    # SRC-005：入口文件大小（过大说明不可维护）
    size = entry.stat().st_size if entry.is_file() else 0
    if size > 40_000:
        results.append(
            CheckResult("SRC-005", Severity.WARNING, f"SKILL.md 过大（{size} 字节），建议拆分为参考文档", file=entry.name)
        )
    elif size == 0:
        results.append(CheckResult("SRC-005", Severity.ERROR, "SKILL.md 为空文件", file=entry.name))

    return results


# ----------------------------------------------------------------------
# 引用完整性
# ----------------------------------------------------------------------
def _reference_checks(skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
    results: list[CheckResult] = []
    entry = _find_entry(skill_dir)
    if entry is None:
        return results

    text = entry.read_text(encoding="utf-8", errors="replace")
    existing_files = {p.name for p in skill_dir.rglob("*") if p.is_file()}

    for m in _REFERENCE_PATTERNS[0].finditer(text):
        raw = m.group(0).strip("`").lstrip("./")
        if not raw:
            continue
        ref_name = raw.split("/")[-1]
        if ref_name and ref_name not in existing_files:
            results.append(
                CheckResult(
                    "REF-001",
                    Severity.WARNING,
                    f"引用的本地脚本/文件可能不存在: {raw}",
                    file=entry.name,
                )
            )

    # REF-002：引用了脚本但脚本目录为空
    scripts_dir = skill_dir / "scripts"
    if "scripts" in text and scripts_dir.is_dir() and not any(scripts_dir.iterdir()):
        results.append(
            CheckResult("REF-002", Severity.WARNING, "SKILL.md 引用了 scripts/ 但目录为空", file=entry.name)
        )

    return results


# ----------------------------------------------------------------------
# 安全扫描
# ----------------------------------------------------------------------
def _safety_checks(skill_dir: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    text_files = [
        p
        for p in skill_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".sh", ".py", ".js", ".ts", ".txt", ".yaml", ".yml", ".json"}
    ]
    for path in text_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for rule_id, pattern, severity in DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                results.append(
                    CheckResult(rule_id, severity, f"检测到危险模式: {pattern[:60]}", file=str(path.relative_to(skill_dir)))
                )
    return results

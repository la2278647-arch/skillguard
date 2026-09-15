"""规则注册表：支持内置规则 + 用户自定义规则（插件）。

自定义规则通过 `skillguard.rules` 入口点或直接注册 Checker 对象实现。
每个 Checker 接收 (skill_dir, skill) 并返回 CheckResult 列表。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .models import CheckResult, SkillInfo

# 检查器签名：接收目录与 SkillInfo，返回检查结果列表
Checker = Callable[[Path, SkillInfo], list[CheckResult]]


@dataclass
class RuleSet:
    """一组规则的集合，可组合多个检查器。"""

    name: str
    checkers: list[Checker] = field(default_factory=list)

    def add(self, checker: Checker) -> RuleSet:
        self.checkers.append(checker)
        return self

    def run_all(self, skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
        results: list[CheckResult] = []
        for checker in self.checkers:
            results.extend(checker(skill_dir, skill))
        return results


class RuleRegistry:
    """全局规则注册表：按规则前缀分派。

    - 内置规则（SRC/REF/SEC/DOC）由 validator 提供
    - 自定义规则通过 `register()` 注册，使用自定义前缀（如 CUS-）
    """

    def __init__(self) -> None:
        self._custom_checkers: dict[str, Checker] = {}

    def register(self, prefix: str, checker: Checker) -> None:
        """注册自定义检查器。

        Args:
            prefix: 规则 ID 前缀（如 "CUS"），对应规则 ID 如 CUS-001。
            checker: 签名 (skill_dir: Path, skill: SkillInfo) -> list[CheckResult]
        """
        if not prefix or not prefix.isalnum() or len(prefix) < 3:
            raise ValueError("prefix 必须为 3+ 位字母数字（如 CUS、STYLE）")
        normalized = prefix.upper()
        if normalized in _BUILTIN_PREFIXES:
            raise ValueError(f"prefix {normalized} 与内置规则冲突")
        self._custom_checkers[normalized] = checker

    def unregister(self, prefix: str) -> None:
        self._custom_checkers.pop(prefix.upper(), None)

    def run_custom(self, skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
        results: list[CheckResult] = []
        for checker in self._custom_checkers.values():
            results.extend(checker(skill_dir, skill))
        return results

    def has_custom(self) -> bool:
        return bool(self._custom_checkers)

    def custom_prefixes(self) -> list[str]:
        return sorted(self._custom_checkers)


_BUILTIN_PREFIXES = {"SRC", "REF", "SEC", "DOC"}


# 全局单例
registry = RuleRegistry()

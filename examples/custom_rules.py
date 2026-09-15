"""SkillGuard 自定义规则示例（插件系统演示）。

本文件展示如何为 SkillGuard 注册团队自定义检查规则。
保存为 `my_rules.py`，然后在你的代码中导入注册：

    # 注册（在程序入口执行一次）
    from my_rules import register_custom_rules
    register_custom_rules()

    # 之后所有 skillguard check / scan / report 都会自动包含这些规则

规则 ID 前缀约定：自定义规则用 3+ 位字母数字前缀（如 CUS、TEAM、STYLE），
与内置前缀 SRC/REF/SEC/DOC 不冲突。
自定义规则默认归入「可维护性」评分维度。
"""

from __future__ import annotations

from pathlib import Path

from skillguard.models import CheckResult, Severity, SkillInfo
from skillguard.rules import registry


# ----------------------------------------------------------------------
# 规则 1：CUS-001 检查 TODO / FIXME 遗留
# ----------------------------------------------------------------------
def no_todo_leftovers(skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
    """扫描 SKILL.md 中的 TODO/FIXME 遗留标记。

    遗留的 TODO 说明 Skill 尚未完成，作者应清理后再发布。
    """
    entry = skill_dir / "SKILL.md"
    if not entry.is_file():
        return []
    text = entry.read_text(encoding="utf-8", errors="replace")
    findings: list[CheckResult] = []
    for i, line in enumerate(text.splitlines(), 1):
        upper = line.upper()
        if "TODO" in upper or "FIXME" in upper:
            findings.append(
                CheckResult(
                    "CUS-001",
                    Severity.WARNING,
                    f"发现遗留标记: {line.strip()[:60]}",
                    file="SKILL.md",
                    line=i,
                )
            )
    return findings


# ----------------------------------------------------------------------
# 规则 2：CUS-002 检查必需的前言部分
# ----------------------------------------------------------------------
REQUIRED_SECTIONS = ["## 用途", "## 使用方式", "## 注意事项"]


def has_required_sections(skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
    """检查 SKILL.md 是否包含团队约定的必备章节。"""
    entry = skill_dir / "SKILL.md"
    if not entry.is_file():
        return []
    text = entry.read_text(encoding="utf-8", errors="replace")
    findings: list[CheckResult] = []
    for section in REQUIRED_SECTIONS:
        if section not in text:
            findings.append(
                CheckResult(
                    "CUS-002",
                    Severity.WARNING,
                    f"缺少约定章节: {section}",
                    file="SKILL.md",
                )
            )
    return findings


# ----------------------------------------------------------------------
# 规则 3：CUS-003 检查脚本是否有错误处理
# ----------------------------------------------------------------------
def scripts_check_error_handling(skill_dir: Path, skill: SkillInfo) -> list[CheckResult]:
    """检查 scripts/ 目录中的 .sh 脚本是否包含 set -e 或错误处理。

    缺少错误处理的脚本可能在中间步骤失败后继续执行，产生错误结果。
    """
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []
    findings: list[CheckResult] = []
    for script in sorted(scripts_dir.glob("*.sh")):
        text = script.read_text(encoding="utf-8", errors="replace")
        if "set -e" not in text and "set -o errexit" not in text:
            findings.append(
                CheckResult(
                    "CUS-003",
                    Severity.WARNING,
                    "脚本缺少 set -e（出错后继续执行风险）",
                    file=script.name,
                )
            )
    return findings


# ----------------------------------------------------------------------
# 注册入口
# ----------------------------------------------------------------------
def register_custom_rules() -> None:
    """注册全部自定义规则到全局注册表（幂等：重复调用安全）。"""
    registry.unregister("CUS")
    registry.register("CUS", no_todo_leftovers)
    registry.register("CUS", has_required_sections)
    registry.register("CUS", scripts_check_error_handling)


if __name__ == "__main__":
    # 测试注册（直接运行：python my_rules.py）
    register_custom_rules()
    print(f"✅ 已注册自定义规则前缀: {registry.custom_prefixes()}")

    # 使用示例
    from skillguard import Config, SkillGuard

    report = SkillGuard(Config(skill_dir=".")).validate()
    cus_issues = [c for c in report.checks if c.rule_id.startswith("CUS-")]
    print(f"自定义检查发现 {len(cus_issues)} 个问题:")
    for c in cus_issues:
        print(f"  {c.rule_id}: {c.message} ({c.file})")
"""质量评分模型：对 Skill 进行多维度打分（0-100）。

五个维度：
- structure      结构完整性（入口、脚本、命名）
- documentation  文档清晰度（描述、示例、参数说明）
- safety         安全性（无危险模式、无硬编码密钥）
- maintainability 可维护性（体积、模块化、脚本整洁）
- usability      实用性（有测试、有元数据、版本规范）
"""

from __future__ import annotations

from .models import CheckResult, QualityReport, ScoreBreakdown, Severity, SkillInfo

# 维度 -> 严重级扣分
_PENALTY = {
    "structure": {Severity.ERROR: 30, Severity.WARNING: 10, Severity.INFO: 2},
    "documentation": {Severity.ERROR: 25, Severity.WARNING: 10, Severity.INFO: 2},
    "safety": {Severity.ERROR: 50, Severity.WARNING: 15, Severity.INFO: 3},
    "maintainability": {Severity.ERROR: 25, Severity.WARNING: 10, Severity.INFO: 2},
    "usability": {Severity.ERROR: 25, Severity.WARNING: 10, Severity.INFO: 2},
}


def score_skill(skill: SkillInfo, checks: list[CheckResult], tests: list) -> tuple[ScoreBreakdown, float]:
    """计算质量评分（扣分制，满分 100 起步）。

    Returns:
        (分项明细, 综合分数 0-100)
    """
    breakdown = ScoreBreakdown(
        structure=100.0,
        documentation=100.0,
        safety=100.0,
        maintainability=100.0,
        usability=100.0,
    )

    # 按规则前缀分派到维度
    _map = {
        "SRC": "structure",
        "REF": "maintainability",
        "SEC": "safety",
        "DOC": "documentation",
        "CUS": "maintainability",  # 自定义规则默认归入可维护性
    }
    for check in checks:
        prefix = check.rule_id.split("-")[0]
        dim = _map.get(prefix)
        if dim is None:
            continue
        breakdown = _apply_penalty(breakdown, dim, check.severity)

    # 缺失项扣分（usability / maintainability）
    if not skill.tags:
        breakdown.usability = max(0.0, breakdown.usability - 5)
    if not _valid_version(skill.version):
        breakdown.usability = max(0.0, breakdown.usability - 3)
    if not skill.has_scripts:
        breakdown.maintainability = max(0.0, breakdown.maintainability - 5)
        breakdown.usability = max(0.0, breakdown.usability - 5)

    # 测试加分项
    passed = sum(1 for t in tests if t.outcome.value == "passed")
    if tests and passed == len(tests):
        breakdown.usability = _bump(breakdown.usability, 10)
        breakdown.maintainability = _bump(breakdown.maintainability, 5)

    overall = (
        breakdown.structure * 0.25
        + breakdown.documentation * 0.20
        + breakdown.safety * 0.30
        + breakdown.maintainability * 0.15
        + breakdown.usability * 0.10
    )
    return breakdown, round(max(0.0, min(100.0, overall)), 2)


def _apply_penalty(breakdown: ScoreBreakdown, dim: str, severity: Severity) -> ScoreBreakdown:
    """对指定维度应用扣分（不可低于 0）。"""
    penalty = _PENALTY[dim][severity]
    current = getattr(breakdown, dim)
    setattr(breakdown, dim, max(0.0, current - penalty))
    return breakdown


def _bump(value: float, amount: float) -> float:
    return min(100.0, value + amount)


def _valid_version(version: str) -> bool:
    import re

    return bool(re.match(r"^\d+\.\d+(\.\d+)?$", version))


def evaluate_passed(report: QualityReport, threshold: float) -> bool:
    """判断是否通过质量门禁。

    通过条件：
    1. 无 ERROR 级检查问题
    2. 无 FAILED 测试
    3. 综合分数 >= threshold
    """
    if report.error_count() > 0:
        return False
    if report.failed_tests() > 0:
        return False
    return report.overall_score >= threshold

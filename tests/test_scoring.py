"""测试：质量评分模型。"""

from __future__ import annotations

from skillguard.models import CheckResult, Severity, SkillInfo, TestOutcome, TestResult
from skillguard.scoring import _valid_version, evaluate_passed, score_skill


def _skill(**kw) -> SkillInfo:
    """构造一个接近完美的 Skill（有 tags、有脚本、版本有效）。"""
    defaults = {
        "name": "s",
        "description": "d",
        "version": "1.0.0",
        "framework": "generic",
        "tags": ["example"],
        "has_scripts": True,
        "script_count": 1,
    }
    defaults.update(kw)
    return SkillInfo(**defaults)


class TestScoreSkill:
    def test_perfect_baseline(self) -> None:
        skill = _skill()
        breakdown, overall = score_skill(skill, [], [])
        assert overall == 100.0
        assert breakdown.structure == 100.0

    def test_safety_error_heavy_penalty(self) -> None:
        skill = _skill()
        checks = [CheckResult("SEC-001", Severity.ERROR, "rm -rf")]
        breakdown, overall = score_skill(skill, checks, [])
        assert breakdown.safety == 50.0
        assert overall < 100.0

    def test_structure_error(self) -> None:
        skill = _skill()
        checks = [CheckResult("SRC-001", Severity.ERROR, "no entry")]
        breakdown, _ = score_skill(skill, checks, [])
        assert breakdown.structure == 70.0

    def test_multiple_warnings_accumulate(self) -> None:
        skill = _skill()
        checks = [
            CheckResult("SRC-003", Severity.WARNING, "a"),
            CheckResult("SRC-004", Severity.WARNING, "b"),
            CheckResult("SRC-005", Severity.WARNING, "c"),
        ]
        breakdown, _ = score_skill(skill, checks, [])
        assert breakdown.structure == 70.0  # 100 - 10*3

    def test_score_floor_at_zero(self) -> None:
        skill = _skill()
        checks = [
            CheckResult("SEC-001", Severity.ERROR, "1"),
            CheckResult("SEC-002", Severity.ERROR, "2"),
            CheckResult("SEC-003", Severity.ERROR, "3"),
        ]
        breakdown, _ = score_skill(skill, checks, [])
        assert breakdown.safety == 0.0

    def test_missing_tags_penalty(self) -> None:
        skill = _skill(tags=[])
        breakdown, _ = score_skill(skill, [], [])
        assert breakdown.usability == 95.0  # 100 - 5

    def test_invalid_version_penalty(self) -> None:
        skill = _skill(version="latest")
        breakdown, _ = score_skill(skill, [], [])
        assert breakdown.usability == 97.0  # 100 - 3

    def test_no_scripts_penalty(self) -> None:
        skill = _skill(has_scripts=False, script_count=0)
        breakdown, _ = score_skill(skill, [], [])
        assert breakdown.maintainability == 95.0  # 100 - 5
        assert breakdown.usability == 95.0  # 100 - 5

    def test_all_tests_passed_bonus(self) -> None:
        skill = _skill()
        tests = [TestResult("t", TestOutcome.PASSED)]
        breakdown, _ = score_skill(skill, [], tests)
        # 100 + 10(usability) / +5(maintainability) 封顶 100
        assert breakdown.usability == 100.0
        assert breakdown.maintainability == 100.0

    def test_unknown_rule_prefix_ignored(self) -> None:
        skill = _skill()
        checks = [CheckResult("XYZ-001", Severity.ERROR, "unknown")]
        breakdown, overall = score_skill(skill, checks, [])
        assert overall == 100.0  # 未知规则不扣分
        assert breakdown.structure == 100.0

    def test_floor_never_negative(self) -> None:
        skill = _skill()
        checks = [CheckResult(f"SRC-00{i}", Severity.ERROR, f"e{i}") for i in range(10)]
        breakdown, _ = score_skill(skill, checks, [])
        assert breakdown.structure >= 0.0


class TestValidVersion:
    def test_valid(self) -> None:
        assert _valid_version("1.0.0")
        assert _valid_version("0.1")
        assert _valid_version("2.3.4")

    def test_invalid(self) -> None:
        assert not _valid_version("latest")
        assert not _valid_version("v1.0")
        assert not _valid_version("")
        assert not _valid_version("1")


class TestEvaluatePassed:
    def test_all_green(self) -> None:
        skill = _skill()
        breakdown, overall = score_skill(skill, [], [])
        from skillguard.models import QualityReport

        report = QualityReport(
            skill=skill, version="0.1.0", timestamp="t", score=breakdown, overall_score=overall
        )
        assert evaluate_passed(report, 60.0) is True

    def test_error_blocks(self) -> None:
        from skillguard.models import QualityReport

        report = QualityReport(
            skill=_skill(),
            version="0.1.0",
            timestamp="t",
            checks=[CheckResult("SEC-001", Severity.ERROR, "x")],
            score=None,  # type: ignore[arg-type]
            overall_score=90.0,
        )
        assert evaluate_passed(report, 60.0) is False

    def test_failed_test_blocks(self) -> None:
        from skillguard.models import QualityReport

        report = QualityReport(
            skill=_skill(),
            version="0.1.0",
            timestamp="t",
            tests=[TestResult("t", TestOutcome.FAILED)],
            score=None,  # type: ignore[arg-type]
            overall_score=90.0,
        )
        assert evaluate_passed(report, 60.0) is False

    def test_below_threshold_blocks(self) -> None:
        from skillguard.models import QualityReport

        report = QualityReport(
            skill=_skill(),
            version="0.1.0",
            timestamp="t",
            score=None,  # type: ignore[arg-type]
            overall_score=50.0,
        )
        assert evaluate_passed(report, 60.0) is False
        assert evaluate_passed(report, 40.0) is True

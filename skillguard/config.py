"""配置模型：SkillGuard 的运行时配置。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """SkillGuard 运行时配置。

    Attributes:
        skill_dir: 目标 Skill 目录（包含 SKILL.md 的目录）。
        rules: 启用的规则 ID 列表；为空表示启用全部内置规则。
        run_tests: 是否执行 Skill 自带的测试脚本（沙箱中）。
        test_timeout: 单个测试脚本的超时秒数。
        skip_safety: 是否跳过安全模式扫描（默认 False，即执行）。
        report_format: 报告输出格式，可选 "json" / "markdown" / "html"。
        report_output: 报告输出路径；None 时仅打印摘要。
        threshold: 质量门禁分数（0-100），低于该分则 CI 失败。
    """

    skill_dir: str = "."
    rules: tuple[str, ...] = ()
    run_tests: bool = True
    test_timeout: int = 60
    skip_safety: bool = False
    report_format: str = "json"
    report_output: str | None = None
    threshold: float = 60.0

    def __post_init__(self) -> None:
        if self.test_timeout <= 0:
            raise ValueError("test_timeout 必须为正整数")
        if not 0 <= self.threshold <= 100:
            raise ValueError("threshold 必须在 0-100 之间")
        if self.report_format not in ("json", "markdown", "html"):
            raise ValueError("report_format 必须是 json / markdown / html 之一")

    @property
    def skill_path(self) -> Path:
        return Path(self.skill_dir).resolve()

    def with_overrides(self, **kwargs: object) -> Config:
        """返回应用了部分覆盖的新配置（不变更原配置）。"""
        return Config(**{**self.__dict__, **kwargs})

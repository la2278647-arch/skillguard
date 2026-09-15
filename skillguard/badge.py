"""评分徽章生成器：输出 SVG 徽章（可嵌入 README）。

徽章样式参考 shields.io 扁平风格，零外部依赖，生成后可：
- 放入 Skill 仓库 README，展示 SkillGuard 评分
- 用于 CI 报告附件 / 网站展示

示例（Markdown 用法）：
    ![SkillGuard](skillguard-badge.svg)
"""

from __future__ import annotations

import html
from pathlib import Path

from .models import QualityReport


def _score_color(score: float) -> str:
    """按分数返回徽章颜色。"""
    if score >= 90:
        return "brightgreen"  # 4c1
    if score >= 75:
        return "green"  # 97ca00
    if score >= 60:
        return "yellowgreen"  # a4a61d
    if score >= 40:
        return "yellow"  # dfb317
    return "red"  # e05d44


def _hex_color(name: str) -> str:
    return {
        "brightgreen": "#4c1",
        "green": "#97ca00",
        "yellowgreen": "#a4a61d",
        "yellow": "#dfb317",
        "orange": "#fe7d37",
        "red": "#e05d44",
        "blue": "#007ec6",
        "grey": "#555",
    }[name]


def render_badge(
    score: float,
    label: str = "skillguard",
    passed: bool | None = None,
    style: str = "flat",
) -> str:
    """生成 SVG 徽章字符串。

    Args:
        score: 质量分数（0-100）。
        label: 左侧标签（默认 skillguard）。
        passed: 通过状态；None 时不显示状态文本。
        style: 样式（flat / plastic）。
    """
    color = _score_color(score)
    passed_text = ""
    if passed is not None:
        passed_text = " ✅" if passed else " ❌"

    value = f"{score:.0f}/100{passed_text}"
    # 粗略宽度估算（每字符约 7px）
    label_w = 8 + len(label) * 7
    value_w = 8 + len(value) * 7.2
    total_w = label_w + value_w

    if style == "plastic":
        # 塑料风格：有渐变与圆角更明显
        height = 20
        radius = 3
        grad = (
            '<linearGradient id="g" x2="0" y2="100%">'
            '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
            '<stop offset="1" stop-opacity=".1"/></linearGradient>'
        )
    else:
        height = 20
        radius = 3
        grad = ""

    label_bg = "#555"
    value_bg = _hex_color(color)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{height}" role="img" aria-label="{html.escape(label)}: {html.escape(value)}">'
        f"{grad}"
        f'<title>{html.escape(label)}: {html.escape(value)}</title>'
        # 左侧标签背景
        f'<rect x="0" y="0" width="{label_w}" height="{height}" fill="{label_bg}" rx="{radius}"/>'
        f'<rect x="{label_w}" y="0" width="{value_w}" height="{height}" fill="{value_bg}" rx="0"/>'
        f'<rect x="{label_w - radius}" y="0" width="{radius + 1}" height="{height}" fill="{value_bg}"/>'
        # 文本
        f'<g fill="#fff" text-anchor="middle" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="{label_w / 2:.0f}" y="14">{html.escape(label)}</text>'
        f'<text x="{label_w + value_w / 2:.0f}" y="14">{html.escape(value)}</text>'
        f"</g></svg>"
    )


def write_badge(report: QualityReport, output: str | Path) -> Path:
    """将报告渲染为评分徽章并写入文件，返回写入路径。"""
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        render_badge(report.overall_score, passed=report.passed),
        encoding="utf-8",
    )
    return out


def badge_markdown(output: str | Path, repo_url: str = "") -> str:
    """生成嵌入 README 的 Markdown 片段。"""
    path = str(output).replace("\\", "/")
    if repo_url:
        return f"[![SkillGuard]({path})]({repo_url})"
    return f"![SkillGuard]({path})"

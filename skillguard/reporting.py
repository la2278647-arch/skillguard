"""报告生成器：将 QualityReport 输出为 JSON / Markdown / HTML。

- JSON：结构化数据，供 CI 与外部工具消费
- Markdown：人类可读摘要，可粘贴到 PR 评论 / README
- HTML：自包含单文件报告，含样式，可直接分享
"""

from __future__ import annotations

import html as html_lib
import math
from pathlib import Path

from .models import QualityReport, Severity, TestOutcome

_SEVERITY_EMOJI = {
    Severity.ERROR: "🔴",
    Severity.WARNING: "🟡",
    Severity.INFO: "🔵",
}
_TEST_EMOJI = {
    TestOutcome.PASSED: "✅",
    TestOutcome.FAILED: "❌",
    TestOutcome.SKIPPED: "⏭️",
    TestOutcome.ERROR: "⚠️",
}


def _radar_svg(scores: dict[str, float], size: int = 320) -> str:
    """生成五维评分的 SVG 雷达图（零外部依赖）。"""
    labels = [
        ("structure", "结构"),
        ("documentation", "文档"),
        ("safety", "安全"),
        ("maintainability", "维护"),
        ("usability", "实用"),
    ]
    n = len(labels)
    cx = cy = size / 2
    radius = size * 0.34

    def point(i: int, value: float) -> tuple[float, float]:
        angle = -90 + i * (360 / n)
        r = radius * (value / 100.0)
        rad = angle * math.pi / 180
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    # 背景网格（50 / 100 两层）
    grid = ""
    for level in (0.5, 1.0):
        pts = " ".join(f"{point(i, level * 100)[0]:.1f},{point(i, level * 100)[1]:.1f}" for i in range(n))
        grid += f'<polygon points="{pts}" fill="none" stroke="#334155" stroke-width="1"/>'

    # 轴与标签
    axes = ""
    label_text = ""
    for i, (key, zh) in enumerate(labels):
        tip = point(i, 100)
        axes += f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{tip[0]:.1f}" y2="{tip[1]:.1f}" stroke="#334155" stroke-width="1"/>'
        lp = point(i, 128)
        label_text += f'<text x="{lp[0]:.1f}" y="{lp[1]:.1f}" fill="#94a3b8" font-size="12" text-anchor="middle" dominant-baseline="middle">{zh}</text>'

    # 数据多边形
    pts = " ".join(f"{point(i, scores.get(k, 0))[0]:.1f},{point(i, scores.get(k, 0))[1]:.1f}" for i, (k, _) in enumerate(labels))
    # 数据点
    dots = ""
    for i, (k, _) in enumerate(labels):
        px, py = point(i, scores.get(k, 0))
        dots += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="#60a5fa"/>'

    return (
        f'<svg viewBox="0 0 {size} {size}" width="100%" style="max-width:{size}px" role="img" aria-label="五维评分雷达图">'
        f"{grid}{axes}{label_text}"
        f'<polygon points="{pts}" fill="rgba(96,165,250,.25)" stroke="#60a5fa" stroke-width="2"/>'
        f"{dots}</svg>"
    )


def _bar(value: float, label: str) -> str:
    """生成单维评分进度条。"""
    pct = max(0.0, min(100.0, value))
    color = "#4ade80" if pct >= 80 else "#fbbf24" if pct >= 60 else "#f87171"
    return (
        f'<div class="bar-row"><span class="bar-label">{label}</span>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%;background:{color}"></div></div>'
        f'<span class="bar-value">{value:.1f}</span></div>'
    )


def render_report(report: QualityReport, fmt: str) -> str:
    """按格式渲染报告。fmt: json / markdown / html"""
    if fmt == "json":
        return report.to_json()
    if fmt == "markdown":
        return _render_markdown(report)
    if fmt == "html":
        return _render_html(report)
    raise ValueError(f"不支持的格式: {fmt}")


def write_report(report: QualityReport, output: Path, fmt: str) -> Path:
    """渲染并写入报告文件，返回写入路径。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    content = render_report(report, fmt)
    output.write_text(content, encoding="utf-8")
    return output


def _render_markdown(report: QualityReport) -> str:
    s = report.skill
    lines: list[str] = [
        f"# SkillGuard 评估报告：{s.name}",
        "",
        f"- **工具版本**: skillguard {report.version}",
        f"- **评估时间**: {report.timestamp}",
        f"- **Skill 版本**: {s.version} | **框架**: {s.framework} | **作者**: {s.author or '未知'}",
        f"- **综合评分**: **{report.overall_score}/100** ({'✅ 通过' if report.passed else '❌ 未通过'})",
        "",
        "## 检查摘要",
        "",
        "| 级别 | 数量 |",
        "|------|------|",
        f"| 🔴 error | {report.error_count()} |",
        f"| 🟡 warning | {report.warning_count()} |",
        f"| 🔵 info | {report.info_count()} |",
        "",
    ]

    if report.checks:
        lines.append("## 检查明细")
        lines.append("")
        lines.append("| 级别 | 规则 | 文件 | 问题 |")
        lines.append("|------|------|------|------|")
        for c in report.checks:
            lines.append(
                f"| {_SEVERITY_EMOJI[c.severity]} {c.severity.value} | `{c.rule_id}` | {c.file or '-'} | {c.message} |"
            )
        lines.append("")

    if report.tests:
        lines.append("## 测试结果")
        lines.append("")
        lines.append("| 状态 | 测试 | 耗时 | 详情 |")
        lines.append("|------|------|------|------|")
        for t in report.tests:
            lines.append(
                f"| {_TEST_EMOJI[t.outcome]} {t.outcome.value} | `{t.name}` | {t.duration_ms:.0f}ms | {t.detail[:80]} |"
            )
        lines.append("")

    lines.append("## 评分明细")
    lines.append("")
    lines.append("| 维度 | 分数 |")
    lines.append("|------|------|")
    lines.append(f"| 结构完整性 | {report.score.structure:.1f} |")
    lines.append(f"| 文档清晰度 | {report.score.documentation:.1f} |")
    lines.append(f"| 安全性 | {report.score.safety:.1f} |")
    lines.append(f"| 可维护性 | {report.score.maintainability:.1f} |")
    lines.append(f"| 实用性 | {report.score.usability:.1f} |")
    lines.append("")
    lines.append("---")
    lines.append("_由 [SkillGuard](https://github.com/skillguard/skillguard) 生成_")
    return "\n".join(lines)


def _render_html(report: QualityReport) -> str:
    s = report.skill
    checks_rows = "".join(
        f"<tr class='{c.severity.value}'><td>{_SEVERITY_EMOJI[c.severity]} {c.severity.value}</td>"
        f"<td><code>{html_lib.escape(c.rule_id)}</code></td>"
        f"<td>{html_lib.escape(c.file or '-')}</td>"
        f"<td>{html_lib.escape(c.message)}</td></tr>"
        for c in report.checks
    )
    tests_rows = "".join(
        f"<tr class='{t.outcome.value}'><td>{_TEST_EMOJI[t.outcome]} {t.outcome.value}</td>"
        f"<td><code>{html_lib.escape(t.name)}</code></td>"
        f"<td>{t.duration_ms:.0f}ms</td>"
        f"<td>{html_lib.escape(t.detail[:120])}</td></tr>"
        for t in report.tests
    )
    badge_class = "pass" if report.passed else "fail"
    radar = _radar_svg(
        {
            "structure": report.score.structure,
            "documentation": report.score.documentation,
            "safety": report.score.safety,
            "maintainability": report.score.maintainability,
            "usability": report.score.usability,
        }
    )
    bars = "".join(
        [
            _bar(report.score.structure, "结构完整性"),
            _bar(report.score.documentation, "文档清晰度"),
            _bar(report.score.safety, "安全性"),
            _bar(report.score.maintainability, "可维护性"),
            _bar(report.score.usability, "实用性"),
        ]
    )
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SkillGuard 报告 — {html_lib.escape(s.name)}</title>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #e2e8f0; }}
  .wrap {{ max-width: 920px; margin: 0 auto; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
  h2 {{ font-size: 1.15rem; margin-top: 32px; border-bottom: 1px solid #1e293b; padding-bottom: 8px; }}
  .meta {{ color: #94a3b8; font-size: .9rem; margin-bottom: 20px; }}
  .score {{ font-size: 3rem; font-weight: 700; }}
  .badge {{ display: inline-block; padding: 4px 14px; border-radius: 999px; font-weight: 600; vertical-align: middle; margin-left: 8px; }}
  .badge.pass {{ background: #14532d; color: #4ade80; }}
  .badge.fail {{ background: #7f1d1d; color: #fca5a5; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; font-size: .9rem; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #1e293b; }}
  th {{ background: #1e293b; color: #94a3b8; }}
  tr.error td {{ background: rgba(127,29,29,.35); }}
  tr.warning td {{ background: rgba(113,63,18,.3); }}
  tr.passed td {{ background: rgba(20,83,45,.3); }}
  tr.failed td {{ background: rgba(127,29,29,.3); }}
  .dash {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: center; }}
  .radar-wrap {{ background: #1e293b; border-radius: 12px; padding: 16px; display: flex; justify-content: center; }}
  .bars {{ display: flex; flex-direction: column; gap: 10px; }}
  .bar-row {{ display: grid; grid-template-columns: 72px 1fr 44px; gap: 10px; align-items: center; }}
  .bar-label {{ color: #94a3b8; font-size: .82rem; }}
  .bar-value {{ color: #e2e8f0; font-size: .85rem; font-weight: 600; text-align: right; }}
  .bar-track {{ background: #334155; border-radius: 999px; height: 8px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 999px; transition: width .5s ease; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }}
  .card {{ background: #1e293b; border-radius: 10px; padding: 14px; }}
  .card .label {{ color: #94a3b8; font-size: .8rem; }}
  .card .value {{ font-size: 1.3rem; font-weight: 600; }}
  code {{ background: #1e293b; padding: 1px 6px; border-radius: 4px; }}
  @media (max-width: 640px) {{ .dash {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>SkillGuard 评估报告：{html_lib.escape(s.name)}</h1>
  <div class="meta">skillguard {html_lib.escape(report.version)} · {html_lib.escape(report.timestamp)} · {html_lib.escape(s.framework)} · v{html_lib.escape(s.version)}</div>
  <div class="score">{report.overall_score:.1f}<span style="font-size:1rem;color:#94a3b8">/100</span>
    <span class="badge {badge_class}">{'✅ 通过' if report.passed else '❌ 未通过'}</span>
  </div>
  <div class="dash">
    <div class="radar-wrap">{radar}</div>
    <div class="bars">{bars}</div>
  </div>
  <h2>检查明细（{len(report.checks)}）</h2>
  <table><thead><tr><th>级别</th><th>规则</th><th>文件</th><th>问题</th></tr></thead><tbody>{checks_rows or '<tr><td colspan=4>无</td></tr>'}</tbody></table>
  <h2>测试结果（{len(report.tests)}）</h2>
  <table><thead><tr><th>状态</th><th>测试</th><th>耗时</th><th>详情</th></tr></thead><tbody>{tests_rows or '<tr><td colspan=4>未发现测试脚本</td></tr>'}</tbody></table>
  <div class="meta" style="margin-top:30px">Generated by <a href="https://github.com/skillguard/skillguard" style="color:#60a5fa">SkillGuard</a></div>
</div>
</body>
</html>
"""


# ----------------------------------------------------------------------
# 聚合报告（多 Skill 质量总览）
# ----------------------------------------------------------------------


def aggregate_summary(items: list[dict]) -> dict:
    """从 full_scan_directory 的结果计算聚合统计。"""
    count = len(items)
    if count == 0:
        return {
            "skill_count": 0,
            "avg_score": 0.0,
            "pass_rate": 0.0,
            "total_errors": 0,
            "total_warnings": 0,
            "total_tests": 0,
            "score_distribution": {"90-100": 0, "75-89": 0, "60-74": 0, "40-59": 0, "0-39": 0},
        }
    avg = sum(i["score"] for i in items) / count
    passed = sum(1 for i in items if i["passed"])
    dist = {"90-100": 0, "75-89": 0, "60-74": 0, "40-59": 0, "0-39": 0}
    for i in items:
        s = i["score"]
        if s >= 90:
            dist["90-100"] += 1
        elif s >= 75:
            dist["75-89"] += 1
        elif s >= 60:
            dist["60-74"] += 1
        elif s >= 40:
            dist["40-59"] += 1
        else:
            dist["0-39"] += 1
    return {
        "skill_count": count,
        "avg_score": round(avg, 2),
        "pass_rate": round(passed / count, 2),
        "total_errors": sum(i["errors"] for i in items),
        "total_warnings": sum(i["warnings"] for i in items),
        "total_tests": sum(i["tests"] for i in items),
        "score_distribution": dist,
    }


def render_aggregate(items: list[dict], fmt: str, title: str = "SkillGuard 聚合报告") -> str:
    """渲染多 Skill 聚合报告。fmt: json / markdown / html"""
    summary = aggregate_summary(items)
    if fmt == "json":
        import json as json_lib

        return json_lib.dumps(
            {"summary": summary, "skills": items}, ensure_ascii=False, indent=2
        )
    if fmt == "markdown":
        return _render_aggregate_md(items, summary, title)
    if fmt == "html":
        return _render_aggregate_html(items, summary, title)
    raise ValueError(f"不支持的格式: {fmt}")


def _render_aggregate_md(items: list[dict], summary: dict, title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"- **Skill 数量**: {summary['skill_count']}",
        f"- **平均分**: {summary['avg_score']}",
        f"- **通过率**: {summary['pass_rate'] * 100:.0f}%",
        f"- **累计问题**: 🔴 {summary['total_errors']} / 🟡 {summary['total_warnings']}",
        "",
        "## 评分分布",
        "",
        "| 区间 | 数量 |",
        "|------|------|",
    ]
    for k, v in summary["score_distribution"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Skill 明细", "", "| 分数 | 状态 | Skill | 🔴 | 🟡 | 测试 |", "|------|------|-------|----|----|------|"]
    for i in items:
        status = "✅" if i["passed"] else "❌"
        lines.append(
            f"| {i['score']:.1f} | {status} | {i['name']} | {i['errors']} | {i['warnings']} | {i['tests_passed']}/{i['tests']} |"
        )
    lines += ["", "---", f"_由 SkillGuard 生成_{''}"]
    return "\n".join(lines)


def _render_aggregate_html(items: list[dict], summary: dict, title: str) -> str:
    rows = "".join(
        f"<tr><td><b>{i['score']:.1f}</b></td><td>{'✅' if i['passed'] else '❌'}</td>"
        f"<td>{html_lib.escape(i['name'])}</td><td>{i['errors']}</td><td>{i['warnings']}</td>"
        f"<td>{i['tests_passed']}/{i['tests']}</td></tr>"
        for i in items
    )
    dist_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in summary["score_distribution"].items()
    )
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_lib.escape(title)}</title>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #e2e8f0; }}
  .wrap {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 28px; border-bottom: 1px solid #1e293b; padding-bottom: 8px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }}
  .card {{ background: #1e293b; border-radius: 10px; padding: 14px; }}
  .card .label {{ color: #94a3b8; font-size: .8rem; }}
  .card .value {{ font-size: 1.4rem; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #1e293b; }}
  th {{ background: #1e293b; color: #94a3b8; }}
  code {{ background: #1e293b; padding: 1px 6px; border-radius: 4px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{html_lib.escape(title)}</h1>
  <div class="stats">
    <div class="card"><div class="label">Skill 数量</div><div class="value">{summary['skill_count']}</div></div>
    <div class="card"><div class="label">平均分</div><div class="value">{summary['avg_score']}</div></div>
    <div class="card"><div class="label">通过率</div><div class="value">{summary['pass_rate'] * 100:.0f}%</div></div>
    <div class="card"><div class="label">累计问题</div><div class="value">🔴 {summary['total_errors']} 🟡 {summary['total_warnings']}</div></div>
  </div>
  <h2>评分分布</h2>
  <table><thead><tr><th>区间</th><th>数量</th></tr></thead><tbody>{dist_rows}</tbody></table>
  <h2>Skill 明细（{len(items)}）</h2>
  <table><thead><tr><th>分数</th><th>状态</th><th>Skill</th><th>🔴</th><th>🟡</th><th>测试</th></tr></thead><tbody>{rows or '<tr><td colspan=6>无</td></tr>'}</tbody></table>
  <div class="meta" style="margin-top:30px;color:#94a3b8">Generated by <a href="https://github.com/skillguard/skillguard" style="color:#60a5fa">SkillGuard</a></div>
</div>
</body>
</html>
"""

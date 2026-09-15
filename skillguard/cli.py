"""SkillGuard CLI 入口。"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .config import Config
from .engine import SkillGuard
from .version import __version__


def _force_utf8_output() -> None:
    """Windows 控制台默认 GBK 无法输出 emoji/中文符号，强制 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


@click.group()
@click.version_option(__version__, prog_name="skillguard")
def main() -> None:
    """SkillGuard — Agent Skills 质量保障与测试框架。"""
    _force_utf8_output()


@main.command("check")
@click.argument("skill_dir", type=click.Path(exists=True), default=".")
@click.option("--rules", "-r", multiple=True, help="启用指定规则（可多次）；默认全部规则")
@click.option("--no-tests", is_flag=True, help="跳过测试执行")
@click.option("--skip-safety", is_flag=True, help="跳过安全模式扫描")
@click.option("--timeout", type=int, default=60, show_default=True, help="测试超时秒数")
@click.option("--threshold", type=float, default=60.0, show_default=True, help="质量门禁分数（0-100）")
@click.option("--format", "fmt", type=click.Choice(["json", "markdown", "html"]), default="json",
              show_default=True, help="报告格式")
@click.option("--output", "-o", type=click.Path(), default=None, help="报告输出路径（默认仅打印摘要）")
@click.option("--ci", is_flag=True, help="CI 模式：不通过时退出码为 1")
def check(
    skill_dir: str,
    rules: tuple[str, ...],
    no_tests: bool,
    skip_safety: bool,
    timeout: int,
    threshold: float,
    fmt: str,
    output: str | None,
    ci: bool,
) -> None:
    """检查一个 Skill 目录的质量。"""
    try:
        config = Config(
            skill_dir=skill_dir,
            rules=rules,
            run_tests=not no_tests,
            skip_safety=skip_safety,
            test_timeout=timeout,
            report_format=fmt,
            threshold=threshold,
        )
    except ValueError as exc:
        click.echo(f"❌ 配置错误: {exc}", err=True)
        sys.exit(2)

    guard = SkillGuard(config)
    try:
        report = guard.run()
    except ValueError as exc:
        click.echo(f"❌ {exc}", err=True)
        sys.exit(2)

    _print_summary(report)

    if output:
        guard.export(report, output)
        click.echo(f"📄 报告已写入: {output}")

    if ci and not report.passed:
        sys.exit(1)


@main.command("scan")
@click.argument("root_dir", type=click.Path(exists=True), default=".")
@click.option("--depth", type=int, default=3, show_default=True, help="扫描深度")
@click.option("--threshold", type=float, default=60.0, show_default=True, help="质量门禁分数")
@click.option("--skip-safety", is_flag=True, help="跳过安全模式扫描")
@click.option("--top", type=int, default=20, show_default=True, help="只显示前 N 个")
def scan(root_dir: str, depth: int, threshold: float, skip_safety: bool, top: int) -> None:
    """扫描目录树中的全部 Skill 目录并输出质量排行。"""
    try:
        config = Config(skill_dir=root_dir, threshold=threshold, skip_safety=skip_safety, run_tests=False)
    except ValueError as exc:
        click.echo(f"❌ 配置错误: {exc}", err=True)
        sys.exit(2)

    guard = SkillGuard(config)
    try:
        results = guard.scan_directory(root_dir, max_depth=depth)
    except ValueError as exc:
        click.echo(f"❌ {exc}", err=True)
        sys.exit(2)

    if not results:
        click.echo("未在目录树中发现任何 Skill（需要 SKILL.md 或 skill.md）")
        return

    click.echo(f"\n🔍 扫描完成: 发现 {len(results)} 个 Skill（目录: {root_dir}）\n")
    header = f"{'#':>3}  {'分数':>5}  {'状态':<4}  {'🔴':>3} {'🟡':>3}  {'名称':<30} 路径"
    click.echo(header)
    click.echo("-" * len(header))
    for idx, r in enumerate(results[:top], 1):
        status = "✅" if r["passed"] else "❌"
        click.echo(
            f"{idx:>3}  {r['score']:>5.1f}  {status:<4}  {r['errors']:>3} {r['warnings']:>3}  "
            f"{r['name']:<30} {r['path']}"
        )
    if len(results) > top:
        click.echo(f"... 其余 {len(results) - top} 个略过（--top 调整）")
    click.echo(f"\n平均分: {sum(r['score'] for r in results) / len(results):.1f}")
    click.echo(f"通过率: {sum(1 for r in results if r['passed']) / len(results) * 100:.0f}%")


@main.command("init")
@click.argument("skill_dir", type=click.Path(), default=".")
@click.option("--name", default=None, help="Skill 名称（默认取目录名）")
@click.option("--framework", default="generic", show_default=True,
              type=click.Choice(["generic", "claude-code", "codex", "cursor"]), help="目标框架")
def init(skill_dir: str, name: str, framework: str) -> None:
    """初始化一个 SkillGuard 兼容的 Skill 项目骨架。"""
    target = Path(skill_dir)
    target.mkdir(parents=True, exist_ok=True)
    skill_name = name or target.name or "my-skill"
    entry = target / "SKILL.md"
    if entry.exists():
        click.echo(f"⚠️  {entry} 已存在，跳过创建", err=True)
    else:
        entry.write_text(
            f"""---
name: {skill_name}
description: 一句话描述这个 Skill 的用途
version: 0.1.0
framework: {framework}
tags:
  - example
---

# {skill_name}

## 用途

在下方描述这个 Skill 的使用场景与能力边界。

## 使用方式

告诉 AI 何时以及如何使用本 Skill。

## 注意事项

记录已知限制与注意事项。
""",
            encoding="utf-8",
        )
        click.echo(f"✅ 已创建 {entry}")

    tests_dir = target / "tests"
    tests_dir.mkdir(exist_ok=True)
    smoke = tests_dir / "smoke.sh"
    if not smoke.exists():
        smoke.write_text(
            "#!/usr/bin/env bash\n# 冒烟测试：验证 SKILL.md 存在且非空\nset -euo pipefail\n"
            'test -f "$(dirname "$0")/../SKILL.md" && echo "SKILL.md 存在" && test -s "$(dirname "$0")/../SKILL.md" && echo "SKILL.md 非空"\n',
            encoding="utf-8",
        )
        click.echo(f"✅ 已创建 {smoke}")

    click.echo(f"\n下一步: skillguard check {target}")


def _print_summary(report) -> None:
    """打印人类可读的评估摘要。"""
    s = report.skill
    click.echo(f"\n🔍 SkillGuard 评估: {s.name} (v{s.version}, {s.framework})")
    click.echo(f"  综合评分: {report.overall_score:.1f}/100  {'✅ 通过' if report.passed else '❌ 未通过'}")
    click.echo(
        f"  检查: {len(report.checks)} 项 "
        f"(🔴 {report.error_count()} / 🟡 {report.warning_count()} / 🔵 {report.info_count()})"
    )
    if report.tests:
        click.echo(
            f"  测试: {len(report.tests)} 项 (✅ {report.passed_tests()} / ❌ {report.failed_tests()})"
        )
    for c in report.checks:
        level = {"error": "🔴", "warning": "🟡", "info": "🔵"}[c.severity.value]
        click.echo(f"    {level} [{c.rule_id}] {c.message} ({c.file})")


if __name__ == "__main__":
    main()

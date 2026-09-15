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
@click.option("--config", "config_path", type=click.Path(exists=True), default=None,
              help="配置文件路径（skillguard.yml/toml）；默认自动发现")
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
    config_path: str | None,
) -> None:
    """检查一个 Skill 目录的质量。"""
    from .configfile import build_config

    try:
        if config_path is not None:
            config = build_config(skill_dir=skill_dir, config_path=config_path)
            # 命令行显式参数优先于配置文件
            if rules:
                config = config.with_overrides(rules=rules)
            if no_tests:
                config = config.with_overrides(run_tests=False)
            if skip_safety:
                config = config.with_overrides(skip_safety=True)
            if fmt != "json":
                config = config.with_overrides(report_format=fmt)
        else:
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


@main.command("bench")
@click.argument("repo_url")
@click.option("--depth", type=int, default=2, show_default=True, help="扫描深度")
@click.option("--max-skills", type=int, default=200, show_default=True, help="最多扫描的 Skill 数")
@click.option("--threshold", type=float, default=60.0, show_default=True, help="质量门禁分数")
@click.option("--top", type=int, default=10, show_default=True, help="排行榜显示条数")
@click.option("--json", "json_out", type=click.Path(), default=None, help="JSON 报告输出路径")
def bench(repo_url: str, depth: int, max_skills: int, threshold: float, top: int, json_out: str | None) -> None:
    """对远程 GitHub 仓库执行生态质量基准扫描。"""
    from .benchmark import BenchmarkRunner

    click.echo(f"🔍 正在克隆并扫描: {repo_url} (depth={depth}, max_skills={max_skills})")
    try:
        summary = BenchmarkRunner(
            repo_url=repo_url, depth=depth, max_skills=max_skills, threshold=threshold
        ).run()
    except RuntimeError as exc:
        click.echo(f"❌ {exc}", err=True)
        sys.exit(2)

    _print_bench_summary(summary, top)

    if json_out:
        import json as json_lib

        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(json_out).write_text(
            json_lib.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        click.echo(f"📄 JSON 报告已写入: {json_out}")


def _print_bench_summary(summary, top: int) -> None:
    """打印生态基准扫描摘要。"""
    s = summary
    click.echo(f"\n📊 生态质量报告: {s.repo_url}")
    click.echo(f"  扫描到 {s.skill_count} 个 Skill | 平均分 {s.avg_score:.1f} | 通过率 {s.pass_rate * 100:.0f}%")
    click.echo(f"  累计问题: 🔴 {s.total_errors} error / 🟡 {s.total_warnings} warning")
    if s.score_distribution:
        click.echo("  评分分布: " + "  ".join(f"{k}:{v}" for k, v in s.score_distribution.items()))
    if s.skills:
        click.echo(f"\n  Top {min(top, len(s.skills))} 排行:")
        for idx, r in enumerate(s.skills[:top], 1):
            status = "✅" if r["passed"] else "❌"
            click.echo(f"    {idx:>2}. [{r['score']:>5.1f}] {status} {r['name']:<28} (errors:{r['errors']})")
    else:
        click.echo("\n  未发现任何 Skill（需要 SKILL.md / skill.md）")


@main.command("badge")
@click.argument("skill_dir", type=click.Path(exists=True), default=".")
@click.option("--output", "-o", type=click.Path(), default="skillguard-badge.svg", show_default=True,
              help="徽章输出路径")
@click.option("--markdown", is_flag=True, help="同时输出 README 嵌入片段")
@click.option("--repo-url", default="", help="徽章链接指向的仓库 URL")
def badge(skill_dir: str, output: str, markdown: bool, repo_url: str) -> None:
    """生成 Skill 的评分徽章（SVG，可嵌入 README）。"""
    from .badge import badge_markdown, write_badge

    try:
        config = Config(skill_dir=skill_dir, run_tests=False)
    except ValueError as exc:
        click.echo(f"❌ 配置错误: {exc}", err=True)
        sys.exit(2)

    guard = SkillGuard(config)
    try:
        report = guard.validate()
    except ValueError as exc:
        click.echo(f"❌ {exc}", err=True)
        sys.exit(2)

    path = write_badge(report, output)
    click.echo(f"🛡️  徽章已生成: {path} (评分 {report.overall_score:.0f}/100)")
    if markdown:
        click.echo("\nREADME 嵌入片段：")
        click.echo(badge_markdown(output, repo_url))


@main.command("schema")
@click.argument("report_json", type=click.Path(exists=True), required=False)
def schema_cmd(report_json: str | None) -> None:
    """输出 QualityReport 的 JSON Schema，或校验报告文件。"""
    import json as json_lib

    from .schema import QUALITY_REPORT_SCHEMA

    if report_json is None:
        click.echo(json_lib.dumps(QUALITY_REPORT_SCHEMA, ensure_ascii=False, indent=2))
        return

    # 校验模式：读取报告文件并检查是否符合 schema
    try:
        data = json_lib.loads(Path(report_json).read_text(encoding="utf-8"))
    except (OSError, json_lib.JSONDecodeError) as exc:
        click.echo(f"❌ 无法读取 JSON: {exc}", err=True)
        sys.exit(2)

    try:
        import jsonschema

        jsonschema.validate(data, QUALITY_REPORT_SCHEMA)
        click.echo(f"✅ {report_json} 符合 SkillGuard JSON Schema")
    except ImportError:
        # 无 jsonschema 库时做基础校验
        required = {"skill", "tool", "tool_version", "timestamp", "summary", "checks", "tests"}
        missing = required - set(data.keys())
        if missing:
            click.echo(f"❌ 缺少字段: {', '.join(sorted(missing))}", err=True)
            sys.exit(1)
        click.echo(f"✅ {report_json} 通过基础字段校验（安装 jsonschema 可做完整校验）")
    except Exception as exc:  # noqa: BLE001 - jsonschema 抛出 ValidationError
        click.echo(f"❌ 校验失败: {exc}", err=True)
        sys.exit(1)


@main.command("config")
@click.option("--init", "init_flag", is_flag=True, help="在当前目录生成 skillguard.yml 模板")
@click.option("--show", "show_flag", is_flag=True, help="显示当前生效配置")
@click.option("--skill-dir", default=".", help="Skill 目录（配合 --show）")
def config_cmd(init_flag: bool, show_flag: bool, skill_dir: str) -> None:
    """管理 SkillGuard 配置文件（生成模板 / 显示当前配置）。"""
    from .configfile import build_config, config_to_dict

    if init_flag:
        import yaml

        target = Path.cwd() / "skillguard.yml"
        if target.exists():
            click.echo(f"⚠️  {target} 已存在，跳过", err=True)
            return
        template = {
            "# SkillGuard 配置文件": None,
            "# 质量门禁分数（0-100）": None,
            "threshold": 60.0,
            "# 测试超时秒数": None,
            "test_timeout": 60,
            "# 是否跳过安全扫描": None,
            "skip_safety": False,
            "# 是否运行测试": None,
            "run_tests": True,
            "# 报告格式: json / markdown / html": None,
            "report_format": "json",
            "# 启用规则列表（默认全部）": None,
            "rules": [],
        }
        target.write_text(
            yaml.safe_dump({k: v for k, v in template.items() if v is not None}, allow_unicode=True, sort_keys=False)
            + "# rules:\n#   - SEC-001\n#   - CUS-001\n",
            encoding="utf-8",
        )
        click.echo(f"✅ 已生成配置模板: {target}")
        return

    if show_flag:
        try:
            config = build_config(skill_dir=skill_dir)
        except ValueError as exc:
            click.echo(f"❌ {exc}", err=True)
            sys.exit(2)
        click.echo(f"当前配置（skill_dir={skill_dir}）:")
        for key, value in config_to_dict(config).items():
            click.echo(f"  {key}: {value}")
        return

    click.echo("用法: skillguard config --init | --show [--skill-dir DIR]", err=True)
    sys.exit(2)


@main.command("report")
@click.argument("root_dir", type=click.Path(exists=True), default=".")
@click.option("--depth", type=int, default=3, show_default=True, help="扫描深度")
@click.option("--format", "fmt", type=click.Choice(["json", "markdown", "html"]), default="markdown",
              show_default=True, help="报告格式")
@click.option("--output", "-o", type=click.Path(), default=None, help="报告输出路径")
@click.option("--no-tests", is_flag=True, help="跳过测试执行（加速）")
def report_cmd(root_dir: str, depth: int, fmt: str, output: str | None, no_tests: bool) -> None:
    """生成多 Skill 聚合质量报告（团队/仓库级总览）。"""
    from .reporting import render_aggregate

    try:
        config = Config(skill_dir=root_dir, run_tests=not no_tests, report_format=fmt)
    except ValueError as exc:
        click.echo(f"❌ 配置错误: {exc}", err=True)
        sys.exit(2)

    guard = SkillGuard(config)
    try:
        items = guard.full_scan_directory(root_dir, max_depth=depth)
    except ValueError as exc:
        click.echo(f"❌ {exc}", err=True)
        sys.exit(2)

    if not items:
        click.echo("未在目录树中发现任何 Skill")
        return

    content = render_aggregate(items, fmt)
    click.echo(f"📊 聚合报告: {len(items)} 个 Skill | 平均分 "
               f"{sum(i['score'] for i in items) / len(items):.1f}")
    if output:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        click.echo(f"📄 报告已写入: {out}")
    else:
        click.echo(content[:3000])


@main.command("mcp")
def mcp_cmd() -> None:
    """启动 MCP 服务器（stdio），供 AI 代理调用 SkillGuard 工具。"""
    try:
        from .mcp_server import run_stdio

        run_stdio()
    except ImportError:
        click.echo('❌ MCP 支持需要额外依赖: pip install "skillguard[mcp]"', err=True)
        sys.exit(2)


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


@main.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish", "powershell"]))
def completion(shell: str) -> None:
    """输出指定 shell 的自动补全脚本。"""
    import click.shell_completion

    if shell == "powershell":
        click.echo(
            "Register-ArgumentCompleter -Native -CommandName skillguard -ScriptBlock {\n"
            "    param($wordToComplete, $commandAst, $cursorPosition)\n"
            "    $commands = @('check','init','scan','bench','completion','doctor','--help','--version')\n"
            "    $commands | Where-Object { $_ -like \"$wordToComplete*\" } | ForEach-Object {\n"
            "        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)\n"
            "    }\n"
            "}\n"
        )
        return

    comp_cls = {"bash": click.shell_completion.BashComplete, "zsh": click.shell_completion.ZshComplete, "fish": click.shell_completion.FishComplete}[shell]
    comp = comp_cls(main, {}, "skillguard", "_SKILLGUARD_COMPLETE")
    click.echo(comp.source())


@main.command("doctor")
def doctor() -> None:
    """检查 SkillGuard 运行环境是否健康。"""
    import platform
    import shutil

    click.echo(f"🏥 SkillGuard Doctor — v{__version__}")
    click.echo(f"  系统: {platform.system()} {platform.release()}")
    click.echo(f"  Python: {platform.python_version()}")
    click.echo(f"  Shell: {shutil.which('bash') or 'bash 未找到（测试脚本需 bash）'}")
    click.echo(f"  Git: {shutil.which('git') or 'git 未找到（bench 命令需要）'}")

    ok = True
    if not shutil.which("bash"):
        click.echo("  ⚠️  bash 缺失：沙箱测试中的 .sh 脚本将无法执行", err=True)
        ok = False
    if not shutil.which("git"):
        click.echo("  ⚠️  git 缺失：bench 生态扫描将无法使用", err=True)
        ok = False
    if ok:
        click.echo("  ✅ 环境健康")
    else:
        click.echo("  ⚠️ 存在缺失组件（不影响 check/init 基础功能）")


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

"""MCP 服务器：让 AI 代理（Claude/Cursor/Codex 等）直接调用 SkillGuard。

暴露的工具：
- check_skill: 检查一个 Skill 目录的质量
- scan_skills: 批量扫描目录树中的 Skills
- bench_repo: 对远程仓库执行生态基准扫描

启动方式（stdio 传输）：
    pip install "skillguard[mcp]"
    skillguard mcp

然后在 MCP 客户端配置：
    claude mcp add skillguard -- skillguard mcp
"""

from __future__ import annotations

from .config import Config
from .engine import SkillGuard

# ----------------------------------------------------------------------
# 工具实现（与 mcp SDK 解耦，便于测试）
# ----------------------------------------------------------------------


def check_skill_impl(skill_dir: str, threshold: float = 60.0, run_tests: bool = True) -> dict:
    """检查一个 Skill 目录的质量，返回 JSON 可序列化结果。"""
    guard = SkillGuard(
        Config(skill_dir=skill_dir, threshold=threshold, run_tests=run_tests)
    )
    report = guard.run()
    return report.to_dict()


def scan_skills_impl(root_dir: str, depth: int = 3, top: int = 20) -> dict:
    """批量扫描目录树中的 Skills，返回排行摘要。"""
    guard = SkillGuard(Config(skill_dir=root_dir, run_tests=False))
    results = guard.scan_directory(root_dir, max_depth=depth)
    return {
        "skill_count": len(results),
        "avg_score": round(sum(r["score"] for r in results) / len(results), 2) if results else 0.0,
        "pass_rate": round(sum(1 for r in results if r["passed"]) / len(results), 2) if results else 0.0,
        "top": results[:top],
    }


def bench_repo_impl(repo_url: str, depth: int = 2, max_skills: int = 200) -> dict:
    """对远程仓库执行生态基准扫描。"""
    from .benchmark import BenchmarkRunner

    summary = BenchmarkRunner(repo_url=repo_url, depth=depth, max_skills=max_skills).run()
    return summary.to_dict()


# ----------------------------------------------------------------------
# mcp 服务器装配
# ----------------------------------------------------------------------


def create_server():
    """创建 MCP 服务器实例（兼容 mcp 1.x / 2.x）。"""
    try:
        # mcp 2.x: MCPServer
        from mcp.server.mcpserver import MCPServer as ServerCls

        server = ServerCls(name="skillguard", version="0.5.0")
        server.add_tool(check_skill_impl, name="check_skill",
                        description="检查一个 Agent Skill 目录的质量（静态校验+测试+评分）")
        server.add_tool(scan_skills_impl, name="scan_skills",
                        description="批量扫描目录树中的 Agent Skills 并输出质量排行")
        server.add_tool(bench_repo_impl, name="bench_repo",
                        description="对远程仓库执行生态质量基准扫描")
        return server
    except ImportError:
        # mcp 1.x: FastMCP
        from mcp.server.fastmcp import FastMCP

        server = FastMCP("skillguard", version="0.5.0")
        server.add_tool(check_skill_impl, name="check_skill",
                        description="检查一个 Agent Skill 目录的质量（静态校验+测试+评分）")
        server.add_tool(scan_skills_impl, name="scan_skills",
                        description="批量扫描目录树中的 Agent Skills 并输出质量排行")
        server.add_tool(bench_repo_impl, name="bench_repo",
                        description="对远程仓库执行生态质量基准扫描")
        return server


def run_stdio() -> None:
    """以 stdio 传输方式启动 MCP 服务器（供 CLI 调用）。"""
    server = create_server()
    server.run()  # 默认 transport='stdio'
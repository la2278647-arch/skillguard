# MCP 集成

SkillGuard 提供 **MCP（Model Context Protocol）服务器**，让任意 AI 编码代理（Claude、Cursor、Codex、OpenCode 等）直接调用 SkillGuard 的质量检测能力。

## 安装

```bash
pip install "skillguard[mcp]"
```

## 启动

```bash
skillguard mcp
```

以 **stdio 传输**方式启动服务器，监听标准输入输出，自动完成 MCP 握手。

## 客户端配置

### Claude Code / Claude Desktop

```bash
claude mcp add skillguard -- skillguard mcp
```

### Claude Desktop 配置文件（claude_desktop_config.json）

```json
{
  "mcpServers": {
    "skillguard": {
      "command": "skillguard",
      "args": ["mcp"]
    }
  }
}
```

### Cursor

Settings → MCP → Add new MCP server：

```
Command: skillguard mcp
```

### VS Code (Copilot)

`.vscode/mcp.json`：

```json
{
  "servers": {
    "skillguard": {
      "type": "stdio",
      "command": "skillguard",
      "args": ["mcp"]
    }
  }
}
```

## 暴露的工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `check_skill` | `skill_dir`（必填）、`threshold`、`run_tests` | 检查一个 Skill 目录的质量，返回完整报告（校验/测试/评分/门禁） |
| `scan_skills` | `root_dir`（必填）、`depth`、`top` | 批量扫描目录树中的 Skills，返回质量排行与聚合统计 |
| `bench_repo` | `repo_url`（必填）、`depth`、`max_skills` | 对远程仓库执行生态质量基准扫描 |

每个工具的输入参数均带完整 JSON Schema 描述，AI 代理可自动生成合法调用。

## 使用示例

向 AI 代理提问：

> "用 check_skill 检查一下 ./skills/code-review 目录的质量，阈值设为 80"

AI 代理会调用：

```
check_skill(skill_dir="./skills/code-review", threshold=80)
```

并基于返回的 JSON 报告（评分、检查明细、测试结果）给出解读与改进建议。

## 架构

```
AI Agent (MCP Client)
    │  stdio + JSON-RPC
    ▼
skillguard mcp (MCP Server)
    │
    ├── check_skill  → SkillGuard.run()
    ├── scan_skills  → SkillGuard.scan_directory()
    └── bench_repo   → BenchmarkRunner.run()
```

MCP 服务器复用 SkillGuard 核心引擎，无重复逻辑；工具实现与协议解耦，便于独立测试。

## 开发与测试

```bash
# 运行 MCP 相关测试
pytest tests/test_mcp.py

# 手动测试握手
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1.0"}}}' | skillguard mcp
```
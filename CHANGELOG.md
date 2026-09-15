# Changelog

本项目的所有重要变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- 更多安全规则（云凭据扩展、路径遍历深化）
- 规则插件系统（自定义检查器注册，已支持基础版本）
- Skill 生态质量基准（bench 命令已支持，规划定期报告）

## [0.7.0] - 2026-09-15

### 新增
- `report` 命令：多 Skill 聚合质量报告（团队/仓库级总览）
  - 平均分 / 通过率 / 评分分布 / 累计问题
  - 完整评估（含沙箱测试）或快速模式（--no-tests）
  - JSON / Markdown / HTML 三格式
- `full_scan_directory()`：完整评估版目录扫描 API
- 聚合报告渲染函数（aggregate_summary / render_aggregate）

## [0.6.0] - 2026-09-15

### 新增
- MCP 服务器：AI 代理（Claude/Cursor/Codex）可直接调用 SkillGuard
  - `check_skill`：检查 Skill 目录质量
  - `scan_skills`：批量扫描目录树
  - `bench_repo`：生态基准扫描
- `mcp` 命令（stdio 传输），兼容 mcp 1.x (FastMCP) 与 2.x (MCPServer)
- `[mcp]` 可选依赖：`pip install "skillguard[mcp]"`
- 各平台 MCP 客户端配置文档（Claude/Cursor/VS Code）

## [0.5.0] - 2026-09-15

### 新增
- pre-commit 质量门禁（原生 git hook + pre-commit 框架双路径）
- CHANGELOG.md（Keep-a-Changelog 格式）
- SECURITY.md（安全披露政策）
- GitHub Release 直接安装分发（PyPI 替代通道）
- 多平台 CI 配置（CircleCI/Azure Pipelines）
- 一键发布包（docs/publish-kit.md）
- 英文 README（README.en.md）

### 修复
- 版本一致性：pyproject/version.py 统一

## [0.4.0] - 2026-09-15

### 新增
- 配置文件支持：YAML/TOML 配置（`skillguard.yml`/`.toml`），自动发现（当前目录+父目录链）
- `config` 命令：`--init` 生成模板 / `--show` 显示当前配置
- `check --config <path>`：显式配置文件，优先级高于命令行默认值

### 修复
- 配置文件 rules 字段规范化（列表/CSV/null 三种形式）

## [0.3.0] - 2026-09-14

### 新增
- `badge` 命令：SVG 评分徽章（可嵌入 README，按分数着色 + 通过状态）
- `schema` 命令：QualityReport JSON Schema 输出与校验
- 项目 Logo（docs/logo.svg，盾牌+对勾品牌标识）

## [0.2.0] - 2026-09-14

### 新增
- 可视化 HTML 报告：SVG 五维雷达图 + 评分进度条
- `bench` 命令：生态质量基准扫描（克隆远程仓库 + 批量评分）
- 插件系统：自定义规则注册表（`CUS-` 前缀，归入可维护性维度）
- `scan` 命令：目录树 Skills 质量排行
- 6 条新安全规则：SEC-010 AWS Key / SEC-011 云凭据 / SEC-012 路径遍历 / SEC-013 下载执行 / SEC-014 密钥导出 / SEC-015 base64 混淆

### 修复
- 批量扫描跳过隐藏目录导致 `.agents`/`.claude` 等 Skills 存放位置漏扫

## [0.1.0] - 2026-09-14

### 新增
- 首版发布：静态校验（结构/引用/安全扫描，17 条 SEC 规则）
- 沙箱测试执行（Skill 目录副本隔离运行、强制超时、环境净化）
- 五维质量评分模型（结构/文档/安全/可维护/实用）
- JSON / Markdown / HTML 三格式报告
- CLI：`check` / `init` 命令
- Python API：`SkillGuard` / `Config` / `QualityReport`

[Unreleased]: https://github.com/la2278647-arch/skillguard/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/la2278647-arch/skillguard/releases/tag/v0.4.0
[0.3.0]: https://github.com/la2278647-arch/skillguard/releases/tag/v0.3.0
[0.2.0]: https://github.com/la2278647-arch/skillguard/releases/tag/v0.2.0
[0.1.0]: https://github.com/la2278647-arch/skillguard/releases/tag/v0.1.0
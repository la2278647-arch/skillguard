# V2EX 帖子（中文）

> 节点：分享创造 · 标题：SkillGuard —— 给 AI Agent 的 Skills 做质检的开源工具

---

装了一堆 Claude Code / Codex 的 Skills，坏的比好的多？

这个开源工具能对 Skill 目录做这些事：

1. **静态校验**：SKILL.md 结构、引用完整性、33 条安全规则扫描（rm -rf、硬编码 API Key、GitHub Token、私钥泄露、curl|sh、eval 等）
2. **沙箱测试**：把整个 Skill 目录复制到隔离临时目录跑 tests/ 脚本，脚本删库也碰不到你的源码，强制超时
3. **质量评分**：结构/文档/安全/可维护/实用五维打分（0-100）+ CI 门禁
4. **聚合报告**：一个命令给出全仓库 Skills 的质量总览
5. **MCP 服务器**：Claude / Cursor 配置后，AI 代理可以直接在对话里调用质检（`check_skill` / `scan_skills` / `bench_repo`）

自卖自夸一下工程质量：274 个测试、95%+ 覆盖率、ruff clean、Python 3.10-3.13、MIT。
另外我们用这个工具扫了 GitHub 上 6 个最热门的 Skills 仓库（共 113 个 Skill），发现一个有意思的结果：**Anthropic 官方仓库只有 75% 通过率，而社区头部仓库（mattpocock 等）100% 通过** —— 官方≠最优。完整报告见文档站。

```bash
pip install skillguard
skillguard init my-skill --framework claude-code
skillguard check my-skill --ci --threshold 70
skillguard bench https://github.com/anthropics/skills.git   # 生态扫描
```

GitHub：https://github.com/la2278647-arch/skillguard
文档：https://la2278647-arch.github.io/skillguard/
教程（从零建 Skill）：https://la2278647-arch.github.io/skillguard/tutorial/
生态报告：https://la2278647-arch.github.io/skillguard/ecosystem-report/

---

# 知乎回答（中文）

> 问题：《如何评估和选择高质量的 AI Agent Skills？》

## 先说结论

目前这个领域**几乎没有标准化工具**。微软有个 waza（1310 star）还在早期，中文社区空白。我最近开源了 SkillGuard 来填补这个空缺，下面结合它讲讲我理解的评估维度。

## 一、为什么需要评估 Skills？

AI 编码代理（Claude Code、Codex、Cursor）正在大规模使用 Skills，生态增长惊人（superpowers 28.6 万 star、Anthropic 官方仓库 17.6 万 star）。但 Skills 本质上是「提示词 + 脚本」的混合体，质量参差：

- 有的 Skill 的脚本里藏着 `rm -rf`（我实际见过）
- 有的引用了不存在的文件，跑一次报一次错
- 有的元数据缺失，AI 根本不知道该什么时候用它

## 二、我建议从 5 个维度评估

### 1. 结构完整性（权重 25%）
- SKILL.md 是否存在、name/description/version 元数据是否完整
- scripts/ 目录是否规范

### 2. 文档清晰度（权重 20%）
- 描述是否能让 AI 准确理解用途
- 是否包含使用方式和注意事项

### 3. 安全性（权重 30%）
这是最重要的维度：
- 破坏性命令：rm -rf、mkfs、dd 到 /dev/
- 远程执行：curl | sh、eval
- 密钥泄露：硬编码 API Key / Token
- 权限滥用：chmod 777、sudo、git push --force

### 4. 可维护性（权重 15%）
- 引用的文件是否都存在（防断链）
- 体积是否可控（超过 40KB 的 SKILL.md 建议拆分）

### 5. 实用性（权重 10%）
- 有没有测试脚本（tests/ 目录）
- tags、版本号是否规范

## 三、自动化评估工具

手评估太累，我写了个开源 CLI 把这些维度自动化了：

```bash
pip install skillguard
skillguard check path/to/skill --format html -o report.html
```

它会输出每个维度的分数、全部检查明细，还能跑沙箱测试 + CI 门禁。

## 四、选择 Skills 的实操建议

1. **优先看有没有测试**：一个带 tests/ 的 Skill 通常比没有的靠谱一个量级
2. **扫一遍安全**：哪怕手动 grep 一下 `rm -rf`、`api_key` 都行
3. **看元数据完整度**：name/description/version 都齐的，作者大概率认真
4. **社区背书**：star 数和 issue 响应速度是重要信号

## 五、关于 SkillGuard

- GitHub：https://github.com/la2278647-arch/skillguard
- 文档：https://la2278647-arch.github.io/skillguard/
- 项目自身：126 tests、98%+ coverage、ruff clean、MIT

欢迎批评指正，也欢迎贡献规则和插件。


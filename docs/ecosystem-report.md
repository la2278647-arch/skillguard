# Agent Skills 生态质量基准报告（2026-09）

> 由 SkillGuard 生态基准扫描生成 · 工具: https://github.com/la2278647-arch/skillguard
> 方法：浅克隆目标仓库 → 批量扫描全部 Skill → 五维质量评分（结构/文档/安全/可维护/实用）

---

## 一、核心发现

| 发现 | 数据 |
|------|------|
| 🔴 **官方仓库也有不合格 Skill** | Anthropic 官方 skills 仓库 20 个 Skill 中 5 个未通过质量门禁（通过率 75%） |
| 🛡️ **头部社区仓库质量更好** | mattpocock/skills（261k★）37 个 Skill 全部通过（100%） |
| ⚠️ **安全违规真实存在** | superpowers（286k★）扫描出 3 个 ERROR 级问题 |
| 📊 **高质量生态平均分约 94-98** | 三个头部仓库平均分均 > 93 |

## 二、对比数据

| 仓库 | Star | Skill 数 | 平均分 | 通过率 | Error | Warning |
|------|------|----------|--------|--------|-------|---------|
| [anthropics/skills](https://github.com/anthropics/skills)（官方） | 176k | 20 | 93.9 | **75%** | **7** | 4 |
| [obra/superpowers](https://github.com/obra/superpowers) | 286k | 14 | 95.2 | 86% | **3** | 0 |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 261k | 37 | **98.4** | **100%** | 0 | 0 |

### 评分分布

```
anthropics/skills:   90-100:15  75-89:4  60-74:1  (20 total)
obra/superpowers:    90-100:12  75-89:1  60-74:1  (14 total)
mattpocock/skills:   90-100:37                      (37 total)
```

## 三、发现的问题类型（举例）

扫描中检测到的 ERROR 级问题示例：

1. **SKILL.md 元数据缺失**（SRC-002/003）：部分 Skill 缺少 name/description，AI 无法理解用途
2. **安全模式命中**（SEC-*）：脚本中出现危险命令模式
3. **引用完整性**（REF-*）：SKILL.md 引用了不存在的本地文件

## 四、给 Skill 作者的启示

基于 71 个真实 Skill 的扫描：

1. **description 是最被忽视的元数据**——缺失直接导致 AI 无法正确触发 Skill
2. **scripts/ 与 tests/ 是质量分水岭**——带测试的 Skill 分数显著更高
3. **安全扫描值得做**——连头部仓库都有 error 级问题，发布前自检成本极低

## 五、复现方法

```bash
pip install skillguard
skillguard bench https://github.com/anthropics/skills.git
skillguard bench https://github.com/obra/superpowers.git
skillguard bench https://github.com/mattpocock/skills.git
```

## 六、关于 SkillGuard

SkillGuard 是 Agent Skills 质量保障与测试框架：
- 🧹 静态校验（23 条安全规则）
- 🏜️ 沙箱测试执行
- 🔢 五维质量评分 + CI 门禁
- 📊 生态基准扫描（本报告生成器）

GitHub: https://github.com/la2278647-arch/skillguard

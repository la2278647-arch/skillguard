# 快速开始

## 安装

```bash
pip install skillguard
```

需要 Python 3.10+。

## 一分钟上手

### 1. 初始化一个 Skill 项目

```bash
skillguard init my-skill --name my-skill --framework claude-code
```

这会创建：

```
my-skill/
├── SKILL.md          # 带元数据模板
└── tests/
    └── smoke.sh      # 冒烟测试
```

### 2. 检查质量

```bash
skillguard check my-skill
```

输出综合评分、检查明细与测试结果。

### 3. 配置 CI 门禁

```bash
skillguard check my-skill --ci --threshold 70
```

不通过时退出码为 1，可直接用于 GitHub Actions。

## 下一步

- [CLI 参考](cli.md) — 全部命令与选项
- [API 参考](api.md) — Python 库用法
- [CI 集成](ci.md) — 接入 CI 的最佳实践
- [质量规则](rules.md) — 检查规则详解

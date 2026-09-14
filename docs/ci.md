# SkillGuard CI 集成指南

> 在 CI 中将 SkillGuard 作为质量门禁，阻止不合格的 Skill 合并。

## GitHub Actions

创建 `.github/workflows/skillguard.yml`：

```yaml
name: SkillGuard Quality Gate

on:
  pull_request:
    paths:
      - 'skills/**'
      - '!skills/**/*.md'   # 可选：排除纯文档变更
  push:
    branches: [main]

jobs:
  skillguard-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install SkillGuard
        run: pip install skillguard

      - name: Check all skills
        run: |
          set -e
          for skill in skills/*/; do
            echo "=== Checking $skill ==="
            skillguard check "$skill" --ci --format markdown -o "$skill/report.md"
          done
```

## 针对单个 Skill 的矩阵检查

```yaml
jobs:
  skillguard:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        skill: [code-review, doc-gen, refactor]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install skillguard
      - name: Quality gate
        run: skillguard check "skills/${{ matrix.skill }}" --ci --threshold 70
```

## CI 集成要点

1. **退出码语义**：`--ci` 模式下未通过门禁返回退出码 1，CI 自动失败。
2. **报告附件**：用 `-o report.json` 导出报告，通过 `actions/upload-artifact` 供下载。
3. **阈值选择**：先本地运行查看基线分数，再设阈值（建议 60-80）。
4. **变更检测**：`paths:` 限定只有 Skill 变更时触发，节省 CI 时间。
5. **失败即反馈**：PR 中直接展示 markdown 报告：

```yaml
- name: Upload report to PR comment
  if: failure()
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const report = fs.readFileSync('report.md', 'utf8');
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: report
      });
```

## 本地 pre-commit 钩子（可选）

`.pre-commit-config.yaml`：

```yaml
repos:
  - repo: local
    hooks:
      - id: skillguard
        name: SkillGuard quality gate
        entry: skillguard check
        language: system
        types: [file]
        files: ^skills/.+/SKILL\.md$
        pass_filenames: false
```

## 常见问题

### 报告在 Windows CI 上乱码？

SkillGuard 已内置 UTF-8 强制输出，无需额外配置。

### 测试脚本需要网络/环境变量？

沙箱默认丢弃敏感环境变量（`AWS_`/`OPENAI_`/`TOKEN` 等）。若测试确实需要，可在 CI 步骤中显式传入，但**强烈不建议**在 Skill 测试中依赖外部凭据。

### 如何只检查部分规则？

```bash
skillguard check skills/my-skill -r SEC-001 -r SEC-005 --ci
```

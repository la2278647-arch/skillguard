# Tutorial: Build a High-Quality Agent Skill from Scratch (Full Workflow)

> Audience: developers new to Claude Code / Codex / Cursor Skills, and advanced users
> who want to raise their skills' quality. This tutorial walks the full loop —
> create → check → test → score → publish → badge → CI gating — using SkillGuard.

---

## Prerequisites

```bash
# Install SkillGuard (direct from GitHub Release, or PyPI once published)
pip install https://github.com/la2278647-arch/skillguard/releases/download/v0.8.0/skillguard-0.8.0-py3-none-any.whl

# Verify
skillguard --version
```

---

## Step 1: Initialize the Skill skeleton

```bash
skillguard init my-code-review --name my-code-review --framework claude-code
cd my-code-review
```

The generated skeleton:

```
my-code-review/
├── SKILL.md          # metadata + documentation
└── tests/
    └── smoke.sh      # smoke test (verifies SKILL.md exists and is non-empty)
```

---

## Step 2: Write SKILL.md

Edit `SKILL.md` and fill in real content. The spec requires **YAML front-matter metadata + structured body**:

```markdown
---
name: my-code-review
description: Review code changes against engineering best practices; identify bugs, security risks and maintainability issues
version: 1.0.0
framework: claude-code
tags:
  - code-review
  - quality
---

# My Code Review

## Purpose

Review code changes in a git diff or PR and produce a structured review:
- Bugs and logic errors
- Security risks
- Maintainability issues

## Usage

Activate when the user asks to "review this PR / review this code". Steps:
1. Read the diff and related context
2. Inspect each file (error handling, edge cases, security, performance)
3. Report findings by severity (blocker / major / minor / nit)

## Notes

- Review only the diff; do not rewrite code
- Every finding must cite concrete evidence (line number / code reference)
- No praise-only comments
```

---

## Step 3: Add helper scripts (optional but recommended)

```bash
mkdir scripts
```

`scripts/summary.sh` — summarize review statistics:

```bash
#!/usr/bin/env bash
# Summarize review findings
set -euo pipefail
echo "=== Review stats ==="
grep -c "\[blocker\]" "$1" 2>/dev/null || echo "blocker: 0"
grep -c "\[major\]" "$1" 2>/dev/null || echo "major: 0"
```

---

## Step 4: Add tests

Tests live in `tests/` or `test/`; supported: `.sh` / `.py` / `.js` / `.ts`.

`tests/smoke.sh` — verify key files exist:

```bash
#!/usr/bin/env bash
set -euo pipefail
test -f "$(dirname "$0")/../SKILL.md" && echo "SKILL.md exists"
test -f "$(dirname "$0")/../scripts/summary.sh" && echo "summary.sh exists"
```

---

## Step 5: Run the quality check

```bash
skillguard check .
```

Output:

```
🔍 SkillGuard 评估: my-code-review (v1.0.0, claude-code)
  综合评分: 100.0/100  ✅ 通过
  检查: 0 项 (🔴 0 / 🟡 0 / 🔵 0)
  测试: 1 项 (✅ 1 / ❌ 0)
```

If anything fails, follow the reported findings to fix it (missing front-matter,
description, script error handling, etc.).

---

## Step 6: Generate visual reports

```bash
# HTML report (radar chart + score bars)
skillguard check . --format html -o report.html

# Score badge (embed in README)
skillguard badge . -o badge.svg --markdown --repo-url https://github.com/you/my-code-review
```

Add the badge to your README:

```markdown
![SkillGuard](badge.svg)
```

---

## Step 7: Team-specific rules (optional)

Create `skillguard.yml` to set team quality gates:

```yaml
threshold: 80          # gate score
test_timeout: 120      # test timeout
rules:
  - SEC-001            # only enable selected rules (example)
```

Or share team checkers via the plugin system (see `examples/custom_rules.py`):
- TODO/FIXME leftover detection
- Required documentation sections
- Script error-handling checks

---

## Step 8: Configure CI gating

### GitHub Actions (after granting workflow scope)

Copy `templates/github-workflows/ci.yml` to `.github/workflows/`.

### Other CI (CircleCI / Azure, no special permissions needed)

- `.circleci/config.yml`: CircleCI config, add the project and it works
- `azure-pipelines.yml`: Azure Pipelines config

### Local / pre-commit (zero dependencies)

```bash
# pre-commit hook: auto-check before commit
ln -s ../../scripts/pre-commit .git/hooks/pre-commit
SKILLGUARD_THRESHOLD=80 git commit -m "update skill"
```

---

## Step 9: Publish and spread

1. **Push to GitHub**, update README (badge + usage)
2. **Generate ecosystem reports** (or score others' skills):

```bash
skillguard bench https://github.com/anthropics/skills.git
```

3. Let AI agents check quality directly (MCP):

```bash
pip install "skillguard[mcp]"
claude mcp add skillguard -- skillguard mcp
# In chat: use check_skill to review my skill directory
```

---

## Pre-publish checklist

Run these before releasing your skill:

| Check | Command | Pass criteria |
|-------|---------|---------------|
| Overall quality | `skillguard check . --ci` | exit code 0 |
| Security | `skillguard check . -r SEC-001 -r SEC-005` | no ERROR |
| Tests | `skillguard check . --format json` | tests.passed == tests.total |
| Badge | `skillguard badge .` | SVG generated |
| Aggregate | `skillguard report .` | stats output |

---

## Next steps

- Full [API Reference](api.md) / [CLI Reference](cli.md)
- [Custom rules example](../examples/custom_rules.py)
- [Ecosystem quality report](ecosystem-report.md)
- [MCP integration](mcp.md)
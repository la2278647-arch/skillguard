<div align="center">

<img src="docs/logo.svg" alt="SkillGuard Logo" width="96"/>

# 🛡️ SkillGuard

**Quality assurance & testing framework for Agent Skills** — static validation, sandboxed testing, quality scoring and CI gating for Skills used by Claude Code / Codex / Cursor and other AI coding agents.

[![English](https://img.shields.io/badge/README-English-blue)](README.en.md) [![中文](https://img.shields.io/badge/README-中文-red)](README.md)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-95.2%25-brightgreen)](https://github.com/la2278647-arch/skillguard)
[![Ruff](https://img.shields.io/badge/linter-ruff-purple)](https://github.com/astral-sh/ruff)
[![Security](https://img.shields.io/badge/Security-Policy-important)](SECURITY.md)

</div>

---

## Why SkillGuard?

The Agent Skills ecosystem is exploding (superpowers ⭐286k, anthropics/skills ⭐176k, spec-kit ⭐136k) — but **there is no standard tooling to verify that a skill is safe, correct and maintainable**. SkillGuard fills that gap:

- 🧹 **Static validation** — structure, broken references, and 26 security pattern checks
- 🏜️ **Sandboxed test execution** — runs tests in an isolated copy of the skill dir
- 🔢 **Quality scoring** — 5 weighted dimensions (0-100) with CI gating
- 📄 **Reports** — JSON (CI), Markdown (PR comments), HTML (self-contained)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧹 **Static validation** | Structure, reference integrity, 425 security patterns (SEC-001..015) |
| 🏜️ **Sandbox tests** | Whole skill dir copied to temp dir; scripts can't touch your source; forced timeouts; sanitized env |
| 🔢 **Quality scoring** | 5 dimensions (structure/docs/safety/maintainability/usability), configurable CI threshold |
| 📄 **Multi-format reports** | JSON (CI consumption), Markdown (PR comments), HTML (shareable page) |
| 🤖 **CI integration** | `--ci` mode (exit 1 on failure), GitHub Actions template, pre-commit hook |
| 📊 **Ecosystem benchmarking** | Clone any repo and rank its skills (`skillguard bench`) |
| 🛡️ **Badges** | SVG quality badge for your README (`skillguard badge`) |

## 🚀 Quick Start

### Install

```bash
# Option 1: PyPI (once published)
pip install skillguard

# Option 2: Install directly from GitHub Release (available now, same as PyPI)
pip install https://github.com/la2278647-arch/skillguard/releases/download/v0.5.0/skillguard-0.5.0-py3-none-any.whl
```

### 1. Initialize a new Skill

```bash
skillguard init my-skill --name my-skill --framework claude-code
cd my-skill
skillguard check .
```

### 2. Check an existing Skill

```bash
# Basic check
skillguard check path/to/skill

# HTML report
skillguard check path/to/skill --format html -o report.html

# CI mode (exit 1 on failure)
skillguard check path/to/skill --ci
```

### 3. Benchmark an ecosystem / repo

```bash
skillguard bench https://github.com/anthropics/skills.git
skillguard bench https://github.com/obra/superpowers.git --max-skills 50 --json bench.json
```

### 4. Generate a quality badge

```bash
skillguard badge path/to/skill -o skillguard-badge.svg --markdown
```

### 5. Use as a Python library

```python
from skillguard import SkillGuard, Config

guard = SkillGuard(Config(skill_dir="path/to/skill"))
report = guard.run()          # full evaluation
print(report.overall_score)   # 0-100
print(report.to_json())       # JSON report
guard.export(report, "report.html")

# Bulk scan a directory tree
for item in guard.scan_directory("./skills"):
    print(item["name"], item["score"], item["passed"])
```

## 📚 Documentation

- [Tutorial: Build a High-Quality Skill from Scratch](docs/tutorial.en.md)
- [API Reference](docs/api.md)
- [CLI Reference](docs/cli.md)
- [Architecture](docs/architecture.md)
- [Quality Rules](docs/rules.md)
- [CI Integration](docs/ci.md)
- [Ecosystem Report](docs/ecosystem-report.md)

## 🏗️ Project Structure

```
skillguard/
├── skillguard/          # Core package
│   ├── cli.py           # CLI entry
│   ├── config.py        # Config model
│   ├── engine.py        # Orchestration engine
│   ├── models.py        # Data models
│   ├── parser.py        # SKILL.md parsing
│   ├── reporting.py     # Report generators
│   ├── runner.py        # Sandboxed test runner
│   ├── scoring.py       # Quality scoring
│   ├── validator.py     # Static validation
│   ├── benchmark.py     # Ecosystem benchmarking
│   ├── badge.py         # SVG badge generator
│   ├── schema.py        # JSON Schema
│   ├── configfile.py    # YAML/TOML config support
│   └── rules.py         # Plugin rule registry
├── tests/               # 218 tests (95.2% coverage)
├── scripts/             # CI + pre-commit scripts
└── templates/           # GitHub Actions template
```

## 🛠️ Development

```bash
git clone https://github.com/la2278647-arch/skillguard.git
cd skillguard
pip install -e ".[dev]"
pytest                  # run tests
ruff check skillguard tests  # lint
```

## 📄 License

[MIT](LICENSE)

## ⭐ Support

If SkillGuard helps you, give it a Star ⭐ and share it with other developers!



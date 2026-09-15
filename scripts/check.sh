#!/usr/bin/env bash
# SkillGuard 本地 CI 验证脚本
# 在 GitHub Actions 不可用的环境下，本地执行完整质量检查。
# 用法: bash scripts/check.sh
set -euo pipefail

echo "=== [1/4] 代码质量检查 (ruff) ==="
ruff check skillguard tests

echo "=== [2/4] 类型检查 (mypy) ==="
mypy skillguard --ignore-missing-imports

echo "=== [3/4] 单元测试 + 覆盖率 (pytest) ==="
pytest --cov=skillguard --cov-fail-under=95

echo "=== [4/4] 构建验证 (build) ==="
python -m build --outdir /tmp/skillguard-dist

echo ""
echo "✅ 全部检查通过！"

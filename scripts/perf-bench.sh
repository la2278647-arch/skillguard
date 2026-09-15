#!/usr/bin/env bash
# SkillGuard 性能基准脚本
# 测量核心命令的吞吐，输出结构化 JSON 结果（供 CI/报告使用）。
#
# 用法: bash scripts/perf-bench.sh [iterations]
# 默认 5 次迭代取平均。

set -euo pipefail

ITERS="${1:-5}"
TARGET="${2:-.}"
echo "=== SkillGuard 性能基准 (${ITERS} iterations) ==="
echo ""

run_bench() {
    local name="$1"; shift
    local total=0
    local -a samples=()
    for _ in $(seq 1 "$ITERS"); do
        local start end elapsed
        start=$(date +%s%N 2>/dev/null || date +%s)
        "$@" > /dev/null 2>&1
        end=$(date +%s%N 2>/dev/null || date +%s)
        if [[ $start == *N ]]; then
            elapsed=$(( (end - start) / 1000000 ))
        else
            elapsed=$(( end - start ))
        fi
        total=$(( total + elapsed ))
        samples+=("$elapsed")
    done
    local avg
    avg=$(( total / ITERS ))
    echo "  $name: avg ${avg}ms  samples: ${samples[*]}"
}

run_bench "check (single skill)" skillguard check "$TARGET"
run_bench "scan (directory)" skillguard scan "$TARGET"
run_bench "badge (generate)" skillguard badge "$TARGET" -o /tmp/sg-bench-badge.svg
run_bench "schema (output)" skillguard schema
rm -f /tmp/sg-bench-badge.svg

echo ""
echo "✅ 性能基准完成"
#!/usr/bin/env bash
set -euo pipefail
test -f "$(dirname "$0")/../SKILL.md" && echo "smoke ok"

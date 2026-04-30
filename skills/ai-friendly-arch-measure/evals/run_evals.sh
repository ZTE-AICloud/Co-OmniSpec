#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVILS_DIR="$SKILL_DIR/agent/skills/ai-friendly-arch-measure/evals"

echo "========================================"
echo "Running AI-Friendly Architecture Evals"
echo "========================================"

PASSED=0
FAILED=0

run_eval() {
    local name="$1"
    local script="$2"
    echo ""
    echo ">>> $name"
    if [[ -f "$script" ]]; then
        if python3 "$script"; then
            ((PASSED++))
        else
            ((FAILED++))
            echo "[ERROR] $name FAILED"
        fi
    else
        echo "[SKIP] $script not found"
    fi
}

# 遍历所有 skill 的 evals 目录
for evals_dir in \
    "$SKILL_DIR/agent/skills/ai-friendly-arch-measure/evals" \
    "$SKILL_DIR/agent/skills/ai-friendly-component-srp-orchestrate/evals" \
    "$SKILL_DIR/agent/skills/ai-friendly-module-identifier/evals"; do

    if [[ -d "$evals_dir" ]]; then
        for script in "$evals_dir"/eval-*.py; do
            if [[ -f "$script" ]]; then
                name="$(basename "$script" .py)"
                echo ""
                echo ">>> $name"
                if python3 "$script"; then
                    ((PASSED++))
                else
                    ((FAILED++))
                    echo "[ERROR] $name FAILED"
                fi
            fi
        done
    fi
done

echo ""
echo "========================================"
echo "Summary: $PASSED passed, $FAILED failed"
echo "========================================"
if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
exit 0

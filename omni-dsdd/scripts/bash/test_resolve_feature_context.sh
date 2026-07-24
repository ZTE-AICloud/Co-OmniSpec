#!/usr/bin/env bash
# Acceptance tests for resolve-feature-context.sh and build-specify-feature-args.sh
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH="" cd "${SCRIPT_DIR}/../.." && pwd)"
RESOLVE="${SCRIPT_DIR}/resolve-feature-context.sh"
BUILD="${SCRIPT_DIR}/build-specify-feature-args.sh"

PASS=0
FAIL=0

assert_eq() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        PASS=$((PASS + 1))
        echo "PASS: $name"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $name" >&2
        echo "  expected: $expected" >&2
        echo "  actual:   $actual" >&2
    fi
}

assert_exit() {
    local name="$1"
    local expected_exit="$2"
    shift 2
    set +e
    "$@" >/dev/null 2>&1
    local code=$?
    set -e
    if [[ "$code" -eq "$expected_exit" ]]; then
        PASS=$((PASS + 1))
        echo "PASS: $name"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $name (exit $code, expected $expected_exit)" >&2
    fi
}

json_field() {
    local json="$1"
    local field="$2"
    printf '%s' "$json" | python3 -c "import json,sys; v=json.load(sys.stdin).get(sys.argv[1], ''); print(str(v).lower() if isinstance(v, bool) else v)" "$field"
}

echo "=== resolve-feature-context.sh ==="

out="$(bash "$RESOLVE" --working-dir "$REPO_ROOT" --feature-dir "changes/001-example" --json 2>/dev/null)"
assert_eq "only feature-dir -> derived branch" "001-example" "$(json_field "$out" branch_name)"
assert_eq "only feature-dir -> preset true" "true" "$(json_field "$out" feature_context_preset)"

out="$(bash "$RESOLVE" --working-dir "$REPO_ROOT" --branch-name "001-example" --json 2>/dev/null)"
assert_eq "only branch-name -> changes path" "${REPO_ROOT}/changes/001-example" "$(json_field "$out" feature_dir)"

out="$(bash "$RESOLVE" --working-dir "$REPO_ROOT" --feature-dir "changes/DSDD/001-example" --json 2>/dev/null)"
assert_eq "nested path" "${REPO_ROOT}/changes/DSDD/001-example" "$(json_field "$out" feature_dir)"
assert_eq "nested basename branch" "001-example" "$(json_field "$out" branch_name)"

out="$(bash "$RESOLVE" --working-dir "$REPO_ROOT" --json 2>/dev/null)"
assert_eq "no input -> preset false" "false" "$(json_field "$out" feature_context_preset)"

assert_exit "outside changes/ -> exit 1" 1 \
    bash "$RESOLVE" --working-dir "$REPO_ROOT" --feature-dir "/tmp/outside" --json

(
    export FEATURE_DIR="changes/002-old" BRANCH_NAME="002-old"
    out="$(bash "$RESOLVE" --working-dir "$REPO_ROOT" --feature-dir "001-example" --branch-name "001-example" --json 2>/dev/null)"
    assert_eq "CLI overrides export" "cli" "$(json_field "$out" feature_dir_source)"
)

(
    export FEATURE_DIR="changes/aaa" OMNISPEC_FEATURE_DIR="changes/bbb" BRANCH_NAME="bbb"
    out="$(bash "$RESOLVE" --working-dir "$REPO_ROOT" --json 2>/dev/null)"
    assert_eq "OMNISPEC_FEATURE_DIR priority" "${REPO_ROOT}/changes/bbb" "$(json_field "$out" feature_dir)"
)

(
    export BRANCH_NAME="custom-branch"
    out="$(bash "$RESOLVE" --working-dir "$REPO_ROOT" --feature-dir "changes/DSDD/001-example" --json 2>/dev/null)"
    assert_eq "mixed CLI dir + env branch" "custom-branch" "$(json_field "$out" branch_name)"
)

echo "=== build-specify-feature-args.sh ==="

args="$(bash "$BUILD" --working-dir "$REPO_ROOT" --feature-dir "changes/001-example")"
[[ "$args" == *"--feature-dir"* ]] && [[ "$args" == *"--branch-name"* ]] && {
    PASS=$((PASS + 1))
    echo "PASS: build args for preset"
} || {
    FAIL=$((FAIL + 1))
    echo "FAIL: build args for preset" >&2
    echo "  actual: $args" >&2
}

args="$(bash "$BUILD" --working-dir "$REPO_ROOT")"
assert_eq "build args empty when no preset" "" "$args"

echo "=== summary: ${PASS} passed, ${FAIL} failed ==="
[[ "$FAIL" -eq 0 ]]

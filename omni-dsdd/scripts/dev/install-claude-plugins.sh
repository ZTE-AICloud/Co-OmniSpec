#!/usr/bin/env bash

set -euo pipefail

# Must stay in sync with .claude-plugin/marketplace.json
MARKETPLACE_NAME="CoMind-plugins"
PLUGIN_NAMES=(
    "omni-dsdd"
    "omni-reverse"
)

usage() {
    cat <<EOF
Usage: install-claude-plugins.sh [OPTIONS]

Install or uninstall OmniSpec Claude Code plugins from this repository.

Marketplace: ${MARKETPLACE_NAME}
Plugins:     ${PLUGIN_NAMES[*]}

Options:
  --uninstall, -u    Uninstall only (remove plugins and marketplace, skip reinstall)
  --help, -h         Show this help message

Default (no options): uninstall existing plugins/marketplace, then reinstall from REPO_ROOT.
EOF
}

uninstall_only=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uninstall|-u)
            uninstall_only=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

remove_plugins() {
    local plugin
    for plugin in "${PLUGIN_NAMES[@]}"; do
        claude plugins remove "$plugin" 2>/dev/null || true
    done
}

install_plugins() {
    local plugin
    for plugin in "${PLUGIN_NAMES[@]}"; do
        claude plugins install "${plugin}@${MARKETPLACE_NAME}"
    done
}

script_dir="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Follow reverse-on-demand pattern: prefer CLAUDE_WORKING_DIR environment variable,
# do NOT use git rev-parse --show-toplevel (may lift above subdir workspace).
if [[ -n "${CLAUDE_WORKING_DIR:-}" && -d "${CLAUDE_WORKING_DIR}" ]]; then
    search_root="$(CDPATH="" cd "${CLAUDE_WORKING_DIR}" && pwd)"
else
    search_root="$(CDPATH="" cd "$script_dir/../.." && pwd)"
fi

# marketplace.json lives at the monorepo root (e.g. omnispec-dot), not inside omni-dsdd.
REPO_ROOT=""
dir="$search_root"
while [[ -n "$dir" && "$dir" != "/" ]]; do
    if [[ -f "$dir/.claude-plugin/marketplace.json" ]]; then
        REPO_ROOT="$dir"
        break
    fi
    dir="$(dirname "$dir")"
done

if [[ "$uninstall_only" == false && -z "$REPO_ROOT" ]]; then
    echo "Error: marketplace file not found (searched from $search_root)" >&2
    exit 1
fi

echo "REPO_ROOT: $REPO_ROOT"
echo "MARKETPLACE: $MARKETPLACE_NAME"
echo "PLUGINS: ${PLUGIN_NAMES[*]}"

# Best-effort cleanup: missing plugin/marketplace is not an error.
remove_plugins
claude plugins marketplace remove "$MARKETPLACE_NAME" 2>/dev/null || true

if [[ "$uninstall_only" == true ]]; then
    echo "Uninstall complete."
    exit 0
fi

claude plugins marketplace add --scope user "$REPO_ROOT"
install_plugins

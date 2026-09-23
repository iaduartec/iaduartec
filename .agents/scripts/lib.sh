#!/usr/bin/env bash
# Project Bridge shared helpers (portable: no absolute paths).
set -euo pipefail

# bridge_root: resolve the repository root holding this bridge install.
bridge_root() {
  if [[ -n "${PROJECT_BRIDGE_ROOT:-}" && -d "${PROJECT_BRIDGE_ROOT}" ]]; then
    printf '%s' "$PROJECT_BRIDGE_ROOT"
    return
  fi
  local dir
  dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd || true)"
  if [[ -n "$dir" && -d "$dir/.agents/project-bridge" ]]; then
    printf '%s' "$dir"
    return
  fi
  dir="$PWD"
  while [[ "$dir" != "/" ]]; do
    if [[ -d "$dir/.agents/project-bridge" ]]; then
      printf '%s' "$dir"
      return
    fi
    dir="$(dirname "$dir")"
  done
  git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$PWD"
}

bridge_py() {
  printf '%s/.agents/project-bridge/bridge.py' "$(bridge_root)"
}

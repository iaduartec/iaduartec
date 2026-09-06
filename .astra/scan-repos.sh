#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/home/ubuntu}"

printf "%-45s %-16s %-12s %s\n" \
  "REPOSITORY" "BRANCH" "DIRTY" "REMOTE"

printf '%*s\n' 110 '' | tr ' ' '-'

while IFS= read -r gitdir; do
  repo="$(dirname "$gitdir")"

  branch="$(git -C "$repo" branch --show-current 2>/dev/null || echo '-')"

  if [ -n "$(git -C "$repo" status --porcelain 2>/dev/null)" ]; then
    dirty="YES"
  else
    dirty="no"
  fi

  remote="$(git -C "$repo" remote get-url origin 2>/dev/null || echo '-')"

  printf "%-45s %-16s %-12s %s\n" \
    "$repo" "$branch" "$dirty" "$remote"

done < <(
  find "$ROOT" \
    -maxdepth 5 \
    -type d \
    -name .git \
    -prune \
    -print 2>/dev/null |
  sort
)

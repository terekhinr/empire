#!/usr/bin/env bash
# Локальный git-snapshot на VPS (без push, без секретов в коммите если в .gitignore).
set -uo pipefail
ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
cd "$ROOT" || exit 0
[[ -d .git ]] || exit 0
git add -A 2>/dev/null || true
git diff --cached --quiet 2>/dev/null && exit 0
git commit -m "vps-snapshot $(date -u +%Y%m%dT%H%M%SZ)" --no-verify 2>/dev/null || true

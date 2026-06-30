#!/bin/bash
# Блокирует старт/деплой, если критичные файлы пустые или подозрительно малы.
# Автовосстановление main.py из git или бэкапа Я.Диска (--auto-restore).
#
#   ./scripts/guard_critical_files.sh              # fail if bad
#   ./scripts/guard_critical_files.sh --warn       # log only
#   ./scripts/guard_critical_files.sh --auto-restore [--warn]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WARN_ONLY=0
AUTO_RESTORE=0

for arg in "$@"; do
  case "$arg" in
    --warn) WARN_ONLY=1 ;;
    --auto-restore) AUTO_RESTORE=1 ;;
  esac
done

log() { echo "[$(date -Iseconds)] guard: $*"; }

fail() {
  if [[ "$WARN_ONLY" -eq 1 ]]; then
    log "WARN $*"
    exit 0
  fi
  log "ERROR $*"
  exit 1
}

check_min_bytes() {
  local rel="$1" min="$2"
  local path="$ROOT/$rel"
  if [[ ! -f "$path" ]]; then
    fail "missing $rel"
  fi
  local size
  size="$(wc -c <"$path" | tr -d ' ')"
  if [[ "$size" -lt "$min" ]]; then
    fail "$rel is $size bytes (min $min) — похоже на обнуление/не тот файл"
  fi
}

restore_main_py_from_git() {
  [[ -d "$ROOT/.git" ]] || return 1
  local tmp
  tmp="$(mktemp)"
  if ! git -C "$ROOT" show HEAD:main.py >"$tmp" 2>/dev/null; then
    rm -f "$tmp"
    return 1
  fi
  local size
  size="$(wc -c <"$tmp" | tr -d ' ')"
  if [[ "$size" -lt 100000 ]]; then
    rm -f "$tmp"
    return 1
  fi
  cp -a "$ROOT/main.py" "$ROOT/main.py.corrupt.$(date -u +%Y%m%dT%H%M%SZ).bak" 2>/dev/null || true
  mv "$tmp" "$ROOT/main.py"
  log "restored main.py from git HEAD ($size bytes)"
  return 0
}

restore_main_py_from_yandex() {
  local remote="${RCLONE_REMOTE:-yandex}"
  local host
  host="$(hostname -s 2>/dev/null || echo vps)"
  local base="${RCLONE_BACKUP_REMOTE_PATH:-VPS-backup}/${host}"
  local tmp
  tmp="$(mktemp)"
  local day
  for day in "$(date +%Y-%m-%d)" latest; do
    if rclone cat "${remote}:${base}/${day}/empire/main.py" >"$tmp" 2>/dev/null; then
      local size
      size="$(wc -c <"$tmp" | tr -d ' ')"
      if [[ "$size" -ge 100000 ]]; then
        cp -a "$ROOT/main.py" "$ROOT/main.py.corrupt.$(date -u +%Y%m%dT%H%M%SZ).bak" 2>/dev/null || true
        mv "$tmp" "$ROOT/main.py"
        log "restored main.py from yandex:${base}/${day}/empire/main.py ($size bytes)"
        return 0
      fi
    fi
  done
  rm -f "$tmp"
  return 1
}

maybe_auto_restore_main() {
  local path="$ROOT/main.py"
  local size=0
  [[ -f "$path" ]] && size="$(wc -c <"$path" | tr -d ' ')"
  if [[ "$size" -ge 100000 ]] && grep -q 'async def main' "$path" 2>/dev/null; then
    return 0
  fi
  log "main.py повреждён ($size bytes) — пробую восстановить..."
  restore_main_py_from_git || restore_main_py_from_yandex || {
    fail "main.py не удалось восстановить (git/yandex)"
  }
}

if [[ "$AUTO_RESTORE" -eq 1 ]]; then
  maybe_auto_restore_main || true
fi

checks=(
  "main.py 100000"
  "gdepar_app.py 50000"
  "dashboard.py 5000"
  "web_app.py 3000"
  "empire_worker.py 3000"
  "gdepar_content.py 10000"
  "content_config.json 5000"
)

for item in "${checks[@]}"; do
  read -r rel min <<<"$item"
  check_min_bytes "$rel" "$min"
done

if ! grep -qE 'async def main|Оркестратор запущен' "$ROOT/main.py" 2>/dev/null; then
  fail "main.py не похож на оркестратор"
fi

exit 0
